from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/flipper"
    anthropic_api_key: str = ""
    ebay_app_id: str = ""
    ebay_cert_id: str = ""
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    linkup_api_key: str = ""
    ebay_stub: bool = True
    linkup_stub: bool = True
    environment: str = "development"
    log_level: str = "INFO"
    poll_interval_seconds: int = 180
    opportunity_score_threshold: float = 0.6
    alert_score_threshold: float = 0.6
    alert_distance_miles: int = 50
    seed_data: bool = False

    # Parts pricing service
    parts_stub: bool = True          # Set false when scrapers are verified in production
    user_postcode: str = "LE4 8JF"  # Default postcode for delivery calculation
    parts_cache_ttl_hours: int = 24  # How long to cache parts pricing results
    scraper_timeout_seconds: int = 5  # Per-adapter HTTP timeout

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
