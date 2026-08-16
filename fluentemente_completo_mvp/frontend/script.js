const API = "https://fluencesmente.onrender.com";

let phrases = [];
let currentPhrase = "";

// ==================================================
// ELEMENTOS
// ==================================================

const grid = document.getElementById("phraseGrid");
const filter = document.getElementById("levelFilter");

const modal = document.getElementById("modal");
const closeModal = document.getElementById("closeModal");
const modalPhrase = document.getElementById("modalPhrase");
const modalTranslation = document.getElementById("modalTranslation");
const modalLevel = document.getElementById("modalLevel");
const modalExplanation = document.getElementById("modalExplanation");
const speakButton = document.getElementById("speakButton");


// ==================================================
// IDIOMAS
// ==================================================

const languageNames = {
  fr: "Francês",
  en: "Inglês",
  de: "Alemão",
  es: "Espanhol",
  it: "Italiano",
  sv: "Sueco",
  pt: "Português",
  ja: "Japonês",
  zh: "Chinês"
};


// ==================================================
// YOUTUBE
// ==================================================

function getYouTubeId(url) {

  try {

    const parsed = new URL(url);

    if (parsed.hostname.includes("youtu.be")) {

      return (
        parsed.pathname
          .split("/")[1] || null
      );
    }

    if (parsed.hostname.includes("youtube.com")) {

      const videoId =
        parsed.searchParams.get("v");

      if (videoId) {
        return videoId;
      }

      const parts =
        parsed.pathname
          .split("/")
          .filter(Boolean);

      if (
        parts.length >= 2 &&
        (
          parts[0] === "shorts" ||
          parts[0] === "embed"
        )
      ) {
        return parts[1];
      }
    }

    return null;

  } catch {

    return null;

  }
}


// ==================================================
// PLAYER YOUTUBE
// ==================================================

function updateYouTubePlayer(url) {

  const videoId =
    getYouTubeId(url);

  if (!videoId) return;

  const player =
    document.getElementById(
      "youtubePlayer"
    );

  if (player) {

    player.src =
      `https://www.youtube.com/embed/${videoId}?enablejsapi=1`;

  }
}


// ==================================================
// CARREGAR VÍDEO
// ==================================================

async function loadVideo(url) {

  const videoId =
    getYouTubeId(url);

  if (!videoId) {

    alert(
      "Coloque uma URL válida do YouTube."
    );

    return;
  }


  // ----------------------------------------------
  // IDIOMAS ESCOLHIDOS
  // ----------------------------------------------

  const sourceLanguage =
    document.getElementById(
      "sourceLanguage"
    )?.value || "fr";

  const targetLanguage =
    document.getElementById(
      "targetLanguage"
    )?.value || "pt";


  // ----------------------------------------------
  // LOADING
  // ----------------------------------------------

  grid.innerHTML = `
    <div class="loading">
      <div>
        <strong>Processando vídeo...</strong>
        <br>
        <span>
          Extraindo frases e preparando a tradução.
        </span>
      </div>
    </div>
  `;


  try {

    const response =
      await fetch(
        `${API}/api/video`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body: JSON.stringify({

            url: url,

            source_language:
              sourceLanguage,

            target_language:
              targetLanguage

          })
        }
      );


    const data =
      await response.json();


    if (!response.ok) {

      throw new Error(
        data.detail ||
        "Não foi possível processar o vídeo."
      );

    }


    // ----------------------------------------------
    // FRASES
    // ----------------------------------------------

    phrases =
      data.phrases.map(
        (item) => ({

          phrase:
            item.original,

          translation:
            item.translation ||
            "Tradução não disponível",

          level:
            item.level ||
            "A1",

          explanation:
            item.explanation ||
            "Sem explicação disponível.",

          start:
            item.start,

          duration:
            item.duration,

          sourceLanguage:
            sourceLanguage,

          targetLanguage:
            targetLanguage

        })
      );


    renderPhrases();


    console.log(
      "Vídeo processado:",
      data
    );


  } catch (error) {

    console.error(error);


    grid.innerHTML = `
      <div class="error">

        <strong>
          Não foi possível processar o vídeo.
        </strong>

        <br><br>

        ${escapeHTML(error.message)}

      </div>
    `;

  }
}


// ==================================================
// RENDERIZAR FRASES
// ==================================================

function renderPhrases() {

  if (!grid) return;


  const selected =
    filter
      ? filter.value
      : "todos";


  const filtered =
    selected === "todos"
      ? phrases
      : phrases.filter(
          (item) =>
            item.level === selected
        );


  if (filtered.length === 0) {

    grid.innerHTML = `
      <div class="empty">
        Nenhuma frase encontrada.
      </div>
    `;

    return;
  }


  grid.innerHTML =
    filtered
      .map(
        (item) => {

          const index =
            phrases.indexOf(item);


          const source =
            languageNames[
              item.sourceLanguage
            ] ||
            item.sourceLanguage;


          return `

            <article
              class="phrase-card"
              data-index="${index}"
            >

              <div class="fr">
                ${escapeHTML(
                  item.phrase
                )}
              </div>


              <div class="pt">
                ${escapeHTML(
                  item.translation
                )}
              </div>


              <span class="badge">
                ${escapeHTML(
                  item.level
                )}
              </span>


              <small class="language-label">
                ${escapeHTML(source)}
              </small>

            </article>

          `;
        }
      )
      .join("");


  document
    .querySelectorAll(
      ".phrase-card"
    )
    .forEach(
      (card) => {

        card.addEventListener(
          "click",
          () => {

            openPhrase(
              Number(
                card.dataset.index
              )
            );

          }
        );

      }
    );
}


// ==================================================
// MODAL
// ==================================================

function openPhrase(index) {

  const item =
    phrases[index];

  if (!item) return;


  currentPhrase =
    item.phrase;


  const source =
    languageNames[
      item.sourceLanguage
    ] ||
    item.sourceLanguage;


  modalLevel.textContent =
    `${item.level} • ${source.toUpperCase()}`;


  modalPhrase.textContent =
    item.phrase;


  modalTranslation.textContent =
    item.translation;


  modalExplanation.textContent =
    item.explanation;


  modal.classList.remove(
    "hidden"
  );
}


function close() {

  modal.classList.add(
    "hidden"
  );

}


// ==================================================
// PRONÚNCIA
// ==================================================

function speakPhrase() {

  if (
    !("speechSynthesis" in window)
  ) {

    alert(
      "Seu navegador não oferece síntese de voz."
    );

    return;
  }


  if (!currentPhrase) return;


  const sourceLanguage =
    document.getElementById(
      "sourceLanguage"
    )?.value || "fr";


  const speechLanguages = {

    fr: "fr-FR",

    en: "en-US",

    de: "de-DE",

    es: "es-ES",

    it: "it-IT",

    sv: "sv-SE",

    pt: "pt-BR",

    ja: "ja-JP",

    zh: "zh-CN"

  };


  speechSynthesis.cancel();


  const utterance =
    new SpeechSynthesisUtterance(
      currentPhrase
    );


  utterance.lang =
    speechLanguages[
      sourceLanguage
    ] || "fr-FR";


  utterance.rate =
    0.85;


  speechSynthesis.speak(
    utterance
  );

}


// ==================================================
// SEGURANÇA
// ==================================================

function escapeHTML(text) {

  return String(text)

    .replaceAll(
      "&",
      "&amp;"
    )

    .replaceAll(
      "<",
      "&lt;"
    )

    .replaceAll(
      ">",
      "&gt;"
    )

    .replaceAll(
      '"',
      "&quot;"
    )

    .replaceAll(
      "'",
      "&#039;"
    );

}


// ==================================================
// EVENTOS
// ==================================================

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

      if (
        event.target === modal
      ) {

        close();

      }

    }
  );

}


document.addEventListener(
  "keydown",
  (event) => {

    if (
      event.key === "Escape"
    ) {

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


// ==================================================
// INPUT DO YOUTUBE
// ==================================================

const urlInput =

  document.getElementById(
    "youtubeUrl"
  ) ||

  document.getElementById(
    "videoUrl"
  ) ||

  document.querySelector(
    'input[type="url"]'
  );


const loadButton =

  document.getElementById(
    "loadVideo"
  ) ||

  document.getElementById(
    "loadButton"
  ) ||

  document.querySelector(
    'button[type="submit"]'
  );


// ==================================================
// CARREGAR
// ==================================================

if (
  loadButton &&
  urlInput
) {

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


      updateYouTubePlayer(
        url
      );


      await loadVideo(
        url
      );

    }
  );

}


// ==================================================
// INICIALIZAÇÃO
// ==================================================

renderPhrases();
// --------------------------------------------------
// INICIALIZAÇÃO
// --------------------------------------------------

renderPhrases();
