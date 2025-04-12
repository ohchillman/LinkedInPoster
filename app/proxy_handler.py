from typing import Dict, Optional

class ProxyHandler:
    """
    Обработчик прокси для запросов к API LinkedIn
    """
    
    def __init__(self, proxy_settings: Optional[Dict] = None):
        """
        Инициализирует обработчик прокси
        
        :param proxy_settings: Словарь с настройками прокси:
            - host: хост прокси-сервера
            - port: порт прокси-сервера
            - username: имя пользователя для авторизации (опционально)
            - password: пароль для авторизации (опционально)
        """
        self.proxy_settings = proxy_settings
    
    def get_proxies(self) -> Dict:
        """
        Возвращает словарь с настройками прокси для использования в requests
        
        :return: Словарь с настройками прокси или пустой словарь, если прокси не настроены
        """
        if not self.proxy_settings:
            return {}
        
        host = self.proxy_settings.get("host")
        port = self.proxy_settings.get("port")
        
        if not host or not port:
            return {}
        
        username = self.proxy_settings.get("username")
        password = self.proxy_settings.get("password")
        
        # Формируем URL прокси
        proxy_url = f"http://"
        
        # Добавляем учетные данные, если они предоставлены
        if username and password:
            proxy_url += f"{username}:{password}@"
        
        proxy_url += f"{host}:{port}"
        
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    def apply_to_session(self, session):
        """
        Применяет настройки прокси к сессии requests
        
        :param session: Объект сессии requests
        :return: Сессия с примененными настройками прокси
        """
        proxies = self.get_proxies()
        if proxies:
            session.proxies.update(proxies)
        return session
