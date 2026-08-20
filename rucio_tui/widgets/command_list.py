"""CommandList widget — a styled list of CommandNode items."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import ListView, ListItem, Label

from rucio_tui.command_parser import CommandNode


class CommandList(Widget):
    """
    A scrollable list of commands with name + description columns.
    Posts a CommandList.Selected message when the user activates an item.
    """

    DEFAULT_CSS = """
    CommandList {
        height: 1fr;
        border: none;
    }
    CommandList ListView {
        height: 1fr;
        border: none;
        background: transparent;
    }
    CommandList ListItem {
        layout: horizontal;
        padding: 0 1;
        height: 2;
    }
    CommandList ListItem .cmd-name {
        width: 22;
        color: $success;
        text-style: bold;
        content-align: left middle;
        height: 2;
    }
    CommandList ListItem .cmd-desc {
        color: $text-muted;
        content-align: left middle;
        height: 2;
        width: 1fr;
    }
    CommandList ListItem.--highlight .cmd-name {
        color: $accent;
    }
    CommandList ListItem.--highlight .cmd-desc {
        color: $text;
    }
    """

    class Selected(Message):
        """Posted when the user selects a command."""
        def __init__(self, node: CommandNode) -> None:
            super().__init__()
            self.node = node

    def __init__(self, nodes: list[CommandNode], **kwargs) -> None:
        super().__init__(**kwargs)
        self._command_nodes = nodes

    def compose(self) -> ComposeResult:
        items: list[ListItem] = []
        for i, node in enumerate(self._command_nodes):
            arrow = "▶ " if node.is_group else "  "
            item = ListItem(
                Label(f"{arrow}{node.name}", classes="cmd-name"),
                Label(node.description, classes="cmd-desc"),
                name=str(i),  # store index as name for lookup
            )
            items.append(item)
        yield ListView(*items)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        event.stop()
        idx = int(event.item.name)
        node = self._command_nodes[idx]
        self.post_message(self.Selected(node))

    def focus_list(self) -> None:
        self.query_one(ListView).focus()
