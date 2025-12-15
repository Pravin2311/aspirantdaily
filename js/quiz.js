// ===============================
// quiz.js – FINAL VERSION (SAFE FIXED)
// ===============================
const lang = localStorage.getItem("lang") || "en";

// 🔒 Clear legacy attempts (fixes SSC score issue)
localStorage.removeItem("examData");
localStorage.removeItem("userAnswers");

const exam = new URLSearchParams(window.location.search)
  .get("exam")?.toLowerCase() || "mixed";

document.getElementById("examLabel").innerText =
  exam.toUpperCase() + " • Daily Practice";

let questions = [];
let currentIndex = 0;
let userAnswers = [];

loadQuestions();

async function loadQuestions() {
  try {
    const res = await fetch(
      `https://exam-prep-generator.mydomain2311.workers.dev/?exam=${exam}`,
      { cache: "no-store" }
    );

    const data = await res.json();

    // ✅ FIX: API safety guard
    if (!data?.questions || !Array.isArray(data.questions) || data.questions.length === 0) {
      alert("Questions not available. Please try again later.");
      return;
    }

    questions = data.questions;
    userAnswers = Array(questions.length).fill(null);

    document.getElementById("loadingBox").classList.add("hidden");
    document.getElementById("quizBox").classList.remove("hidden");

    loadQuestion();
  } catch (e) {
    alert("Failed to load quiz. Please refresh.");
  }
}

function loadQuestion() {
  const q = questions[currentIndex];

  document.getElementById("questionNumber").innerText =
    `Question ${currentIndex + 1} of ${questions.length}`;

  // ✅ FIX: safe language fallback
  document.getElementById("questionText").innerText =
    q.question?.[lang] || q.question?.en || "Question unavailable";

  const container = document.getElementById("optionsContainer");
  container.innerHTML = "";

  // ✅ FIX: safe options fallback
  const options = q.options?.[lang] || q.options?.en || [];

  options.forEach(opt => {
    if (!opt) return;

    const div = document.createElement("div");
    div.className = "option";

    if (userAnswers[currentIndex] === opt) {
      div.classList.add("selected");
    }

    div.innerText = opt;
    div.onclick = () => selectOption(opt, div);

    container.appendChild(div);
  });
}

function selectOption(opt, el) {
  userAnswers[currentIndex] = opt;
  document
    .querySelectorAll(".option")
    .forEach(e => e.classList.remove("selected"));
  el.classList.add("selected");
}

function nextQuestion() {
  if (currentIndex === questions.length - 1) {
    return submitQuiz();
  }
  currentIndex++;
  loadQuestion();
}

function prevQuestion() {
  if (currentIndex > 0) {
    currentIndex--;
    loadQuestion();
  }
}

function submitQuiz() {
  localStorage.setItem("examData", JSON.stringify({ questions }));
  localStorage.setItem("userAnswers", JSON.stringify(userAnswers));
  window.location.href = "result.html";
}
