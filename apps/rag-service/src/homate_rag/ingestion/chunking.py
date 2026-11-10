"""Overlapping text windows for indexing documents."""
import re


def split_document(text: str) -> list[dict]:
    # Small windows keep multilingual passages within the encoder token budget.
    chunks = []
    paragraphs = re.split(r'\n\s*\n', text.strip())
    for paragraph in paragraphs:
        for start in range(0, len(paragraph), 320):
            content = paragraph[start:start + 400].strip()
            if content:
                chunks.append({'content':content, 'metadata':{'paragraph':len(chunks) + 1}})
    return chunks

