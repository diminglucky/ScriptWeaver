"""Story mixin exports with lazy composition."""

__all__ = ["StoryMixin"]


def __getattr__(name):
    if name != "StoryMixin":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from .config_handler import StoryConfigMixin
    from .outline_generator import OutlineGeneratorMixin
    from .story_generator import StoryGeneratorMixin
    from .ui_builder import StoryUIBuilderMixin

    class StoryMixin(
        StoryUIBuilderMixin,
        OutlineGeneratorMixin,
        StoryGeneratorMixin,
        StoryConfigMixin,
    ):
        """Story feature mixin."""

    globals()["StoryMixin"] = StoryMixin
    return StoryMixin
