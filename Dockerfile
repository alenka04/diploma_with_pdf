FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    tesseract-ocr \
    tesseract-ocr-rus \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Настройка Hugging Face и Tesseract
ENV HF_HOME=/app/models
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# Создаём папку для моделей
RUN mkdir -p $HF_HOME

# Копируем весь проект
COPY . .

# Экспонируем порт
EXPOSE 8000

# Запускаем сервер
CMD ["uvicorn", "back.main:app", "--host", "0.0.0.0", "--port", "8000"]