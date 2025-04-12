from typing import Dict, Optional
import requests
import logging

logger = logging.getLogger(__name__)

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
        self.is_proxy_working = None  # None означает, что прокси еще не проверялся
        # Если прокси указаны, они всегда обязательны
        self.proxy_required = proxy_settings is not None
    
    def get_proxies(self) -> Dict:
        """
        Возвращает словарь с настройками прокси для использования в requests
        
        :return: Словарь с настройками прокси или пустой словарь, если прокси не настроены
        :raises: ValueError если прокси обязательны, но не работают
        """
        if not self.proxy_settings:
            return {}
        
        host = self.proxy_settings.get("host")
        port = self.proxy_settings.get("port")
        
        if not host or not port:
            if self.proxy_required:
                raise ValueError("Прокси указаны некорректно, но являются обязательными для запросов")
            return {}
        
        username = self.proxy_settings.get("username")
        password = self.proxy_settings.get("password")
        
        # Формируем URL прокси
        proxy_url = f"http://"
        
        # Добавляем учетные данные, если они предоставлены
        if username and password:
            proxy_url += f"{username}:{password}@"
        
        proxy_url += f"{host}:{port}"
        
        # Если прокси уже проверен и не работает, всегда выбрасываем исключение
        # так как если прокси указаны, они должны работать
        if self.is_proxy_working is False:
            raise ValueError(f"Прокси {host}:{port} не работает, но является обязательным для запросов")
            
        # Этот код никогда не выполнится, но оставлен для совместимости
        if self.is_proxy_working is False and not self.proxy_required:
            logger.warning(f"Прокси {host}:{port} не работает, запросы будут выполняться без прокси")
            return {}
        
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    def check_proxy(self, timeout: int = 5) -> bool:
        """
        Проверяет работоспособность прокси
        
        :param timeout: Таймаут для проверки прокси в секундах
        :return: True если прокси работает, False в противном случае
        :raises: ValueError если прокси обязательны, но не работают
        """
        if not self.proxy_settings:
            self.is_proxy_working = True
            return True
        
        # Получаем настройки прокси без проверки работоспособности
        host = self.proxy_settings.get("host")
        port = self.proxy_settings.get("port")
        
        if not host or not port:
            # Если прокси указаны, но некорректно, всегда выбрасываем исключение
            raise ValueError("Прокси указаны некорректно, но являются обязательными для запросов")
            # Этот код никогда не выполнится, но оставлен для совместимости
            self.is_proxy_working = False
            return False
        
        username = self.proxy_settings.get("username")
        password = self.proxy_settings.get("password")
        
        # Формируем URL прокси
        proxy_url = f"http://"
        
        # Добавляем учетные данные, если они предоставлены
        if username and password:
            proxy_url += f"{username}:{password}@"
        
        proxy_url += f"{host}:{port}"
        
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        try:
            logger.info(f"Проверка работоспособности прокси: {proxies}")
            # Используем LinkedIn API для проверки, так как это наиболее релевантно
            test_url = "https://api.linkedin.com/v2/me"
            
            # Делаем запрос с таймаутом
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=timeout,
                # Не проверяем статус ответа, только соединение
                allow_redirects=False
            )
            
            # Если получили какой-то ответ (даже ошибку авторизации), значит прокси работает
            self.is_proxy_working = True
            logger.info(f"Прокси работает, получен ответ с кодом: {response.status_code}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Прокси не работает: {str(e)}")
            self.is_proxy_working = False
            
            # Если прокси указаны, всегда выбрасываем исключение
            raise ValueError(f"Прокси {host}:{port} не работает, но является обязательным для запросов: {str(e)}")
            
            # Этот код никогда не выполнится, но оставлен для совместимости
            return False
    
    def apply_to_session(self, session):
        """
        Применяет настройки прокси к сессии requests
        
        :param session: Объект сессии requests
        :return: Сессия с примененными настройками прокси
        :raises: ValueError если прокси обязательны, но не работают
        """
        # Проверяем прокси перед применением
        if self.is_proxy_working is None:
            self.check_proxy()
            
        proxies = self.get_proxies()
        if proxies:
            session.proxies.update(proxies)
        elif self.proxy_settings is not None:
            # Если прокси указаны, но не работают или указаны некорректно
            raise ValueError("Прокси указаны, но не работают или указаны некорректно")
            
        return session
