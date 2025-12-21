// ===============================
// loader.js – FINAL LOCAL-FIRST VERSION
// Navigation + Local Data Loader
// ===============================

(function () {
  const params = new URLSearchParams(window.location.search);

  const exam = params.get("exam");
  const subject = params.get("subject");
  const quiz = parseInt(params.get("quiz"), 10);

  // ===============================
  // EXAM MODE (direct)
  // ===============================
  if (exam) {
    window.location.href = `quiz.html?exam=${exam}`;
    return;
  }

  // ===============================
  // SUBJECT MODE (via selector)
  // ===============================
  if (subject) {
    const quizIndex =
      !isNaN(quiz) && quiz >= 1 && quiz <= 4 ? quiz - 1 : 0;

    localStorage.setItem(
      "practiceContext",
      JSON.stringify({
        subject,
        quizIndex
      })
    );

    window.location.href = "quiz.html";
    return;
  }

  // ===============================
  // INVALID ACCESS
  // ===============================
  alert("Invalid selection. Redirecting to home.");
  window.location.href = "index.html";
})();

// =======================================================
// QUIZ RUNTIME (quiz.html)
// =======================================================

let current = 0;
let questions = [];

// Load based on subject stored by selector
const context = JSON.parse(localStorage.getItem("practiceContext") || "{}");
const subject = context.subject || "reasoning";

loadQuestions(subject).then(qs => {
  questions = qs;

  if (!Array.isArray(questions) || questions.length === 0) {
    alert("No questions available for this subject.");
    return;
  }

  showQuestion();
});

// =======================================================
// LOCAL DATA LOADER (NO KV, NO WORKER)
// =======================================================

async function loadQuestions(subject) {
  try {
    // Map subject → file name
    const fileMap = {
      "reasoning": "reasoning.json",
      "quant": "quant.json",
      "english": "english.json",
      "science": "science.json",
      "current-affairs": "current-affairs.json",
      "static-gk": "static-gk.json",
      "computer": "computer.json",
      "economy": "economy.json",
      "geography": "geography.json"
    };

    const file = fileMap[subject];
    if (!file) {
      console.error("Unknown subject:", subject);
      return [];
    }

    const res = await fetch(`./data/${file}`, { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to fetch local JSON");

    const data = await res.json();
    return Array.isArray(data.questions) ? data.questions : [];

  } catch (err) {
    console.error(`Failed to load ${subject}:`, err);
    return [];
  }
}

// =======================================================
// QUIZ UI LOGIC (UNCHANGED FOR NOW)
// =======================================================

function showQuestion() {
  const q = questions[current];

  document.getElementById("q-en").innerText = q.question.en || "";
  document.getElementById("q-hi").innerText = q.question.hi || "";

  q.options.en.forEach((opt, i) => {
    const btn = document.getElementById("opt" + i);
    btn.innerText = opt;
    btn.onclick = () => checkAnswer(opt);
  });
}

function checkAnswer(selected) {
  const correct = questions[current].answer.en;
  alert(selected === correct ? "✅ Correct" : "❌ Wrong");
  current++;
}
