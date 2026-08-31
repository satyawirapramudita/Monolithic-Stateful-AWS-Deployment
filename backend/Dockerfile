FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/server.py .
COPY frontend ./frontend

RUN useradd --create-home appuser \
    && mkdir -p /app/sessions \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["python", "server.py"]
