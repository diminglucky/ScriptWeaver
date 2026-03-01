"""Entry color behavior extracted from settings mixin."""

import logging

from ...theme import Theme

logger = logging.getLogger(__name__)


class EntryColorMixin:
    """Maintain stable entry colors on focus changes."""

    def _fix_entry_colors(self, entry_widget):
        def force_dark_colors(event=None):
            try:
                entry_widget.config(
                    bg=Theme.BG_TERTIARY,
                    fg=Theme.TEXT_PRIMARY,
                    insertbackground=Theme.TEXT_PRIMARY,
                    selectbackground=Theme.PRIMARY,
                    selectforeground=Theme.TEXT_PRIMARY,
                    disabledbackground=Theme.BG_TERTIARY,
                    disabledforeground=Theme.TEXT_DISABLED,
                    readonlybackground=Theme.BG_TERTIARY,
                )
                entry_widget.after(
                    1,
                    lambda: entry_widget.config(
                        bg=Theme.BG_TERTIARY,
                        fg=Theme.TEXT_PRIMARY,
                        insertbackground=Theme.TEXT_PRIMARY,
                    ),
                )
                entry_widget.after(
                    10,
                    lambda: entry_widget.config(
                        bg=Theme.BG_TERTIARY,
                        fg=Theme.TEXT_PRIMARY,
                        insertbackground=Theme.TEXT_PRIMARY,
                    ),
                )
            except Exception as e:
                logger.debug("force entry color failed: %s", e)

        entry_widget.bind("<FocusIn>", force_dark_colors)
        entry_widget.bind("<FocusOut>", force_dark_colors)
        entry_widget.bind("<Button-1>", force_dark_colors)
        entry_widget.bind("<KeyPress>", force_dark_colors)
        entry_widget.bind("<KeyRelease>", force_dark_colors)
        entry_widget.bind("<ButtonRelease-1>", force_dark_colors)
        force_dark_colors()
