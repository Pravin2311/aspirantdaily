// ==========================================
// examComposer.js – FINAL LOCKED VERSION
// Exam-aware, deterministic, hybrid loader
// ==========================================

import { EXAM_BLUEPRINTS } from "./examBlueprints.js";

const CA_API =
  "https://exam-prep-generator.mydomain2311.workers.dev/currentaffairs";

// ===============================
// PUBLIC API
// ===============================
export async function buildExam(exam) {
  const blueprint = EXAM_BLUEPRINTS[exam];
  if (!blueprint) throw new Error("Invalid exam");

  const bucketKey = getBucketKey(blueprint.refresh);
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
  let finalQuestions = [];

  for (const section of blueprint.sections) {
    const pool = await loadSubject(section.subject);

    if (!Array.isArray(pool) || pool.length === 0) continue;

    const shuffled = seededShuffle(
      pool,
      `${exam}-${section.subject}-${bucketKey}`
    );

    finalQuestions.push(...shuffled.slice(0, section.count));
  }

  // Final exam-level shuffle (still deterministic)
  finalQuestions = seededShuffle(
    finalQuestions,
    `${exam}-final-${bucketKey}`
  );

  localStorage.setItem(cacheKey, JSON.stringify(finalQuestions));
  return finalQuestions;
}

// ===============================
// SUBJECT LOADER
// ===============================
async function loadSubject(subject) {
  // 🔥 Current Affairs → Worker / KV
  if (subject === "current-affairs") {
    const res = await fetch(CA_API, { cache: "no-store" });
    const data = await res.json();
    return data.questions || [];
  }

  // 📦 Static subjects → local JSON
  const res = await fetch(`./data/${subject}.json`);
  const data = await res.json();
  return data.questions || [];
}

// ===============================
// BUCKET LOGIC (IST SAFE)
// ===============================
function getBucketKey(refresh) {
  const now = new Date();
  const ist = new Date(
    now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" })
  );

  if (refresh === "daily") {
    return ist.toISOString().split("T")[0]; // YYYY-MM-DD
  }

  if (refresh === "weekly") {
    return getISOWeek(ist); // YYYY-W##
  }

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
// DETERMINISTIC SHUFFLE (NO RANDOM)
// ===============================
function seededShuffle(array, seed) {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash << 5) - hash + seed.charCodeAt(i);
    hash |= 0;
  }

  const result = [...array];

  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.abs(hash + i) % (i + 1);
    [result[i], result[j]] = [result[j], result[i]];
  }

  return result;
}
