// ===============================
// loader.js – Production Version
// ===============================

const API_BASE = "https://exam-prep-generator.mydomain2311.workers.dev";

/**
 * Load questions for a given exam
 * @param {string} exam - ssc | bank | upsc | psc | rrb | cuet | mixed
 * @returns {Promise<Array>} questions array
 */
async function loadQuestions(exam) {
  try {
    const res = await fetch(`${API_BASE}/?exam=${exam}`);

    if (!res.ok) {
      throw new Error("Exam not ready");
    }

    const data = await res.json();

    if (!data || !Array.isArray(data.questions)) {
      throw new Error("Invalid question format");
    }

    return data.questions;
  } catch (err) {
    console.error("Loader error:", err);
    throw err;
  }
}
