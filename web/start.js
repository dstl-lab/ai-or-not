import { api } from "./api.js";

const form = document.getElementById("start-form");
const input = document.getElementById("participant");
const practice = document.getElementById("practice");
const error = document.getElementById("error");
const button = document.getElementById("start");

input.focus();

function showError(message) {
  error.textContent = message;
  error.hidden = !message;
}

async function start(allowDuplicate = false) {
  const body = {
    participant_id: input.value.trim(),
    practice: practice.checked,
    allow_duplicate: allowDuplicate,
    screen: `${window.screen.width}x${window.screen.height}`,
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
