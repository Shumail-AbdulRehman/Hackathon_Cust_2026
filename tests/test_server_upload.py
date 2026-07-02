# tests/test_server_upload.py
import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
import server


def test_upload_csv():
    client = TestClient(server.app)
    csv_bytes = b"full_name,declared_income_pkr\nAlice,50000\n"
    response = client.post(
        "/api/upload",
        files={"files": ("tax.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "profiles" in data
    assert data["profiles"][0]["name"] == "tax.csv"
    assert data["profiles"][0]["row_count"] == 1


def test_run_files():
    client = TestClient(server.app)
    csv_bytes = b"full_name,declared_income_pkr,tax_paid_pkr,filer_status\nAlice,50000,2000,Filer\n"
    response = client.post(
        "/api/run-files",
        files={"files": ("tax.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"mappings": "{}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "uploaded"
    assert "ml_used" in data
    assert "profiles" in data


def test_status():
    client = TestClient(server.app)
    response = client.get("/api/status/test-job")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["job_id"] == "test-job"


def test_upload_invalid_extension():
    client = TestClient(server.app)
    xlsx_bytes = b"PK\x03\x04fake xlsx content"
    response = client.post(
        "/api/upload",
        files={"files": ("data.xlsx", io.BytesIO(xlsx_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 400


def test_run_files_invalid_mappings():
    client = TestClient(server.app)
    csv_bytes = b"full_name,declared_income_pkr,tax_paid_pkr,filer_status\nAlice,50000,2000,Filer\n"
    response = client.post(
        "/api/run-files",
        files={"files": ("tax.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"mappings": "not-json"},
    )
    assert response.status_code == 400
