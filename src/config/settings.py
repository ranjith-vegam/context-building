from pydantic_settings import BaseSettings, SettingsConfigDict

from src.models import (
    Layer1Settings,
    Layer2Settings
)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")
    layer1: Layer1Settings
    layer2: Layer2Settings


_config_instance = None

def get_config():
    """
    Returns the singleton instance of the Settings class.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Settings()  # type: ignore
    return _config_instance