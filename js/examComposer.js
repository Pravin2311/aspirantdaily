// ==========================================
// examComposer.js – FINAL LOCAL-FIRST VERSION
// Zero overlap across exams per subject/day
// ==========================================

import { EXAM_BLUEPRINTS } from "./examBlueprints.js";

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

    // 🔥 Exam-specific offset (zero overlap)
    const offset = getExamOffset(
      exam,
      section.subject,
      bucketKey,
      section.count,
      shuffled.length
    );

    finalQuestions.push(
      ...shuffled.slice(offset, offset + section.count)
    );
  }

  // Final deterministic shuffle
  finalQuestions = seededShuffle(
    finalQuestions,
    `${exam}-final-${bucketKey}`
  );

  localStorage.setItem(cacheKey, JSON.stringify(finalQuestions));
  return finalQuestions;
}

// ===============================
// SUBJECT LOADER (LOCAL ONLY)
// ===============================
async function loadSubject(subject) {
  try {
    const res = await fetch(`./data/${subject}.json`, {
      cache: "no-store"
    });

    if (!res.ok) {
      console.error(`❌ Missing data file for ${subject}`);
      return [];
    }

    const data = await res.json();
    return Array.isArray(data.questions) ? data.questions : [];

  } catch (err) {
    console.error(`❌ Failed to load subject ${subject}`, err);
    return [];
  }
}

// ===============================
// EXAM OFFSET LOGIC (SAFE VERSION)
// ===============================
function getExamOffset(exam, subject, bucketKey, count, poolSize) {
  const index = EXAM_ORDER.indexOf(exam);
  if (index === -1 || poolSize === 0) return 0;

  const rawOffset = index * count;

  // 🔒 Wrap safely if pool is smaller
  if (rawOffset >= poolSize) {
    return rawOffset % poolSize;
  }

  return rawOffset;
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
