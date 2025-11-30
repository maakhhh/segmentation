import os


class Settings:
    """Настройки приложения"""
    app_name: str = "Liver Segmentation Service"
    version: str = "1.0.0"

    # Пути
    upload_dir: str = "uploads"
    model_path: str = os.path.join("..", "..", "model", "unet.keras")

    # Настройки сервера
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    class Config:
        env_file = ".env"


settings = Settings()