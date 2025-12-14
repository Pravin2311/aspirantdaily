// ===============================
// quiz.js – FINAL PRODUCTION VERSION
// Uses /api/exam proxy via Vercel
// ===============================

// --------------------------------
// Read exam from URL (cleaned & normalized)
// --------------------------------
const urlParams = new URLSearchParams(window.location.search);
const rawExam = urlParams.get("exam");
const exam = (rawExam ? rawExam.trim().toLowerCase() : "mixed");

console.log("Raw exam from URL:", rawExam);
console.log("Cleaned exam used:", exam);

document.getElementById("examLabel").innerText =
  exam.toUpperCase() + " • Daily Practice";

// --------------------------------
// Global State
// --------------------------------
let questions = [];
let currentIndex = 0;
let userAnswers = [];

// --------------------------------
// Init
// --------------------------------
loadQuestions();

// --------------------------------
// Load questions from API (proxied through Vercel)
// --------------------------------
async function loadQuestions() {
  // ✅ Use relative path for Vercel proxy
  const apiUrl = `/api/exam?exam=${encodeURIComponent(exam)}`;
  
  console.log("Fetching from URL:", apiUrl);

  try {
    const res = await fetch(apiUrl, {
      cache: "no-store",
      headers: { "Accept": "application/json" }
    });

    const rawText = await res.text();
    console.log("RAW API RESPONSE:", rawText);
    console.log("Response status:", res.status);

    if (!res.ok) {
      // Try to parse error JSON if possible
      try {
        const errorJson = JSON.parse(rawText);
        throw new Error(`API error ${res.status}: ${errorJson.error || 'Unknown error'}`);
      } catch {
        // Check for firewall block (Zscaler, etc.)
        if (rawText.includes("Zscaler") || rawText.includes("<html>")) {
          throw new Error("Network firewall blocked the request. Please try on a different network.");
        }
        throw new Error(`API error ${res.status}: ${rawText.substring(0, 100)}`);
      }
    }

    let data;
    try {
      data = JSON.parse(rawText);
    } catch (parseErr) {
      console.error("JSON Parse Error:", parseErr);
      throw new Error("Response is not valid JSON");
    }

    // 🔒 Strict validation
    if (!data || !Array.isArray(data.questions) || data.questions.length === 0) {
      throw new Error("No valid questions available in response");
    }

    questions = data.questions;
    userAnswers = Array(questions.length).fill(null);

    // UI switch
    document.getElementById("loadingBox").classList.add("hidden");
    document.getElementById("quizBox").classList.remove("hidden");

    loadQuestion();

  } catch (err) {
    console.error("Quiz load failed:", err);

    alert(
      "Unable to load today's quiz.\n\n" +
      "Error: " + err.message + "\n\n" +
      "Tip: Try again later or use a different network."
    );
  }
}

// --------------------------------
// Render one question
// --------------------------------
function loadQuestion() {
  if (
    !questions[currentIndex] ||
    !Array.isArray(questions[currentIndex].options)
  ) {
    alert("Question data is unavailable. Please refresh.");
    return;
  }

  const q = questions[currentIndex];

  document.getElementById("questionNumber").innerText =
    `Question ${currentIndex + 1} of ${questions.length}`;

  document.getElementById("questionText").innerText =
    q.question || "";

  const container = document.getElementById("optionsContainer");
  container.innerHTML = "";

  q.options.forEach((opt, idx) => {
    const div = document.createElement("div");
    div.className =
      "option bg-gray-100 p-3 rounded-lg cursor-pointer border";

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

// --------------------------------
// Option select
// --------------------------------
function selectOption(optionIndex, element) {
  userAnswers[currentIndex] = optionIndex;
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

  const encoded = encodeURIComponent(
    JSON.stringify({ questions, userAnswers })
  );

  window.location.href = `result.html?data=${encoded}`;
}

function confirmExit() {
  // If quiz hasn't started yet
  if (!questions.length || userAnswers.every(a => a === null)) {
    window.location.href = "index.html";
    return;
  }

  const sure = confirm(
    "If you go back, your current progress will be lost.\n\nDo you want to change exam?"
  );

  if (sure) {
    window.location.href = "index.html";
  }
}
