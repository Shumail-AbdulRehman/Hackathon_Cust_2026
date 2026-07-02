import os
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import server


@contextmanager
def make_client(profiles=None):
    with patch.object(server, "_load_profiles", return_value=profiles or {}):
        with TestClient(server.app) as client:
            yield client


def test_health():
    with make_client() as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_slm_provider():
    with make_client() as client:
        response = client.get("/api/slm-provider")
        assert response.status_code == 200
        assert response.json()["provider"] == "ollama"


def test_list_profiles():
    profiles = {
        "ENT-1": {
            "entity_id": "ENT-1",
            "canonical_name": "Test Entity",
            "risk_score": 85.0,
            "risk_tier": "high",
        }
    }
    with make_client(profiles) as client:
        response = client.get("/api/profiles")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["entity_id"] == "ENT-1"
        assert data[0]["name"] == "Test Entity"


def test_get_profile_not_found():
    with make_client({"ENT-1": {"entity_id": "ENT-1"}}) as client:
        response = client.get("/api/profiles/UNKNOWN")
        assert response.status_code == 404
        assert response.json()["detail"] == "Entity not found"


def test_ask():
    mock_retriever = MagicMock()
    mock_retriever.get_context.return_value = "Test law context"

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Mocked answer"
    mock_result.stderr = ""

    with patch.object(server, "_get_retriever", return_value=mock_retriever):
        with patch("server.subprocess.run", return_value=mock_result):
            with make_client() as client:
                response = client.post("/api/ask", json={"question": "What is tax?"})
                assert response.status_code == 200
                data = response.json()
                assert data["answer"] == "Mocked answer"
                assert data["provider"] == "ollama"
