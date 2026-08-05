"""Central configuration with dotenv loading and secret-safe diagnostics."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        env_file_encoding="utf-8",
    )

    step_api_key: SecretStr | None = Field(default=None, alias="STEP_API_KEY", repr=False)
    step_base_url: str = Field(default="https://api.stepfun.com/v1", alias="STEP_BASE_URL")
    step_model: str = Field(default="step-3.7-flash", alias="STEP_MODEL")
    step_connect_timeout_seconds: int = Field(default=10, alias="STEP_CONNECT_TIMEOUT_SECONDS", ge=1, le=120)
    step_read_timeout_seconds: int = Field(default=90, alias="STEP_READ_TIMEOUT_SECONDS", ge=1, le=600)
    step_max_retries: int = Field(default=3, alias="STEP_MAX_RETRIES", ge=0, le=5)

    ncbi_api_key: SecretStr | None = Field(default=None, alias="NCBI_API_KEY", repr=False)
    ncbi_email: str | None = Field(default=None, alias="NCBI_EMAIL")
    runs_dir: Path = Field(default=PROJECT_ROOT / "runs", alias="TARGET_AGENT_RUN_DIR")
    projects_dir: Path = Field(default=PROJECT_ROOT / "projects", alias="RESEARCH_AGENT_PROJECT_DIR")
    cache_dir: Path = Field(default=PROJECT_ROOT / "cache", alias="TARGET_AGENT_CACHE_DIR")
    tool_registry_path: Path = Field(
        default=PROJECT_ROOT / "configs" / "tool_registry.yaml",
        alias="TARGET_AGENT_TOOL_REGISTRY",
    )
    cache_only: bool = Field(default=False, alias="TARGET_AGENT_CACHE_ONLY")
    enable_limma: bool = Field(default=False, alias="TARGET_AGENT_ENABLE_LIMMA")
    enable_census_expression: bool = Field(default=False, alias="TARGET_AGENT_ENABLE_CENSUS_EXPRESSION")
    web_workers: int = Field(default=2, alias="TARGET_AGENT_WEB_WORKERS", ge=1, le=16)
    web_queue_size: int = Field(default=8, alias="TARGET_AGENT_WEB_QUEUE_SIZE", ge=1, le=100)
    gsea_permutations: int = Field(default=1000, alias="TARGET_AGENT_GSEA_PERMUTATIONS", ge=100, le=10000)
    random_seed: int = Field(default=123, alias="TARGET_AGENT_RANDOM_SEED")
    reviewer_lora_base: Path | None = Field(default=None, alias="TARGET_AGENT_REVIEWER_LORA_BASE")
    reviewer_lora_adapter: Path | None = Field(default=None, alias="TARGET_AGENT_REVIEWER_LORA_ADAPTER")

    @property
    def step_configured(self) -> bool:
        return bool(self.step_api_key and self.step_api_key.get_secret_value().strip() and self.step_model.strip())

    def public_summary(self) -> dict[str, Any]:
        return {
            "step_configured": self.step_configured,
            "step_model": self.step_model,
            "step_base_url": self.step_base_url,
            "cache_only": self.cache_only,
            "limma_enabled": self.enable_limma,
            "census_expression_enabled": self.enable_census_expression,
            "reviewer_lora_configured": bool(self.reviewer_lora_base and self.reviewer_lora_adapter),
            "runs_dir_writable": _writable_parent(self.runs_dir),
            "projects_dir_writable": _writable_parent(self.projects_dir),
            "cache_dir_writable": _writable_parent(self.cache_dir),
        }


def _writable_parent(path: Path) -> bool:
    candidate = path.expanduser()
    while not candidate.exists() and candidate.parent != candidate:
        candidate = candidate.parent
    return candidate.exists() and os.access(candidate, os.W_OK)


def load_settings(env_file: Path | None = None) -> Settings:
    """Load process environment first, then one explicit/default dotenv file."""
    selected = env_file if env_file is not None else PROJECT_ROOT / ".env"
    return Settings(_env_file=selected if selected and selected.exists() else None)
