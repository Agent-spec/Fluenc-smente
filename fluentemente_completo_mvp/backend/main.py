from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from urllib.parse import urlparse, parse_qs
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
import re
import os
import json


app = FastAPI(
    title="Fluentemente API",
    version="0.2.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# OPENAI
# =========================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("AVISO: OPENAI_API_KEY não encontrada.")

client = OpenAI(
    api_key=OPENAI_API_KEY
) if OPENAI_API_KEY else None


# =========================================================
# MODELO DA REQUISIÇÃO
# =========================================================

class VideoRequest(BaseModel):

    url: HttpUrl

    source_language: str = "fr"

    target_language: str = "pt"


# =========================================================
# IDIOMAS
# =========================================================

LANGUAGE_NAMES = {

    "fr": "francês",

    "en": "inglês",

    "de": "alemão",

    "es": "espanhol",

    "it": "italiano",

    "sv": "sueco",

    "pt": "português",

    "ja": "japonês",

    "zh": "chinês"

}


# =========================================================
# YOUTUBE ID
# =========================================================

def youtube_id(url: str):

    parsed = urlparse(url)

    host = parsed.netloc.lower()


    if "youtu.be" in host:

        return (
            parsed.path
            .strip("/")
            .split("/")[0]
            or None
        )


    if "youtube.com" in host:

        query = parse_qs(
            parsed.query
        )


        if "v" in query:

            return query["v"][0]


        parts = (
            parsed.path
            .strip("/")
            .split("/")
        )


        if (
            len(parts) >= 2
            and parts[0] in (
                "shorts",
                "embed"
            )
        ):

            return parts[1]


    return None


# =========================================================
# LIMPAR TEXTO
# =========================================================

def clean_text(text: str):

    text = re.sub(
        r"\s+",
        " ",
        text or ""
    )

    return text.strip()


# =========================================================
# JUNTAR TRANSCRIÇÃO
# =========================================================

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
            re.search(
                r"[.!?…]$",
                combined
            )
            or len(combined) >= 95
        ):

            phrases.append({

                "start": round(
                    start,
                    2
                ),

                "duration": round(
                    duration,
                    2
                ),

                "original": combined

            })


            buffer = []

            start = None

            duration = 0.0


    if buffer:

        phrases.append({

            "start": round(
                start or 0,
                2
            ),

            "duration": round(
                duration,
                2
            ),

            "original":
                " ".join(buffer)

        })


    return phrases


# =========================================================
# PEGAR TRANSCRIÇÃO
# =========================================================

def get_transcript(
    video_id,
    language
):

    api = YouTubeTranscriptApi()


    languages = [
        language
    ]


    fallbacks = {

        "fr": [
            "fr-FR",
            "fr"
        ],

        "en": [
            "en-US",
            "en"
        ],

        "de": [
            "de-DE",
            "de"
        ],

        "es": [
            "es-ES",
            "es"
        ],

        "it": [
            "it-IT",
            "it"
        ],

        "sv": [
            "sv-SE",
            "sv"
        ],

        "pt": [
            "pt-BR",
            "pt"
        ],

        "ja": [
            "ja-JP",
            "ja"
        ],

        "zh": [
            "zh-CN",
            "zh"
        ]

    }


    languages += fallbacks.get(
        language,
        []
    )


    languages = list(
        dict.fromkeys(
            languages
        )
    )


    try:

        transcript = api.fetch(
            video_id,
            languages=languages
        )

        return transcript


    except Exception:

        try:

            transcripts = api.list(
                video_id
            )


            for transcript in transcripts:

                lang_code = getattr(
                    transcript,
                    "language_code",
                    ""
                )


                if (
                    lang_code in languages
                    or lang_code.startswith(
                        language
                    )
                ):

                    return transcript.fetch()


        except Exception as error:

            print(
                "Erro procurando transcrição:",
                error
            )


    raise HTTPException(

        status_code=422,

        detail=(
            "Não foi encontrada uma "
            "transcrição compatível "
            "para este vídeo."
        )

    )


# =========================================================
# TRADUZIR FRASES COM OPENAI
# =========================================================

def translate_phrases(
    phrases,
    source_language,
    target_language
):

    if not phrases:

        return phrases


    if source_language == target_language:

        for phrase in phrases:

            phrase["translation"] = (
                phrase["original"]
            )

        return phrases


    if not client:

        raise HTTPException(

            status_code=500,

            detail=(
                "OPENAI_API_KEY não está "
                "configurada no servidor."
            )

        )


    source_name = LANGUAGE_NAMES.get(
        source_language,
        source_language
    )


    target_name = LANGUAGE_NAMES.get(
        target_language,
        target_language
    )


    # Enviamos grupos de frases para reduzir
    # o número de chamadas à API.

    batch_size = 20


    for start_index in range(
        0,
        len(phrases),
        batch_size
    ):

        batch = phrases[
            start_index:
            start_index + batch_size
        ]


        input_phrases = [

            {
                "id": index,
                "text": item["original"]
            }

            for index, item in enumerate(
                batch
            )
        ]


        prompt = f"""
Você é o tradutor do Fluentemente,
uma plataforma de aprendizagem de idiomas.

Traduza as frases abaixo do
{source_name} para {target_name}.

REGRAS:

1. Preserve o significado original.
2. Use uma tradução natural.
3. Não faça tradução palavra por palavra quando isso soar estranho.
4. Mantenha gírias e expressões naturais quando existirem.
5. Não adicione explicações.
6. Não altere a ordem das frases.
7. Retorne SOMENTE JSON válido.
8. O JSON deve possuir uma chave chamada "translations".
9. Cada tradução deve possuir "id" e "translation".

Frases:

{json.dumps(
    input_phrases,
    ensure_ascii=False
)}
"""


        try:

            response = client.chat.completions.create(

                model="gpt-4o-mini",

                messages=[

                    {
                        "role": "system",
                        "content":
                            "Você é um tradutor preciso."
                    },

                    {
                        "role": "user",
                        "content":
                            prompt
                    }

                ],

                temperature=0.2,

                response_format={
                    "type": "json_object"
                }

            )


            content = (
                response
                .choices[0]
                .message
                .content
            )


            result = json.loads(
                content
            )


            translations = result.get(
                "translations",
                []
            )


            for translated in translations:

                item_id = translated.get(
                    "id"
                )


                translation = translated.get(
                    "translation",
                    ""
                )


                if (
                    isinstance(
                        item_id,
                        int
                    )
                    and 0 <= item_id < len(batch)
                ):

                    batch[
                        item_id
                    ]["translation"] = (
                        translation
                    )


        except Exception as error:

            print(
                "Erro na tradução:",
                error
            )


            raise HTTPException(

                status_code=500,

                detail=(
                    "Erro ao traduzir as "
                    "legendas com a IA."
                )

            )


    # Se alguma tradução não veio,
    # evita quebrar o frontend.

    for phrase in phrases:

        if "translation" not in phrase:

            phrase["translation"] = (
                "Tradução não disponível"
            )


    return phrases


# =========================================================
# ROTA PRINCIPAL
# =========================================================

@app.get("/")
def root():

    return {

        "name":
            "Fluentemente API",

        "status":
            "online",

        "message":
            "API de estudo de idiomas para vídeos do YouTube."

    }


# =========================================================
# PROCESSAR VÍDEO
# =========================================================

@app.post("/api/video")
def process_video(
    request: VideoRequest
):

    video_id = youtube_id(
        str(request.url)
    )


    if not video_id:

        raise HTTPException(

            status_code=400,

            detail:
                "URL do YouTube inválida."

        )


    source_language = (
        request.source_language.lower()
    )


    target_language = (
        request.target_language.lower()
    )


    if source_language not in LANGUAGE_NAMES:

        raise HTTPException(

            status_code=400,

            detail:
                "Idioma de origem não suportado."

        )


    if target_language not in LANGUAGE_NAMES:

        raise HTTPException(

            status_code=400,

            detail:
                "Idioma de destino não suportado."

        )


    # ---------------------------------------------
    # TRANSCRIÇÃO
    # ---------------------------------------------

    transcript = get_transcript(

        video_id,

        source_language

    )


    phrases = merge_transcript(
        transcript
    )


    if not phrases:

        raise HTTPException(

            status_code=422,

            detail:
                "A transcrição não contém texto utilizável."

        )


    # ---------------------------------------------
    # LIMITE DE 30 MINUTOS
    # ---------------------------------------------

    last = phrases[-1]


    estimated_end = (
        last["start"]
        + last["duration"]
    )


    if estimated_end > 30 * 60:

        raise HTTPException(

            status_code=413,

            detail:
                "Este MVP aceita vídeos de até 30 minutos."

        )


    # ---------------------------------------------
    # TRADUÇÃO
    # ---------------------------------------------

    phrases = translate_phrases(

        phrases,

        source_language,

        target_language

    )


    # ---------------------------------------------
    # RESPOSTA
    # ---------------------------------------------

    return {

        "video": {

            "id":
                video_id,

            "duration_estimate":
                round(
                    estimated_end,
                    2
                ),

            "youtube_url":
                f"https://www.youtube.com/watch?v={video_id}"

        },

        "source_language":
            source_language,

        "target_language":
            target_language,

        "phrases":
            phrases

    }
