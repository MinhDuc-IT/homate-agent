FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py catalog.py control.py devices.json profiles.json ./
CMD ["python", "-u", "app.py"]
