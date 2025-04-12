#!/bin/bash

# Скрипт для тестирования LinkedIn Poster API

echo "Запуск тестирования LinkedIn Poster API..."

# Создаем тестовый файл изображения
echo "Создание тестового изображения..."
cat > test_image.txt << EOL
Это тестовое изображение для LinkedIn Poster API.
Данный файл используется только для тестирования загрузки файлов.
EOL

# Запускаем сервис
echo "Запуск сервиса..."
cd /home/ubuntu/LinkedInPoster
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 5001 &
PID=$!

# Ждем запуска сервиса
echo "Ожидание запуска сервиса..."
sleep 5

# Проверяем, что сервис запущен
echo "Проверка работоспособности сервиса..."
HEALTH_CHECK=$(curl -s http://localhost:5001/health)
echo "Ответ от /health: $HEALTH_CHECK"

echo "Тестирование завершено. Сервис запущен на http://localhost:5001"
echo "Вы можете открыть веб-интерфейс в браузере и протестировать API."
echo "Для остановки сервиса выполните: kill $PID"

# Оставляем сервис запущенным для ручного тестирования
echo "PID сервиса: $PID"
