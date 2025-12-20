const langSelect = document.getElementById("languageSelect");
if (langSelect) {
  const savedLang = localStorage.getItem("lang") || "en";
  langSelect.value = savedLang;

  langSelect.addEventListener("change", () => {
    localStorage.setItem("lang", langSelect.value);
    location.reload();
  });
}

async function loadReasoning() {
  const res = await fetch("./data/reasoning.json");
  const data = await res.json();
  return data.questions;
}
