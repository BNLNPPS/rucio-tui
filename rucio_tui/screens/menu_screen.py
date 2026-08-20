"""MenuScreen — shows a navigable list of commands at a given level."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Label
from textual.containers import Horizontal, Vertical

from rucio_tui.command_parser import CommandNode, get_children
from rucio_tui.widgets.breadcrumb import Breadcrumb
from rucio_tui.widgets.command_list import CommandList


class MenuScreen(Screen):
    """Displays a command group's children as a navigable list."""

    BINDINGS = [
        ("b", "go_back", "Back"),
        ("h", "go_home", "Home"),
        ("q", "quit_app", "Quit"),
    ]

    DEFAULT_CSS = """
    MenuScreen {
        layout: vertical;
    }
    MenuScreen #title-bar {
        height: 3;
        background: $primary-darken-3;
        align: center middle;
        border-bottom: solid $primary;
    }
    MenuScreen #title-bar Label {
        color: $accent;
        text-style: bold;
        text-align: center;
    }
    MenuScreen #content {
        height: 1fr;
        padding: 1 2;
    }
    MenuScreen #nav-buttons {
        height: 3;
        layout: horizontal;
        align: center middle;
        background: $surface-darken-1;
        border-top: solid $primary-darken-2;
        padding: 0 2;
    }
    MenuScreen #nav-buttons Button {
        margin: 0 2;
        min-width: 14;
    }
    MenuScreen #hint {
        height: 1;
        color: $text-muted;
        text-align: center;
        padding: 0 2;
    }
    """

    def __init__(self, node: CommandNode, is_root: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._node = node
        self._is_root = is_root

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        # Resolve children so is_group flags are accurate
        children = get_children(self._node)

        with Vertical(id="content"):
            yield Breadcrumb(self._node.path, id="breadcrumb")
            yield Label(
                f"[bold]{self._node.description}[/bold]" if self._node.description else "",
                id="hint",
            )
            yield CommandList(children, id="command-list")

        with Horizontal(id="nav-buttons"):
            if not self._is_root:
                yield Button("◀ Back", id="btn-back", variant="default")
            yield Button("⌂ Home", id="btn-home", variant="default")

        yield Footer()

    def on_mount(self) -> None:
        self.query_one(CommandList).focus_list()

    def on_command_list_selected(self, event: CommandList.Selected) -> None:
        node = event.node
        if node.is_group:
            self.app.push_screen(MenuScreen(node))
        else:
            from rucio_tui.screens.runner_screen import RunnerScreen
            self.app.push_screen(RunnerScreen(node))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-home":
            self.action_go_home()

    def on_breadcrumb_crumb_clicked(self, event: Breadcrumb.CrumbClicked) -> None:
        """Navigate back to the clicked ancestor path level."""
        pops = len(self._node.path) - 1 - event.index
        for _ in range(pops):
            if len(self.app.screen_stack) > 2:
                self.app.pop_screen()

    def action_go_back(self) -> None:
        if not self._is_root:
            self.app.pop_screen()

    def action_go_home(self) -> None:
        # Pop all screens until only the default screen + root MenuScreen remain
        while len(self.app.screen_stack) > 2:
            self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()
