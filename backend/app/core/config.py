import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _environment_file() -> str | None:
    """Select one of the two supported local environment contracts.

    Deployed containers receive values through Compose or their secret manager;
    the file is only a fallback. Tests deliberately load no developer file.
    """

    environment = (
        os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "development"
    ).strip().lower()

    if environment in {"test", "testing"}:
        return None
    if environment in {"prod", "production", "stage", "staging"}:
        return ".env.prod"
    if environment in {"", "dev", "development", "local"}:
        return ".env.dev"
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_environment_file(),
        extra="ignore",  # <-- allow other env vars without crashing
        case_sensitive=False,
    )

    DATABASE_URL: str
    LANGGRAPH_CHECKPOINT_DB_URL: str

    # JWT
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    # Cookies
    ACCESS_COOKIE_MAX_AGE: int = 1200
    REFRESH_COOKIE_MAX_AGE: int = 604800

    COOKIE_SECURE: bool = False  # True in prod (https)
    COOKIE_SAMESITE: str = "lax"  # "lax" or "strict" or "none"
    WEB_APP_URL: str = "http://localhost:3000"
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 1440
    CSRF_ENFORCED: bool = False
    MAX_REQUEST_BODY_BYTES: int = 2_000_000
    RATE_LIMIT_ENABLED: bool = True
    REDIS_URL: str | None = None
    AGENT_AUTO_AWAY_MINUTES: int = 15
    AGENT_PRESENCE_LEASE_SECONDS: int = 75
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 120
    RATE_LIMIT_AUTH_PER_MINUTE: int = 20
    RATE_LIMIT_AGENT_PER_MINUTE: int = 30
    ESTIMATED_INPUT_MICROUSD_PER_MILLION_TOKENS: int = 400_000
    ESTIMATED_OUTPUT_MICROUSD_PER_MILLION_TOKENS: int = 1_600_000
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.05
    RESEND_API_KEY: str | None = None
    INBOUND_EMAIL_WEBHOOK_SECRET: str | None = None
    ATTACHMENT_STORAGE_ROOT: str = "/tmp/tajeran-attachments"
    MAX_ATTACHMENT_BYTES: int = 10_000_000
    ATTACHMENT_SCAN_MODE: str = "builtin"  # builtin | clamdscan
    ATTACHMENT_STORAGE_BACKEND: str = "local"  # local | s3
    ATTACHMENT_RETENTION_DAYS: int = 365
    ATTACHMENT_SIGNED_URL_SECONDS: int = 300
    S3_ENDPOINT_URL: str | None = None
    S3_BUCKET: str | None = None
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    BILLING_WEBHOOK_SECRET: str | None = None
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_STARTER_PRICE_ID: str | None = None
    STRIPE_GROWTH_PRICE_ID: str | None = None
    STRIPE_PRO_PRICE_ID: str | None = None
    BILLING_SUCCESS_URL: str = "http://localhost:3000/settings/billing?checkout=success"
    BILLING_CANCEL_URL: str = "http://localhost:3000/settings/billing?checkout=canceled"
    SHOPIFY_BILLING_TEST: bool = True
    DEFAULT_TRIAL_DAYS: int = 14
    CUSTOMER_DATA_RETENTION_DAYS: int = 730
    WORKER_HEARTBEAT_PATH: str = "/tmp/tajeran-worker-heartbeat"
    WORKER_HEARTBEAT_MAX_AGE_SECONDS: int = 90
    # Pool settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30

    # LLM defaults
    LLM_PROVIDER: str = "openai"  # openai | anthropic | groq | etc (future)
    OPENAI_MODEL: str = "gpt-4.1-mini-2025-04-14"
    LLM_PROVIDER_MAX_ATTEMPTS: int = 3
    LLM_RETRY_BASE_SECONDS: float = 2.0
    LLM_RETRY_MAX_SECONDS: float = 30.0
    LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    LLM_CIRCUIT_BREAKER_RESET_SECONDS: float = 60.0

    # API keys (add more later here)
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    TAVILY_API_KEY: str | None = None

    GOOGLE_API_KEY: str | None = None
    GOOGLE_CSE_ID: str | None = None

    SEARCH_PROVIDER: str = "searxng"

    SEARXNG_URL: str | None = None
    TAVILY_API_KEY: str | None = None
    BRAVE_API_KEY: str | None = None
    BRIGHTDATA_API_KEY: str | None = None

    MCP_SEARCH_URL: str | None = None
    MCP_API_KEY: str | None = None
    MCP_SEARCH_PATH: str | None = None

    # Shopify real-store integration
    SHOPIFY_USE_REAL_PROVIDER: bool = False
    SHOPIFY_API_VERSION: str = "2026-07"
    SHOPIFY_API_KEY: str | None = None
    SHOPIFY_API_SECRET: str | None = None
    SHOPIFY_REDIRECT_URI: str = (
        "http://localhost:8000/customer-service/shopify/oauth/callback"
    )
    SHOPIFY_SCOPES: str = (
        "read_orders,read_draft_orders,read_customers,read_products,write_orders,read_fulfillments,"
        "write_draft_orders,read_content"
    )
    SHOPIFY_TOKEN: str | None = None

    # Customer Service AI Context Controls
    CS_AI_RECENT_MESSAGE_LIMIT: int = 20
    CS_AI_INCLUDE_INTERNAL_NOTES: bool = False
    CS_AI_MAX_CONTEXT_CHARS: int = 12000
    CS_AI_KNOWLEDGE_TOP_K: int = 5
    CS_INTELLIGENCE_MODEL_ENABLED: bool = False
    CS_INTELLIGENCE_MODEL: str | None = None

    # Capability provider-health maintenance
    #
    # The dedicated job-worker process periodically attempts to enqueue one
    # reconcile job for the current completed UTC health window. Database job
    # idempotency makes this safe across multiple worker processes.
    CAPABILITY_HEALTH_MAINTENANCE_ENABLED: bool = True
    CAPABILITY_HEALTH_MAINTENANCE_CHECK_INTERVAL_SECONDS: float = 60.0
    CAPABILITY_HEALTH_WINDOW_HOURS: int = 1
    CAPABILITY_HEALTH_LOOKBACK_WINDOWS: int = 24
    CAPABILITY_HEALTH_SCOPE_LIMIT: int = 1000


settings = Settings()
