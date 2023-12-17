# Используем официальный образ Python
FROM python:3.10-alpine3.17

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /opt/bot

# Обновляем pip до последней версии
RUN pip install --no-cache-dir --upgrade pip

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install -r requirements.txt

# Команда, которая будет выполнена при запуске контейнера
CMD ["python", "main.py"]
