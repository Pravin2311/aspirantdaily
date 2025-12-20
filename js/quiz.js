// ===============================
// quiz.js – FINAL LOCKED VERSION
// SUBJECT-WISE + LOCAL EXAM COMPOSER
// ===============================

const lang = localStorage.getItem("lang") || "en";

// 🔒 Clear previous attempts
localStorage.removeItem("examData");
localStorage.removeItem("userAnswers");

// ===============================
// DETECT MODE
// ===============================
const urlParams = new URLSearchParams(window.location.search);
const exam = urlParams.get("exam")?.toLowerCase();

const context = JSON.parse(localStorage.getItem("practiceContext") || "{}");
const isSubjectMode = !!context.subject;

const subject = context.subject;
const quizIndex = context.quizIndex ?? 0;

// ===============================
// LABELS
// ===============================
const subjectLabels = {
  "current-affairs": "Current Affairs",
  reasoning: "Reasoning",
  quant: "Quantitative Aptitude",
  computer: "Computer Awareness",
  science: "General Science",
  "static-gk": "Static GK",
  english: "English (Grammar & Verbal)",
  economics: "Economics",
  geography: "Geography"
};

document.getElementById("examLabel").innerText = isSubjectMode
  ? `${subjectLabels[subject] || "Practice"} • Quiz ${quizIndex + 1}`
  : `${(exam || "mixed").toUpperCase()} • Daily Practice`;

// ===============================
// STATE
// ===============================
let questions = [];
let currentIndex = 0;
let userAnswers = [];
let isSubmitting = false; // 🔒 prevent double submit

// ===============================
// LOAD QUESTIONS
// ===============================
loadQuestions();

async function loadQuestions() {
  try {
    // ===============================
    // SUBJECT MODE
    // ===============================
    if (isSubjectMode) {

      // 🔥 CURRENT AFFAIRS → WORKER → KV
      if (subject === "current-affairs") {
        const res = await fetch(
          "https://exam-prep-generator.mydomain2311.workers.dev/currentaffairs",
          { cache: "no-store" }
        );
        const data = await res.json();
        questions = data.questions.slice(0, 25);
      }

      // 📦 STATIC SUBJECTS → LOCAL JSON
      else {
        const res = await fetch(`./data/${subject}.json`);
        const data = await res.json();

        const start = quizIndex * 25;
        questions = data.questions.slice(start, start + 25);
      }
    }

    // ===============================
    // EXAM MODE → LOCAL COMPOSER
    // ===============================
    else {
      const { buildExam } = await import("./examComposer.js");
      questions = await buildExam(exam || "mixed");
    }

    if (!questions || questions.length === 0) {
      alert("Questions not available. Please try again later.");
      return;
    }

    userAnswers = Array(questions.length).fill(null);

    document.getElementById("loadingBox").classList.add("hidden");
    document.getElementById("quizBox").classList.remove("hidden");

    loadQuestion();

  } catch (e) {
    console.error(e);
    alert("Failed to load quiz. Please refresh.");
  }
}

// ===============================
// RENDER QUESTION
// ===============================
function loadQuestion() {
  const q = questions[currentIndex];

  document.getElementById("questionNumber").innerText =
    `Question ${currentIndex + 1} of ${questions.length}`;

  document.getElementById("questionText").innerText =
    q.question?.[lang] || q.question?.en || "Question unavailable";

  const container = document.getElementById("optionsContainer");
  container.innerHTML = "";

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

  // 🔥 Button state sync
  document.getElementById("prevBtn").disabled = currentIndex === 0;
  document.getElementById("nextBtn").innerText =
    currentIndex === questions.length - 1 ? "Submit" : "Next";
}

// ===============================
// ANSWER SELECTION
// ===============================
function selectOption(opt, el) {
  userAnswers[currentIndex] = opt;
  document
    .querySelectorAll(".option")
    .forEach(e => e.classList.remove("selected"));
  el.classList.add("selected");
}

// ===============================
// NAVIGATION
// ===============================
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

// ===============================
// SUBMIT (BULLETPROOF)
// ===============================
function submitQuiz() {
  if (isSubmitting) return;
  isSubmitting = true;

  localStorage.setItem(
    "examData",
    JSON.stringify({
      mode: isSubjectMode ? "subject" : "exam",
      exam,
      subject,
      quizIndex,
      questions
    })
  );

  localStorage.setItem("userAnswers", JSON.stringify(userAnswers));

  // 🔒 Ensure storage flush before redirect
  setTimeout(() => {
    window.location.href = "result.html";
  }, 50);
}

// ===============================
// EXPOSE NAVIGATION
// ===============================
window.nextQuestion = nextQuestion;
window.prevQuestion = prevQuestion;
