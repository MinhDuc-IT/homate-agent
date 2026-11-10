"""Load -> chunk -> embed -> index, with source-file persistence."""
from uuid import uuid4
from homate_rag.ingestion.loader import load_text
from homate_rag.ingestion.chunking import split_document
from homate_rag.embedding.model import MODEL, validate_vectors


class IngestionPipeline:
    def __init__(self, index, embeddings, storage, devices):
        self.index, self.embeddings, self.storage, self.devices = index, embeddings, storage, devices

    def run(self, user, title, filename, content, device_ids):
        device_ids = list(dict.fromkeys(device_ids))
        self.devices.validate(device_ids)
        content = load_text(content)
        chunks = split_document(content)
        vectors = self.embeddings.embed([c['content'] for c in chunks])
        validate_vectors(vectors, len(chunks))
        identifier = str(uuid4())
        key = identifier + '.txt'
        document = dict(id=identifier, home_id=user['home_id'], created_by=user['id'], title=title,
            filename=filename, storage_key=key, model=MODEL, device_ids=device_ids)
        self.storage.write(key, content)
        try:
            self.index.create(document, chunks, vectors)
        except Exception:
            self.storage.delete(key)
            raise
        return self.index.get(user['home_id'], identifier)

