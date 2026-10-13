"""Local B02 configuration. No credentials are returned to the browser."""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database: Path
    mode: str = "FIXTURE"

    @classmethod
    def load(cls, env_file=Path(".env")):
        values = {}
        path = Path(env_file)
        if path.is_file():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip().strip("\"'")
        allowed = {"TRIPMATE_DATABASE_PATH", "TRIPMATE_EXECUTION_MODE", "TRIPMATE_LLM_PROVIDER",
                   "TRIPMATE_LLM_MODEL", "ELEC5620_API_KEY", "ELEC5620_BASE_URL", "ELEC5620_MODEL"}
        for key in allowed:
            if key in values:
                os.environ.setdefault(key, values[key])
        mode = os.environ.get("TRIPMATE_EXECUTION_MODE", "FIXTURE").upper()
        if mode not in {"FIXTURE", "STUB"}:
            raise ValueError("B02 supports FIXTURE or STUB only; integrated REAL business execution is not ready")
        return cls(Path(os.environ.get("TRIPMATE_DATABASE_PATH", "data/tripmate.sqlite3")).resolve(), mode)


def has_model_key():
    key = os.environ.get("ELEC5620_API_KEY", "").strip()
    return bool(key and key != "REPLACE_LOCALLY")
