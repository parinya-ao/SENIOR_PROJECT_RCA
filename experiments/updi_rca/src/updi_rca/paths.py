"""Paths shared by the experiment package and its scripts."""

from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = EXPERIMENT_ROOT.parents[1]
ARTIFACTS_ROOT = REPOSITORY_ROOT / "artifacts/updi"
VENDOR_ROOT = REPOSITORY_ROOT / "third_party"
