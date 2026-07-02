import subprocess
import sys
from pathlib import Path

LIBRARIAN = Path(__file__).parent.parent / "slm" / "librarian.py"


def test_ask_requires_input():
    result = subprocess.run(
        [sys.executable, str(LIBRARIAN), "ask"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "requires either" in result.stderr.lower() or "requires either" in result.stdout.lower()


def test_ask_override_prompt():
    result = subprocess.run(
        [sys.executable, str(LIBRARIAN), "ask", "--prompt", "Custom prompt", "--system", "Custom system", "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Custom system" in result.stdout
    assert "Custom prompt" in result.stdout
