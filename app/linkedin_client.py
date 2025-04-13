import requests
from typing import List, Optional, Dict
from app.proxy_handler import ProxyHandler
import json
import logging

logger = logging.getLogger(__name__)

class LinkedInClient:
    """
    Клиент для работы с API LinkedIn
    """
    
    def __init__(self, client_id: str, client_secret: str, access_token: str, proxy_handler: ProxyHandler, user_id: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.proxy_handler = proxy_handler
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        self.user_id = user_id
    
    def _make_request(self, method: str, endpoint: str, data=None, files=None, json=None):
        """
        Выполняет запрос к API LinkedIn с учетом настроек прокси
        """
        url = f"{self.base_url}{endpoint}"
        
        # Проверяем, что прокси работает, если он настроен
        if self.proxy_handler.proxy_settings:
            self.proxy_handler.check_proxy()  # Это выбросит исключение, если прокси не работает
            
        proxies = self.proxy_handler.get_proxies()
        
        logger.info(f"Отправка {method} запроса к {url}")
        if proxies:
            logger.info(f"Используются прокси: {proxies}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                data=data,
                files=files,
                json=json,
                proxies=proxies,
                timeout=30  # Добавляем таймаут для предотвращения бесконечной загрузки
            )
            
            logger.info(f"Получен ответ от API LinkedIn: {response.status_code}")
            
            if response.status_code >= 400:
                error_message = f"LinkedIn API error: {response.status_code} - {response.text}"
                logger.error(f"Ошибка API LinkedIn: {error_message}")
                
                if response.status_code == 401:
                    raise Exception(f"Ошибка аутентификации: токен доступа недействителен или истек срок его действия. {response.text}")
                elif response.status_code == 403:
                    raise Exception(f"Ошибка авторизации: недостаточно прав для выполнения операции. Токен должен иметь разрешения: r_liteprofile, w_member_social. {response.text}")
                else:
                    raise Exception(error_message)
            
            return response.json() if response.text else {}
            
        except requests.RequestException as e:
            logger.error(f"Ошибка сетевого запроса: {str(e)}")
            raise Exception(f"Ошибка сетевого запроса: {str(e)}")
    
    def get_user_profile(self):
        """
        Получает информацию о профиле пользователя
        """
        try:
            logger.info("Получение информации о профиле пользователя")
            endpoint = "/me"
            return self._make_request("GET", endpoint)
        except Exception as e:
            logger.error(f"Ошибка при получении профиля пользователя: {str(e)}")
            
            # Если у нас есть user_id, используем его вместо запроса к /me
            if self.user_id:
                logger.info(f"Используем предоставленный user_id: {self.user_id}")
                return {"id": self.user_id}
            
            # Пытаемся извлечь ID пользователя из токена (если это возможно)
            try:
                user_id = self._extract_user_id_from_token()
                if user_id:
                    logger.info(f"Извлечен ID пользователя из токена: {user_id}")
                    return {"id": user_id}
            except Exception as extract_error:
                logger.error(f"Не удалось извлечь ID пользователя из токена: {str(extract_error)}")
            
            # Если не удалось получить ID пользователя, выбрасываем исключение чтобы не продолжать
            raise Exception(f"Не удалось получить ID пользователя: {str(e)}")
    
    def _extract_user_id_from_token(self):
        """
        Пытается извлечь ID пользователя из токена или других источников
        """
        # Пробуем получить информацию о токене
        try:
            token_info_endpoint = "/oauth/v2/introspectToken"
            token_info = self._make_request("POST", token_info_endpoint, data={"token": self.access_token})
            if "sub" in token_info:
                return token_info["sub"]
        except Exception as e:
            logger.error(f"Не удалось получить информацию о токене: {str(e)}")
        
        # Если не удалось получить информацию о токене, пробуем другие методы
        # Например, можно попробовать получить информацию о текущем пользователе через другие эндпоинты
        try:
            # Пробуем получить информацию через эндпоинт /userinfo
            userinfo_endpoint = "/userinfo"
            userinfo = self._make_request("GET", userinfo_endpoint)
            if "sub" in userinfo:
                return userinfo["sub"]
        except Exception as e:
            logger.error(f"Не удалось получить информацию о пользователе через /userinfo: {str(e)}")
        
        # Если все методы не сработали, возвращаем None
        return None
    
    def upload_image(self, image_data: bytes, filename: str) -> str:
        """
        Загружает изображение в LinkedIn и возвращает URL для использования в посте
        """
        try:
            logger.info(f"Загрузка изображения: {filename}")
            
            # Проверяем, что прокси работает, если он настроен
            if self.proxy_handler.proxy_settings:
                self.proxy_handler.check_proxy()  # Это выбросит исключение, если прокси не работает
            
            # Получаем ID пользователя
            user_profile = self.get_user_profile()
            if "id" not in user_profile:
                raise Exception("Не удалось получить ID пользователя из профиля. Проверьте разрешения токена.")
            
            user_id = user_profile["id"]
            logger.info(f"ID пользователя LinkedIn: {user_id}")
            
            # Шаг 1: Инициализация загрузки изображения с расширенными разрешениями
            register_endpoint = "/assets?action=registerUpload"
            
            # Обновленный запрос с дополнительными параметрами для поддержки PNG и других форматов
            register_data = {
                "registerUploadRequest": {
                    "recipes": [
                        "urn:li:digitalmediaRecipe:feedshare-image"
                    ],
                    "owner": f"urn:li:person:{user_id}",
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ],
                    "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"]
                }
            }
            
            # Добавляем расширенные заголовки для запроса на регистрацию загрузки
            upload_headers = self.headers.copy()
            upload_headers["Content-Type"] = "application/json"
            upload_headers["X-Restli-Protocol-Version"] = "2.0.0"
            
            # Выполняем запрос с обновленными заголовками
            url = f"{self.base_url}{register_endpoint}"
            proxies = self.proxy_handler.get_proxies()
            
            logger.info(f"Отправка POST запроса для регистрации загрузки к {url}")
            if proxies:
                logger.info(f"Используются прокси: {proxies}")
            
            try:
                response = requests.post(
                    url=url,
                    headers=upload_headers,
                    json=register_data,
                    proxies=proxies,
                    timeout=30
                )
                
                logger.info(f"Получен ответ от API LinkedIn: {response.status_code}")
                
                if response.status_code >= 400:
                    error_message = f"LinkedIn API error: {response.status_code} - {response.text}"
                    logger.error(f"Ошибка API LinkedIn при регистрации загрузки: {error_message}")
                    
                    if response.status_code == 403:
                        logger.error("Ошибка доступа 403. Проверьте, что токен имеет разрешения: r_liteprofile, w_member_social")
                        raise Exception(f"Ошибка авторизации: недостаточно прав для выполнения операции. Токен должен иметь разрешения: r_liteprofile, w_member_social. {response.text}")
                    else:
                        raise Exception(error_message)
                
                upload_info = response.json()
            except requests.RequestException as e:
                logger.error(f"Ошибка сетевого запроса при регистрации загрузки: {str(e)}")
                raise Exception(f"Ошибка сетевого запроса при регистрации загрузки: {str(e)}")
            
            logger.info("Получена информация для загрузки изображения")
            
            # Шаг 2: Загрузка изображения по полученному URL
            if "value" not in upload_info or "uploadMechanism" not in upload_info["value"] or "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest" not in upload_info["value"]["uploadMechanism"]:
                raise Exception(f"Неверный формат ответа при регистрации загрузки: {json.dumps(upload_info)}")
            
            upload_url = upload_info["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            asset_id = upload_info["value"]["asset"]
            
            logger.info(f"URL для загрузки изображения: {upload_url}")
            logger.info(f"ID ресурса: {asset_id}")
            
            # Определяем тип контента на основе расширения файла
            content_type = "application/octet-stream"
            if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                content_type = "image/jpeg"
            elif filename.lower().endswith('.png'):
                content_type = "image/png"
            elif filename.lower().endswith('.gif'):
                content_type = "image/gif"
            
            # Загрузка изображения на полученный URL с правильным Content-Type
            proxies = self.proxy_handler.get_proxies()
            upload_headers = {
                "Content-Type": content_type
            }
            
            logger.info(f"Загрузка изображения с Content-Type: {content_type}")
            
            upload_response = requests.put(
                url=upload_url,
                data=image_data,
                headers=upload_headers,
                proxies=proxies,
                timeout=60  # Увеличиваем таймаут для загрузки больших изображений
            )
            
            if upload_response.status_code >= 400:
                raise Exception(f"Ошибка при загрузке изображения: {upload_response.status_code} - {upload_response.text}")
            
            logger.info(f"Изображение успешно загружено: {asset_id}")
            return asset_id
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения: {str(e)}")
            raise Exception(f"Не удалось загрузить изображение в LinkedIn. Ошибка: {str(e)}")
    
    def create_post(self, text: str, image_urls: List[str] = None) -> str:
        """
        Создает пост в LinkedIn с текстом и опционально с изображениями
        Возвращает URL созданного поста
        """
        try:
            logger.info(f"Создание поста в LinkedIn. Текст: {text[:50]}...")
            
            # Проверяем, что прокси работает, если он настроен
            if self.proxy_handler.proxy_settings:
                self.proxy_handler.check_proxy()  # Это выбросит исключение, если прокси не работает
            
            # Получаем ID пользователя
            user_profile = self.get_user_profile()
            if "id" not in user_profile:
                raise Exception("Не удалось получить ID пользователя из профиля. Проверьте разрешения токена.")
            
            user_id = user_profile["id"]
            logger.info(f"ID пользователя LinkedIn: {user_id}")
            
            # Формируем данные для поста
            post_data = {
                "author": f"urn:li:person:{user_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Если есть изображения, добавляем их в пост
            if image_urls and len(image_urls) > 0:
                logger.info(f"Добавление {len(image_urls)} изображений к посту")
                media_list = []
                for i, image_url in enumerate(image_urls):
                    media_list.append({
                        "status": "READY",
                        "description": {
                            "text": f"Image {i+1}"
                        },
                        "media": image_url,
                        "title": {
                            "text": f"Image {i+1}"
                        }
                    })
                
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = media_list
            
            # Отправляем запрос на создание поста
            endpoint = "/ugcPosts"
            response = self._make_request("POST", endpoint, json=post_data)
            
            # Получаем ID созданного поста
            if "id" not in response:
                raise Exception(f"Неверный формат ответа при создании поста: {json.dumps(response)}")
            
            post_id = response["id"]
            logger.info(f"Пост успешно создан. ID: {post_id}")
            
            # Формируем URL поста
            post_url = f"https://www.linkedin.com/feed/update/{post_id}"
            logger.info(f"URL поста: {post_url}")
            
            return post_url
            
        except Exception as e:
            logger.error(f"Ошибка при создании поста: {str(e)}")
            # Перебрасываем исключение дальше, чтобы его перехватил вызывающий код
            raise Exception(f"Не удалось создать пост в LinkedIn. Ошибка: {str(e)}")