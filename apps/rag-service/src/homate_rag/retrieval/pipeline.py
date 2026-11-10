"""Question -> query embedding -> vector search -> source context."""
from homate_rag.embedding.model import validate_vectors
from homate_rag.retrieval.context import build_context


class RetrievalPipeline:
    def __init__(self, index, embeddings, devices):
        self.index, self.embeddings, self.devices = index, embeddings, devices

    def run(self, home_id, query, device_id=None, limit=5):
        if device_id: self.devices.validate([device_id])
        vectors = self.embeddings.embed([query])
        validate_vectors(vectors, 1)
        return build_context(self.index.search(home_id, vectors[0], device_id, limit, 0.35))

