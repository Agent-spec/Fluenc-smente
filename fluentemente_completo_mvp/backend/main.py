from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from urllib.parse import urlparse, parse_qs
import re
from youtube_transcript_api import YouTubeTranscriptApi

app = FastAPI(title="Fluentemente API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: HttpUrl
    source_language: str = "fr"
    target_language: str = "pt"

def youtube_id(url: str):
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if "youtu.be" in host:
        return parsed.path.strip("/").split("/")[0] or None

    if "youtube.com" in host:
        query = parse_qs(parsed.query)
        if "v" in query:
            return query["v"][0]
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in ("shorts", "embed"):
            return parts[1]

    return None

def clean_text(text: str):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text

def merge_transcript(items):
    # Junta blocos muito curtos para formar unidades de estudo mais naturais.
    phrases=[]
    buffer=[]
    start=None
    duration=0.0

    for item in items:
        text=clean_text(item.text if hasattr(item, "text") else item.get("text",""))
        if not text:
            continue

        item_start=float(item.start if hasattr(item, "start") else item.get("start",0))
        item_duration=float(item.duration if hasattr(item, "duration") else item.get("duration",0))

        if start is None:
            start=item_start

        buffer.append(text)
        duration += item_duration
        combined=" ".join(buffer)

        # Cria uma unidade quando há pontuação ou quando a frase já ficou longa.
        if re.search(r"[.!?…]$", combined) or len(combined) >= 95:
            phrases.append({
                "start": round(start,2),
                "duration": round(duration,2),
                "original": combined
            })
            buffer=[]
            start=None
            duration=0.0

    if buffer:
        phrases.append({
            "start": round(start or 0,2),
            "duration": round(duration,2),
            "original": " ".join(buffer)
        })

    return phrases

def get_transcript(video_id, language):
    api = YouTubeTranscriptApi()

    # O código tenta primeiro o idioma escolhido e depois alguns fallbacks.
    languages = [language]
    if language == "fr":
        languages += ["fr-FR", "fr"]
    elif language == "en":
        languages += ["en-US", "en"]
    elif language == "de":
        languages += ["de-DE", "de"]

    # Remove duplicatas preservando ordem.
    languages=list(dict.fromkeys(languages))

    try:
        transcript = api.fetch(video_id, languages=languages)
        return transcript
    except Exception:
        try:
            # Fallback: tenta localizar uma transcrição disponível.
            transcripts = api.list(video_id)
            for t in transcripts:
                lang_code=getattr(t, "language_code", "")
                if lang_code in languages or lang_code.startswith(language):
                    return t.fetch()
        except Exception:
            pass

    raise HTTPException(
        status_code=422,
        detail="Não foi encontrada uma transcrição compatível para este vídeo."
    )

@app.get("/")
def root():
    return {
        "name": "Fluentemente API",
        "status": "online",
        "message": "API de estudo de idiomas para vídeos do YouTube."
    }

@app.post("/api/video")
def process_video(request: VideoRequest):
    video_id = youtube_id(str(request.url))

    if not video_id:
        raise HTTPException(status_code=400, detail="URL do YouTube inválida.")

    transcript = get_transcript(video_id, request.source_language)
    phrases = merge_transcript(transcript)

    if not phrases:
        raise HTTPException(status_code=422, detail="A transcrição não contém texto utilizável.")

    # Limite de 30 minutos. Como a API de transcrição fornece timestamps,
    # usamos o maior instante conhecido como aproximação segura do tamanho.
    last = phrases[-1]
    estimated_end = last["start"] + last["duration"]

    if estimated_end > 30 * 60:
        raise HTTPException(
            status_code=413,
            detail="Este MVP aceita vídeos de até 30 minutos."
        )

    return {
        "video": {
            "id": video_id,
            "duration_estimate": round(estimated_end, 2),
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}"
        },
        "source_language": request.source_language,
        "target_language": request.target_language,
        "phrases": phrases,
        "note": "Tradução e análise lexical podem ser adicionadas ao próximo serviço da pipeline."
    }
