from __future__ import annotations

import os
from pathlib import Path
from typing import List

import typer
try:
	from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
	def load_dotenv(*args, **kwargs):
		return False
from rich.console import Console
from rich.markdown import Markdown

from src.clients.deepseek_client import DeepSeekClient
from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
from src.kb.search import KnowledgeBaseSearcher, SearchConfig

app = typer.Typer(help="创作知乎故事：知识库检索增强 + DeepSeek 生成")
console = Console()


@app.command()
def ingest(
	data_root: str = typer.Argument("data/raw", help="包含爬取文章的根目录"),
	index_dir: str = typer.Option("index", help="索引保存目录"),
	embedding_model: str = typer.Option("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
	max_chars: int = typer.Option(800),
	overlap: int = typer.Option(120),
):
	"""从本地文本构建 Chroma 向量索引。"""
	cfg = IngestConfig(data_root=Path(data_root), index_dir=Path(index_dir), embedding_model_name=embedding_model, max_chars=max_chars, overlap=overlap)
	KnowledgeBaseIngestor(cfg).build()


@app.command()
def generate(
	query: str = typer.Argument(..., help="你的创作要求/主题"),
	index_dir: str = typer.Option("index", help="索引目录"),
	top_k: int = typer.Option(6, help="检索片段数"),
	temperature: float = typer.Option(0.7),
	model: str | None = typer.Option(None, help="覆盖默认模型"),
	show_context: bool = typer.Option(False, help="是否打印检索到的上下文"),
):
	"""基于知识库检索，调用 DeepSeek 生成知乎风格的故事。"""
	load_dotenv()
	searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(index_dir), top_k=top_k))
	results = searcher.search(query, top_k)
	contexts: List[str] = [c for c, _score, _meta in results]
	if show_context:
		console.rule("Retrieved Context")
		for i, (c, score, meta) in enumerate(results, 1):
			console.print(f"[bold cyan]{i}.[/] score={score:.3f} source={meta[0]}#{meta[1]}")
			console.print(Markdown(c[:1000]))
			console.print()

	client = DeepSeekClient(model=model)
	prompt = _build_prompt(query, contexts)
	console.rule("DeepSeek Output")
	output = client.chat([
		{"role": "system", "content": "你是资深知乎创作者，擅长结合资料写出有观点、有结构、可读性强的中文故事。请引用知识库信息，但不要直接复制粘贴，需进行改写与整合。"},
		{"role": "user", "content": prompt},
	], temperature=temperature)
	console.print(Markdown(output))


def _build_prompt(requirement: str, contexts: List[str]) -> str:
	ctx = "\n\n".join(f"【资料{idx+1}】\n{c}" for idx, c in enumerate(contexts))
	return (
		"请基于以下资料，创作一篇知乎风格的故事/回答。\n"
		"要求：\n"
		"- 语言自然口语化，但保持逻辑清晰；\n"
		"- 有小标题与分段；\n"
		"- 开头引人、结尾有观点或反思；\n"
		"- 若资料冲突，请以更可靠/更一致的为准；\n"
		f"- 创作主题/需求：{requirement}\n\n"
		f"资料：\n{ctx}"
	)


if __name__ == "__main__":
	app()

