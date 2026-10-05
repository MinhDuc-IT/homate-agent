FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY migrations ./migrations
CMD ["sh", "-c", "alembic upgrade head && uvicorn homate.bootstrap:create_app --factory --host 0.0.0.0 --port 8000"]
