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

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        # Инициализация обработчика прокси
        proxy_handler = ProxyHandler(proxy_settings)
        
        # Проверка работоспособности прокси, если они указаны
        if proxy_settings:
            if not proxy_handler.check_proxy():
                logger.warning("Указанные прокси не работают. Запросы будут выполняться напрямую.")
        
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
            # Не выбрасываем исключение здесь, так как get_user_profile теперь имеет механизмы обхода
        
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
                raise HTTPException(status_code=400, detail=f"Ошибка при обработке изображения: {str(e)}")
        
        # Публикация поста
        logger.info("Публикация поста в LinkedIn")
        post_url = linkedin_client.create_post(request_data.text, image_urls)
        logger.info(f"Пост успешно опубликован: {post_url}")
        
        # Извлекаем ID поста из URL
        post_id = post_url.split("/")[-1] if "/" in post_url else post_url
        
        # Формируем ответ в новом формате
        response_data = {
            "status": "success",
            "post_url": post_url,
            "post_id": post_id,
            "request": {
                "credentials": {
                    "client_id": request_data.client_id,
                    "client_secret": "***" + request_data.client_secret[-4:],
                    "access_token": request_data.access_token[:10] + "***"
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
        error_response = {
            "status": "error",
            "message": str(e),
            "request": {
                "credentials": {
                    "client_id": request_data.client_id,
                    "client_secret": "***" + request_data.client_secret[-4:],
                    "access_token": request_data.access_token[:10] + "***"
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
                "password": proxy_password
            }
            logger.info(f"Используются настройки прокси: {proxy_host}:{proxy_port}")
        else:
            logger.info("Прокси не указаны, запросы будут выполняться напрямую")
        
        # Инициализация обработчика прокси
        proxy_handler = ProxyHandler(proxy_settings)
        
        # Проверка работоспособности прокси, если они указаны
        if proxy_settings:
            if not proxy_handler.check_proxy():
                logger.warning("Указанные прокси не работают. Запросы будут выполняться напрямую.")
        
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
            # Не выбрасываем исключение здесь, так как get_user_profile теперь имеет механизмы обхода
        
        # Загрузка изображений, если они есть
        image_urls = []
        if images:
            logger.info(f"Загрузка {len(images)} изображений")
            for i, image in enumerate(images):
                if image.filename:  # Проверяем, что файл действительно был загружен
                    logger.info(f"Загрузка изображения {i+1}: {image.filename}")
                    image_data = await image.read()
                    image_url = linkedin_client.upload_image(image_data, image.filename)
                    image_urls.append(image_url)
                    logger.info(f"Изображение {i+1} успешно загружено: {image_url}")
        
        # Публикация поста
        logger.info("Публикация поста в LinkedIn")
        post_url = linkedin_client.create_post(text, image_urls)
        logger.info(f"Пост успешно опубликован: {post_url}")
        
        # Извлекаем ID поста из URL для совместимости с новым форматом
        post_id = post_url.split("/")[-1] if "/" in post_url else post_url
        
        response_data = {
            "status": "success",
            "message": "Пост успешно опубликован",
            "post_url": post_url,
            "post_id": post_id
        }
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        logger.error(f"Ошибка при публикации поста: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при публикации: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=Config.HOST, port=Config.PORT, reload=True)
