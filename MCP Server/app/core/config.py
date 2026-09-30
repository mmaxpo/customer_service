from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MCP_API_KEY: str = "dev-secret"

    SEARXNG_URL: str = "http://searxng:8080"

    TAVILY_API_KEY: str | None = None
    BRAVE_API_KEY: str | None = None
    BRIGHTDATA_TOKEN: str | None = None


settings = Settings()
