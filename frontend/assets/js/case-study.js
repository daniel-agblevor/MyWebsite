import { api } from "./api.js";
import { initTheme } from "./theme.js";

const title = document.querySelector("[data-case-title]");
const summary = document.querySelector("[data-case-summary]");
const narrative = document.querySelector("[data-case-narrative]");
const tools = document.querySelector("[data-case-tools]");
const sections = [["context", "Context"], ["challenge", "Challenge"], ["constraints", "Constraints"], ["approach", "Approach"], ["solution", "Solution"], ["outcome", "Outcome"], ["reflection", "Reflection"]];

async function load() {
  initTheme();
  document.querySelector("[data-current-year]").textContent = new Date().getFullYear();
  const slug = new URLSearchParams(location.search).get("slug");
  if (!slug) return fail("No case study was selected.");
  try {
    const [caseResult, profileResult] = await Promise.all([api(`/api/case-studies/${encodeURIComponent(slug)}`), api("/api/profile")]);
    const item = caseResult.data;
    const profile = profileResult.data;
    if (profile?.display_name) {
      document.querySelectorAll("[data-brand-name]").forEach((node) => { node.textContent = profile.display_name; });
    }
    title.textContent = item.title; summary.textContent = item.summary; document.title = `${item.title} · ${profile?.display_name || "Daniel Yao Agblevor"}`;
    item.tools.forEach((value) => { const pill = document.createElement("span"); pill.className = "pill"; pill.textContent = value; tools.append(pill); });
    sections.forEach(([key, label], index) => { const section = document.createElement("section"); section.className = "case-narrative-block"; const number = document.createElement("span"); number.textContent = String(index + 1).padStart(2, "0"); const content = document.createElement("div"); const heading = document.createElement("h2"); heading.textContent = label; const body = document.createElement("p"); body.textContent = item[key]; content.append(heading, body); section.append(number, content); narrative.append(section); });
  } catch (_error) { fail("This case study is unavailable."); }
}

function fail(message) {
  title.textContent = message; summary.textContent = "It may have been unpublished or the website service may be temporarily unavailable.";
  const link = document.createElement("a"); link.className = "button"; link.href = "../#case-studies"; link.textContent = "Return to case studies"; narrative.append(link);
}

load();

