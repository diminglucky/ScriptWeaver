from src.gui.mixins.story_modules.outline_generate_mixin import OutlineGenerateMixin


def test_missing_rag_dependencies_are_recoverable():
    error = RuntimeError(
        "知识库依赖缺失，暂时无法构建索引。\n"
        "缺失包: chromadb, sentence-transformers"
    )

    assert OutlineGenerateMixin._is_missing_rag_dependency_error(error)


def test_unrelated_rag_errors_are_not_suppressed():
    assert not OutlineGenerateMixin._is_missing_rag_dependency_error(
        RuntimeError("索引文件损坏")
    )
