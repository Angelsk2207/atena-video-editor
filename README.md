# Atena Video Editor

Web app open-source para transformar vídeos curtos com legendas automáticas e cortes.

## MVP atual
- Upload de vídeo
- Transcrição com faster-whisper (se `WHISPER_MODEL` estiver disponível)
- Legendas SRT
- Exportação MP4 com FFmpeg
- Interface simples, responsiva e sem marca d'água

## Executar
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

FFmpeg precisa estar instalado no servidor. Para o primeiro deploy, use `WHISPER_MODEL=small` ou `base`.

> B-roll automático e efeitos inteligentes entram na próxima camada; não vou fingir que estão prontos nesta primeira versão.
