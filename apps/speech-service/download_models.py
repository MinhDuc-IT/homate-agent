"""Download known model files; run during image build or local setup."""
from pathlib import Path
from urllib.request import urlretrieve

root = Path(__file__).parent / 'models'
stt = root / 'sherpa-onnx-zipformer-vi-30M-int8-2026-02-09'
stt.mkdir(parents=True, exist_ok=True)
base = 'https://huggingface.co/csukuangfj2/sherpa-onnx-zipformer-vi-30M-int8-2026-02-09/resolve/main/'
for name in ('encoder.int8.onnx', 'decoder.onnx', 'joiner.int8.onnx', 'tokens.txt'):
    target = stt / name
    if not target.exists():
        temporary = target.with_name(target.name + '.part')
        urlretrieve(base + name, temporary)
        temporary.replace(target)
tts = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/vi/vi_VN/vais1000/medium/'
for name in ('vi_VN-vais1000-medium.onnx', 'vi_VN-vais1000-medium.onnx.json'):
    target = root / name
    if not target.exists():
        temporary = target.with_name(target.name + '.part')
        urlretrieve(tts + name, temporary)
        temporary.replace(target)
