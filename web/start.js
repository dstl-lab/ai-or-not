import { api } from "./api.js";

const form = document.getElementById("start-form");
const input = document.getElementById("participant");
const practice = document.getElementById("practice");
const error = document.getElementById("error");
const button = document.getElementById("start");
const cohort = document.getElementById("cohort");
const courseBackground = document.getElementById("course-background");
const excludedSites = document.getElementById("excluded-sites");

input.focus();

function showError(message) {
  error.textContent = message;
  error.hidden = !message;
}

async function start(allowDuplicate = false) {
  if (!cohort.value) throw new Error("Choose the participant's background group.");
  const course = document.querySelector('input[name="dsc106"]:checked');
  if (cohort.value === "agentic_internship" && !course) {
    throw new Error("Specify whether this participant has completed DSC106.");
  }
  const body = {
    participant_id: input.value.trim(),
    practice: practice.checked,
    allow_duplicate: allowDuplicate,
    screen: `${window.screen.width}x${window.screen.height}`,
    cohort: cohort.value,
    dsc106_completed: cohort.value === "agentic_internship" ? course.value === "true" : cohort.value === "dsc106",
    excluded_site_ids: [...document.querySelectorAll('#excluded-sites input:checked')].map((i) => i.value),
  };
  const { id } = await api("/api/sessions", { method: "POST", body });
  // replace() so the browser's Back button can't drop the participant onto this setup page.
  window.location.replace(`/study/${id}`);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  if (!input.value.trim()) {
    showError("Enter a participant ID first.");
    input.focus();
    return;
  }
  button.disabled = true;
  try {
    await start();
  } catch (err) {
    if (err.status === 409 && confirm(`${err.message}. Start another session for them anyway?`)) {
      await start(true).catch((e) => showError(e.message));
    } else if (err.status !== 409) {
      showError(err.message);
    }
  } finally {
    button.disabled = false;
  }
});

input.addEventListener("input", () => showError(""));
cohort.addEventListener("change", () => {
  courseBackground.hidden = cohort.value !== "agentic_internship";
  showError("");
});

async function init() {
  button.disabled = true;
  try {
    const data = await api("/api/study");
    for (const c of data.cohorts) {
      const option = document.createElement("option");
      option.value = c.id;
      option.textContent = c.label;
      cohort.append(option);
      const description = document.createElement("p");
      description.textContent = `${c.label}: ${c.description}`;
      document.getElementById("cohort-descriptions").append(description);
    }
    for (const site of data.sites) {
      const label = document.createElement("label");
      label.className = "check";
      const check = document.createElement("input");
      check.type = "checkbox";
      check.value = site.id;
      const text = document.createElement("span");
      text.textContent = `${site.id} — ${site.title}`;
      label.append(check, text);
      excludedSites.append(label);
    }
    const instructions = data.instructions || `You will review up to ${data.sites_per_session} webpages. Browse each webpage and answer based on your overall impression. Your answers save automatically.`;
    document.getElementById("instructions").textContent = Array.isArray(instructions) ? instructions.join("\n\n") : instructions;
    button.disabled = false;
  } catch (err) {
    showError(`Couldn't load the study setup: ${err.message}. Reload this page to try again.`);
  }
}

init();
