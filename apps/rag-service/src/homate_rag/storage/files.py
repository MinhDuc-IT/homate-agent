from pathlib import Path
from uuid import UUID


class LocalDocumentStorage:
    def __init__(self, directory): self.directory = Path(directory)

    def path(self, key):
        UUID(key.removesuffix('.txt'))
        if '/' in key or '\\' in key: raise ValueError('Invalid storage key')
        return self.directory / key

    def write(self, key, text):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path(key).write_text(text, encoding='utf-8')

    def read(self, key): return self.path(key).read_text(encoding='utf-8')
    def delete(self, key): self.path(key).unlink(missing_ok=True)
