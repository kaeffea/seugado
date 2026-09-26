"""Pytest configuration and environment loading."""

import os
from pathlib import Path


def _load_env_if_present() -> None:
    if not os.environ.get("SEUGADO_TEST_DATABASE_URL"):
        root = Path(__file__).resolve().parents[1]
        env_file = root / ".env"
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() in ("SEUGADO_TEST_DATABASE_URL", "DATABASE_URL"):
                            os.environ.setdefault("SEUGADO_TEST_DATABASE_URL", v.strip())


_load_env_if_present()
