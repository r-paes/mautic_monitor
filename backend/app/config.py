"""
config.py — Configurações centralizadas via pydantic-settings.

REGRA: Nenhum valor de configuração deve aparecer hardcoded em outros módulos.
       Sempre importe `settings` deste módulo.
"""

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # 🔐 Segurança & Autenticação
    # -------------------------------------------------------------------------
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    allowed_hosts: List[str] = ["http://localhost:3000"]

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    # -------------------------------------------------------------------------
    # 🗄️ Banco de Dados (TimescaleDB / PostgreSQL)
    # -------------------------------------------------------------------------
    database_url: str
    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "monitor_db"
    db_user: str = "monitor_user"
    db_password: str
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_echo: bool = False
    timescale_chunk_interval: str = "1 day"
    timescale_retention_policy: str = "90 days"

    # -------------------------------------------------------------------------
    # ⏱️ Jobs Agendados (APScheduler)
    # -------------------------------------------------------------------------
    scheduler_job_defaults_coalesce: bool = True
    scheduler_job_defaults_max_instances: int = 1
    metrics_collect_interval_minutes: int = 5
    vps_collect_interval_minutes: int = 15
    mautic_db_collect_interval_minutes: int = 15
    alert_engine_interval_seconds: int = 60
    scheduler_timezone: str = "America/Sao_Paulo"
    scheduler_misfire_grace_time: int = 30
    job_store_type: str = "memory"

    # -------------------------------------------------------------------------
    # 📡 Integrações Externas — Mautic (globais)
    # Credenciais por instância são armazenadas no banco de dados.
    # -------------------------------------------------------------------------
    mautic_timeout_seconds: int = 10
    external_request_retry_attempts: int = 3
    external_request_retry_delay_seconds: int = 2

    # -------------------------------------------------------------------------
    # 📧 Sendpost — Gateway de Email
    # -------------------------------------------------------------------------
    sendpost_api_base_url: str = "https://api.sendpost.io/api/v1"
    sendpost_api_key: str
    sendpost_alert_from_email: str
    sendpost_alert_from_name: str = "Space Monitor"

    # -------------------------------------------------------------------------
    # 📱 Avant SMS — Gateway de SMS
    # -------------------------------------------------------------------------
    avant_sms_api_base_url: str = "https://channel.solucoesdigitais.dev/sms"
    avant_sms_token: str
    avant_sms_alert_from: str = "SpaceCRM"

    # -------------------------------------------------------------------------
    # 🚨 Regras de Alerta — Thresholds
    # -------------------------------------------------------------------------
    alert_threshold_cpu_warning: int = 80
    alert_threshold_cpu_critical: int = 95
    alert_threshold_memory_warning: int = 85
    alert_threshold_memory_critical: int = 95
    alert_threshold_disk_warning: int = 80
    alert_threshold_disk_critical: int = 90
    alert_threshold_email_delta_pct: float = 5.0
    alert_threshold_sms_delta_pct: float = 5.0
    alert_threshold_api_latency_ms: int = 3000
    alert_no_contacts_hours: int = 24
    alert_evaluation_window_minutes: int = 5
    alert_cooldown_minutes: int = 30
    alert_min_severity_to_notify: str = "warning"

    # -------------------------------------------------------------------------
    # 🌐 Servidor & API
    # -------------------------------------------------------------------------
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_workers: int = 1
    app_reload: bool = True
    log_level: str = "info"
    log_format: str = "text"
    api_v1_prefix: str = "/api/v1"
    docs_enabled: bool = True
    request_timeout_seconds: int = 30
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # -------------------------------------------------------------------------
    # 📊 Módulo de Relatórios Mautic
    # Credenciais MySQL por instância são armazenadas no banco de dados.
    # -------------------------------------------------------------------------
    report_storage_path: str = "/app/reports"
    report_retention_days: int = 30
    report_cron_morning: int = 9    # hora BRT (0-23)
    report_cron_evening: int = 18   # hora BRT (0-23)
    mautic_mysql_connect_timeout: int = 10
    mautic_mysql_pool_size: int = 5

    # -------------------------------------------------------------------------
    # 🐳 Docker / EasyPanel
    # -------------------------------------------------------------------------
    compose_project_name: str = "mautic-monitor"
    easypanel_domain: str = "monitor.spacecrm.online"
    tz: str = "America/Sao_Paulo"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def docs_url(self) -> str | None:
        return "/docs" if self.docs_enabled else None

    @property
    def redoc_url(self) -> str | None:
        return "/redoc" if self.docs_enabled else None


@lru_cache
def get_settings() -> Settings:
    """Retorna instância singleton de Settings (cached)."""
    return Settings()


# Instância global para uso direto
settings = get_settings()
