"""RunnerScreen — form for a leaf command, async execution, streaming output."""
from __future__ import annotations

import asyncio
import datetime
import json
import os
import pathlib
import shlex
from typing import AsyncIterator

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Button, Label, Input, Select, Checkbox
)
from textual.containers import Horizontal, Vertical, ScrollableContainer

from rucio_tui.command_parser import CommandNode, OptionDef, ArgumentDef
from rucio_tui.widgets.breadcrumb import Breadcrumb
from rucio_tui.widgets.output_panel import OutputPanel
from rucio_tui.voms import check_voms_proxy


class RunnerScreen(Screen):
    """Form + async runner for a leaf rucio command."""

    BINDINGS = [
        ("b", "go_back", "Back"),
        ("h", "go_home", "Home"),
        ("q", "quit_app", "Quit"),
        ("ctrl+r", "run_command", "Run"),
    ]

    DEFAULT_CSS = """
    RunnerScreen {
        layout: vertical;
    }
    RunnerScreen #scroll-area {
        height: 1fr;
        padding: 1 2;
    }
    RunnerScreen #cmd-header {
        height: auto;
        margin-bottom: 1;
    }
    RunnerScreen #cmd-title {
        text-style: bold;
        color: $accent;
    }
    RunnerScreen #cmd-desc {
        color: $text-muted;
        margin-bottom: 1;
    }
    RunnerScreen .section-label {
        color: $primary-lighten-1;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    RunnerScreen .field-row {
        height: auto;
        layout: horizontal;
        margin-bottom: 1;
        align: left middle;
    }
    RunnerScreen .field-label {
        width: 28;
        color: $text;
        content-align: left middle;
        height: 3;
    }
    RunnerScreen .field-label.required-label {
        color: $warning;
    }
    RunnerScreen Input {
        width: 1fr;
        height: 3;
    }
    RunnerScreen Select {
        width: 1fr;
        height: 3;
    }
    RunnerScreen #run-row {
        height: 3;
        layout: horizontal;
        margin-top: 1;
        align: left middle;
    }
    RunnerScreen #btn-run {
        min-width: 18;
    }
    RunnerScreen #run-status {
        margin-left: 2;
        color: $text-muted;
        content-align: left middle;
        height: 3;
    }
    RunnerScreen #output-file-row {
        height: auto;
        layout: horizontal;
        margin-top: 0;
        margin-bottom: 0;
        align: left middle;
    }
    RunnerScreen #output-file-label {
        width: 14;
        color: $text-muted;
        content-align: left middle;
        height: 3;
    }
    RunnerScreen #output-file {
        width: 1fr;
        height: 3;
    }
    RunnerScreen #nav-buttons {
        height: 3;
        layout: horizontal;
        align: center middle;
        background: $surface-darken-1;
        border-top: solid $primary-darken-2;
        padding: 0 2;
    }
    RunnerScreen #nav-buttons Button {
        margin: 0 2;
        min-width: 14;
    }
    """

    def __init__(self, node: CommandNode, **kwargs) -> None:
        super().__init__(**kwargs)
        self._node = node
        self._executing = False

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with ScrollableContainer(id="scroll-area"):
            yield Breadcrumb(self._node.path, id="breadcrumb")

            with Vertical(id="cmd-header"):
                cmd_str = " ".join(self._node.path)
                yield Label(f"$ {cmd_str}", id="cmd-title")
                if self._node.description:
                    yield Label(self._node.description, id="cmd-desc")

            # ---- Options ----
            if self._node.options:
                yield Label("── Options ──────────────────────", classes="section-label")
                for opt in self._node.options:
                    yield from self._make_option_field(opt)

            # ---- Arguments ----
            if self._node.arguments:
                yield Label("── Arguments ────────────────────", classes="section-label")
                for arg in self._node.arguments:
                    yield from self._make_argument_field(arg)

            with Horizontal(id="run-row"):
                yield Button("▶  Run Command", id="btn-run", variant="success")
                yield Label("", id="run-status")

            with Horizontal(id="output-file-row"):
                yield Label("Output file:", id="output-file-label")
                yield Input(
                    placeholder="e.g. output.txt or output.json (optional)",
                    id="output-file",
                )

            yield OutputPanel(id="output-panel")

        with Horizontal(id="nav-buttons"):
            yield Button("◀ Back", id="btn-back", variant="default")
            yield Button("⌂ Home", id="btn-home", variant="default")

        yield Footer()

    def _make_option_field(self, opt: OptionDef):
        primary_flag = next((f for f in opt.flags if f.startswith("--")), opt.flags[0])
        label_text = primary_flag
        if opt.required:
            label_text += " [red]*[/red]"

        input_id = f"opt_{primary_flag.lstrip('-').replace('-', '_')}"

        # Boolean flag options (no value argument) → render as Checkbox
        if opt.is_flag:
            with Horizontal(classes="field-row"):
                yield Label(
                    label_text,
                    classes="field-label",
                )
                yield Checkbox(
                    opt.help or primary_flag,
                    id=input_id,
                    value=False,
                )
            return

        # Prefer the explicit choices list; fall back to pipe-separated metavar
        # (the fallback preserves compatibility with hand-crafted CommandNodes in tests)
        import re
        enum_choices = opt.choices
        if enum_choices is None:
            choices_match = re.match(r"^([a-z][a-z0-9_]*(?:\|[a-z][a-z0-9_]*)+)$", opt.metavar)
            enum_choices = opt.metavar.split("|") if choices_match else None

        with Horizontal(classes="field-row"):
            yield Label(
                label_text,
                classes="field-label" + (" required-label" if opt.required else ""),
            )
            if enum_choices:
                options = [(c, c) for c in enum_choices]
                yield Select(
                    options=options,
                    id=input_id,
                    allow_blank=not opt.required,
                    prompt=f"Select {primary_flag}…",
                )
            else:
                placeholder = opt.default or f"{opt.metavar}"
                yield Input(
                    placeholder=placeholder,
                    id=input_id,
                )

    def _make_argument_field(self, arg: ArgumentDef):
        label_text = arg.name
        if arg.required:
            label_text += " [red]*[/red]"
        input_id = f"arg_{arg.name.lower().replace('-', '_')}"
        with Horizontal(classes="field-row"):
            yield Label(
                label_text,
                classes="field-label" + (" required-label" if arg.required else ""),
            )
            yield Input(
                placeholder=arg.metavar,
                id=input_id,
            )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-run":
            self.run_worker(self._execute(), exclusive=True, exit_on_error=False)
        elif event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-home":
            self.action_go_home()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Pressing Enter on the last required input triggers Run Command."""
        if event.input.id == self._last_required_input_id() and not self._executing:
            self.run_worker(self._execute(), exclusive=True, exit_on_error=False)

    def on_breadcrumb_crumb_clicked(self, event: Breadcrumb.CrumbClicked) -> None:
        """Navigate back to the clicked ancestor path level."""
        pops = len(self._node.path) - 1 - event.index
        for _ in range(pops):
            if len(self.app.screen_stack) > 2:
                self.app.pop_screen()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_go_home(self) -> None:
        while len(self.app.screen_stack) > 2:
            self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def action_run_command(self) -> None:
        if not self._executing:
            self.run_worker(self._execute(), exclusive=True, exit_on_error=False)

    async def _execute(self) -> None:
        output: OutputPanel = self.query_one("#output-panel", OutputPanel)
        status_label: Label = self.query_one("#run-status", Label)
        run_btn: Button = self.query_one("#btn-run", Button)

        output.reset()
        self._executing = True
        run_btn.disabled = True
        status_label.update("[yellow]⟳ Running…[/yellow]")

        cmd = self._build_command()
        if cmd is None:
            output.stream_line("[red]✗ Required fields are missing.[/red]")
            output.show_error()
            self._executing = False
            run_btn.disabled = False
            status_label.update("")
            return

        voms = await check_voms_proxy()
        if not voms.valid:
            output.stream_line(f"[red]✗ VOMS proxy error: {voms.message}[/red]")
            output.show_error()
            self._executing = False
            run_btn.disabled = False
            status_label.update("[red]✗ No valid VOMS proxy[/red]")
            return

        output.stream_line(f"[dim]$ {shlex.join(cmd)}[/dim]")
        output.stream_line("")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert proc.stdout is not None
            async for line in proc.stdout:
                output.stream_line(line.decode(errors="replace").rstrip())
            returncode = await proc.wait()
        except Exception as exc:
            output.stream_line(f"[red]✗ Error: {exc}[/red]")
            output.show_error()
            self._executing = False
            run_btn.disabled = False
            status_label.update("[red]✗ Error[/red]")
            return

        if returncode == 0:
            status_label.update("[green]✓ Done[/green]")
            output.show_success()
        else:
            status_label.update(f"[red]✗ Exit {returncode}[/red]")
            output.show_error()

        await self._save_output_if_requested(output, cmd, returncode)

        self._executing = False
        run_btn.disabled = False

    async def _save_output_if_requested(
        self, output: OutputPanel, cmd: list[str], exit_code: int
    ) -> None:
        """Save output to a file if the user specified one."""
        try:
            path_input = self.query_one("#output-file", Input)
        except Exception:
            return
        path = os.path.expandvars(path_input.value.strip())
        if not path:
            return

        p = pathlib.Path(path)
        text = output.get_plain_text()
        try:
            if p.suffix.lower() == ".json":
                data = {
                    "command": shlex.join(cmd),
                    "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                    "exit_code": exit_code,
                    "output": text.splitlines(),
                }
                p.write_text(json.dumps(data, indent=2))
            else:
                p.write_text(text)
            self.notify(f"Output saved to {path}", severity="information")
        except OSError as exc:
            self.notify(f"Could not save output: {exc}", severity="error")

    def _last_required_input_id(self) -> str | None:
        """
        Return the widget ID of the last required *text* input in form order
        (options first, then positional arguments).  Returns None if there are
        no required text inputs.
        """
        import re

        last_id: str | None = None

        for opt in self._node.options:
            if not opt.required:
                continue
            # Flag (checkbox) options never take a text value — skip them.
            if opt.is_flag:
                continue
            primary_flag = next((f for f in opt.flags if f.startswith("--")), opt.flags[0])
            # Only counts if it renders as an Input (not a Select).
            enum_choices = opt.choices
            if enum_choices is None:
                choices_match = re.match(
                    r"^([a-z][a-z0-9_]*(?:\|[a-z][a-z0-9_]*)+)$", opt.metavar
                )
                enum_choices = opt.metavar.split("|") if choices_match else None
            if not enum_choices:
                last_id = f"opt_{primary_flag.lstrip('-').replace('-', '_')}"

        for arg in self._node.arguments:
            if arg.required:
                last_id = f"arg_{arg.name.lower().replace('-', '_')}"

        return last_id

    def _build_command(self) -> list[str] | None:
        """Assemble the rucio command from form fields; return None if validation fails."""
        cmd = list(self._node.path)  # e.g. ["rucio", "did", "add"]
        top_dir = os.environ.get("TopDir", "").rstrip("/")
        candidate = f"{top_dir}/rucio" if top_dir else ""
        if candidate and os.path.exists(candidate):
            cmd[0] = candidate
        import re

        for opt in self._node.options:
            primary_flag = next((f for f in opt.flags if f.startswith("--")), opt.flags[0])
            input_id = f"opt_{primary_flag.lstrip('-').replace('-', '_')}"
            try:
                widget = self.query_one(f"#{input_id}")
            except Exception:
                continue

            if isinstance(widget, Checkbox):
                # Flag options: append the flag only when checked; no value argument.
                if widget.value:
                    cmd.append(primary_flag)
            elif isinstance(widget, Select):
                val = widget.value
                if val is not None and str(val) != Select.BLANK:
                    cmd += [primary_flag, str(val)]
                elif opt.required:
                    return None
            elif isinstance(widget, Input):
                val = os.path.expandvars(widget.value.strip())
                if val:
                    cmd += [primary_flag, val]
                elif opt.required:
                    return None

        for arg in self._node.arguments:
            input_id = f"arg_{arg.name.lower().replace('-', '_')}"
            try:
                widget = self.query_one(f"#{input_id}", Input)
            except Exception:
                if arg.required:
                    return None
                continue
            val = os.path.expandvars(widget.value.strip())
            if val:
                cmd.append(val)
            elif arg.required:
                return None

        return cmd
