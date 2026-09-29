import pathlib
import pytest
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_abai_qc_screen():
    script = ROOT / "scripts" / "run_abai_qc_screen.py"
    res = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0, f"ABAI QC screen failed:\n{res.stdout}\n{res.stderr}"
    assert "ABAI QC SCREEN: VERDICT CLEAR" in res.stdout
    assert (ROOT / ".abai" / "attest.json").exists()
