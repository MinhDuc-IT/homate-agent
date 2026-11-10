import threading
from functools import lru_cache
from homate_rag.embedding.model import MODEL


class EmbeddingUnavailable(RuntimeError): pass


class LocalEmbeddings:
    def __init__(self, directory):
        self.directory = directory
        self.lock = threading.Lock()

    @lru_cache(maxsize=1)
    def encoder(self):
        from fastembed import TextEmbedding
        return TextEmbedding(model_name=MODEL, cache_dir=self.directory, threads=2)

    def embed(self, texts):
        try:
            with self.lock:
                return [vector.tolist() for vector in self.encoder().embed(texts, batch_size=32)]
        except Exception:
            raise EmbeddingUnavailable('Model embedding chưa sẵn sàng; vui lòng thử lại.') from None
