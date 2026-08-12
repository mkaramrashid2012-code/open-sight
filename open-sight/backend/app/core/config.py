from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://opensight:change-me@localhost:5432/opensight"
    secret_key: str = "change-me"
    media_root: str = "./data/media"
    clips_root: str = "./data/clips"
    thumbnails_root: str = "./data/thumbnails"
    default_retention_days: int = 14
    model_path: str = "yolov8n.pt"
    confidence_threshold: float = 0.35
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
