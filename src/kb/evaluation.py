"""Offline evaluation helpers for the RAG retriever.

The evaluation set must provide the expected source_id or chunk_id for each
query. This module deliberately does not infer labels from generated answers.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from src.services.rag_service.core.embedding_hub import DEFAULT_MODEL_NAME, EmbeddingHub
from src.services.rag_service.core.index_hub import IndexHub
from src.services.rag_service.core.retrievers import CreativeRetriever


@dataclass(frozen=True)
class EvalCase:
    """One query with human- or benchmark-labeled relevant records."""

    case_id: str
    query: str
    kb_types: list[str]
    project_id: str | None = None
    relevant_source_ids: frozenset[str] = field(default_factory=frozenset)
    relevant_chunk_ids: frozenset[str] = field(default_factory=frozenset)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, line_number: int = 0) -> "EvalCase":
        prefix = f"line {line_number}: " if line_number else ""
        query = str(raw.get("query", "")).strip()
        source_ids = frozenset(str(x) for x in raw.get("relevant_source_ids", []) if str(x))
        chunk_ids = frozenset(str(x) for x in raw.get("relevant_chunk_ids", []) if str(x))
        if not query:
            raise ValueError(f"{prefix}query is required")
        if not source_ids and not chunk_ids:
            raise ValueError(f"{prefix}at least one relevant_source_ids or relevant_chunk_ids is required")
        kb_types = [str(x) for x in raw.get("kb_types", ["reference"]) if str(x)]
        if not kb_types:
            raise ValueError(f"{prefix}kb_types must not be empty")
        return cls(
            case_id=str(raw.get("id") or raw.get("case_id") or f"case-{line_number}"),
            query=query,
            kb_types=kb_types,
            project_id=str(raw["project_id"]) if raw.get("project_id") is not None else None,
            relevant_source_ids=source_ids,
            relevant_chunk_ids=chunk_ids,
            tags=[str(x) for x in raw.get("tags", []) if str(x)],
        )


def load_eval_cases(path: Path) -> list[EvalCase]:
    """Load JSONL cases, with a JSON array accepted for convenience."""
    raw_text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(raw_text)
        if not isinstance(payload, list):
            raise ValueError("JSON evaluation set must contain an array")
        rows = [(index + 1, item) for index, item in enumerate(payload)]
    else:
        rows = []
        for line_number, line in enumerate(raw_text.splitlines(), 1):
            if not line.strip():
                continue
            item = json.loads(line)
            rows.append((line_number, item))
    cases = [EvalCase.from_dict(item, line_number=line_number) for line_number, item in rows]
    if not cases:
        raise ValueError("evaluation set must contain at least one case")
    return cases


def _case_hit(result: Any, case: EvalCase) -> bool:
    source = getattr(result, "source", None)
    source_id = str(getattr(source, "source_id", ""))
    chunk_id = str(getattr(source, "chunk_id", ""))
    return (
        chunk_id in case.relevant_chunk_ids
        or source_id in case.relevant_source_ids
    )


def recall_at_k(results: list[Any], case: EvalCase, k: int) -> bool:
    """Return whether a relevant source/chunk appears in the first k hits."""
    if k <= 0:
        raise ValueError("k must be positive")
    return any(_case_hit(result, case) for result in results[:k])


def reciprocal_rank(results: list[Any], case: EvalCase) -> float:
    """Return reciprocal rank, or zero when no relevant result was retrieved."""
    for rank, result in enumerate(results, 1):
        if _case_hit(result, case):
            return 1.0 / rank
    return 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percentile / 100) * len(ordered)) - 1))
    return ordered[index]


async def evaluate_retriever(
    retriever: Any,
    cases: Iterable[EvalCase],
    *,
    ks: tuple[int, ...] = (1, 3, 5, 6, 8),
    min_score: float = 0.0,
) -> dict[str, Any]:
    """Evaluate Recall@k, MRR and retrieval latency for a retriever."""
    normalized_ks = tuple(sorted(set(int(k) for k in ks)))
    if not normalized_ks or normalized_ks[0] <= 0:
        raise ValueError("ks must contain positive integers")

    case_list = list(cases)
    per_case: list[dict[str, Any]] = []
    latencies: list[float] = []
    for case in case_list:
        started = time.perf_counter()
        results = await retriever.retrieve(
            case.query,
            kb_types=case.kb_types,
            project_id=case.project_id,
            top_k=max(normalized_ks),
            min_score=min_score,
            tags=case.tags,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies.append(elapsed_ms)
        per_case.append({
            "id": case.case_id,
            "retrieved": len(results),
            "reciprocal_rank": reciprocal_rank(results, case),
            "recall": {str(k): recall_at_k(results, case, k) for k in normalized_ks},
        })

    count = len(case_list)
    recall = {
        f"Recall@{k}": round(
            sum(bool(item["recall"][str(k)]) for item in per_case) / count,
            4,
        ) if count else 0.0
        for k in normalized_ks
    }
    return {
        "cases": count,
        "recall": recall,
        "mrr": round(statistics.mean(item["reciprocal_rank"] for item in per_case), 4) if per_case else 0.0,
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "p50": round(_percentile(latencies, 50), 2),
            "p95": round(_percentile(latencies, 95), 2),
        },
        "details": per_case,
    }


def _parse_ks(raw: str) -> tuple[int, ...]:
    try:
        ks = tuple(int(value.strip()) for value in raw.split(",") if value.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ks must be comma-separated positive integers") from exc
    if not ks or any(k <= 0 for k in ks):
        raise argparse.ArgumentTypeError("ks must be comma-separated positive integers")
    return ks


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    cases = load_eval_cases(Path(args.eval_set))
    hub = IndexHub(index_root=Path(args.index_dir), embedding_model=args.embedding_model)
    try:
        retriever = CreativeRetriever(
            hub=hub,
            embedder=EmbeddingHub(args.embedding_model),
        )
        return await evaluate_retriever(retriever, cases, ks=args.ks, min_score=args.min_score)
    finally:
        hub.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG Recall@k and retrieval latency.")
    parser.add_argument("--eval-set", required=True, help="JSONL/JSON file with labeled retrieval cases")
    parser.add_argument("--index-dir", default="index", help="RAG index root")
    parser.add_argument("--embedding-model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--ks", type=_parse_ks, default=(1, 3, 5, 6, 8))
    parser.add_argument("--min-score", type=float, default=0.0)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_run(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
