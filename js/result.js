// Read encoded data from URL
const urlParams = new URLSearchParams(window.location.search);
const rawData = urlParams.get("data");

if (!rawData) {
  document.body.innerHTML = "<h2 class='text-center mt-20 text-2xl'>No data found.</h2>";
}

const { questions, userAnswers } = JSON.parse(decodeURIComponent(rawData));

let correctCount = 0;
let wrongCount = 0;

// Subject breakdown
let subjectMap = {};

// Calculate results
questions.forEach((q, i) => {
  const isCorrect = q.options[userAnswers[i]] === q.answer;

  if (!subjectMap[q.subject]) {
    subjectMap[q.subject] = { correct: 0, total: 0 };
  }

  subjectMap[q.subject].total++;

  if (isCorrect) {
    correctCount++;
    subjectMap[q.subject].correct++;
  } else {
    wrongCount++;
  }
});

// Update score UI
document.getElementById("scoreText").innerText =
  `Score: ${correctCount} / ${questions.length}`;

document.getElementById("statsText").innerText =
  `${correctCount} correct • ${wrongCount} incorrect`;

// Subject Breakdown UI
const subjectList = document.getElementById("subjectList");

Object.keys(subjectMap).forEach(sub => {
  const entry = subjectMap[sub];
  const percent = Math.round((entry.correct / entry.total) * 100);

  const row = document.createElement("div");
  row.innerHTML = `
    <p class="font-semibold text-gray-700">${sub}</p>
    <div class="w-full bg-gray-200 rounded-full h-3">
      <div class="h-3 rounded-full" 
           style="width:${percent}%; background:#6C63FF;"></div>
    </div>
    <p class="text-sm text-gray-500">${entry.correct} / ${entry.total} correct</p>
  `;
  subjectList.appendChild(row);
});

// Build expandable answers list
const container = document.getElementById("answersContainer");

questions.forEach((q, i) => {
  const userAns = q.options[userAnswers[i]];
  const isCorrect = userAns === q.answer;

  const card = document.createElement("div");
  card.className =
    "expand-card p-4 border rounded-lg cursor-pointer";

  card.innerHTML = `
    <div class="flex justify-between">
      <p class="font-semibold ${isCorrect ? 'text-green-600' : 'text-red-600'}">
        ${isCorrect ? "✔ Correct" : "✘ Wrong"}
      </p>
      <p class="text-gray-600 text-sm">Q${i + 1}</p>
    </div>

    <p class="mt-2 font-semibold">${q.question}</p>

    <div class="hidden mt-3 text-gray-700 explanation-box">
      <p><strong>Your answer:</strong> ${userAns || "No Answer"}</p>
      <p><strong>Correct answer:</strong> ${q.answer}</p>
      <p class="mt-2"><strong>Explanation:</strong><br>${q.explanation}</p>
    </div>
  `;

  card.onclick = () => {
    const box = card.querySelector(".explanation-box");
    box.classList.toggle("hidden");
  };

  container.appendChild(card);
});

function shareScore() {
  const text = `I scored ${correctCount}/${questions.length} in today's Daily 25 Quiz on Exam Prep Booster! 🔥`;

  if (navigator.share) {
    navigator.share({ text });
  } else {
    alert("Copy this score:\n\n" + text);
  }
}
