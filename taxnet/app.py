"""Small HTTP server for the TaxNet XAI prototype."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .ingestion import profile_datasets
from .pipeline import compact_result, run_benchmark, run_pipeline

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "dist"


def bounded_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


class TaxNetHandler(BaseHTTPRequestHandler):
    server_version = "TaxNetXAI/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "service": "taxnet-xai", "falkordb": falkor_health()})
            return
        if parsed.path == "/api/demo":
            result = compact_result(run_pipeline())
            self.send_json(result)
            return
        if parsed.path == "/api/benchmark":
            params = parse_qs(parsed.query)
            citizens = bounded_int(params.get("citizens", [500])[0], 500, 1, 5000)
            seed = bounded_int(params.get("seed", [42])[0], 42, 0, 999999)
            self.send_json(run_benchmark(citizens=citizens, synthetic_seed=seed))
            return
        if parsed.path == "/":
            self.send_file(WEB / "index.html")
            return
        requested = parsed.path.lstrip("/")
        safe_path = (WEB / requested).resolve()
        if WEB.resolve() not in safe_path.parents and safe_path != WEB.resolve():
            self.send_error(403)
            return
        self.send_file(safe_path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/profile", "/api/run"}:
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            datasets = payload.get("datasets")
            mappings = payload.get("mappings")
            if not isinstance(datasets, dict):
                self.send_json({"error": "Expected JSON body with datasets object"}, status=400)
                return
            if mappings is not None and not isinstance(mappings, dict):
                self.send_json({"error": "Expected mappings to be an object when provided"}, status=400)
                return
            if parsed.path == "/api/profile":
                self.send_json({"profiles": profile_datasets(datasets, mappings=mappings)})
                return
            result = compact_result(run_pipeline(datasets=datasets, mappings=mappings))
            self.send_json(result)
        except json.JSONDecodeError as exc:
            self.send_json({"error": f"Invalid JSON: {exc}"}, status=400)
        except Exception as exc:  # pragma: no cover - server safety
            self.send_json({"error": str(exc)}, status=500)

def falkor_health() -> dict[str, Any]:
    try:
        from .falkor_engine import get_falkordb_client

        client = get_falkordb_client()
        client.connection.ping()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TaxNet XAI prototype server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--benchmark", action="store_true", help="Run a synthetic scalability benchmark and exit")
    parser.add_argument("--citizens", type=int, default=500, help="Synthetic citizens for benchmark mode")
    parser.add_argument("--seed", type=int, default=42, help="Synthetic data seed")
    args = parser.parse_args()
    if args.benchmark:
        print(json.dumps(run_benchmark(citizens=args.citizens, synthetic_seed=args.seed), indent=2))
        return
    server = ThreadingHTTPServer((args.host, args.port), TaxNetHandler)
    print(f"TaxNet XAI running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

