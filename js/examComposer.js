// ==========================================
// examComposer.js
// Local exam composer with refresh buckets
// ==========================================

import { EXAM_BLUEPRINTS } from "./examBlueprints.js";

const API = "https://exam-prep-generator.mydomain2311.workers.dev";

// ===============================
// PUBLIC API
// ===============================
export async function buildExam(exam) {
  const blueprint = EXAM_BLUEPRINTS[exam];
  if (!blueprint) throw new Error("Invalid exam");

  const bucketKey = getBucketKey(exam, blueprint.refresh);
  const cacheKey = `exam_${exam}_${bucketKey}`;

  // ===============================
  // CACHE CHECK
  // ===============================
  const cached = localStorage.getItem(cacheKey);
  if (cached) {
    return JSON.parse(cached);
  }

  // ===============================
  // BUILD EXAM
  // ===============================
  let questions = [];

  for (const section of blueprint.sections) {
    const data = await fetchSubject(section.subject);
    questions.push(...pick(data.questions, section.count));
  }

  questions = shuffle(questions);

  localStorage.setItem(cacheKey, JSON.stringify(questions));
  return questions;
}

// ===============================
// BUCKET LOGIC
// ===============================
function getBucketKey(exam, refresh) {
  const now = new Date();

  // Force IST
  const ist = new Date(
    now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" })
  );

  if (refresh === "daily") {
    return ist.toISOString().split("T")[0]; // YYYY-MM-DD
  }

  if (refresh === "weekly") {
    return getISOWeek(ist); // YYYY-W##
  }

  // fallback
  return ist.toISOString().split("T")[0];
}

// ISO week number (Monday start)
function getISOWeek(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
  return `${d.getUTCFullYear()}-W${weekNo}`;
}

// ===============================
// HELPERS
// ===============================
async function fetchSubject(subject) {
  const res = await fetch(`${API}/?subject=${subject}`, {
    cache: "no-store"
  });
  const data = await res.json();
  return data;
}

function pick(pool, count) {
  return shuffle([...pool]).slice(0, count);
}

function shuffle(arr) {
  return arr.sort(() => Math.random() - 0.5);
}
