const API = "https://fluencesmente.onrender.com";

let phrases = [];
let currentPhrase = "";

const grid = document.getElementById("phraseGrid");
const filter = document.getElementById("levelFilter");

const modal = document.getElementById("modal");
const closeModal = document.getElementById("closeModal");
const modalPhrase = document.getElementById("modalPhrase");
const modalTranslation = document.getElementById("modalTranslation");
const modalLevel = document.getElementById("modalLevel");
const modalExplanation = document.getElementById("modalExplanation");
const speakButton = document.getElementById("speakButton");

// --------------------------------------------------
// YOUTUBE
// --------------------------------------------------

function getYouTubeId(url) {
  try {
    const parsed = new URL(url);

    if (parsed.hostname.includes("youtu.be")) {
      return parsed.pathname.split("/")[1] || null;
    }

    if (parsed.hostname.includes("youtube.com")) {
      const videoId = parsed.searchParams.get("v");

      if (videoId) {
        return videoId;
      }

      const parts = parsed.pathname.split("/").filter(Boolean);

      if (
        parts.length >= 2 &&
        (parts[0] === "shorts" || parts[0] === "embed")
      ) {
        return parts[1];
      }
    }

    return null;
  } catch {
    return null;
  }
}

// --------------------------------------------------
// CARREGAR VÍDEO
// --------------------------------------------------

async function loadVideo(url) {
  const videoId = getYouTubeId(url);

  if (!videoId) {
    alert("Coloque uma URL válida do YouTube.");
    return;
  }

  try {
    // Mostra estado de carregamento
    grid.innerHTML = `
      <div class="loading">
        Carregando transcrição...
      </div>
    `;

    const response = await fetch(`${API}/api/video`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        url: url,
        source_language: "fr",
        target_language: "pt"
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "Não foi possível processar o vídeo."
      );
    }

    // O backend devolve as frases reais do vídeo
    phrases = data.phrases.map((item) => ({
      phrase: item.original,
      translation: "Tradução ainda não disponível",
      level: "A1",
      explanation: "Esta frase foi extraída diretamente da transcrição do vídeo.",
      start: item.start,
      duration: item.duration
    }));

    renderPhrases();

    console.log("Vídeo processado:", data);

  } catch (error) {
    console.error(error);

    grid.innerHTML = `
      <div class="error">
        ${error.message}
      </div>
    `;
  }
}

// --------------------------------------------------
// PLAYER DO YOUTUBE
// --------------------------------------------------

function updateYouTubePlayer(url) {
  const videoId = getYouTubeId(url);

  if (!videoId) return;

  const player = document.getElementById("youtubePlayer");

  if (player) {
    player.src =
      `https://www.youtube.com/embed/${videoId}?enablejsapi=1`;
  }
}

// --------------------------------------------------
// RENDERIZAR FRASES
// --------------------------------------------------

function renderPhrases() {
  if (!grid) return;

  const selected = filter ? filter.value : "todos";

  const filtered =
    selected === "todos"
      ? phrases
      : phrases.filter((item) => item.level === selected);

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="empty">
        Nenhuma frase encontrada.
      </div>
    `;

    return;
  }

  grid.innerHTML = filtered
    .map((item) => {
      const index = phrases.indexOf(item);

      return `
        <article
          class="phrase-card"
          data-index="${index}"
        >
          <div class="fr">
            ${escapeHTML(item.phrase)}
          </div>

          <div class="pt">
            ${escapeHTML(item.translation)}
          </div>

          <span class="badge">
            ${item.level}
          </span>
        </article>
      `;
    })
    .join("");

  document
    .querySelectorAll(".phrase-card")
    .forEach((card) => {
      card.addEventListener("click", () => {
        openPhrase(Number(card.dataset.index));
      });
    });
}

// --------------------------------------------------
// MODAL
// --------------------------------------------------

function openPhrase(index) {
  const item = phrases[index];

  if (!item) return;

  currentPhrase = item.phrase;

  modalLevel.textContent =
    `${item.level} • FRANCÊS`;

  modalPhrase.textContent =
    item.phrase;

  modalTranslation.textContent =
    item.translation;

  modalExplanation.textContent =
    item.explanation;

  modal.classList.remove("hidden");
}

function close() {
  modal.classList.add("hidden");
}

// --------------------------------------------------
// PRONÚNCIA
// --------------------------------------------------

function speakPhrase() {
  if (!("speechSynthesis" in window)) {
    alert(
      "Seu navegador não oferece síntese de voz."
    );

    return;
  }

  if (!currentPhrase) return;

  speechSynthesis.cancel();

  const utterance =
    new SpeechSynthesisUtterance(currentPhrase);

  utterance.lang = "fr-FR";
  utterance.rate = 0.85;

  speechSynthesis.speak(utterance);
}

// --------------------------------------------------
// SEGURANÇA
// --------------------------------------------------

function escapeHTML(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// --------------------------------------------------
// EVENTOS
// --------------------------------------------------

if (filter) {
  filter.addEventListener(
    "change",
    renderPhrases
  );
}

if (closeModal) {
  closeModal.addEventListener(
    "click",
    close
  );
}

if (modal) {
  modal.addEventListener(
    "click",
    (event) => {
      if (event.target === modal) {
        close();
      }
    }
  );
}

document.addEventListener(
  "keydown",
  (event) => {
    if (event.key === "Escape") {
      close();
    }
  }
);

if (speakButton) {
  speakButton.addEventListener(
    "click",
    speakPhrase
  );
}

// --------------------------------------------------
// BOTÃO DE CARREGAR
// --------------------------------------------------

// Procura alguns nomes comuns para o campo da URL
const urlInput =
  document.getElementById("youtubeUrl") ||
  document.getElementById("videoUrl") ||
  document.querySelector(
    'input[type="url"]'
  );

const loadButton =
  document.getElementById("loadVideo") ||
  document.getElementById("loadButton") ||
  document.querySelector(
    'button[type="submit"]'
  );

if (loadButton && urlInput) {
  loadButton.addEventListener(
    "click",
    async (event) => {
      event.preventDefault();

      const url =
        urlInput.value.trim();

      if (!url) {
        alert(
          "Cole o link de um vídeo do YouTube."
        );

        return;
      }

      updateYouTubePlayer(url);

      await loadVideo(url);
    }
  );
}

// --------------------------------------------------
// INICIALIZAÇÃO
// --------------------------------------------------

renderPhrases();
