// ===============================
// loader.js – FINAL VERSION
// Navigation Controller Only
// ===============================

(function () {
  const params = new URLSearchParams(window.location.search);

  const exam = params.get("exam");
  const subject = params.get("subject");
  const quiz = parseInt(params.get("quiz"), 10);

  // ===============================
  // EXAM MODE (direct)
  // ===============================
  if (exam) {
    window.location.href = `quiz.html?exam=${exam}`;
    return;
  }

  // ===============================
  // SUBJECT MODE (via selector)
  // ===============================
  if (subject) {
    const quizIndex =
      !isNaN(quiz) && quiz >= 1 && quiz <= 4 ? quiz - 1 : 0;

    localStorage.setItem(
      "practiceContext",
      JSON.stringify({
        subject,
        quizIndex
      })
    );

    window.location.href = "quiz.html";
    return;
  }

  // ===============================
  // INVALID ACCESS
  // ===============================
  alert("Invalid selection. Redirecting to home.");
  window.location.href = "index.html";
})();
