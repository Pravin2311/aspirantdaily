// ===============================
// quiz.js – FINAL CORRECTED VERSION
// ===============================

const exam = new URLSearchParams(window.location.search)
  .get("exam")?.toLowerCase() || "mixed";

document.getElementById("examLabel").innerText =
  exam.toUpperCase() + " • Daily Practice";

let questions = [];
let currentIndex = 0;
let userAnswers = [];

// ✅ ONLY ONE loadQuestions function
async function loadQuestions() {
  // ✅ FIXED: No trailing spaces
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

function loadQuestion() {
  if (!questions[currentIndex] || !Array.isArray(questions[currentIndex].options)) {
    alert("Question data is unavailable. Please refresh.");
    return;
  }

  const q = questions[currentIndex];

  document.getElementById("questionNumber").innerText =
    `Question ${currentIndex + 1} of ${questions.length}`;

  document.getElementById("questionText").innerText = q.question || "";

  const container = document.getElementById("optionsContainer");
  container.innerHTML = "";

  q.options.forEach((opt, idx) => {
    const div = document.createElement("div");
    div.className = "option bg-gray-100 p-3 rounded-lg cursor-pointer border";
    if (userAnswers[currentIndex] === idx) {
      div.classList.add("selected");
    }
    div.innerText = opt;
    div.onclick = () => selectOption(idx, div);
    container.appendChild(div);
  });

  document.getElementById("prevBtn").disabled = currentIndex === 0;
  document.getElementById("nextBtn").innerText =
    currentIndex === questions.length - 1 ? "Submit" : "Next";
}

function selectOption(optionIndex, element) {
  userAnswers[currentIndex] = optionIndex;
  document.querySelectorAll(".option").forEach(el => el.classList.remove("selected"));
  element.classList.add("selected");
}

function nextQuestion() {
  if (currentIndex === questions.length - 1) {
    submitQuiz();
    return;
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
  // ✅ Use sessionStorage only — no localStorage wipe
  sessionStorage.setItem("examData", JSON.stringify({ questions }));
  sessionStorage.setItem("userAnswers", JSON.stringify(userAnswers));
  window.location.href = "result.html";
}

// ✅ INIT
loadQuestions();