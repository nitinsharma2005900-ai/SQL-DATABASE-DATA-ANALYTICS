"""Application Configuration and Environment Settings."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Root directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if it exists
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Central configuration class."""

    def __init__(self) -> None:
        self.BASE_DIR: Path = BASE_DIR
        self.DATA_DIR: Path = BASE_DIR / "data"
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Gemini LLM Settings
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

        # Database Settings
        # Support default local sqlite path with relative-to-base resolution
        raw_db_url = os.getenv("DATABASE_URL", f"sqlite:///{self.DATA_DIR / 'analytics.db'}").strip()
        if raw_db_url.startswith("sqlite:///./data/"):
            sqlite_subpath = raw_db_url.replace("sqlite:///./data/", "")
            self.DATABASE_URL: str = f"sqlite:///{self.DATA_DIR / sqlite_subpath}"
        elif raw_db_url.startswith("sqlite:///") and not os.path.isabs(raw_db_url.replace("sqlite:///", "")):
            rel_path = raw_db_url.replace("sqlite:///", "")
            self.DATABASE_URL: str = f"sqlite:///{self.BASE_DIR / rel_path}"
        else:
            self.DATABASE_URL: str = raw_db_url

        # Security & Flow Controls
        self.MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
        self.READ_ONLY_MODE: bool = os.getenv("READ_ONLY_MODE", "true").lower() in ("true", "1", "yes")
        self.ENABLE_NEMO_GUARDRAILS: bool = os.getenv("ENABLE_NEMO_GUARDRAILS", "true").lower() in ("true", "1", "yes")

        # NeMo Guardrails Configuration Path
        self.GUARDRAILS_CONFIG_DIR: Path = BASE_DIR / "config" / "guardrails"

    @property
    def is_demo_mode(self) -> bool:
        """Returns True if Gemini API key is missing, placeholder, or explicitly mocked."""
        if not self.GEMINI_API_KEY:
            return True
        key = self.GEMINI_API_KEY.lower().strip()
        return (
            key.startswith("mock")
            or "your_" in key
            or "api_key" in key
            or key in ("none", "null", "false", "")
        )


settings = Settings()
