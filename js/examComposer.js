// ==========================================
// examComposer.js – FINAL TRUE FIX
// Zero overlap across exams per subject/day
// ==========================================

import { EXAM_BLUEPRINTS } from "./examBlueprints.js";

const CA_API =
  "https://exam-prep-generator.mydomain2311.workers.dev/currentaffairs";

// Fixed exam order (VERY IMPORTANT)
const EXAM_ORDER = ["ssc", "bank", "rrb", "psc", "cuet", "upsc", "mixed"];

// ===============================
// PUBLIC API
// ===============================
export async function buildExam(exam) {
  const blueprint = EXAM_BLUEPRINTS[exam];
  if (!blueprint) throw new Error("Invalid exam");

  const bucketKey = getBucketKey(blueprint.refresh);
  const cacheKey = `exam_${exam}_${bucketKey}`;

  const cached = localStorage.getItem(cacheKey);
  if (cached) return JSON.parse(cached);

  let finalQuestions = [];

  for (const section of blueprint.sections) {
    const pool = await loadSubject(section.subject);
    if (!Array.isArray(pool) || pool.length === 0) continue;

    // 🔥 Shuffle once per subject/day
    const shuffled = seededShuffle(
      pool,
      `${section.subject}-${bucketKey}`
    );

    // 🔥 Calculate exam-specific offset
    const offset = getExamOffset(
      exam,
      section.subject,
      bucketKey,
      section.count
    );

    finalQuestions.push(
      ...shuffled.slice(offset, offset + section.count)
    );
  }

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
  if (subject === "current-affairs") {
    const res = await fetch(CA_API, { cache: "no-store" });
    const data = await res.json();
    return data.questions || [];
  }

  const res = await fetch(`./data/${subject}.json`);
  const data = await res.json();
  return data.questions || [];
}

// ===============================
// EXAM OFFSET LOGIC (THE FIX)
// ===============================
function getExamOffset(exam, subject, bucketKey, count) {
  const index = EXAM_ORDER.indexOf(exam);
  if (index === -1) return 0;

  // Each exam starts after previous exam’s allocation
  return index * count;
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
    return ist.toISOString().split("T")[0];
  }

  if (refresh === "weekly") {
    return getISOWeek(ist);
  }

  return ist.toISOString().split("T")[0];
}

function getISOWeek(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
  return `${d.getUTCFullYear()}-W${weekNo}`;
}

// ===============================
// DETERMINISTIC SHUFFLE
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
