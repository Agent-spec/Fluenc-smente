from fastapi import (
    FastAPI,
    HTTPException,
    Depends
)

from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm
)

from pydantic import (
    BaseModel,
    HttpUrl
)

from urllib.parse import (
    urlparse,
    parse_qs
)

from youtube_transcript_api import (
    YouTubeTranscriptApi
)

from pwdlib import PasswordHash

import jwt
import requests
import re
import sqlite3
import os
import secrets
from datetime import datetime, timedelta, timezone


# =========================================================
# CONFIGURAÇÃO
# =========================================================

app = FastAPI(
    title="Fluentemente API",
    version="0.4.0"
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
# SEGURANÇA
# =========================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "CHAVE-DE-TESTE-TROQUE-NO-RENDER"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_DAYS = 7

MAX_DEVICES_PER_USER = 1


password_hash = PasswordHash.recommended()


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/login"
)


# =========================================================
# BANCO DE DADOS
# =========================================================

DATABASE = "fluentemente.db"


def get_db():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    db = get_db()

    cursor = db.cursor()


    # -----------------------------------------------------
    # Usuários
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            email TEXT UNIQUE NOT NULL,

            password_hash TEXT NOT NULL,

            active INTEGER DEFAULT 1,

            created_at TEXT NOT NULL

        )
    """)


    # -----------------------------------------------------
    # Dispositivos
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            device_token TEXT NOT NULL,

            created_at TEXT NOT NULL,

            last_seen TEXT NOT NULL,

            FOREIGN KEY(user_id)
                REFERENCES users(id)

        )
    """)


    db.commit()

    db.close()


init_database()


# =========================================================
# MODELOS
# =========================================================

class RegisterRequest(BaseModel):

    email: str

    password: str


class DeviceRequest(BaseModel):

    device_id: str


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
# FUNÇÕES DE AUTENTICAÇÃO
# =========================================================

def create_access_token(user_id):

    expiration = datetime.now(
        timezone.utc
    ) + timedelta(
        days=ACCESS_TOKEN_EXPIRE_DAYS
    )


    payload = {

        "sub": str(user_id),

        "exp": expiration

    }


    return jwt.encode(

        payload,

        SECRET_KEY,

        algorithm=ALGORITHM

    )


def get_current_user(
    token: str = Depends(oauth2_scheme)
):

    credentials_exception = HTTPException(

        status_code=401,

        detail="Não autenticado.",

        headers={
            "WWW-Authenticate": "Bearer"
        }

    )


    try:

        payload = jwt.decode(

            token,

            SECRET_KEY,

            algorithms=[ALGORITHM]

        )


        user_id = payload.get(
            "sub"
        )


        if not user_id:

            raise credentials_exception


    except jwt.ExpiredSignatureError:

        raise HTTPException(

            status_code=401,

            detail="Sessão expirada."

        )


    except jwt.InvalidTokenError:

        raise credentials_exception


    db = get_db()

    user = db.execute(

        """
        SELECT *
        FROM users
        WHERE id = ?
        """,

        (user_id,)

    ).fetchone()


    db.close()


    if not user:

        raise credentials_exception


    if not user["active"]:

        raise HTTPException(

            status_code=403,

            detail="Usuário bloqueado."

        )


    return user


# =========================================================
# VERIFICAR DISPOSITIVO
# =========================================================

def check_device(
    user_id,
    device_id
):

    if not device_id:

        raise HTTPException(

            status_code=400,

            detail="Identificador do dispositivo ausente."

        )


    db = get_db()


    devices = db.execute(

        """
        SELECT *
        FROM devices
        WHERE user_id = ?
        """,

        (user_id,)

    ).fetchall()


    # -----------------------------------------------------
    # Dispositivo já cadastrado
    # -----------------------------------------------------

    for device in devices:

        if device["device_token"] == device_id:

            db.execute(

                """
                UPDATE devices
                SET last_seen = ?
                WHERE id = ?
                """,

                (
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                    device["id"]
                )

            )

            db.commit()

            db.close()

            return True


    # -----------------------------------------------------
    # Limite atingido
    # -----------------------------------------------------

    if len(devices) >= MAX_DEVICES_PER_USER:

        db.close()

        raise HTTPException(

            status_code=403,

            detail=(
                "Esta conta já está vinculada "
                "a outro dispositivo."
            )

        )


    # -----------------------------------------------------
    # Registrar novo dispositivo
    # -----------------------------------------------------

    now = datetime.now(
        timezone.utc
    ).isoformat()


    db.execute(

        """
        INSERT INTO devices
        (
            user_id,
            device_token,
            created_at,
            last_seen
        )

        VALUES (?, ?, ?, ?)
        """,

        (
            user_id,
            device_id,
            now,
            now
        )

    )


    db.commit()

    db.close()

    return True


# =========================================================
# CADASTRAR USUÁRIO
# =========================================================

@app.post("/api/register")
def register(
    request: RegisterRequest
):

    email = request.email.strip().lower()

    password = request.password


    if len(password) < 6:

        raise HTTPException(

            status_code=400,

            detail=(
                "A senha precisa ter pelo menos "
                "6 caracteres."
            )

        )


    if "@" not in email:

        raise HTTPException(

            status_code=400,

            detail="E-mail inválido."

        )


    db = get_db()


    existing = db.execute(

        """
        SELECT id
        FROM users
        WHERE email = ?
        """,

        (email,)

    ).fetchone()


    if existing:

        db.close()

        raise HTTPException(

            status_code=409,

            detail="Este e-mail já está cadastrado."

        )


    hashed_password = password_hash.hash(
        password
    )


    now = datetime.now(
        timezone.utc
    ).isoformat()


    cursor = db.execute(

        """
        INSERT INTO users
        (
            email,
            password_hash,
            active,
            created_at
        )

        VALUES (?, ?, ?, ?)
        """,

        (
            email,
            hashed_password,
            1,
            now
        )

    )


    user_id = cursor.lastrowid


    db.commit()

    db.close()


    return {

        "message":
            "Usuário criado com sucesso.",

        "user_id":
            user_id

    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/api/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends()
):

    email = form_data.username.strip().lower()

    password = form_data.password


    db = get_db()


    user = db.execute(

        """
        SELECT *
        FROM users
        WHERE email = ?
        """,

        (email,)

    ).fetchone()


    db.close()


    if not user:

        raise HTTPException(

            status_code=401,

            detail="E-mail ou senha incorretos."

        )


    if not password_hash.verify(

        password,

        user["password_hash"]

    ):

        raise HTTPException(

            status_code=401,

            detail="E-mail ou senha incorretos."

        )


    if not user["active"]:

        raise HTTPException(

            status_code=403,

            detail="Esta conta está bloqueada."

        )


    token = create_access_token(
        user["id"]
    )


    return {

        "access_token":
            token,

        "token_type":
            "bearer",

        "user_id":
            user["id"],

        "email":
            user["email"]

    }


# =========================================================
# VALIDAR DISPOSITIVO
# =========================================================

@app.post("/api/device")
def register_device(

    request: DeviceRequest,

    user = Depends(
        get_current_user
    )

):

    check_device(

        user["id"],

        request.device_id

    )


    return {

        "success":
            True,

        "message":
            "Dispositivo autorizado."

    }


# =========================================================
# LOGOUT
# =========================================================

@app.delete("/api/device")
def logout_device(

    request: DeviceRequest,

    user = Depends(
        get_current_user
    )

):

    db = get_db()


    db.execute(

        """
        DELETE FROM devices

        WHERE user_id = ?

        AND device_token = ?

        """,

        (
            user["id"],

            request.device_id

        )

    )


    db.commit()

    db.close()


    return {

        "success":
            True,

        "message":
            "Dispositivo removido."

    }


# =========================================================
# USUÁRIO ATUAL
# =========================================================

@app.get("/api/me")
def me(

    user = Depends(
        get_current_user
    )

):

    return {

        "id":
            user["id"],

        "email":
            user["email"],

        "active":
            bool(user["active"])

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

            else item.get(
                "text",
                ""
            )

        )


        if not text:

            continue


        item_start = float(

            item.start

            if hasattr(item, "start")

            else item.get(
                "start",
                0
            )

        )


        item_duration = float(

            item.duration

            if hasattr(item, "duration")

            else item.get(
                "duration",
                0
            )

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


    except Exception as error:

        print(
            "Primeira tentativa falhou:",
            error
        )


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
# TRADUZIR UMA FRASE
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
                    (
                        f"{source_language}"
                        f"|"
                        f"{target_language}"
                    )

            },

            timeout=30

        )


        response.raise_for_status()


        data = response.json()


        translation = (

            data

            .get(
                "responseData",
                {}
            )

            .get(
                "translatedText"
            )

        )


        if not translation:

            raise ValueError(
                "MyMemory não retornou tradução."
            )


        return translation


    except requests.exceptions.Timeout:

        raise HTTPException(

            status_code=504,

            detail=(
                "O serviço de tradução "
                "demorou demais para responder."
            )

        )


    except requests.exceptions.RequestException as error:

        print(
            "Erro MyMemory:",
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
# TRADUZIR FRASES
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


    for index, phrase in enumerate(
        phrases
    ):

        print(

            f"Traduzindo "
            f"{index + 1}/"
            f"{len(phrases)}"

        )


        phrase["translation"] = (

            translate_text(

                phrase["original"],

                source_language,

                target_language

            )

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
            "API de estudo de idiomas."

    }


# =========================================================
# PROCESSAR VÍDEO
# =========================================================

@app.post("/api/video")
def process_video(

    request: VideoRequest,

    user = Depends(
        get_current_user
    )

):

    # -----------------------------------------------------
    # ID DO YOUTUBE
    # -----------------------------------------------------

    video_id = youtube_id(

        str(request.url)

    )


    if not video_id:

        raise HTTPException(

            status_code=400,

            detail=
                "URL do YouTube inválida."

        )


    # -----------------------------------------------------
    # IDIOMAS
    # -----------------------------------------------------

    source_language = (

        request.source_language.lower()

    )


    target_language = (

        request.target_language.lower()

    )


    if source_language not in LANGUAGE_NAMES:

        raise HTTPException(

            status_code=400,

            detail=
                "Idioma de origem não suportado."

        )


    if target_language not in LANGUAGE_NAMES:

        raise HTTPException(

            status_code=400,

            detail=
                "Idioma de destino não suportado."

        )


    # -----------------------------------------------------
    # TRANSCRIÇÃO
    # -----------------------------------------------------

    transcript = get_transcript(

        video_id,

        source_language

    )


    # -----------------------------------------------------
    # FRASES
    # -----------------------------------------------------

    phrases = merge_transcript(

        transcript

    )


    if not phrases:

        raise HTTPException(

            status_code=422,

            detail=
                "A transcrição não contém texto utilizável."

        )


    # -----------------------------------------------------
    # LIMITE DE 30 MINUTOS
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # TRADUÇÃO
    # -----------------------------------------------------

    phrases = translate_phrases(

        phrases,

        source_language,

        target_language

    )


    # -----------------------------------------------------
    # RESPOSTA
    # -----------------------------------------------------

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
