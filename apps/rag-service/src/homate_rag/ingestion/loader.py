"""Read validated Markdown/TXT content for the ingestion pipeline."""


def load_text(content: str) -> str:
    if not content.strip(): raise ValueError('Tài liệu không được để trống')
    return content
