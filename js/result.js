// ===============================
// result.js – FINAL FIXED VERSION
// Session-safe + backward compatible
// ===============================

document.addEventListener("DOMContentLoaded", () => {
  // 🔒 Read from sessionStorage FIRST, fallback to localStorage
  let examDataRaw =
    sessionStorage.getItem("examData") ||
    localStorage.getItem("examData");

  let userAnswersRaw =
    sessionStorage.getItem("userAnswers") ||
    localStorage.getItem("userAnswers");

  if (!examDataRaw || !userAnswersRaw) {
    showError("Result data not found. Please take the quiz again.");
    return;
  }

  let examData, userAnswers;
  try {
    examData = JSON.parse(examDataRaw);
    userAnswers = JSON.parse(userAnswersRaw);
  } catch (e) {
    showError("Result data corrupted. Please retry the quiz.");
    return;
  }

  if (!examData.questions || !Array.isArray(examData.questions)) {
    showError("Invalid result format.");
    return;
  }

  const questions = examData.questions;
  const total = questions.length;

  let correct = 0;
  let attempted = 0;

  questions.forEach((q, i) => {
    let ua = userAnswers[i];

    // ✅ Legacy support: index → option text (old SSC)
    if (typeof ua === "number" && Array.isArray(q.options) && q.options[ua]) {
      ua = q.options[ua];
    }

    const userAnswer = String(ua || "").trim().toLowerCase();
    const correctAnswer = String(q.answer || "").trim().toLowerCase();

    if (userAnswer) attempted++;
    if (userAnswer && userAnswer === correctAnswer) {
      correct++;
    }
  });

  // ---- UI UPDATE ----
  document.getElementById("scoreText").innerText =
    `Score: ${correct} / ${total}`;

  document.getElementById("statsText").innerText =
    `Attempted ${attempted} out of ${total} questions`;
});

// ===============================
// Helper
// ===============================
function showError(message) {
  const scoreEl = document.getElementById("scoreText");
  const statsEl = document.getElementById("statsText");

  if (scoreEl) scoreEl.innerText = message;
  if (statsEl) statsEl.innerText = "";
}
