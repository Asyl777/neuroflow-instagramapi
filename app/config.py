"""
Конфигурация приложения Instagram API с ИИ
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # API Configuration
    api_key: str = "neuro123"
    
    # Database Configuration (используем существующую БД)
    db_host: str = "postgres"
    db_port: int = 5432
    db_user: str = "neuroflow"
    db_password: str = "neuroflow"
    db_name: str = "neuroflow"
    
    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8001
    log_level: str = "INFO"
    cors_origins: str = "*"
    environment: str = "development"
    
    # AI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    ai_max_tokens: int = 1000
    ai_temperature: float = 0.7
    
    # Redis Configuration
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Instagram Configuration  
    instagram_session_path: str = "/app/sessions"
    instagram_max_retries: int = 3
    
    @property
    def database_url(self) -> str:
        """Строка подключения к PostgreSQL"""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property 
    def redis_url(self) -> str:
        """Строка подключения к Redis"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Список разрешенных CORS origins"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Глобальный объект настроек
settings = Settings()