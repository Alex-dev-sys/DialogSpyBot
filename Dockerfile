FROM python:3.12-slim

# Без .pyc и с небуферизованным выводом (логи сразу видны в docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала зависимости — для эффективного кеширования слоёв.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем исходный код.
COPY . .

# Каталог под файл SQLite (монтируется как volume в docker-compose).
RUN mkdir -p /app/data

CMD ["python", "bot.py"]
