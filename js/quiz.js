// ===============================
// quiz.js – FINAL VERSION
// ===============================

// 🔒 Clear legacy attempts (fixes SSC score issue)
// ✅ Reset only when quiz starts fresh
if (currentIndex === 0) {
  localStorage.removeItem("examData");
  localStorage.removeItem("userAnswers");
}

const exam = new URLSearchParams(window.location.search)
  .get("exam")?.toLowerCase() || "mixed";

document.getElementById("examLabel").innerText =
  exam.toUpperCase() + " • Daily Practice";

let questions = [];
let currentIndex = 0;
let userAnswers = [];

loadQuestions();

async function loadQuestions() {
  const res = await fetch(`https://exam-prep-generator.mydomain2311.workers.dev/?exam=${exam}`, { cache: "no-store" });
  const data = await res.json();

  questions = data.questions;
  userAnswers = Array(questions.length).fill(null);

  document.getElementById("loadingBox").classList.add("hidden");
  document.getElementById("quizBox").classList.remove("hidden");

  loadQuestion();
}

async function loadQuestions() {
  const apiUrl = `https://exam-prep-generator.mydomain2311.workers.dev/?exam=${exam}`;

  try {
    const res = await fetch(apiUrl, { cache: "no-store" });

    if (!res.ok) {
      throw new Error(`Server error: ${res.status}`);
    }

    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error("Invalid JSON response from server");
    }

    if (!data || !Array.isArray(data.questions) || data.questions.length === 0) {
      throw new Error("No questions available today");
    }

    questions = data.questions;
    userAnswers = Array(questions.length).fill(null);

    // ✅ UI switch (THIS WAS NEVER REACHED BEFORE)
    document.getElementById("loadingBox").classList.add("hidden");
    document.getElementById("quizBox").classList.remove("hidden");

    loadQuestion();

  } catch (err) {
    console.error("Quiz load failed:", err);

    document.getElementById("loadingBox").innerHTML = `
      <p style="color:red; text-align:center;">
        Unable to load today's questions.<br>
        Please try again later.
      </p>
    `;
  }
}


function selectOption(opt, el) {
  userAnswers[currentIndex] = opt;
  document.querySelectorAll(".option").forEach(e => e.classList.remove("selected"));
  el.classList.add("selected");
}

function nextQuestion() {
  if (currentIndex === questions.length - 1) return submitQuiz();
  currentIndex++;
  loadQuestion();
}

function prevQuestion() {
  if (currentIndex > 0) currentIndex--;
  loadQuestion();
}

function submitQuiz() {
  // 🔒 Use sessionStorage (stable across navigation)
  sessionStorage.setItem("examData", JSON.stringify({ questions }));
  sessionStorage.setItem("userAnswers", JSON.stringify(userAnswers));

  window.location.href = "result.html";
}
