const phrases = [
  {
    phrase: "Tu regardes quoi ?",
    translation: "O que você está assistindo?",
    level: "A1",
    explanation: "É uma forma muito comum e informal de perguntar o que alguém está assistindo ou olhando. Em francês falado, a estrutura 'quoi ?' no final é extremamente natural."
  },
  {
    phrase: "Tu fais quoi ?",
    translation: "O que você está fazendo?",
    level: "A1",
    explanation: "Uma pergunta informal e muito usada no dia a dia. Literalmente, é algo como 'Você faz o quê?'."
  },
  {
    phrase: "Ça va ?",
    translation: "Tudo bem?",
    level: "A1",
    explanation: "Uma das expressões mais importantes do francês cotidiano. Pode significar 'Tudo bem?', 'Como você está?' ou simplesmente funcionar como cumprimento."
  },
  {
    phrase: "J'en sais rien.",
    translation: "Não faço ideia.",
    level: "A2",
    explanation: "Forma informal de dizer que você não sabe. 'En' substitui algo já mencionado no contexto."
  },
  {
    phrase: "T'en as trouvé où ?",
    translation: "Onde você encontrou isso?",
    level: "A2",
    explanation: "'T'en' vem de 'tu en'. A frase é uma maneira natural de perguntar onde a pessoa encontrou ou conseguiu alguma coisa."
  },
  {
    phrase: "Ne t'en fais pas.",
    translation: "Não se preocupe.",
    level: "A2",
    explanation: "Expressão muito comum. Na fala informal, o 'ne' costuma desaparecer: 'T'en fais pas.'"
  },
  {
    phrase: "Je vais jouer.",
    translation: "Eu vou jogar.",
    level: "A1",
    explanation: "Usa 'aller + infinitivo' para falar de uma ação futura próxima: 'je vais' + 'jouer'."
  },
  {
    phrase: "Tout va bien.",
    translation: "Está tudo bem.",
    level: "A1",
    explanation: "Expressão simples para dizer que está tudo certo ou que está tudo bem."
  },
  {
    phrase: "Vous m'avez fait peur.",
    translation: "Você me assustou.",
    level: "B1",
    explanation: "Literalmente, 'você me fez medo'. Em francês, 'faire peur à quelqu'un' significa assustar alguém."
  }
];

const grid = document.getElementById("phraseGrid");
const filter = document.getElementById("levelFilter");

const modal = document.getElementById("modal");
const closeModal = document.getElementById("closeModal");
const modalPhrase = document.getElementById("modalPhrase");
const modalTranslation = document.getElementById("modalTranslation");
const modalLevel = document.getElementById("modalLevel");
const modalExplanation = document.getElementById("modalExplanation");
const speakButton = document.getElementById("speakButton");

let currentPhrase = "";

function renderPhrases() {
  const selected = filter.value;

  const filtered = selected === "todos"
    ? phrases
    : phrases.filter(item => item.level === selected);

  grid.innerHTML = filtered.map((item, index) => `
    <article class="phrase-card" data-index="${phrases.indexOf(item)}">
      <div class="fr">${item.phrase}</div>
      <div class="pt">${item.translation}</div>
      <span class="badge">${item.level}</span>
    </article>
  `).join("");

  document.querySelectorAll(".phrase-card").forEach(card => {
    card.addEventListener("click", () => openPhrase(Number(card.dataset.index)));
  });
}

function openPhrase(index) {
  const item = phrases[index];
  currentPhrase = item.phrase;

  modalLevel.textContent = `${item.level} • FRANCÊS`;
  modalPhrase.textContent = item.phrase;
  modalTranslation.textContent = item.translation;
  modalExplanation.textContent = item.explanation;

  modal.classList.remove("hidden");
}

function close() {
  modal.classList.add("hidden");
}

filter.addEventListener("change", renderPhrases);
closeModal.addEventListener("click", close);

modal.addEventListener("click", (event) => {
  if (event.target === modal) close();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") close();
});

speakButton.addEventListener("click", () => {
  if (!("speechSynthesis" in window)) {
    alert("Seu navegador não oferece síntese de voz.");
    return;
  }

  speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(currentPhrase);
  utterance.lang = "fr-FR";
  utterance.rate = 0.85;

  speechSynthesis.speak(utterance);
});

renderPhrases();
