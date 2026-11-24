"""Renaming a demo device must replace its generated guide, not manual uploads."""
import importlib.util
from pathlib import Path
import sys

import httpx


def test_renamed_generated_guide_is_replaced_without_deleting_manual(monkeypatch, tmp_path):
    source = Path(__file__).resolve().parents[3] / 'tools/seed_device_knowledge.py'
    spec = importlib.util.spec_from_file_location('seed_guides', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    deleted = []
    created = []
    device = {'id': 'light-balcony', 'name': 'Living light 2', 'room': 'living', 'kind': 'bulb',
              'controls': [{'type': 'toggle', 'key': 'power', 'label': 'Power'}]}

    def handle(request):
        path = request.url.path
        if path.endswith('/agent/tools'):
            return httpx.Response(200, json={'rooms': [{'id': 'living', 'label': 'Living'}], 'devices': [device]})
        if path == '/api/rag/documents' and request.method == 'GET':
            return httpx.Response(200, json={'documents': [
                {'id': 'old-generated', 'filename': 'light-balcony.md', 'title': module.GUIDE_PREFIX + 'Old balcony light', 'device_ids': ['light-balcony']},
                {'id': 'manual', 'filename': 'light-balcony.md', 'title': 'User manual', 'device_ids': ['light-balcony']},
            ]})
        if path.endswith('/source'): return httpx.Response(200, text='Old generated content')
        if path == '/api/rag/documents' and request.method == 'POST':
            created.append(request.content)
            return httpx.Response(201, json={'id': 'replacement'})
        if request.method == 'DELETE':
            deleted.append(path.rsplit('/', 1)[1])
            return httpx.Response(204)
        raise AssertionError((request.method, path))

    real_client = httpx.Client
    monkeypatch.setattr(module.httpx, 'Client', lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(handle)))
    monkeypatch.setenv('HOMATE_ACCESS_TOKEN', 'test-token')
    monkeypatch.setattr(sys, 'argv', ['seed', '--output', str(tmp_path), '--replace-generated'])
    module.main()
    assert len(created) == 1 and deleted == ['old-generated']
    assert 'Living light 2' in (tmp_path / 'light-balcony.md').read_text(encoding='utf-8')
    assert 'document_id' not in (tmp_path / 'manifest.json').read_text(encoding='utf-8')
