"""Breadcrumb widget — shows the current navigation path."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label
from textual.containers import Horizontal


class Breadcrumb(Widget):
    """
    Renders a path like  rucio  ›  did  ›  add.

    All segments except the last (current) are rendered as clickable
    ``CrumbLink`` widgets.  Clicking one posts a ``Breadcrumb.CrumbClicked``
    message carrying the zero-based *index* of the clicked segment.
    """

    class CrumbClicked(Message):
        """Posted when a non-current (parent) breadcrumb segment is clicked."""

        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    DEFAULT_CSS = """
    Breadcrumb {
        height: 1;
        layout: horizontal;
        background: $primary-darken-2;
        padding: 0 2;
        color: $text-muted;
    }
    Breadcrumb Label {
        color: $text-muted;
    }
    Breadcrumb Label.crumb-current {
        color: $text;
        text-style: bold;
    }
    Breadcrumb Label.crumb-sep {
        color: $primary-lighten-2;
        margin: 0 1;
    }
    Breadcrumb CrumbLink {
        color: $primary-lighten-1;
    }
    Breadcrumb CrumbLink:hover {
        color: $accent;
        text-style: underline;
    }
    """

    def __init__(self, path: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self._path = path

    def compose(self) -> ComposeResult:
        yield from self._make_widgets()

    def update_path(self, path: list[str]) -> None:
        """Rebuild the breadcrumb for a new path."""
        self._path = path
        self.remove_children()
        self.mount(*list(self._make_widgets()))

    def _make_widgets(self):
        for i, segment in enumerate(self._path):
            is_last = i == len(self._path) - 1
            if is_last:
                yield Label(segment, classes="crumb-current")
            else:
                yield CrumbLink(segment, index=i)
            if not is_last:
                yield Label("›", classes="crumb-sep")


class CrumbLink(Label):
    """
    A non-current breadcrumb segment rendered as a clickable link.
    Posts ``Breadcrumb.CrumbClicked`` with its zero-based path index on click.
    """

    def __init__(self, text: str, *, index: int, **kwargs) -> None:
        super().__init__(text, **kwargs)
        self._index = index

    def on_click(self) -> None:
        self.post_message(Breadcrumb.CrumbClicked(self._index))
