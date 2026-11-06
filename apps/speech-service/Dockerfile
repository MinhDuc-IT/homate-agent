FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY download_models.py .
RUN python download_models.py
COPY app.py recognizer.py ./
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9020"]
