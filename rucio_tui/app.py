"""
app.py — RucioTuiApp: the main Textual application.
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import LoadingIndicator, Label
from textual.containers import Center, Middle

from rucio_tui.command_parser import build_root


class _SplashScreen:
    """Used as a sentinel; actual splash is inline in on_mount."""


class RucioTuiApp(App):
    """
    rucio-tui — browse and run rucio commands interactively.

    Keyboard shortcuts available on every screen:
        b  →  Go Back
        h  →  Go Home (root menu)
        q  →  Quit
    """

    TITLE = "rucio-tui"
    SUB_TITLE = "Interactive Rucio Command Explorer"
    CSS_PATH = "styles/app.tcss"

    def compose(self) -> ComposeResult:
        with Middle():
            with Center():
                yield Label(
                    "[bold cyan]rucio-tui[/bold cyan]\n"
                    "[dim]Loading command tree…[/dim]",
                    id="splash-label",
                )
                yield LoadingIndicator(id="splash-spinner")

    def on_mount(self) -> None:
        """Build the command tree then push the home MenuScreen."""
        self.run_worker(self._load_and_launch(), exclusive=True, thread=False)

    async def _load_and_launch(self) -> None:
        from rucio_tui.screens.menu_screen import MenuScreen
        root = build_root()
        await self.push_screen(MenuScreen(root, is_root=True))
