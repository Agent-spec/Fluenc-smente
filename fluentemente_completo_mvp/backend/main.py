from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi

import requests
import re


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="Fluentemente API",
    version="0.3.0"
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
# MODELO DA REQUISIÇÃO
# =========================================================

class VideoRequest(BaseModel):

    url: HttpUrl

    source_language: str = "fr"

    target_language: str = "pt"


# =========================================================
# IDIOMAS SUPORTADOS
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


    # -----------------------------------------------------
    # youtu.be
    # -----------------------------------------------------

    if "youtu.be" in host:

        return (
            parsed.path
            .strip("/")
            .split("/")[0]
            or None
        )


    # -----------------------------------------------------
    # youtube.com
    # -----------------------------------------------------

    if "youtube.com" in host:

        query = parse_qs(
            parsed.query
        )


        # youtube.com/watch?v=XXXX

        if "v" in query:

            return query["v"][0]


        parts = (
            parsed.path
            .strip("/")
            .split("/")
        )


        # youtube.com/shorts/XXXX
        # youtube.com/embed/XXXX

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

        # -------------------------------------------------
        # Pegar texto
        # -------------------------------------------------

        text = clean_text(

            item.text
            if hasattr(item, "text")
            else item.get("text", "")

        )


        if not text:

            continue


        # -------------------------------------------------
        # Tempo inicial
        # -------------------------------------------------

        item_start = float(

            item.start
            if hasattr(item, "start")
            else item.get("start", 0)

        )


        # -------------------------------------------------
        # Duração
        # -------------------------------------------------

        item_duration = float(

            item.duration
            if hasattr(item, "duration")
            else item.get("duration", 0)

        )


        # -------------------------------------------------
        # Início da frase
        # -------------------------------------------------

        if start is None:

            start = item_start


        buffer.append(text)

        duration += item_duration

        combined = " ".join(buffer)


        # -------------------------------------------------
        # Finalizar frase
        # -------------------------------------------------

        if (

            re.search(
                r"[.!?…]$",
                combined
            )

            or len(combined) >= 95

        ):

            phrases.append({

                "start":
                    round(
                        start,
                        2
                    ),

                "duration":
                    round(
                        duration,
                        2
                    ),

                "original":
                    combined

            })


            buffer = []

            start = None

            duration = 0.0


    # =====================================================
    # ÚLTIMA FRASE
    # =====================================================

    if buffer:

        phrases.append({

            "start":
                round(
                    start or 0,
                    2
                ),

            "duration":
                round(
                    duration,
                    2
                ),

            "original":
                " ".join(buffer)

        })


    return phrases


# =========================================================
# PEGAR TRANSCRIÇÃO DO YOUTUBE
# =========================================================

def get_transcript(
    video_id,
    language
):

    api = YouTubeTranscriptApi()


    # -----------------------------------------------------
    # Idioma principal
    # -----------------------------------------------------

    languages = [
        language
    ]


    # -----------------------------------------------------
    # Fallbacks
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # Remover duplicados
    # -----------------------------------------------------

    languages = list(
        dict.fromkeys(
            languages
        )
    )


    # =====================================================
    # PRIMEIRA TENTATIVA
    # =====================================================

    try:

        transcript = api.fetch(

            video_id,

            languages=languages

        )

        return transcript


    except Exception as error:

        print(
            "Primeira tentativa de transcrição falhou:",
            error
        )


    # =====================================================
    # SEGUNDA TENTATIVA
    # =====================================================

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


    # =====================================================
    # ERRO
    # =====================================================

    raise HTTPException(

        status_code=422,

        detail=(

            "Não foi encontrada uma "
            "transcrição compatível "
            "para este vídeo."

        )

    )


# =========================================================
# TRADUZIR UMA FRASE COM MYMEMORY
# =========================================================

def translate_text(
    text,
    source_language,
    target_language
):

    try:

        response = requests.get(

            "https://api.mymemory.translated.net/get",

            params={

                "q":
                    text,

                "langpair":
                    f"{source_language}|{target_language}"

            },

            timeout=30

        )


        # -------------------------------------------------
        # Verificar resposta HTTP
        # -------------------------------------------------

        response.raise_for_status()


        data = response.json()


        # -------------------------------------------------
        # Verificar resposta da API
        # -------------------------------------------------

        response_data = data.get(
            "responseData",
            {}
        )


        translation = response_data.get(
            "translatedText"
        )


        if not translation:

            raise ValueError(
                "MyMemory não retornou tradução."
            )


        return translation


    except requests.exceptions.Timeout:

        print(
            "MyMemory demorou demais para responder."
        )

        raise HTTPException(

            status_code=504,

            detail=(
                "O serviço de tradução "
                "demorou demais para responder."
            )

        )


    except requests.exceptions.RequestException as error:

        print(
            "Erro de conexão com MyMemory:",
            error
        )

        raise HTTPException(

            status_code=502,

            detail=(
                "Não foi possível conectar "
                "ao serviço de tradução."
            )

        )


    except Exception as error:

        print(
            "Erro na tradução:",
            error
        )

        raise HTTPException(

            status_code=500,

            detail=(
                "Erro ao traduzir as legendas."
            )

        )


# =========================================================
# TRADUZIR TODAS AS FRASES
# =========================================================

def translate_phrases(

    phrases,

    source_language,

    target_language

):

    # -----------------------------------------------------
    # Não há frases
    # -----------------------------------------------------

    if not phrases:

        return phrases


    # -----------------------------------------------------
    # Mesmo idioma
    # -----------------------------------------------------

    if source_language == target_language:

        for phrase in phrases:

            phrase["translation"] = (
                phrase["original"]
            )

        return phrases


    # -----------------------------------------------------
    # Traduzir
    # -----------------------------------------------------

    for index, phrase in enumerate(phrases):

        print(

            f"Traduzindo frase "
            f"{index + 1}/{len(phrases)}"

        )


        translation = translate_text(

            phrase["original"],

            source_language,

            target_language

        )


        phrase["translation"] = translation


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

    # =====================================================
    # PEGAR ID DO YOUTUBE
    # =====================================================

    video_id = youtube_id(

        str(request.url)

    )


    if not video_id:

        raise HTTPException(

            status_code=400,

            detail=
                "URL do YouTube inválida."

        )


    # =====================================================
    # IDIOMAS
    # =====================================================

    source_language = (

        request.source_language.lower()

    )


    target_language = (

        request.target_language.lower()

    )


    # =====================================================
    # VALIDAR IDIOMA DE ORIGEM
    # =====================================================

    if source_language not in LANGUAGE_NAMES:

        raise HTTPException(

            status_code=400,

            detail=
                "Idioma de origem não suportado."

        )


    # =====================================================
    # VALIDAR IDIOMA DE DESTINO
    # =====================================================

    if target_language not in LANGUAGE_NAMES:

        raise HTTPException(

            status_code=400,

            detail=
                "Idioma de destino não suportado."

        )


    # =====================================================
    # PEGAR TRANSCRIÇÃO
    # =====================================================

    transcript = get_transcript(

        video_id,

        source_language

    )


    # =====================================================
    # ORGANIZAR FRASES
    # =====================================================

    phrases = merge_transcript(

        transcript

    )


    if not phrases:

        raise HTTPException(

            status_code=422,

            detail=
                "A transcrição não contém texto utilizável."

        )


    # =====================================================
    # LIMITE DE 30 MINUTOS
    # =====================================================

    last = phrases[-1]


    estimated_end = (

        last["start"]

        + last["duration"]

    )


    if estimated_end > 30 * 60:

        raise HTTPException(

            status_code=413,

            detail=
                "Este MVP aceita vídeos de até 30 minutos."

        )


    # =====================================================
    # TRADUZIR
    # =====================================================

    phrases = translate_phrases(

        phrases,

        source_language,

        target_language

    )


    # =====================================================
    # RESPOSTA
    # =====================================================

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
                (
                    "https://www.youtube.com/watch?v="
                    + video_id
                )

        },

        "source_language":
            source_language,

        "target_language":
            target_language,

        "phrases":
            phrases

    }
        "phrases":
            phrases

    }
