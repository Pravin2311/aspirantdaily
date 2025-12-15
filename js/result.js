// ==========================================
// result.js – FINAL BULLETPROOF VERSION (FIXED)
// Bilingual-safe + legacy-safe
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
  const lang = localStorage.getItem("lang") || "en";

  let examData = localStorage.getItem("examData");
  let userAnswers = localStorage.getItem("userAnswers");

  // 🔒 HARD FAIL GUARD
  if (!examData || !userAnswers) {
    showError();
    return;
  }

  try {
    examData = JSON.parse(examData);
    userAnswers = JSON.parse(userAnswers);
  } catch {
    showError();
    return;
  }

  if (!examData.questions || !Array.isArray(examData.questions)) {
    showError();
    return;
  }

  const questions = examData.questions;
  const total = questions.length;

  let correct = 0;
  let attempted = 0;
  const subjectStats = {};

  const answersContainer = document.getElementById("answersContainer");
  answersContainer.innerHTML = "";

  questions.forEach((q, i) => {
    let ua = userAnswers[i];

    const options =
      q.options?.[lang] || q.options?.en || [];

    // ✅ Legacy numeric index support (old SSC data)
    if (typeof ua === "number" && options[ua]) {
      ua = options[ua];
    }

    const userAnswer = String(ua || "").trim();

    const correctAnswer =
      String(q.answer?.[lang] || q.answer?.en || "").trim();

    if (userAnswer) attempted++;

    const isCorrect =
      userAnswer &&
      correctAnswer &&
      userAnswer.toLowerCase() === correctAnswer.toLowerCase();

    if (isCorrect) correct++;

    // Subject stats
    const subject = q.subject || "General";
    subjectStats[subject] ??= { correct: 0, total: 0 };
    subjectStats[subject].total++;
    if (isCorrect) subjectStats[subject].correct++;

    // UI
    const questionText =
      q.question?.[lang] || q.question?.en || "Question unavailable";

    const explanationText =
      q.explanation?.[lang] || q.explanation?.en || "";

    const div = document.createElement("div");
    div.className = "answer-item";
    div.innerHTML = `
      <p class="question"><strong>Q${i + 1}.</strong> ${questionText}</p>
      <p class="user-answer ${isCorrect ? "correct" : "wrong"}">
        Your Answer: ${userAnswer || "Not Answered"}
      </p>
      ${
        !isCorrect && correctAnswer
          ? `<p class="correct-answer">Correct Answer: ${correctAnswer}</p>`
          : ""
      }
      ${explanationText ? `<p class="explanation">${explanationText}</p>` : ""}
    `;
    answersContainer.appendChild(div);
  });

  document.getElementById("scoreText").innerText =
    `Score: ${correct} / ${total}`;

  document.getElementById("statsText").innerText =
    `Attempted ${attempted} out of ${total} questions`;

  const subjectList = document.getElementById("subjectList");
  subjectList.innerHTML = "";

  Object.entries(subjectStats).forEach(([s, v]) => {
    const row = document.createElement("div");
    row.className = "subject-row";
    row.innerHTML = `<span>${s}</span><span>${v.correct}/${v.total}</span>`;
    subjectList.appendChild(row);
  });
});

function showError() {
  document.getElementById("scoreText").innerText =
    "Result not found. Please take the quiz again.";
}
