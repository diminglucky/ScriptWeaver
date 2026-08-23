from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.kb.evaluation import EvalCase, evaluate_retriever, load_eval_cases
from src.shared.domain.schemas import RetrievedContext, SourceRef


def _result(source_id: str, chunk_id: str, score: float = 1.0) -> RetrievedContext:
    return RetrievedContext(
        text=chunk_id,
        source=SourceRef(
            source_id=source_id,
            path=f"/{source_id}.txt",
            chunk_id=chunk_id,
            score=score,
        ),
    )


class _FakeRetriever:
    async def retrieve(self, query: str, **kwargs):
        return [_result("wrong", "wrong-1"), _result("book-1", "chunk-1")]


def test_eval_case_requires_relevance_label():
    try:
        EvalCase.from_dict({"id": "q1", "query": "who?"})
    except ValueError as exc:
        assert "relevant" in str(exc)
    else:
        raise AssertionError("missing relevance labels must fail")


def test_load_eval_cases_supports_jsonl(tmp_path: Path):
    path = tmp_path / "cases.jsonl"
    path.write_text(
        json.dumps({
            "id": "q1",
            "query": "who?",
            "kb_types": ["reference"],
            "relevant_source_ids": ["book-1"],
        }) + "\n",
        encoding="utf-8",
    )
    cases = load_eval_cases(path)
    assert cases[0].case_id == "q1"
    assert cases[0].relevant_source_ids == frozenset({"book-1"})


def test_evaluate_retriever_reports_recall_and_latency():
    case = EvalCase(
        case_id="q1",
        query="who?",
        kb_types=["reference"],
        relevant_source_ids=frozenset({"book-1"}),
    )
    report = asyncio.run(evaluate_retriever(_FakeRetriever(), [case], ks=(1, 2)))
    assert report["cases"] == 1
    assert report["recall"] == {"Recall@1": 0.0, "Recall@2": 1.0}
    assert report["mrr"] == 0.5
    assert report["latency_ms"]["mean"] >= 0
