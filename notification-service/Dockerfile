FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Запуск модуля app.main
CMD ["python", "-m", "app.main"]