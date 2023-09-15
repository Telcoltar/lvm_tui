from typing import Iterable, Union
from rich.console import RenderableType
from textual.app import ComposeResult
from textual.widgets import Static, Label, Input
from textual.containers import Container, Horizontal
from textual.validation import Regex, Validator

class FormRow(Horizontal):

    def __init__(self, label: str, input_id: str, name: Union[str, None] = None, id: Union[str, None] = None, classes: Union[str, None] = None,
                 validators: Union[Validator, Iterable[Validator], None] = None) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.validators = validators
        self.label = label
        self.input_id = input_id
        self.add_class("horizontal_layout")

    def compose(self) -> ComposeResult:
        yield Container(Label(self.label), classes="form_label container")
        yield Container(Input(validators=self.validators, id=self.input_id), classes="form_input container")