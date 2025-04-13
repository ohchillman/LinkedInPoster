from app.config import Config
from app.proxy_handler import ProxyHandler
from app.linkedin_client import LinkedInClient
from app.api import api_router
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uvicorn
import os
import json
import logging
import base64
import requests
import hashlib
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания отправленных постов
# Структура: {client_id+access_token: {"post_id": id, "post_url": url, "timestamp": time}}
sent_posts_cache = {}

# Функция для генерации уникального ключа для каждого пользователя
def get_user_cache_key(client_id, access_token):
    # Берем первые 8 символов client_id и последние 8 символов access_token
    client_prefix = client_id[:8] if client_id and len(client_id) >= 8 else client_id
    token_suffix = access_token[-8:] if access_token and len(access_token) >= 8 else access_token
    return f"{client_prefix}_{token_suffix}"

app = FastAPI(title="LinkedIn Poster API", 
              description="API для публикации контента в LinkedIn с опциональной поддержкой прокси",
              version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Определяем абсолютный путь к директории static
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
logger.info(f"Static files directory: {static_dir}")

# Настраиваем статические файлы с явным указанием абсолютного пути
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Настраиваем шаблоны
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
logger.info(f"Templates directory: {templates_dir}")
templates = Jinja2Templates(directory=templates_dir)

# Регистрируем API роутер
app.include_router(api_router, prefix="/api")

# Модель для JSON запроса
class LinkedInPostRequest(BaseModel):
    client_id: str
    client_secret: str
    access_token: str
    text: str
    image: Optional[str] = None  # Base64 encoded image
    proxy: Optional[Dict[str, str]] = None
    user_id: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Функция для проверки прокси ПЕРЕД всеми действиями
def test_proxy_connection(proxy_settings):
    """
    Выполняет прямую проверку работоспособности прокси
    Возвращает (success, error_message)
    """
    if not proxy_settings:
        return True, None
    
    host = proxy_settings.get("host")
    port = proxy_settings.get("port")
    
    if not host or not port:
        return False, "Прокси указаны некорректно, проверьте настройки host и port"
    
    username = proxy_settings.get("username")
    password = proxy_settings.get("password")
    protocol = proxy_settings.get("protocol", "http")
    
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
        logger.info(f"Прямая проверка работоспособности прокси: {proxy_url}")
        # Используем LinkedIn API для проверки
        test_url = "https://api.linkedin.com/v2/me"
        
        # Делаем запрос с таймаутом
        response = requests.get(
            test_url,
            proxies=proxies,
            timeout=5,
            # Не проверяем статус ответа, только соединение
            allow_redirects=False
        )
        
        logger.info(f"Прокси работает, получен ответ с кодом: {response.status_code}")
        return True, None
        
    except requests.exceptions.ProxyError as e:
        error_msg = str(e)
        if "SOCKS5" in error_msg.upper():
            error_msg = "Socket error: SOCKS5 authentication failed"
        elif "SOCKS4" in error_msg.upper():
            error_msg = "Socket error: SOCKS4 connection failed"
        elif "authentication" in error_msg.lower():
            error_msg = f"Socket error: {protocol.upper()} authentication failed"
        else:
            error_msg = f"Socket error: {protocol.upper()} connection failed"
        
        logger.error(f"Ошибка прокси при прямой проверке: {error_msg}")
        return False, error_msg
        
    except requests.exceptions.Timeout as e:
        error_msg = f"Socket error: {protocol.upper()} connection timeout"
        logger.error(f"Таймаут прокси-соединения при прямой проверке: {error_msg}")
        return False, error_msg
        
    except requests.RequestException as e:
        error_msg = str(e)
        if "connection" in error_msg.lower():
            error_msg = f"Socket error: Could not connect to {protocol.upper()} proxy"
        else:
            error_msg = f"Socket error: {protocol.upper()} proxy error - {error_msg}"
        
        logger.error(f"Ошибка запроса через прокси при прямой проверке: {error_msg}")
        return False, error_msg

# Новый эндпоинт для JSON API
@app.post("/api/post", response_model=Dict[str, Any])
async def create_post_json(request_data: LinkedInPostRequest = Body(...)):
    try:
        logger.info(f"Получен JSON запрос на публикацию поста. Текст: {request_data.text[:50]}...")
        
        # Настройка прокси (опционально)
        proxy_settings = None
        if request_data.proxy:
            # Извлекаем информацию о прокси из различных форматов (http://, https://, socks5://, etc.)
            # Поддержка как словаря с протоколами, так и прямой строки с URL
            if isinstance(request_data.proxy, dict):
                http_proxy = request_data.proxy.get("http", "")
                https_proxy = request_data.proxy.get("https", http_proxy)
                socks_proxy = request_data.proxy.get("socks5", "")
                
                # Используем прокси в порядке приоритета: socks5 > https > http
                proxy_url = socks_proxy or https_proxy or http_proxy
            else:
                # Если прокси передан как строка, используем его напрямую
                proxy_url = request_data.proxy
            
            if proxy_url:
                # Определяем протокол прокси
                protocol = "http"
                if isinstance(proxy_url, str):
                    if proxy_url.startswith("socks5://"):
                        protocol = "socks5"
                        proxy_url = proxy_url.replace("socks5://", "")
                    elif proxy_url.startswith("socks4://"):
                        protocol = "socks4"
                        proxy_url = proxy_url.replace("socks4://", "")
                    elif proxy_url.startswith("https://"):
                        protocol = "https"
                        proxy_url = proxy_url.replace("https://", "")
                    elif proxy_url.startswith("http://"):
                        proxy_url = proxy_url.replace("http://", "")
                
                # Парсим URL прокси
                proxy_parts = proxy_url.split("@")
                
                if len(proxy_parts) > 1:
                    # Есть аутентификация
                    auth, server = proxy_parts
                    username, password = auth.split(":")
                    host, port = server.split(":")
                    
                    proxy_settings = {
                        "host": host,
                        "port": int(port),
                        "username": username,
                        "password": password,
                        "protocol": protocol
                    }
                else:
                    # Нет аутентификации
                    server = proxy_parts[0]
                    host, port = server.split(":")
                    
                    proxy_settings = {
                        "host": host,
                        "port": int(port),
                        "protocol": protocol
                    }
                
                logger.info(f"Используются настройки прокси: {proxy_settings['host']}:{proxy_settings['port']}")
            else:
                logger.info("Прокси указаны в неверном формате, запросы будут выполняться напрямую")
        else:
            logger.info("Прокси не указаны, запросы будут выполняться напрямую")
        
        # *** КРИТИЧЕСКИ ВАЖНО: Проверяем прокси перед всеми действиями ***
        if proxy_settings:
            # Выполняем прямую проверку прокси перед созданием всех остальных объектов
            proxy_working, proxy_error = test_proxy_connection(proxy_settings)
            if not proxy_working:
                error_response = {
                    "status": "error",
                    "error": f"Proxy connection test failed: {proxy_error}"
                }
                return JSONResponse(status_code=500, content=error_response)
        
        # Инициализация обработчика прокси
        proxy_handler = ProxyHandler(proxy_settings)
        
        # Инициализация клиента LinkedIn с прокси и опциональным user_id
        linkedin_client = LinkedInClient(
            client_id=request_data.client_id,
            client_secret=request_data.client_secret,
            access_token=request_data.access_token,
            proxy_handler=proxy_handler,
            user_id=request_data.user_id
        )
        
        # Проверка подключения к LinkedIn
        try:
            user_profile = linkedin_client.get_user_profile()
            logger.info(f"Успешное подключение к LinkedIn. Пользователь: {user_profile.get('id', 'Unknown')}")
        except Exception as e:
            logger.error(f"Ошибка при подключении к LinkedIn: {str(e)}")
            # Возвращаем ошибку, так как если не удалось подключиться, то и пост создать не получится
            error_response = {
                "status": "error",
                "error": f"LinkedIn connection failed: {str(e)}",
                "request": {
                    "credentials": {
                        "client_id": request_data.client_id,
                        "client_secret": "***" + request_data.client_secret[-4:] if len(request_data.client_secret) > 4 else "***",
                        "access_token": request_data.access_token[:10] + "***" if len(request_data.access_token) > 10 else "***"
                    },
                    "text": request_data.text,
                    "has_image": request_data.image is not None,
                    "proxy_settings": request_data.proxy
                }
            }
            return JSONResponse(status_code=500, content=error_response)
        
        # Загрузка изображения, если оно есть в base64
        image_urls = []
        if request_data.image:
            try:
                logger.info("Декодирование и загрузка изображения из base64")
                # Декодируем base64 в бинарные данные
                image_data = base64.b64decode(request_data.image)
                # Используем временное имя файла с расширением .png
                image_filename = "image.png"
                # Загружаем изображение
                image_url = linkedin_client.upload_image(image_data, image_filename)
                image_urls.append(image_url)
                logger.info(f"Изображение успешно загружено: {image_url}")
            except Exception as e:
                logger.error(f"Ошибка при декодировании или загрузке изображения: {str(e)}")
                error_response = {
                    "status": "error",
                    "error": f"Image upload failed: {str(e)}",
                    "request": {
                        "credentials": {
                            "client_id": request_data.client_id,
                            "client_secret": "***" + request_data.client_secret[-4:] if len(request_data.client_secret) > 4 else "***",
                            "access_token": request_data.access_token[:10] + "***" if len(request_data.access_token) > 10 else "***"
                        },
                        "text": request_data.text,
                        "has_image": request_data.image is not None,
                        "proxy_settings": request_data.proxy
                    }
                }
                return JSONResponse(status_code=400, content=error_response)
        
        # Публикация поста
        logger.info("Публикация поста в LinkedIn")
        try:
            # *** ПОВТОРНАЯ ПРОВЕРКА прокси перед публикацией ***
            if proxy_settings:
                proxy_working, proxy_error = test_proxy_connection(proxy_settings)
                if not proxy_working:
                    error_response = {
                        "status": "error",
                        "error": f"Proxy connection test failed: {proxy_error}"
                    }
                    return JSONResponse(status_code=500, content=error_response)
            
            # Генерируем ключ для проверки кэша
            cache_key = get_user_cache_key(request_data.client_id, request_data.access_token)
            
            # Генерируем хэш текста поста для проверки дублирования
            text_hash = hashlib.md5(request_data.text.encode()).hexdigest()
            
            # Проверяем, не публиковали ли мы уже такой пост недавно
            current_time = datetime.now()
            
            if cache_key in sent_posts_cache:
                cache_entry = sent_posts_cache[cache_key]
                # Если такой же текст поста был опубликован менее 5 минут назад
                if cache_entry.get("text_hash") == text_hash and \
                   current_time - cache_entry.get("timestamp", current_time - timedelta(minutes=10)) < timedelta(minutes=5):
                    logger.warning(f"Обнаружена попытка повторной публикации того же поста в течение 5 минут")
                    error_response = {
                        "status": "error", 
                        "error": "Duplicate post detected. Please wait at least 5 minutes before posting the same content again."
                    }
                    return JSONResponse(status_code=400, content=error_response)
            
            # Создаем пост в LinkedIn
            post_url = linkedin_client.create_post(request_data.text, image_urls)
            logger.info(f"Пост успешно опубликован: {post_url}")
            
            # Извлекаем ID поста из URL
            post_id = post_url.split("/")[-1] if "/" in post_url else post_url
            
            # Обновляем кэш отправленных постов
            sent_posts_cache[cache_key] = {
                "post_id": post_id,
                "post_url": post_url,
                "text_hash": text_hash,
                "timestamp": current_time
            }
            
            # Формируем ответ в новом формате
            response_data = {
                "status": "success",
                "post_url": post_url,
                "post_id": post_id,
                "request": {
                    "credentials": {
                        "client_id": request_data.client_id,
                        "client_secret": "***" + request_data.client_secret[-4:] if len(request_data.client_secret) > 4 else "***",
                        "access_token": request_data.access_token[:10] + "***" if len(request_data.access_token) > 10 else "***"
                    },
                    "text": request_data.text,
                    "has_image": request_data.image is not None,
                    "proxy_settings": request_data.proxy
                },
                "response": {
                    "post_id": post_id,
                    "post_url": post_url
                }
            }
            
            return JSONResponse(content=response_data)
        except Exception as e:
            logger.error(f"Ошибка при публикации поста: {str(e)}")
            
            # Проверяем, не связана ли ошибка с прокси
            if proxy_settings and ("proxy" in str(e).lower() or "socket" in str(e).lower() or "connect" in str(e).lower()):
                proxy_working, proxy_error = test_proxy_connection(proxy_settings)
                if not proxy_working:
                    error_response = {
                        "status": "error",
                        "error": f"Proxy connection test failed: {proxy_error}"
                    }
                    return JSONResponse(status_code=500, content=error_response)
            
            error_response = {
                "status": "error",
                "error": f"Post creation failed: {str(e)}",
                "request": {
                    "credentials": {
                        "client_id": request_data.client_id,
                        "client_secret": "***" + request_data.client_secret[-4:] if len(request_data.client_secret) > 4 else "***",
                        "access_token": request_data.access_token[:10] + "***" if len(request_data.access_token) > 10 else "***"
                    },
                    "text": request_data.text,
                    "has_image": request_data.image is not None,
                    "proxy_settings": request_data.proxy
                }
            }
            return JSONResponse(status_code=500, content=error_response)
    
    except Exception as e:
        logger.error(f"Ошибка при публикации поста: {str(e)}")
        
        # Проверяем, не связана ли ошибка с прокси
        if hasattr(request_data, 'proxy') and request_data.proxy:
            # Извлекаем настройки прокси для проверки
            proxy_settings = {}
            if isinstance(request_data.proxy, dict):
                # Сложная логика извлечения настроек прокси из словаря
                http_proxy = request_data.proxy.get("http", "")
                https_proxy = request_data.proxy.get("https", http_proxy)
                socks_proxy = request_data.proxy.get("socks5", "")
                proxy_url = socks_proxy or https_proxy or http_proxy
                
                if proxy_url:
                    # Упрощенное извлечение настроек для проверки
                    # Это не полная логика, но достаточная для простой проверки
                    try:
                        protocol = "http"
                        if isinstance(proxy_url, str):
                            if "socks5://" in proxy_url:
                                protocol = "socks5"
                            elif "socks4://" in proxy_url:
                                protocol = "socks4"
                            elif "https://" in proxy_url:
                                protocol = "https"
                                
                        # Простая проверка - удаляем протоколы
                        clean_url = proxy_url.replace("socks5://", "").replace("socks4://", "").replace("https://", "").replace("http://", "")
                        
                        # Извлекаем аутентификацию, если есть
                        if "@" in clean_url:
                            auth, server = clean_url.split("@", 1)
                            if ":" in auth and ":" in server:
                                username, password = auth.split(":", 1)
                                host, port = server.split(":", 1)
                                proxy_settings = {
                                    "host": host,
                                    "port": int(port),
                                    "username": username,
                                    "password": password,
                                    "protocol": protocol
                                }
                        elif ":" in clean_url:
                            host, port = clean_url.split(":", 1)
                            proxy_settings = {
                                "host": host,
                                "port": int(port),
                                "protocol": protocol
                            }
                    except Exception:
                        # Если не удалось распарсить, пропускаем проверку
                        pass
            elif isinstance(request_data.proxy, str):
                # Извлечение настроек из строки
                proxy_url = request_data.proxy
                try:
                    protocol = "http"
                    if proxy_url.startswith("socks5://"):
                        protocol = "socks5"
                        proxy_url = proxy_url.replace("socks5://", "")
                    elif proxy_url.startswith("socks4://"):
                        protocol = "socks4"
                        proxy_url = proxy_url.replace("socks4://", "")
                    elif proxy_url.startswith("https://"):
                        protocol = "https"
                        proxy_url = proxy_url.replace("https://", "")
                    elif proxy_url.startswith("http://"):
                        proxy_url = proxy_url.replace("http://", "")
                        
                    # Парсим URL прокси
                    if "@" in proxy_url:
                        auth, server = proxy_url.split("@", 1)
                        if ":" in auth and ":" in server:
                            username, password = auth.split(":", 1)
                            host, port = server.split(":", 1)
                            proxy_settings = {
                                "host": host,
                                "port": int(port),
                                "username": username,
                                "password": password,
                                "protocol": protocol
                            }
                    elif ":" in proxy_url:
                        host, port = proxy_url.split(":", 1)
                        proxy_settings = {
                            "host": host,
                            "port": int(port),
                            "protocol": protocol
                        }
                except Exception:
                    # Если не удалось распарсить, пропускаем проверку
                    pass
                
            if proxy_settings and ("proxy" in str(e).lower() or "socket" in str(e).lower() or "connect" in str(e).lower()):
                proxy_working, proxy_error = test_proxy_connection(proxy_settings)
                if not proxy_working:
                    error_response = {
                        "status": "error",
                        "error": f"Proxy connection test failed: {proxy_error}"
                    }
                    return JSONResponse(status_code=500, content=error_response)
        
        error_response = {
            "status": "error",
            "error": str(e),
            "request": {
                "credentials": {
                    "client_id": request_data.client_id,
                    "client_secret": "***" + request_data.client_secret[-4:] if len(request_data.client_secret) > 4 else "***",
                    "access_token": request_data.access_token[:10] + "***" if len(request_data.access_token) > 10 else "***"
                },
                "text": request_data.text,
                "has_image": request_data.image is not None,
                "proxy_settings": request_data.proxy
            }
        }
        return JSONResponse(status_code=500, content=error_response)

# Сохраняем старый эндпоинт для обратной совместимости
@app.post("/post")
async def create_post(
    linkedin_client_id: str = Form(...),
    linkedin_client_secret: str = Form(...),
    linkedin_access_token: str = Form(...),
    text: str = Form(...),
    images: List[UploadFile] = File(None),
    proxy_host: Optional[str] = Form(None),
    proxy_port: Optional[int] = Form(None),
    proxy_username: Optional[str] = Form(None),
    proxy_password: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    try:
        logger.info(f"Получен Form запрос на публикацию поста. Текст: {text[:50]}...")
        
        # Настройка прокси (теперь опционально)
        proxy_settings = None
        if proxy_host and proxy_port:
            proxy_settings = {
                "host": proxy_host,
                "port": proxy_port,
                "username": proxy_username,
                "password": proxy_password,
                "protocol": "http"  # По умолчанию используем HTTP протокол
            }
            logger.info(f"Используются настройки прокси: {proxy_host}:{proxy_port}")
            
            # Проверяем работоспособность прокси перед всем остальным
            proxy_working, proxy_error = test_proxy_connection(proxy_settings)
            if not proxy_working:
                error_response = {
                    "status": "error",
                    "error": f"Proxy connection test failed: {proxy_error}"
                }
                return JSONResponse(status_code=500, content=error_response)
        else:
            logger.info("Прокси не указаны, запросы будут выполняться напрямую")
        
        # Инициализация обработчика прокси
        proxy_handler = ProxyHandler(proxy_settings)
        
        # Инициализация клиента LinkedIn с прокси и опциональным user_id
        linkedin_client = LinkedInClient(
            client_id=linkedin_client_id,
            client_secret=linkedin_client_secret,
            access_token=linkedin_access_token,
            proxy_handler=proxy_handler,
            user_id=user_id
        )
        
        # Проверка подключения к LinkedIn
        try:
            user_profile = linkedin_client.get_user_profile()
            logger.info(f"Успешное подключение к LinkedIn. Пользователь: {user_profile.get('id', 'Unknown')}")
        except Exception as e:
            logger.error(f"Ошибка при подключении к LinkedIn: {str(e)}")
            error_response = {
                "status": "error",
                "error": f"LinkedIn connection failed: {str(e)}"
            }
            return JSONResponse(status_code=500, content=error_response)
        
        # Загрузка изображений, если они есть
        image_urls = []
        if images:
            logger.info(f"Загрузка {len(images)} изображений")
            for i, image in enumerate(images):
                if image.filename:  # Проверяем, что файл действительно был загружен
                    logger.info(f"Загрузка изображения {i+1}: {image.filename}")
                    try:
                        # Повторная проверка прокси перед каждой загрузкой
                        if proxy_settings:
                            proxy_working, proxy_error = test_proxy_connection(proxy_settings)
                            if not proxy_working:
                                error_response = {
                                    "status": "error",
                                    "error": f"Proxy connection test failed before image upload: {proxy_error}"
                                }
                                return JSONResponse(status_code=500, content=error_response)
                                
                        image_data = await image.read()
                        image_url = linkedin_client.upload_image(image_data, image.filename)
                        image_urls.append(image_url)
                        logger.info(f"Изображение {i+1} успешно загружено: {image_url}")
                    except Exception as e:
                        logger.error(f"Ошибка при загрузке изображения {i+1}: {str(e)}")
                        
                        # Проверяем, не связана ли ошибка с прокси
                        if proxy_settings and ("proxy" in str(e).lower() or "socket" in str(e).lower() or "connect" in str(e).lower()):
                            proxy_working, proxy_error = test_proxy_connection(proxy_settings)
                            if not proxy_working:
                                error_response = {
                                    "status": "error",
                                    "error": f"Proxy connection test failed during image upload: {proxy_error}"
                                }
                                return JSONResponse(status_code=500, content=error_response)
                                
                        error_response = {
                            "status": "error",
                            "error": f"Image upload failed: {str(e)}"
                        }
                        return JSONResponse(status_code=400, content=error_response)
        
        # Публикация поста
        logger.info("Публикация поста в LinkedIn")
        try:
            # Последняя проверка прокси перед публикацией
            if proxy_settings:
                proxy_working, proxy_error = test_proxy_connection(proxy_settings)
                if not proxy_working:
                    error_response = {
                        "status": "error",
                        "error": f"Proxy connection test failed before post creation: {proxy_error}"
                    }
                    return JSONResponse(status_code=500, content=error_response)
            
            # Генерируем ключ для проверки кэша
            cache_key = get_user_cache_key(linkedin_client_id, linkedin_access_token)
            
            # Генерируем хэш текста поста для проверки дублирования
            text_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Проверяем, не публиковали ли мы уже такой пост недавно
            current_time = datetime.now()
            
            if cache_key in sent_posts_cache:
                cache_entry = sent_posts_cache[cache_key]
                # Если такой же текст поста был опубликован менее 5 минут назад
                if cache_entry.get("text_hash") == text_hash and \
                current_time - cache_entry.get("timestamp", current_time - timedelta(minutes=10)) < timedelta(minutes=5):
                    logger.warning(f"Обнаружена попытка повторной публикации того же поста в течение 5 минут")
                    error_response = {
                        "status": "error", 
                        "error": "Duplicate post detected. Please wait at least 5 minutes before posting the same content again."
                    }
                    return JSONResponse(status_code=400, content=error_response)
            
            # Создаем пост в LinkedIn
            post_url = linkedin_client.create_post(text, image_urls)
            logger.info(f"Пост успешно опубликован: {post_url}")
            
            # Извлекаем ID поста из URL для совместимости с новым форматом
            post_id = post_url.split("/")[-1] if "/" in post_url else post_url
            
            # Обновляем кэш отправленных постов
            sent_posts_cache[cache_key] = {
                "post_id": post_id,
                "post_url": post_url,
                "text_hash": text_hash,
                "timestamp": current_time
            }
            
            response_data = {
                "status": "success",
                "message": "Пост успешно опубликован",
                "post_url": post_url,
                "post_id": post_id
            }
            
            return JSONResponse(content=response_data)
        except Exception as e:
            logger.error(f"Ошибка при публикации поста: {str(e)}")
            
            # Проверяем, не связана ли ошибка с прокси
            if proxy_settings and ("proxy" in str(e).lower() or "socket" in str(e).lower() or "connect" in str(e).lower()):
                proxy_working, proxy_error = test_proxy_connection(proxy_settings)
                if not proxy_working:
                    error_response = {
                        "status": "error",
                        "error": f"Proxy connection test failed during post creation: {proxy_error}"
                    }
                    return JSONResponse(status_code=500, content=error_response)
                    
            error_response = {
                "status": "error",
                "error": f"Post creation failed: {str(e)}"
            }
            return JSONResponse(status_code=500, content=error_response)
                        
    except Exception as e:
        logger.error(f"Ошибка при публикации поста: {str(e)}")
        error_response = {
            "status": "error",
            "error": str(e)
        }
        return JSONResponse(status_code=500, content=error_response)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=Config.HOST, port=Config.PORT, reload=True)