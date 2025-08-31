import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Workplace Detect"
    POSTGRES_DSN: str = "postgresql://postgres:br7moLeJ56@192.168.13.89:5432/ArmisVideo"
    YOLO_MODEL: str = "yolov8n.pt"
    THUMBNAILS_DIR: str = "./thumbs"
    FRAME_POLL_DEFAULT: int = 5
    ABSENCE_THRESHOLD_MIN: int = 10

settings = Settings()
