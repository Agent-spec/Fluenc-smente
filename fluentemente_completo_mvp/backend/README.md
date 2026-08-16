# Fluentemente - Frontend + Backend YouTube

## O que esta versão faz

O backend recebe um link do YouTube, extrai o ID, tenta obter uma transcrição disponível para o idioma solicitado, transforma os blocos da transcrição em frases com timestamps e devolve JSON para o frontend.

O limite do MVP é 30 minutos.

### Importante

Este backend NÃO baixa o vídeo. Ele usa o player oficial do YouTube no frontend e trabalha com uma transcrição que esteja disponível e possa ser acessada pelo serviço.

A disponibilidade de transcrições depende do vídeo, do idioma e das condições do YouTube. Portanto, um vídeo sem transcrição compatível pode retornar erro.

## Instalação no Windows

1. Instale Python 3.11 ou mais recente.
2. Abra o terminal dentro da pasta `backend`.
3. Execute:

`python -m venv .venv`

`.venv\Scripts\activate`

`python -m pip install -r requirements.txt`

4. Rode:

`python -m uvicorn main:app --reload --port 8000`

5. API:
`http://127.0.0.1:8000`

Documentação automática:
`http://127.0.0.1:8000/docs`

## Teste

No `/docs`, use `POST /api/video` e envie:

{
  "url": "https://www.youtube.com/watch?v=SEU_ID",
  "source_language": "fr",
  "target_language": "pt"
}

## Próxima etapa

A resposta já possui:

- `start`
- `duration`
- `original`

Isso permite sincronizar a legenda com o player.

Para chegar ao produto final descrito, a próxima camada deve:

1. traduzir cada frase;
2. tokenizar palavras;
3. identificar lema;
4. buscar significados;
5. gerar exemplos cotidianos;
6. enviar tudo para o frontend;
7. sincronizar a frase com o tempo do vídeo.

Não coloque chaves de APIs no JavaScript do frontend.
