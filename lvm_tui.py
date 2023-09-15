from time import monotonic
from typing import Optional

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.reactive import reactive
from textual.containers import ScrollableContainer, Container, Vertical, Horizontal, Center
from textual.widgets import Button, Footer, Header, Static, Label, DataTable, Input, Select
from textual.widget import Widget
from textual.containers import Grid
from textual.binding import Binding, BindingType
from lvm_lib import OPTIONS_LVS, create_lvs, create_thin_lv, create_thin_snapshot, format_entry, get_lvs, NAMES_LVS, Size, get_vgs, remove_lvs
from textual.screen import ModalScreen
from textual.validation import Integer, Regex
from textual.coordinate import Coordinate
from components.FormRow import FormRow
from components.FormRowSelect import FormRowSelect

class ConfirmDelete(ModalScreen):

    def __init__(self, vg: str, lv: str, name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None) -> None:
        super().__init__(name, id, classes)
        self.vg = vg
        self.lv = lv

    def compose(self) -> ComposeResult:
        v = Vertical(
            Label(f"Do you really want to delete \n{self.vg}/{self.lv}?"),
            Horizontal(
                Button("Yes", variant="success", id="yes", classes="form_button"),
                Button("No", variant="primary", id="no", classes="form_button"),
            classes="horizontal_layout"),
            id="dialog"
        )
        v.border_title = "Delete logical volume"
        yield v

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.pop_screen()
        if event.button.id == "yes":
            table = self.app.query_one(DataTable)
            if table.cursor_row is not None:
                remove_lvs(self.lv, self.vg)
                self.app.query_one(Data).update()

class AddSnapshot(ModalScreen):

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, vg: str, lv: str, name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None) -> None:
        super().__init__(name, id, classes)
        self.vg = vg
        self.lv = lv

    def action_cancel(self) -> None:
        """An action to cancel the dialog."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        v = Vertical(
                FormRow("Name", "input_name",
                        validators=Regex("[A-Za-z0-9-]+",failure_description="Only alphanumeric chars are allowed"),
                        ),
                Horizontal(
                    Button("Add", variant="success", id="add", classes="form_button"),
                    Button("Cancel", variant="primary", id="cancel", classes="form_button"),
                classes="horizontal_layout"),
            id="dialog"
        )
        v.border_title = "Add snapshot"
        yield v

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            name_input = self.query_one("#input_name", expect_type=Input)
            validation = name_input.validate(name_input.value)
            if validation:
                if validation.is_valid:
                    create_thin_snapshot(name_input.value, self.vg, self.lv)
        self.app.pop_screen()
        self.app.query_one(Data).update()

class AddLv(ModalScreen):
    """Screen with a dialog to quit."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, name: Optional[str] = None, id: Optional[str] = None,
                 classes: Optional[str] = None, thin: Optional[bool] = False) -> None:
        super().__init__(name, id, classes)
        self.thin = thin

    def action_cancel(self) -> None:
        """An action to cancel the dialog."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        vgs = get_vgs()
        rows: list[Widget] = [
            FormRow("Name", "input_name",
                    validators=Regex("[A-Za-z0-9-]+",failure_description="Only alphanumeric chars are allowed"),
                    ),
            FormRow("Size", "input_size",
                    validators=Regex("[0-9]+(M|G)", failure_description="Only numbers and units are allowed"),
                    )
        ]
        if self.thin:
            rows.append(
                FormRowSelect(
                "Thin Volume", "lv_thin", [(lv["lv_name"], (lv["lv_name"], lv["vg_name"])) for lv in get_lvs(only_thins=True)]
                )
                )
        else:
            rows.append(FormRowSelect("Volume group", "vg_select", [(vg["vg_name"], vg["vg_name"]) for vg in vgs]))
        rows.append(
            Horizontal(
                Button("Add", variant="success", id="add", classes="form_button"),
                Button("Cancel", variant="primary", id="cancel", classes="form_button"),
            classes="horizontal_layout")
        )
        v = Vertical(*rows, id="dialog")
        v.border_title = "Add logical volume"
        yield v

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value:
            event.control.remove_class("error_input")
        elif not event.value:
            event.control.add_class("error_input")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        has_error = False
        if event.button.id == "add":
            nodes = self.query(Input).nodes
            for node in nodes:
                value = node.value
                validation = node.validate(value)
                if validation:
                    if not validation.is_valid:
                        has_error = True
            size = Size.parse(self.query_one("#input_size", expect_type=Input).value)
            name = self.query_one("#input_name", expect_type=Input).value
            if self.thin:
                lv_thin_select: Select[tuple[str,...]] = self.query_one("#lv_thin", expect_type=Select)
                if not lv_thin_select.value:
                    lv_thin_select.add_class("error_input")
                    has_error = True
                if has_error:
                    return
                thin = lv_thin_select.value
                if size and name and thin:
                    create_thin_lv(size, name, thin[1], thin[0])
            else:
                select_element: Select[str] = self.query_one("#vg_select", expect_type=Select)
                if not select_element.value:
                    select_element.add_class("error_input")
                    has_error = True
                if has_error:
                    return
                vg = select_element.value
                if size and name and vg:
                    create_lvs(size, name, vg)
                # should never happen
                else:
                    raise ValueError("Invalid input")
        self.app.pop_screen()
        self.app.query_one(Data).update()


class Options(Static):

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("n) Create a new logical volume"),
            Label("d) Delete a logical volume"),
            Label("u) Update data table"),
            Label("t) Create a new thin logical volume"),
            Label("s) Create a thin snapshot of a logical volume"),
        )

class Data(Static):

    BINDINGS: list[BindingType] = [
        Binding("enter", "select_cursor", "Select", show=False)
    ]

    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*NAMES_LVS)
        table.cursor_type = "row"
        self.update()

    def update(self) -> None:
        lvs = get_lvs()
        table = self.query_one(DataTable)
        table.clear()
        for lv in lvs:
            table.add_row(*[format_entry(n, lv[n]) for n in OPTIONS_LVS])

class MainLayout(Static):

    def compose(self) -> ComposeResult:
        opt = Options(id="options")
        opt.border_title = "Options"
        yield opt
        data = Data(id="data")
        data.border_title = "Data"
        yield data

class LvmTui(App):
    """A Textual app to manage stopwatches."""

    CSS_PATH = "main.css"
    BINDINGS = [("l", "toggle_dark", "Toggle light mode"),
                ("q", "quit", "Quit"),
                ("n", "add_lv", "Add a new logical volume"),
                ("t", "add_thin", "Add a new thin logical volume"),
                ("r", "remove_lv", "Remove a logical volume"),
                ("u", "update", "Update data table"),
                ("d", "delete_lv", "Delete a logical volume"),
                ("s", "create_snapshot", "Create a thin snapshot of a logical volume"),]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield MainLayout(id="main")

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark # type: ignore[has-type]

    def action_add_lv(self) -> None:
        """An action to add a new logical volume."""
        self.push_screen(AddLv())

    def action_add_thin(self) -> None:
        """An action to add a new thin logical volume."""
        self.push_screen(AddLv(thin=True))

    def action_create_snapshot(self) -> None:
        """An action to create a thin snapshot of a logical volume."""
        table = self.app.query_one(DataTable)
        if table.cursor_row is not None:
            lv: str = table.get_cell_at(Coordinate(table.cursor_row, 0))
            vg: str = table.get_cell_at(Coordinate(table.cursor_row, 1))
            self.push_screen(AddSnapshot(lv=lv, vg=vg, classes="modal_container"))

    def action_update(self) -> None:
        """An action to update the data table."""
        self.query_one(Data).update()

    def action_delete_lv(self) -> None:
        """An action to show deletion confirmation."""
        table = self.app.query_one(DataTable)
        if table.cursor_row is not None:
            lv: str = table.get_cell_at(Coordinate(table.cursor_row, 0))
            vg: str = table.get_cell_at(Coordinate(table.cursor_row, 1))
            self.push_screen(ConfirmDelete(lv=lv, vg=vg, classes="modal_container"))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        print(event.cursor_row)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        print(event.cursor_row)

if __name__ == "__main__":
    app = LvmTui()
    app.run()