import re
import subprocess

from rich.console import Console
from rich.table import Table

from enum import Enum

NAMES_LVS = ["Name", "VG", "Attributes", "Size", "Origin", "Pool", "Creation Time", "Path", "Data%", "Thins"]
NAMES_VGS = ["Name", "Attributes", "Size", "Free", "UUID", "PVs", "LVs", "Snapshots", "Tags"]
OPTIONS_LVS = ["lv_name", "vg_name", "lv_attr", "lv_size","origin", "pool_lv", "lv_time", "lv_path", "data_percent", "thin_count"]
OPTIONS_VGS = ["vg_name", "vg_attr", "vg_size", "vg_free", "vg_uuid", "pv_count", "lv_count", "snap_count", "vg_tags"]

class Unit(Enum):
    B = "B"
    K = "K"
    M = "M"
    G = "G"
    T = "T"
    P = "P"

unit_to_power = {
    Unit.B: 0,
    Unit.K: 1,
    Unit.M: 2,
    Unit.G: 3,
    Unit.T: 4,
    Unit.P: 5,
}

class Size:
        
    def __init__(self, size: int, unit: Unit) -> None:
        self.size = size
        self.unit = unit

    @classmethod
    def parse(cls, repr: str) -> "Size":
        pattern = r'^(\d+\.?\d*)([BKMGTP])?$'
        match = re.match(pattern, repr, re.IGNORECASE)
        if match:
            size_num_str, size_indicator = match.groups()
            size = int(size_num_str)
            if size_indicator is None:
                size_indicator = "B"
            return Size(size, Unit(size_indicator))
        else:
            raise ValueError(f"Invalid size: {repr}")
    
    def convert_to(self, unit: Unit) -> "Size":
        if self.unit == unit:
            return self
        else:
            return Size(int(self.size * pow(1024, unit_to_power[self.unit] - unit_to_power[unit])), unit)
        
    def string_in(self, unit: Unit) -> str:
        return f"{self.convert_to(unit).size}{unit.value}"

    def __repr__(self) -> str:
        return f"Size({self.size}, {self.unit.__repr__()})"
    
    def __str__(self) -> str:
        return f"{self.size}{self.unit.value}"

def format_entry(entry: str, value: str) -> str:
    if entry == "lv_size":
        return Size.parse(value).string_in(Unit.G)
    else:
        return value

def get_lvs(only_thins = False) -> list[dict[str, str]]:
    """Return a list of logical volumes."""
    lvs = []
    with subprocess.Popen(
        ["sudo", "lvs", "--units", "b", "--separator", ",", "--noheadings", "--nosuffix", "-o", ','.join(OPTIONS_LVS)],
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ) as proc:
        if proc.stdout is not None:
            for line in proc.stdout:
                lvs.append(dict(zip(OPTIONS_LVS, line.strip().split(","))))
    if only_thins:
        lvs = [lv for lv in lvs if lv["lv_attr"][0] == "t"]
    return lvs

def get_vgs() -> list[dict[str, str]]:
    """Return list of volume groups."""
    vgs = []
    with subprocess.Popen(
        ["sudo", "vgs", "--units", "b", "--separator", ",", "--noheadings", "--nosuffix", "-o", ','.join(OPTIONS_VGS)],
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ) as proc:
        if proc.stdout is not None:
            for line in proc.stdout:
                vgs.append(dict(zip(OPTIONS_VGS, line.strip().split(","))))
    return vgs

def create_lvs(size: Size, name: str,  vgs: str) -> None:
    """Create a new logical volume."""
    with subprocess.Popen(
        ["sudo", "lvcreate", "--size", str(size), "--name", name, vgs],
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ) as proc:
        if proc.stdout is not None:
            for line in proc.stdout:
                print(line.strip())

def lv_exists(name: str, vg: str) -> bool:
    """Check if a logical volume exists."""
    lvs = get_lvs()
    for lv in lvs:
        if lv["lv_name"] == name and lv["vg_name"] == vg:
            return True
    return False

def create_thin_lv(size: Size, name: str, vg: str, thin_pool: str) -> None:
    """Create a new thin logical volume."""
    with subprocess.Popen(
        ["sudo", "lvcreate", "--thin", "--virtualsize", str(size), "--name", name, f"{vg}/{thin_pool}"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ) as proc:
        if proc.stdout is not None:
            for line in proc.stdout:
                print(line.strip())

def create_thin_snapshot(name: str, vg: str, lv: str) -> None:
    """Create a thin snapshot of a thin logical volume."""
    with subprocess.Popen(
        ["sudo", "lvcreate", "--snapshot", "--setactivationskip", "n", "--name", name, f"{vg}/{lv}"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ) as proc:
        if proc.stdout is not None:
            for line in proc.stdout:
                print(line.strip())

def remove_lvs(lv: str, vg: str) -> None:
    """Remove a logical volume."""
    with subprocess.Popen(
        ["sudo", "lvremove", "-f", f"{vg}/{lv}"],
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ) as proc:
        if proc.stdout is not None:
            for line in proc.stdout:
                print(line.strip())

if __name__ == "__main__":

    remove_lvs("test", "vg0")
    lvs = get_lvs()
    console = Console()

    table = Table(show_header=True, header_style="magenta")
    for n in NAMES_LVS:
        table.add_column(n)
    for lv in lvs:
        table.add_row(*[format_entry(n, lv[n]) for n in OPTIONS_LVS])
    console.print(table)

