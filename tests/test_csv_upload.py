# tests/test_csv_upload.py
import io
import pytest
from taxnet.csv_upload import parse_uploaded_csv


def test_parse_simple_csv():
    text = "name,age\nAlice,30\nBob,40\n"
    rows = parse_uploaded_csv(io.BytesIO(text.encode("utf-8")), "people.csv")
    assert rows == [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "40"},
    ]


def test_parse_quoted_csv_with_commas():
    text = 'name,note\nAlice,"likes, commas"\nBob,"x"\n'
    rows = parse_uploaded_csv(io.BytesIO(text.encode("utf-8")), "people.csv")
    assert rows[0]["note"] == "likes, commas"


def test_parse_tab_delimited():
    text = "name\tage\nAlice\t30\n"
    rows = parse_uploaded_csv(io.BytesIO(text.encode("utf-8")), "people.tsv")
    assert rows[0] == {"name": "Alice", "age": "30"}


def test_row_limit():
    text = "id\n" + "\n".join(str(i) for i in range(12))
    with pytest.raises(ValueError, match="more than 10 rows"):
        parse_uploaded_csv(io.BytesIO(text.encode("utf-8")), "big.csv", max_rows=10)


def test_empty_file():
    with pytest.raises(ValueError, match="no data rows"):
        parse_uploaded_csv(io.BytesIO(b"name\n"), "empty.csv")
