from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/flipper"
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_stub: bool = True
    linkup_api_key: str = ""
    linkup_stub: bool = True
    anthropic_api_key: str = ""
    environment: str = "development"
    log_level: str = "INFO"
    poll_interval_seconds: int = 180
    opportunity_score_threshold: float = 0.6
    alert_distance_miles: int = 50

    class Config:
        env_file = ".env"


settings = Settings()
