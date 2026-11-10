FROM python:3.11-slim
WORKDIR /app
ENV MODEL_CACHE=/models KNOWLEDGE_DIRECTORY=/data/knowledge
COPY pyproject.toml ./
RUN python -c "import subprocess,tomllib; subprocess.check_call(['pip','install','--no-cache-dir',*tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']])"
COPY src/homate_rag/embedding/model.py /tmp/knowledge.py
RUN python -c "import runpy; from fastembed import TextEmbedding; TextEmbedding(model_name=runpy.run_path('/tmp/knowledge.py')['MODEL'],cache_dir='/models',threads=2)"
COPY src ./src
RUN pip install --no-cache-dir --no-deps .
CMD ["uvicorn", "homate_rag.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "9030"]
