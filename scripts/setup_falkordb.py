"""Portable FalkorDB setup script.

Run this on any machine to get the same FalkorDB container that the project expects:

    uv run python scripts/setup_falkordb.py

It uses Podman if available, otherwise Docker. The container is named `falkordb`
and exposes port 6379. Data is persisted in a named volume `falkordb_data`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time


CONTAINER_NAME = "falkordb"
VOLUME_NAME = "falkordb_data"
IMAGE = "docker.io/falkordb/falkordb"
PORT = "6379"


def find_runtime() -> str:
    if shutil.which("podman"):
        return "podman"
    if shutil.which("docker"):
        return "docker"
    raise RuntimeError("Neither podman nor docker is installed. Please install one of them.")


def container_exists(runtime: str) -> bool:
    result = subprocess.run(
        [runtime, "ps", "-a", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return CONTAINER_NAME in result.stdout.splitlines()


def container_running(runtime: str) -> bool:
    result = subprocess.run(
        [runtime, "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return CONTAINER_NAME in result.stdout.splitlines()


def create_volume(runtime: str) -> None:
    result = subprocess.run(
        [runtime, "volume", "inspect", VOLUME_NAME],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Creating volume {VOLUME_NAME}...")
        subprocess.run([runtime, "volume", "create", VOLUME_NAME], check=True)
    else:
        print(f"Volume {VOLUME_NAME} already exists.")


def start_container(runtime: str) -> None:
    if container_running(runtime):
        print(f"Container {CONTAINER_NAME} is already running.")
        return

    if container_exists(runtime):
        print(f"Starting existing container {CONTAINER_NAME}...")
        subprocess.run([runtime, "start", CONTAINER_NAME], check=True)
        return

    print(f"Pulling image {IMAGE} and creating container {CONTAINER_NAME}...")
    subprocess.run(
        [
            runtime,
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "-v",
            f"{VOLUME_NAME}:/var/lib/falkordb/data",
            "-p",
            f"{PORT}:6379",
            IMAGE,
        ],
        check=True,
    )


def wait_for_ready(runtime: str, timeout: int = 60) -> None:
    print("Waiting for FalkorDB to be ready...")
    start = time.time()
    while time.time() - start < timeout:
        result = subprocess.run(
            [runtime, "exec", CONTAINER_NAME, "redis-cli", "PING"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and "PONG" in result.stdout:
            print("FalkorDB is ready.")
            return
        time.sleep(1)
    raise RuntimeError(f"FalkorDB did not become ready within {timeout} seconds.")


def main() -> None:
    runtime = find_runtime()
    print(f"Using container runtime: {runtime}")
    create_volume(runtime)
    start_container(runtime)
    wait_for_ready(runtime)
    print(f"\nFalkorDB is running at redis://localhost:{PORT}")
    print("You can now run the pipeline or tests.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
