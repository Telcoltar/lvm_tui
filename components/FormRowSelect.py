from typing import Iterable, Union
from rich.console import RenderableType
from textual.app import ComposeResult
from textual.widgets import Static, Label, Select
from textual.containers import Container, Horizontal
from textual.validation import Regex, Validator

class FormRowSelect(Horizontal):

    def __init__(self, label: str, select_id: str, options: list[tuple[str, Union[str, tuple[str, ...]]]],
                 name: Union[str, None] = None, id: Union[str, None] = None,
                 classes: Union[str, None] = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.label = label
        self.select_id = select_id
        self.options = options
        self.add_class("horizontal_layout")

    def compose(self) -> ComposeResult:
        yield Container(Label(self.label), classes="form_label container")
        yield Container(
                Select(self.options, id=self.select_id),
                classes="form_input container"
            )