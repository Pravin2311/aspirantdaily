// result.js – FULL FEATURED (as in your earlier working version)
document.addEventListener("DOMContentLoaded", () => {
  // Get data (sessionStorage first, then localStorage)
  const examDataRaw = sessionStorage.getItem("examData") || localStorage.getItem("examData");
  const userAnswersRaw = sessionStorage.getItem("userAnswers") || localStorage.getItem("userAnswers");

  if (!examDataRaw || !userAnswersRaw) {
    document.getElementById("scoreText").innerText = "No result data found. Please take the quiz again.";
    return;
  }

  let examData, userAnswers;
  try {
    examData = JSON.parse(examDataRaw);
    userAnswers = JSON.parse(userAnswersRaw);
  } catch (e) {
    document.getElementById("scoreText").innerText = "Result data is corrupted.";
    return;
  }

  const questions = examData.questions || [];
  if (!Array.isArray(questions) || questions.length === 0) {
    document.getElementById("scoreText").innerText = "No questions to review.";
    return;
  }

  let correct = 0;
  let attempted = 0;
  const subjectMap = {};

  // Render each question
  const reviewContainer = document.getElementById("reviewContainer");
  reviewContainer.innerHTML = "";

  questions.forEach((q, i) => {
    let userAnswerValue = userAnswers[i];

    // Support legacy index-based answers (e.g., 0,1,2,3)
    if (typeof userAnswerValue === "number" && q.options && q.options[userAnswerValue] !== undefined) {
      userAnswerValue = q.options[userAnswerValue];
    }

    const userAnswerStr = String(userAnswerValue || "").trim();
    const correctAnswerStr = String(q.answer || "").trim();
    const isCorrect = userAnswerStr && userAnswerStr === correctAnswerStr;
    const isAttempted = !!userAnswerStr;

    if (isAttempted) attempted++;
    if (isCorrect) correct++;

    // Track subject stats
    const subject = q.subject || "General";
    if (!subjectMap[subject]) {
      subjectMap[subject] = { total: 0, correct: 0 };
    }
    subjectMap[subject].total++;
    if (isCorrect) subjectMap[subject].correct++;

    // Render question review
    const item = document.createElement("div");
    item.className = "review-item";
    item.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
        <strong>Q${i + 1}</strong>
        <span style="background:#${q.difficulty === 'easy' ? '4ade80' : q.difficulty === 'medium' ? 'fbbf24' : 'ef4444'};color:white;padding:2px 6px;border-radius:4px;font-size:0.8rem;">
          ${q.difficulty}
        </span>
      </div>
      <p><strong>${q.question}</strong></p>
      <p><em>Subject: ${subject}</em></p>
      <p><strong>Your answer:</strong> 
        <span style="color:${isCorrect ? '#047857' : '#b91c1c'}">${userAnswerStr || "Not attempted"}</span>
      </p>
      <p><strong>Correct answer:</strong> ${correctAnswerStr}</p>
      ${q.explanation ? `<p><em>Explanation:</em> ${q.explanation}</p>` : ''}
      <hr style="margin:1rem 0;">
    `;
    reviewContainer.appendChild(item);
  });

  // Update score
  document.getElementById("scoreText").innerText = `Score: ${correct} / ${questions.length}`;
  document.getElementById("statsText").innerText = `Attempted: ${attempted} | Correct: ${correct}`;

  // Render subject breakdown
  const subjectList = document.getElementById("subjectList");
  const subjectBreakdown = document.getElementById("subjectBreakdown");
  const subjects = Object.keys(subjectMap);
  if (subjects.length > 0) {
    subjectBreakdown.classList.remove("hidden");
    subjectList.innerHTML = subjects.map(subj => {
      const s = subjectMap[subj];
      const pct = Math.round((s.correct / s.total) * 100);
      return `<p><strong>${subj}:</strong> ${s.correct}/${s.total} (${pct}%)</p>`;
    }).join('');
  }
});