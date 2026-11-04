FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
CMD ["uvicorn", "homate_ai.bootstrap:create_app", "--factory", "--host", "0.0.0.0", "--port", "8010"]
