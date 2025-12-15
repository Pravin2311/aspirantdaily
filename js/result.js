// ==========================================
// RESULT PAGE LOGIC – FINAL STABLE VERSION
// Compatible with OLD (index-based) + NEW (text-based) answers
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
  const examData = JSON.parse(localStorage.getItem("examData"));
  const userAnswers = JSON.parse(localStorage.getItem("userAnswers")) || {};

  const scoreTextEl = document.getElementById("scoreText");
  const statsTextEl = document.getElementById("statsText");
  const answersContainer = document.getElementById("answersContainer");
  const subjectList = document.getElementById("subjectList");

  if (!examData || !Array.isArray(examData.questions)) {
    scoreTextEl.innerText = "Result data not found.";
    return;
  }

  const questions = examData.questions;
  const totalQuestions = questions.length;

  let correct = 0;
  let attempted = 0;
  const subjectStats = {};

  questions.forEach((q, index) => {
    let userAnswerRaw = userAnswers[index];
    const options = Array.isArray(q.options) ? q.options : [];

    // ✅ FIX 1: Convert index-based answers (SSC legacy)
    if (typeof userAnswerRaw === "number" && options[userAnswerRaw]) {
      userAnswerRaw = options[userAnswerRaw];
    }

    const userAnswer = String(userAnswerRaw || "").trim();
    const correctAnswer = String(q.answer || "").trim();

    if (userAnswer) attempted++;

    const isCorrect = userAnswer && userAnswer === correctAnswer;
    if (isCorrect) correct++;

    // ✅ Subject stats
    const subject = q.subject || "General";
    if (!subjectStats[subject]) {
      subjectStats[subject] = { correct: 0, total: 0 };
    }
    subjectStats[subject].total++;
    if (isCorrect) subjectStats[subject].correct++;

    // ---- Answer Review UI ----
    const div = document.createElement("div");
    div.className = "answer-item";

    div.innerHTML = `
      <p class="question"><strong>Q${index + 1}.</strong> ${q.question}</p>
      <p class="user-answer ${isCorrect ? "correct" : "wrong"}">
        Your Answer: ${userAnswer || "Not Answered"}
      </p>
      ${
        !isCorrect
          ? `<p class="correct-answer">Correct Answer: ${correctAnswer}</p>`
          : ""
      }
      <p class="explanation">${q.explanation || ""}</p>
    `;

    answersContainer.appendChild(div);
  });

  // ---- SCORE SUMMARY ----
  scoreTextEl.innerText = `Score: ${correct} / ${totalQuestions}`;
  statsTextEl.innerText = `Attempted ${attempted} out of ${totalQuestions} questions`;

  // ---- SUBJECT BREAKDOWN ----
  subjectList.innerHTML = "";
  Object.entries(subjectStats).forEach(([subject, stat]) => {
    const row = document.createElement("div");
    row.className = "subject-row";
    row.innerHTML = `
      <span>${subject}</span>
      <span>${stat.correct} / ${stat.total}</span>
    `;
    subjectList.appendChild(row);
  });
});

// ==========================================
// SHARE SCORE
// ==========================================
function shareScore() {
  const scoreText = document.getElementById("scoreText").innerText;
  const shareText = `I scored ${scoreText} on AspirantDaily! 🚀`;

  if (navigator.share) {
    navigator.share({
      title: "My AspirantDaily Score",
      text: shareText,
      url: window.location.origin
    });
  } else {
    alert(shareText);
  }
}
