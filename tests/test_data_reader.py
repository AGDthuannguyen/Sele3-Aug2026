"""DataReader examples using files a test author can create."""

import json

import pytest

from pylenium import DataReader


def test_json_and_csv_provide_the_same_cases(tmp_path):
    cases = [
        {"email": "an@example.com", "name": "An Nguyễn"},
        {"email": "be@example.com", "name": "Bé, Trần"},
    ]
    json_path = tmp_path / "users.json"
    csv_path = tmp_path / "users.csv"
    json_path.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
    csv_path.write_text(
        'email,name\nan@example.com,An Nguyễn\nbe@example.com,"Bé, Trần"\n',
        encoding="utf-8",
    )

    assert DataReader.read_json(json_path) == cases
    assert DataReader.read_csv(csv_path) == cases


def test_reader_keeps_standard_file_and_json_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataReader.read_csv(tmp_path / "missing.csv")

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        DataReader.read_json(invalid_json)
