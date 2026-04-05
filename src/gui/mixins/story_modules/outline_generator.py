"""Story outline generator aggregator mixin."""

from src.clients.deepseek_client import DeepSeekClient  # backward-compat for tests/monkey-patching

from .outline_generate_mixin import OutlineGenerateMixin
from .outline_quality_mixin import OutlineQualityMixin
from .outline_section_generate_mixin import OutlineSectionGenerateMixin
from .outline_section_utils_mixin import OutlineSectionUtilsMixin


class OutlineGeneratorMixin(
    OutlineQualityMixin,
    OutlineGenerateMixin,
    OutlineSectionGenerateMixin,
    OutlineSectionUtilsMixin,
):
    """Compose outline generation, section generation, and parsing utilities."""

    pass
