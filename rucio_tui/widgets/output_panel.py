"""OutputPanel widget — selectable plain-text output pane for command output."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import TextArea


class OutputPanel(Widget):
    """
    A read-only TextArea that streams command output.

    Supports native mouse selection and Ctrl+C copy.
    Border colour changes to red on error.
    """

    DEFAULT_CSS = """
    OutputPanel {
        border: round $success;
        height: 1fr;
        min-height: 8;
        margin-top: 1;
    }
    OutputPanel.error {
        border: round $error;
    }
    OutputPanel > TextArea {
        height: 1fr;
        background: $surface-darken-1;
        color: $text;
        border: none;
        padding: 0 1;
    }
    OutputPanel > TextArea:focus {
        border: none;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._lines: list[str] = []

    def compose(self) -> ComposeResult:
        yield TextArea(
            "",
            read_only=True,
            show_line_numbers=False,
            theme="css",
            id="output-text",
        )

    def stream_line(self, text: str, style: str = "") -> None:
        """Append a line of output, stripping Rich markup to plain text."""
        from rich.text import Text as RichText
        try:
            plain = RichText.from_markup(text).plain
        except Exception:
            plain = text
        self._lines.append(plain)
        ta = self.query_one(TextArea)
        ta.insert(plain + "\n", location=ta.document.end)
        ta.scroll_end(animate=False)

    def get_plain_text(self) -> str:
        """Return all accumulated plain-text output lines joined by newlines."""
        return "\n".join(self._lines)

    def show_error(self) -> None:
        self.add_class("error")

    def show_success(self) -> None:
        self.remove_class("error")

    def reset(self) -> None:
        """Clear output and reset to success styling."""
        self._lines.clear()
        ta = self.query_one(TextArea)
        ta.load_text("")
        self.show_success()
