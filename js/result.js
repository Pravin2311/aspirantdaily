// ==========================================
// RESULT PAGE LOGIC – FINAL FIXED VERSION
// Works with new generator.js (25 questions)
// ==========================================

// Expected storage format:
// localStorage.setItem("examData", JSON.stringify({ questions: [...] }));
// localStorage.setItem("userAnswers", JSON.stringify({ 0: "Option A", ... }));

document.addEventListener("DOMContentLoaded", () => {
  const examData = JSON.parse(localStorage.getItem("examData"));
  const userAnswers = JSON.parse(localStorage.getItem("userAnswers")) || {};

  if (!examData || !Array.isArray(examData.questions)) {
    document.getElementById("scoreText").innerText =
      "Result data not found.";
    return;
  }

  const questions = examData.questions;
  const totalQuestions = questions.length;

  let correct = 0;
  let attempted = 0;
  let subjectStats = {};

  const answersContainer = document.getElementById("answersContainer");

  questions.forEach((q, index) => {
    const userAnswer = (userAnswers[index] || "").trim();
    const correctAnswer = (q.answer || "").trim();

    if (userAnswer) attempted++;

    const isCorrect = userAnswer === correctAnswer;
    if (isCorrect) correct++;

    // Subject stats
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
      ${!isCorrect ? `<p class="correct-answer">Correct Answer: ${correctAnswer}</p>` : ""}
      <p class="explanation">${q.explanation || ""}</p>
    `;

    answersContainer.appendChild(div);
  });

  // ---- SCORE SUMMARY ----
  document.getElementById("scoreText").innerText =
    `Score: ${correct} / ${totalQuestions}`;

  document.getElementById("statsText").innerText =
    `Attempted ${attempted} out of ${totalQuestions} questions`;

  // ---- SUBJECT BREAKDOWN ----
  const subjectList = document.getElementById("subjectList");
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
