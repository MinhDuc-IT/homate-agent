"""Embedding identity and vector shape shared by indexing and search."""
import math

MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
DIMENSIONS = 384


def validate_vectors(vectors, count):
    if len(vectors) != count or any(len(v) != DIMENSIONS or not all(math.isfinite(x) for x in v) or not any(v) for v in vectors):
        raise ValueError('Embedding service returned invalid vectors')

