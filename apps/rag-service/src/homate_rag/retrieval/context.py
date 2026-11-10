"""Format retrieved passages with metadata and authenticated source locations."""
import json


def build_context(matches):
    sources = []
    for match in matches:
        metadata = match['metadata']
        if isinstance(metadata, str): metadata = json.loads(metadata)
        sources.append({**match, 'metadata':metadata,
            'source':f"/api/rag/documents/{match['document_id']}/source"})
    return sources
