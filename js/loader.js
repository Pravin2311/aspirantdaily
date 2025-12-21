// ===============================
// loader.js – FINAL HYBRID VERSION
// Navigation + Data Loader
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
  if (!questions.length) {
    alert("No questions available");
    return;
  }
  showQuestion();
});

// =======================================================
// HYBRID DATA LOADER
// =======================================================

const KV_SUBJECTS = ["currentaffairs"];
const WORKER_BASE_URL = "https://exam-prep-generator.mydomain2311.workers.dev/currentaffairs"; 
// 🔁 change to your Worker URL

async function loadQuestions(subject) {
  try {
    // 🔥 Current Affairs → KV
    if (KV_SUBJECTS.includes(subject)) {
      const res = await fetch(`${WORKER_BASE_URL}/${subject}`);
      if (!res.ok) throw new Error("KV fetch failed");
      const data = await res.json();
      return data.questions;
    }

    // 📦 Static subjects → local data folder
    const res = await fetch(`./data/${subject}.json`);
    if (!res.ok) throw new Error("Local JSON fetch failed");
    const data = await res.json();
    return data.questions;

  } catch (err) {
    console.error(`Failed to load ${subject}:`, err);
    return [];
  }
}

// =======================================================
// QUIZ UI LOGIC (UNCHANGED)
// =======================================================

function showQuestion() {
  const q = questions[current];

  document.getElementById("q-en").innerText = q.question.en;
  document.getElementById("q-hi").innerText = q.question.hi;

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
