FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r src/requirements.txt
ENV PYTHONUNBUFFERED=1


ENV PYTHONPATH=/app

CMD ["alembic", "upgrade", "head"]
CMD ["python", "src/backend/server/api.py"]