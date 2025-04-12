from app.config import Config
from app.proxy_handler import ProxyHandler
from app.linkedin_client import LinkedInClient
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import uvicorn
import os
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LinkedIn Poster API", 
              description="API для публикации контента в LinkedIn с обязательной поддержкой прокси",
              version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настраиваем шаблоны
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/post")
async def create_post(
    linkedin_client_id: str = Form(...),
    linkedin_client_secret: str = Form(...),
    linkedin_access_token: str = Form(...),
    text: str = Form(...),
    images: List[UploadFile] = File(None),
    proxy_host: str = Form(...),  # Теперь обязательный параметр
    proxy_port: int = Form(...),  # Теперь обязательный параметр
    proxy_username: Optional[str] = Form(None),
    proxy_password: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    try:
        logger.info(f"Получен запрос на публикацию поста. Текст: {text[:50]}...")
        
        # Проверка наличия прокси (теперь обязательно)
        if not proxy_host or not proxy_port:
            logger.error("Отсутствуют обязательные настройки прокси")
            raise HTTPException(status_code=400, detail="Для публикации постов требуется использование прокси. Пожалуйста, укажите proxy_host и proxy_port.")
        
        # Настройка прокси
        proxy_settings = {
            "host": proxy_host,
            "port": proxy_port,
            "username": proxy_username,
            "password": proxy_password
        }
        logger.info(f"Используются настройки прокси: {proxy_host}:{proxy_port}")
        
        # Инициализация клиента LinkedIn с прокси и опциональным user_id
        proxy_handler = ProxyHandler(proxy_settings)
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
        
        response_data = {
            "status": "success",
            "message": "Пост успешно опубликован",
            "post_url": post_url
        }
        
        # Пример JSON для документации
        example_request = {
            "linkedin_client_id": "YOUR_CLIENT_ID",
            "linkedin_client_secret": "YOUR_CLIENT_SECRET",
            "linkedin_access_token": "YOUR_ACCESS_TOKEN",
            "text": "Текст вашего поста",
            "images": ["image1.jpg", "image2.jpg"],
            "proxy_host": "proxy.example.com",  # Обязательный параметр
            "proxy_port": 8080,                 # Обязательный параметр
            "proxy_username": "proxy_user",
            "proxy_password": "proxy_pass",
            "user_id": "optional-linkedin-user-id"
        }
        
        example_response = {
            "status": "success",
            "message": "Пост успешно опубликован",
            "post_url": "https://www.linkedin.com/feed/update/urn:li:share:1234567890"
        }
        
        # Добавляем примеры в ответ для документации
        response_data["example_request"] = example_request
        response_data["example_response"] = example_response
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        logger.error(f"Ошибка при публикации поста: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при публикации: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "LinkedIn Poster API", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=Config.HOST, port=Config.PORT, reload=True)
