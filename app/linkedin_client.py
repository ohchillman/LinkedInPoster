import requests
from typing import List, Optional, Dict
from app.proxy_handler import ProxyHandler
import json

class LinkedInClient:
    """
    Клиент для работы с API LinkedIn
    """
    
    def __init__(self, client_id: str, client_secret: str, access_token: str, proxy_handler: ProxyHandler):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.proxy_handler = proxy_handler
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }
    
    def _make_request(self, method: str, endpoint: str, data=None, files=None, json=None):
        """
        Выполняет запрос к API LinkedIn с учетом настроек прокси
        """
        url = f"{self.base_url}{endpoint}"
        proxies = self.proxy_handler.get_proxies()
        
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            data=data,
            files=files,
            json=json,
            proxies=proxies
        )
        
        if response.status_code >= 400:
            error_message = f"LinkedIn API error: {response.status_code} - {response.text}"
            raise Exception(error_message)
        
        return response.json() if response.text else {}
    
    def get_user_profile(self):
        """
        Получает информацию о профиле пользователя
        """
        endpoint = "/me"
        return self._make_request("GET", endpoint)
    
    def upload_image(self, image_data: bytes, filename: str) -> str:
        """
        Загружает изображение в LinkedIn и возвращает URL для использования в посте
        """
        # Шаг 1: Инициализация загрузки изображения
        register_endpoint = "/assets?action=registerUpload"
        register_data = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": "urn:li:person:" + self.get_user_profile()["id"],
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        
        upload_info = self._make_request("POST", register_endpoint, json=register_data)
        
        # Шаг 2: Загрузка изображения по полученному URL
        upload_url = upload_info["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_id = upload_info["value"]["asset"]
        
        # Загрузка изображения на полученный URL
        proxies = self.proxy_handler.get_proxies()
        upload_response = requests.put(
            url=upload_url,
            data=image_data,
            headers={"Content-Type": "application/octet-stream"},
            proxies=proxies
        )
        
        if upload_response.status_code >= 400:
            raise Exception(f"Ошибка при загрузке изображения: {upload_response.status_code} - {upload_response.text}")
        
        return asset_id
    
    def create_post(self, text: str, image_urls: List[str] = None) -> str:
        """
        Создает пост в LinkedIn с текстом и опционально с изображениями
        Возвращает URL созданного поста
        """
        # Получаем ID пользователя
        user_id = self.get_user_profile()["id"]
        
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
        post_id = response["id"]
        
        # Формируем URL поста
        post_url = f"https://www.linkedin.com/feed/update/{post_id}"
        
        return post_url
