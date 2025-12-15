// ===============================
// result.js – FINAL VERSION
// ===============================

document.addEventListener("DOMContentLoaded", () => {
  const examData = JSON.parse(localStorage.getItem("examData"));
  const userAnswers = JSON.parse(localStorage.getItem("userAnswers")) || [];

  if (!examData || !examData.questions) {
    document.getElementById("scoreText").innerText = "No result found.";
    return;
  }

  let correct = 0;
  let attempted = 0;

  examData.questions.forEach((q, i) => {
    const ua = (userAnswers[i] || "").toLowerCase();
    const ca = (q.answer || "").toLowerCase();
    if (ua) attempted++;
    if (ua && ua === ca) correct++;
  });

  document.getElementById("scoreText").innerText =
    `Score: ${correct} / ${examData.questions.length}`;

  document.getElementById("statsText").innerText =
    `Attempted ${attempted} questions`;
});
