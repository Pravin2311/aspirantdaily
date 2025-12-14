// ===============================
// quiz.js – FINAL VERIFIED VERSION
// Cloudflare Worker API SAFE MODE
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
// Load questions from Worker API
// --------------------------------
async function loadQuestions() {
  // ✅ FIXED: Removed extra spaces in URL
  const apiUrl = `https://exam-prep-generator.mydomain2311.workers.dev/?exam=${exam}`;
  
  console.log("Fetching from URL:", apiUrl);

  try {
    const res = await fetch(apiUrl, {
      cache: "no-store",
      headers: { "Accept": "application/json" }
    });

    const rawText = await res.text();
    console.log("RAW API RESPONSE:", rawText);

    // Log status for clarity
    console.log("Response status:", res.status);

    if (!res.ok) {
      // Try to parse error JSON if possible
      try {
        const errorJson = JSON.parse(rawText);
        throw new Error(`API error ${res.status}: ${errorJson.error || 'Unknown error'}`);
      } catch {
        throw new Error(`API error ${res.status}: ${rawText || 'No response body'}`);
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

    // ✅ Better user feedback
    alert(
      "Unable to load today's quiz.\n\n" +
      "Error: " + err.message + "\n\n" +
      "Please try again later or check your internet connection."
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