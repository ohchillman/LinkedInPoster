from typing import Dict, Optional
import requests
import logging
import socket
import socks

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
            - protocol: протокол прокси (http, https, socks5, socks4) (опционально)
        """
        self.proxy_settings = proxy_settings
        self.is_proxy_working = None  # None означает, что прокси еще не проверялся
        # Если прокси указаны, они всегда обязательны (изменяем логику)
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
        
        # Получаем протокол прокси (по умолчанию http)
        protocol = self.proxy_settings.get("protocol", "http")
        
        # Формируем URL прокси с учетом протокола
        proxy_url = f"{protocol}://"
        
        # Добавляем учетные данные, если они предоставлены
        if username and password:
            proxy_url += f"{username}:{password}@"
        
        proxy_url += f"{host}:{port}"
        
        # Если прокси указан и мы уже проверили, что он не работает - выбрасываем исключение
        if self.is_proxy_working is False and self.proxy_required:
            error_msg = f"Socket error: {protocol.upper()} connection failed"
            raise ValueError(error_msg)
        
        # Возвращаем настройки прокси для обоих протоколов (http и https)
        # Для SOCKS прокси тоже указываем оба протокола
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    def check_proxy(self, timeout: int = 5) -> bool:
        """
        Проверяет работоспособность прокси
        
        :param timeout: Таймаут для проверки прокси в секундах
        :return: True если прокси работает, False в противном случае
        :raises: ValueError если прокси обязательны и не работают
        """
        if not self.proxy_settings:
            self.is_proxy_working = True
            return True
        
        # Получаем настройки прокси
        host = self.proxy_settings.get("host")
        port = self.proxy_settings.get("port")
        
        if not host or not port:
            # Всегда выбрасываем исключение, если прокси указаны не полностью
            error_msg = "Прокси указаны некорректно, проверьте настройки host и port"
            logger.error(error_msg)
            self.is_proxy_working = False
            if self.proxy_required:
                raise ValueError(error_msg)
            return False
        
        username = self.proxy_settings.get("username")
        password = self.proxy_settings.get("password")
        protocol = self.proxy_settings.get("protocol", "http")
        
        # Формируем URL прокси
        proxy_url = f"{protocol}://"
        
        # Добавляем учетные данные, если они предоставлены
        if username and password:
            proxy_url += f"{username}:{password}@"
        
        proxy_url += f"{host}:{port}"
        
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        try:
            logger.info(f"Проверка работоспособности прокси: {proxy_url}")
            # Используем LinkedIn API для проверки
            test_url = "https://api.linkedin.com/v2/me"
            
            # Делаем запрос с таймаутом
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=timeout,
                # Не проверяем статус ответа, только соединение
                allow_redirects=False
            )
            
            # Успешное соединение
            self.is_proxy_working = True
            logger.info(f"Прокси работает, получен ответ с кодом: {response.status_code}")
            return True
            
        except requests.exceptions.ProxyError as e:
            logger.error(f"Ошибка прокси: {str(e)}")
            self.is_proxy_working = False
            
            # Более точное определение типа ошибки для SOCKS5
            error_msg = str(e)
            if "SOCKS5" in error_msg.upper():
                error_msg = "Socket error: SOCKS5 authentication failed"
            elif "SOCKS4" in error_msg.upper():
                error_msg = "Socket error: SOCKS4 connection failed"
            elif "authentication" in error_msg.lower():
                error_msg = f"Socket error: {protocol.upper()} authentication failed"
            else:
                error_msg = f"Socket error: {protocol.upper()} connection failed"
            
            # Всегда выбрасываем исключение, если прокси были указаны, но не работают
            if self.proxy_required:
                logger.error(f"Прокси не работает: {error_msg}")
                raise ValueError(error_msg)
            
            return False
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Таймаут прокси-соединения: {str(e)}")
            self.is_proxy_working = False
            
            error_msg = f"Socket error: {protocol.upper()} connection timeout"
            
            # Всегда выбрасываем исключение, если прокси были указаны, но не работают
            if self.proxy_required:
                raise ValueError(error_msg)
            
            return False
            
        except requests.RequestException as e:
            logger.error(f"Ошибка запроса через прокси: {str(e)}")
            self.is_proxy_working = False
            
            # Определяем тип ошибки
            error_msg = str(e)
            if "connection" in error_msg.lower():
                error_msg = f"Socket error: Could not connect to {protocol.upper()} proxy"
            else:
                error_msg = f"Socket error: {protocol.upper()} proxy error - {error_msg}"
            
            # Всегда выбрасываем исключение, если прокси были указаны, но не работают
            if self.proxy_required:
                raise ValueError(error_msg)
            
            return False
    
    def apply_to_session(self, session):
        """
        Применяет настройки прокси к сессии requests
        
        :param session: Объект сессии requests
        :return: Сессия с примененными настройками прокси
        :raises: ValueError если прокси обязательны, но не работают
        """
        # Проверяем прокси перед применением
        if self.proxy_settings:
            # Делаем явную проверку прокси
            self.check_proxy()
            
            # Получаем настройки прокси
            proxies = self.get_proxies()
            
            # Если прокси работает, применяем настройки к сессии
            if proxies:
                session.proxies.update(proxies)
        
        return session