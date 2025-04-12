import os
from typing import Optional

class Config:
    """
    Конфигурация приложения
    """
    
    # Настройки сервера
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5001"))
    
    # Настройки LinkedIn по умолчанию (могут быть переопределены в запросе)
    LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
    LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    
    # Настройки прокси по умолчанию (могут быть переопределены в запросе)
    PROXY_HOST = os.getenv("PROXY_HOST", "")
    PROXY_PORT = os.getenv("PROXY_PORT", "")
    PROXY_USERNAME = os.getenv("PROXY_USERNAME", "")
    PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "")
    
    @classmethod
    def get_default_proxy_settings(cls) -> Optional[dict]:
        """
        Возвращает настройки прокси из переменных окружения
        """
        if not cls.PROXY_HOST or not cls.PROXY_PORT:
            return None
            
        proxy_settings = {
            "host": cls.PROXY_HOST,
            "port": int(cls.PROXY_PORT) if cls.PROXY_PORT.isdigit() else None
        }
        
        if cls.PROXY_USERNAME:
            proxy_settings["username"] = cls.PROXY_USERNAME
            
        if cls.PROXY_PASSWORD:
            proxy_settings["password"] = cls.PROXY_PASSWORD
            
        return proxy_settings
