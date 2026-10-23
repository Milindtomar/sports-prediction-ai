"""Environment-driven configuration. No secrets are hard-coded; see .env.example."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings:
    def __init__(self) -> None:
        self.database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'sportsai.db'}")
        # Render/Heroku style URLs use the legacy "postgres://" scheme
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+psycopg2://", 1)
        self.cors_origins: list[str] = [o.strip() for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173").split(",") if o.strip()]
        self.rate_limit: str = os.getenv("RATE_LIMIT", "240/minute")
        self.heavy_rate_limit: str = os.getenv("HEAVY_RATE_LIMIT", "60/minute")
        self.artifact_dir: Path = Path(os.getenv("ARTIFACT_DIR", str(BASE_DIR / "artifacts")))
        self.env: str = os.getenv("APP_ENV", "development")
        self.auto_seed: bool = os.getenv("AUTO_SEED", "1").strip().lower() in ("1", "true", "yes")


settings = Settings()
