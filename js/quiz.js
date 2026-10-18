// ===============================
// quiz.js – FINAL LOCAL DATA VERSION
// CA: shuffle 50 → pick 25
// Others: quiz-selector logic unchanged
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
  english: "English",
  economics: "Economics",
  geography: "Geography"
};

document.getElementById("examLabel").innerText = isSubjectMode
  ? `${subjectLabels[subject] || "Practice"}`
  : `${(exam || "mixed").toUpperCase()} • Daily Practice`;

// ===============================
// STATE
// ===============================
let questions = [];
let currentIndex = 0;
let userAnswers = [];
let isSubmitting = false;

// ===============================
// LOAD QUESTIONS
// ===============================
loadQuestions();

async function loadQuestions() {
  try {
    // ===============================
    // SUBJECT MODE → LOCAL JSON
    // ===============================
    if (isSubjectMode) {
      const res = await fetch(`./data/${subject}.json`, {
        cache: "no-store"
      });

      if (!res.ok) throw new Error("Failed to load local subject JSON");

      const data = await res.json();
      let pool = Array.isArray(data.questions) ? [...data.questions] : [];

      // 🔥 CURRENT AFFAIRS → SHUFFLE FULL POOL, PICK 25
      if (subject === "current-affairs") {
        pool.sort(() => Math.random() - 0.5);
        questions = pool.slice(0, 25);
      }
      // 📦 OTHER SUBJECTS → even sets of at most 25 (same maths as quiz-selector.html)
      else {
        const sets = Math.max(1, Math.ceil(pool.length / 25));
        const size = Math.ceil(pool.length / sets);
        const start = quizIndex * size;
        questions = pool.slice(start, start + size);
      }
    }

    // ===============================
    // EXAM MODE → LOCAL COMPOSER
    // ===============================
    else {
      const { buildExam } = await import("./examComposer.js");
      questions = await buildExam(exam || "mixed");
    }

    if (!Array.isArray(questions) || questions.length === 0) {
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

  // Button state
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
// SUBMIT
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

  setTimeout(() => {
    window.location.href = "result.html";
  }, 50);
}

// ===============================
// EXPOSE NAVIGATION
// ===============================
window.nextQuestion = nextQuestion;
window.prevQuestion = prevQuestion;
