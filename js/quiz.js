// ===============================
// quiz.js – FINAL STABLE VERSION
// TEXT-BASED ANSWERS (RESULT-SAFE)
// ===============================

// --------------------------------
// Read exam from URL (normalized)
// --------------------------------
const urlParams = new URLSearchParams(window.location.search);
const rawExam = urlParams.get("exam");
const exam = rawExam ? rawExam.trim().toLowerCase() : "mixed";

document.getElementById("examLabel").innerText =
  exam.toUpperCase() + " • Daily Practice";

// --------------------------------
// Global State
// --------------------------------
let questions = [];
let currentIndex = 0;

// IMPORTANT: store ANSWER TEXT, not index
let userAnswers = [];

// --------------------------------
// Init
// --------------------------------
loadQuestions();

// --------------------------------
// Load questions from Worker API
// --------------------------------
async function loadQuestions() {
  const apiUrl = `https://exam-prep-generator.mydomain2311.workers.dev/?exam=${exam}`;

  try {
    const res = await fetch(apiUrl, {
      cache: "no-store",
      headers: { "Accept": "application/json" }
    });

    const text = await res.text();
    if (!res.ok) throw new Error(text);

    const data = JSON.parse(text);

    if (!data || !Array.isArray(data.questions) || !data.questions.length) {
      throw new Error("No valid questions received");
    }

    questions = data.questions;

    // Initialize answers as null (text-based)
    userAnswers = Array(questions.length).fill(null);

    document.getElementById("loadingBox").classList.add("hidden");
    document.getElementById("quizBox").classList.remove("hidden");

    loadQuestion();

  } catch (err) {
    console.error(err);
    alert("Unable to load quiz. Please try again later.");
  }
}

// --------------------------------
// Render question
// --------------------------------
function loadQuestion() {
  const q = questions[currentIndex];
  if (!q || !Array.isArray(q.options)) {
    alert("Invalid question data.");
    return;
  }

  document.getElementById("questionNumber").innerText =
    `Question ${currentIndex + 1} of ${questions.length}`;

  document.getElementById("questionText").innerText = q.question;

  const container = document.getElementById("optionsContainer");
  container.innerHTML = "";

  q.options.forEach(optionText => {
    const div = document.createElement("div");
    div.className =
      "option bg-gray-100 p-3 rounded-lg cursor-pointer border";

    // Highlight if already selected
    if (userAnswers[currentIndex] === optionText) {
      div.classList.add("selected");
    }

    div.innerText = optionText;
    div.onclick = () => selectOption(optionText, div);

    container.appendChild(div);
  });

  document.getElementById("prevBtn").disabled = currentIndex === 0;
  document.getElementById("nextBtn").innerText =
    currentIndex === questions.length - 1 ? "Submit" : "Next";
}

// --------------------------------
// Option select (TEXT BASED)
// --------------------------------
function selectOption(optionText, element) {
  userAnswers[currentIndex] = optionText;

  document.querySelectorAll(".option").forEach(el =>
    el.classList.remove("selected")
  );
  element.classList.add("selected");
}

// --------------------------------
// Navigation
// --------------------------------
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

// --------------------------------
// Submit quiz
// --------------------------------
function submitQuiz() {
  if (!questions.length) {
    alert("No quiz data to submit.");
    return;
  }

  // ✅ Store in localStorage (results.js expects this)
  localStorage.setItem("examData", JSON.stringify({ questions }));
  localStorage.setItem("userAnswers", JSON.stringify(userAnswers));

  window.location.href = "result.html";
}
