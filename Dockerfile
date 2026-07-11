FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

ENV TELEGRAM_BOT_TOKEN=8512449965:AAHgQe-Ch48de--GBkHrABjj_OEuqbNwLfM
ENV API_URL=https://tarjetassubaru-production.up.railway.app

EXPOSE 8000

CMD ["sh", "-c", "python seed.py; bash start.sh"]
