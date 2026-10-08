"""Read JSON and CSV test data with Python's standard library."""

import csv
import json
from pathlib import Path
from typing import Any


class DataReader:
    """Load structured test cases from UTF-8 files."""

    @staticmethod
    def read_json(path: str | Path) -> Any:
        """Return the parsed JSON value; parsing and I/O errors propagate."""
        with Path(path).open(encoding="utf-8") as source:
            return json.load(source)

    @staticmethod
    def read_csv(path: str | Path) -> list[dict[str, str]]:
        """Return CSV records keyed by their header names."""
        with Path(path).open(encoding="utf-8", newline="") as source:
            return list(csv.DictReader(source))
