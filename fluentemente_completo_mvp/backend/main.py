from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi

from openai import OpenAI

import os
import re
import json


# ==================================================
# CONFIGURAÇÃO
# ==================================================

app = FastAPI(
    title="Fluentemente API",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# OPENAI
# ==================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None


# ==================================================
# MODELOS
# ==================================================

class VideoRequest(BaseModel):
    url: HttpUrl
    source_language: str = "fr"
    target_language: str = "pt"


# ==================================================
# YOUTUBE
# ==================================================

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


# ==================================================
# LIMPAR TEXTO
# ==================================================

def clean_text(text: str):

    text = re.sub(
        r"\s+",
        " ",
        text or ""
    ).strip()

    return text


# ==================================================
# JUNTAR TRANSCRIÇÃO
# ==================================================

def merge_transcript(items):

    phrases = []

    buffer = []

    start = None

    duration = 0.0

    for item in items:

        text = clean_text(
            item.text
            if hasattr(item, "text")
            else item.get("text", "")
        )

        if not text:
            continue

        item_start = float(
            item.start
            if hasattr(item, "start")
            else item.get("start", 0)
        )

        item_duration = float(
            item.duration
            if hasattr(item, "duration")
            else item.get("duration", 0)
        )

        if start is None:
            start = item_start

        buffer.append(text)

        duration += item_duration

        combined = " ".join(buffer)

        if (
            re.search(r"[.!?…]$", combined)
            or len(combined) >= 95
        ):

            phrases.append({
                "start": round(start, 2),
                "duration": round(duration, 2),
                "original": combined
            })

            buffer = []

            start = None

            duration = 0.0

    if buffer:

        phrases.append({
            "start": round(start or 0, 2),
            "duration": round(duration, 2),
            "original": " ".join(buffer)
        })

    return phrases


# ==================================================
# OBTER TRANSCRIÇÃO
# ==================================================

def get_transcript(video_id, language):

    api = YouTubeTranscriptApi()

    languages = [language]

    if language == "fr":
        languages += ["fr-FR", "fr"]

    elif language == "en":
        languages += ["en-US", "en"]

    elif language == "de":
        languages += ["de-DE", "de"]

    languages = list(
        dict.fromkeys(languages)
    )

    try:

        transcript = api.fetch(
            video_id,
            languages=languages
        )

        return transcript

    except Exception:

        try:

            transcripts = api.list(video_id)

            for t in transcripts:

                lang_code = getattr(
                    t,
                    "language_code",
                    ""
                )

                if (
                    lang_code in languages
                    or lang_code.startswith(language)
                ):

                    return t.fetch()

        except Exception:
            pass

    raise HTTPException(
        status_code=422,
        detail=(
            "Não foi encontrada uma "
            "transcrição compatível para este vídeo."
        )
    )


# ==================================================
# TRADUÇÃO COM OPENAI
# ==================================================

def translate_phrases(
    phrases,
    source_language,
    target_language
):

    # Se não houver chave configurada,
    # retorna as frases sem tradução.
    if not client:

        for phrase in phrases:

            phrase["translation"] = (
                "Tradução não configurada."
            )

            phrase["level"] = "A1"

            phrase["explanation"] = (
                "Configure a OPENAI_API_KEY no Render."
            )

        return phrases


    # Enviamos apenas o necessário para a IA.
    items = []

    for index, phrase in enumerate(phrases):

        items.append({
            "index": index,
            "text": phrase["original"]
        })


    prompt = f"""
Você é o professor de francês do aplicativo Fluentemente.

Analise as frases abaixo.

Idioma original: {source_language}
Idioma de destino: {target_language}

Para CADA frase:

1. Traduza para português brasileiro natural.
2. Classifique o nível aproximado da frase usando CEFR:
   A1, A2, B1, B2, C1 ou C2.
3. Explique de maneira curta e simples o significado ou
   alguma construção importante da frase.

IMPORTANTE:

- Não invente informações.
- Preserve o sentido original.
- Para francês informal, mantenha a tradução natural.
- Não traduza palavra por palavra quando isso produzir
  português estranho.
- A explicação deve ser curta.
- Retorne SOMENTE JSON válido.

Formato:

{{
  "translations": [
    {{
      "index": 0,
      "translation": "...",
      "level": "A1",
      "explanation": "..."
    }}
  ]
}}

Frases:

{json.dumps(items, ensure_ascii=False)}
"""


    try:

        response = client.responses.create(

            model="gpt-5.6",

            input=prompt
        )

        text = response.output_text.strip()


        # Remove possíveis cercas de Markdown
        text = re.sub(
            r"^```json\s*",
            "",
            text
        )

        text = re.sub(
            r"\s*```$",
            "",
            text
        )


        result = json.loads(text)

        translations = result.get(
            "translations",
            []
        )


        # Indexa as respostas da IA
        translation_map = {
            item["index"]: item
            for item in translations
            if "index" in item
        }


        # Junta os dados da IA com os timestamps
        for index, phrase in enumerate(phrases):

            ai_data = translation_map.get(
                index
            )

            if ai_data:

                phrase["translation"] = (
                    ai_data.get(
                        "translation",
                        "Tradução não disponível"
                    )
                )

                phrase["level"] = (
                    ai_data.get(
                        "level",
                        "A1"
                    )
                )

                phrase["explanation"] = (
                    ai_data.get(
                        "explanation",
                        "Sem explicação disponível."
                    )
                )

            else:

                phrase["translation"] = (
                    "Tradução não disponível"
                )

                phrase["level"] = "A1"

                phrase["explanation"] = (
                    "Não foi possível analisar esta frase."
                )


        return phrases


    except Exception as error:

        print(
            "Erro na tradução OpenAI:",
            error
        )

        # Se a IA falhar, o vídeo ainda funciona.
        for phrase in phrases:

            phrase["translation"] = (
                "Tradução temporariamente indisponível."
            )

            phrase["level"] = "A1"

            phrase["explanation"] = (
                "A frase foi extraída da transcrição."
            )

        return phrases


# ==================================================
# ROTA PRINCIPAL
# ==================================================

@app.get("/")
def root():

    return {
        "name": "Fluentemente API",
        "status": "online",
        "message": (
            "API de estudo de idiomas "
            "para vídeos do YouTube."
        )
    }


@app.post("/api/video")
def process_video(
    request: VideoRequest
):

    # ----------------------------------------------
    # ID DO YOUTUBE
    # ----------------------------------------------

    video_id = youtube_id(
        str(request.url)
    )

    if not video_id:

        raise HTTPException(
            status_code=400,
            detail="URL do YouTube inválida."
        )


    # ----------------------------------------------
    # TRANSCRIÇÃO
    # ----------------------------------------------

    transcript = get_transcript(
        video_id,
        request.source_language
    )


    phrases = merge_transcript(
        transcript
    )


    if not phrases:

        raise HTTPException(
            status_code=422,
            detail=(
                "A transcrição não contém "
                "texto utilizável."
            )
        )


    # ----------------------------------------------
    # LIMITE DE 30 MINUTOS
    # ----------------------------------------------

    last = phrases[-1]

    estimated_end = (
        last["start"]
        + last["duration"]
    )


    if estimated_end > 30 * 60:

        raise HTTPException(
            status_code=413,
            detail=(
                "Este MVP aceita vídeos "
                "de até 30 minutos."
            )
        )


    # ----------------------------------------------
    # OPENAI
    # ----------------------------------------------

    phrases = translate_phrases(
        phrases,
        request.source_language,
        request.target_language
    )


    # ----------------------------------------------
    # RESPOSTA
    # ----------------------------------------------

    return {

        "video": {

            "id": video_id,

            "duration_estimate": round(
                estimated_end,
                2
            ),

            "youtube_url":
                f"https://www.youtube.com/watch?v={video_id}"
        },

        "source_language":
            request.source_language,

        "target_language":
            request.target_language,

        "phrases":
            phrases,

        "ai_translation":
            bool(client)
    }
