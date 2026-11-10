import { api } from "./api.js";
import { confirmAction } from "./confirm.js";
import { AnnotationTool } from "./annotations.js";

let annotationTool;

const sessionId = location.pathname.split("/").filter(Boolean).pop();
const $ = (id) => document.getElementById(id);
const els = {
  layout: $("layout"), frameWrap: $("frame-wrap"), loading: $("frame-loading"),
  back: $("nav-back"), forward: $("nav-forward"), reload: $("nav-reload"), home: $("nav-home"),
  toolbarLabel: $("toolbar-label"), eyebrow: $("panel-eyebrow"), dots: $("dots"),
  questions: $("questions"), status: $("status"), prev: $("prev"), next: $("next"),
  title: $("panel-title"), rating: $("previous-rating"), guidance: $("phase-guidance"),
  reviewHelp: $("review-help"), websiteNavigation: $("website-navigation"),
  notesLink: $("review-notes-link"), notesCount: $("review-notes-count"),
  survey: $("survey"), surveyEyebrow: $("survey-eyebrow"), surveyTitle: $("survey-title"),
  surveyLede: $("survey-lede"), surveyQuestions: $("survey-questions"),
  surveyStatus: $("survey-status"), surveyBack: $("survey-back"), surveyNext: $("survey-next"),
  markBanner: $("mark-banner"), markDone: $("mark-done"),
};

// Background and closing answers are stored under these keys (see SURVEY_KEYS on the server).
const SURVEY = {
  background: {
    key: "_background", eyebrow: "Before you start", title: "About you",
    lede: "A few questions about you before the websites.",
  },
  closing: {
    key: "_closing", eyebrow: "Last step", title: "Your overall impressions",
    lede: "A few final questions about all the websites you saw.",
  },
};

const state = {
  sites: [],        // [{id, position, label, src, home, completed, unlocked}]
  sections: { questions: [], background: [], closing: [] },
  questions: [],     // compatibility alias for the active per-site section
  byId: {},
  answers: {},      // {siteId or survey key: {questionId: value}}
  index: 0,
  mode: "site",     // "site" | "background" | "closing"
  frame: null,
  showMissing: false,
  phase: "review",
  practice: false,
  followupSites: [],
};

const blank = (v) => v === null || v === undefined || v === "" ||
  (Array.isArray(v) && v.length === 0) || (typeof v === "object" && !Array.isArray(v) && !Object.keys(v).length);
const currentSite = () => state.sites[state.index];
const answersFor = (key) => (state.answers[key] ??= {});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const isSurveyKey = (key) => key.startsWith("_");
const siteQuestions = () => state.questions.length ? state.questions : state.sections.questions;
const questionsFor = (key) => (isSurveyKey(key) ? state.sections[key.slice(1)] : siteQuestions());

// Where the participant is now: which answers, which questions, which form.
function ctx() {
  if (state.mode === "site") {
    return { key: currentSite().id, questions: siteQuestions(), form: els.questions };
  }
  return { key: SURVEY[state.mode].key, questions: state.sections[state.mode], form: els.surveyQuestions };
}

// ---------------------------------------------------------------- answers

function missingIds(a, questions = siteQuestions()) {
  // Mirrors missing_answers() on the server, so the buttons react instantly.
  return questions
    .filter((q) => {
      const v = a[q.id];
      if (blank(v)) return q.required !== false &&
        !(q.required_unless && a[q.required_unless.question_id] === q.required_unless.value);
      if (q.type === "multi" && v.length < (q.min_selected ?? 1)) return true;
      if (q.type === "multi" && q.max_selected && v.length > q.max_selected) return true;
      if (q.type === "grid" && q.rows.some((r) => !(r.value in v))) return true;
      if (q.options_from && !(a[q.options_from] || []).includes(v)) return true;
      return false;
    })
    .map((q) => q.id);
}

function readValue(q, fieldset) {
  if (q.type === "text") return fieldset.querySelector("textarea").value;
  if (q.type === "multi") return [...fieldset.querySelectorAll("input:checked")].map((i) => i.value);
  if (q.type === "grid") {
    const value = {};
    for (const row of fieldset.querySelectorAll(".grid-row")) {
      const checked = row.querySelector("input:checked");
      if (checked) value[row.dataset.row] = checked.value === "na" ? "na" : Number(checked.value);
    }
    return value;
  }
  const checked = fieldset.querySelector("input:checked");
  if (!checked) return null;
  if (q.type === "boolean") return checked.value === "true";
  if (q.type === "scale") return Number(checked.value);
  return checked.value;
}

function setAnswer(q, value) {
  const { key, questions, form } = ctx();
  const a = answersFor(key);
  const firstRating = q.id === "ai_appearance" && blank(a[q.id]) && !blank(value);
  a[q.id] = blank(value) ? null : value;
  warn("");
  // A question that offers "which of those mattered most" must track this one.
  questions.forEach((dep, i) => {
    if (dep.options_from !== q.id) return;
    if (a[dep.id] != null && !(a[q.id] || []).includes(a[dep.id])) a[dep.id] = null;
    const old = form.querySelector(`fieldset[data-qid="${dep.id}"]`);
    old?.replaceWith(renderQuestion(dep, i + 1, a, questions));
  });
  const checks = form.querySelector(".review-checks");
  if (firstRating && checks) checks.open = true;
  saver.mark(key);
  applyMaxSelected(q, form.querySelector(`fieldset[data-qid="${q.id}"]`));
  updateProgress();
}

// Autosave: every change is written to the server shortly after it happens, in order.
const saver = {
  dirty: new Set(),
  timer: null,
  chain: Promise.resolve(),
  pending: 0,
  failing: false,

  mark(key) {
    this.dirty.add(key);
    setStatus("Saving…");
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.flush().catch(() => {}), 350);
  },

  flush() {
    clearTimeout(this.timer);
    for (const key of this.dirty) {
      const payload = {};
      for (const q of questionsFor(key)) payload[q.id] = answersFor(key)[q.id] ?? null;
      this.pending++;
      this.chain = this.chain.then(() => this.send(key, payload), () => this.send(key, payload))
        .finally(() => { this.pending--; });
    }
    this.dirty.clear();
    return this.chain;
  },

  async send(key, answers) {
    const url = isSurveyKey(key)
      ? `/api/sessions/${sessionId}/survey/${key.slice(1)}/answers`
      : `/api/sessions/${sessionId}/sites/${key}/answers`;
    for (let attempt = 0; ; attempt++) {
      try {
        await api(url, { method: "PUT", body: { answers } });
        this.failing = false;
        if (!this.dirty.size && this.pending === 1) setStatus("All answers saved");
        return;
      } catch (err) {
        if (err.status && err.status < 500) {
          this.dirty.add(key);
          this.failing = true;
          setStatus(`Not saved: ${err.message}`, true);
          throw err;
        }
        this.failing = true;
        setStatus("Couldn't reach the study server. Retrying…", true);
        await sleep(Math.min(8000, 1000 * 2 ** attempt));
      }
    }
  },

  get busy() {
    return this.dirty.size > 0 || this.pending > 0 || this.failing;
  },
};

// ---------------------------------------------------------------- rendering

function option(type, name, value, label, checked) {
  const wrap = document.createElement("label");
  wrap.className = "option";
  const input = document.createElement("input");
  Object.assign(input, { type, name, value: String(value), checked });
  const text = document.createElement("span");
  text.textContent = label;
  wrap.append(input, text);
  return wrap;
}

function scaleEnds(q) {
  const ends = document.createElement("div");
  ends.className = "scale-ends";
  ends.innerHTML = "<span></span><span></span>";
  ends.children[0].textContent = q.min_label ? `${q.min} = ${q.min_label}` : "";
  ends.children[1].textContent = q.max_label ? `${q.max} = ${q.max_label}` : "";
  return ends;
}

function renderGrid(q, value) {
  const box = document.createElement("div");
  box.className = "grid";
  if (q.min_label || q.max_label) box.append(scaleEnds(q));
  for (const r of q.rows) {
    const row = document.createElement("div");
    row.className = "grid-row";
    row.dataset.row = r.value;
    const label = document.createElement("div");
    label.className = "grid-label";
    label.textContent = r.label;
    const cells = document.createElement("div");
    cells.className = "grid-cells" + (q.allow_na ? " with-na" : "");
    cells.style.setProperty("--steps", q.max - q.min + 1);
    cells.setAttribute("role", "radiogroup");
    cells.setAttribute("aria-label", r.label);
    const current = value?.[r.value];
    const name = `q-${q.id}-${r.value}`;
    for (let n = q.min; n <= q.max; n++) cells.append(option("radio", name, n, String(n), current === n));
    if (q.allow_na) {
      const na = option("radio", name, "na", "N/A", current === "na");
      na.className += " na";
      cells.append(na);
    }
    row.append(label, cells);
    box.append(row);
  }
  return box;
}

function renderInputs(q, a, questions) {
  const value = a[q.id];
  const name = `q-${q.id}`;
  const box = document.createElement("div");

  if (q.type === "annotation") return annotationTool.render(q, value || []);

  if (q.type === "text") {
    box.className = "text-answer";
    const input = document.createElement("textarea");
    input.name = name;
    input.rows = 3;
    input.value = value ?? "";
    if (q.max_length) input.maxLength = q.max_length;
    input.setAttribute("aria-label", q.prompt);
    box.append(input);
  } else if (q.type === "boolean") {
    box.className = "options pair";
    box.append(option("radio", name, true, q.true_label, value === true),
               option("radio", name, false, q.false_label, value === false));
  } else if (q.type === "scale") {
    box.className = "scale";
    const row = document.createElement("div");
    row.className = "scale-row";
    row.style.setProperty("--steps", q.max - q.min + 1);
    for (let n = q.min; n <= q.max; n++) {
      const choice = option("radio", name, n, String(n), value === n);
      const caption = q.options?.find((o) => String(o.value) === String(n))?.label;
      if (caption) {
        choice.firstChild.setAttribute("aria-label", `${n} — ${caption}`);
        const number = document.createElement("strong");
        number.className = "scale-value";
        number.textContent = n;
        const label = document.createElement("span");
        label.className = "scale-caption";
        label.textContent = caption;
        choice.lastChild.className = "scale-choice";
        choice.lastChild.replaceChildren(number, label);
      }
      row.append(choice);
    }
    box.append(row);
    if (!q.options?.length) {
      box.append(scaleEnds(q));
    }
  } else if (q.type === "grid") {
    return renderGrid(q, value);
  } else if (q.type === "marks") {
    return renderMarks(q, value);
  } else if (q.type === "multi") {
    box.className = "options";
    for (const o of q.options) {
      const opt = option("checkbox", name, o.value, o.label, (value || []).includes(o.value));
      if (o.exclusive) opt.querySelector("input").dataset.exclusive = "true";
      box.append(opt);
    }
    applyMaxSelected(q, box);
  } else {
    let opts = q.options;
    if (q.options_from) {
      const picked = a[q.options_from] || [];
      opts = opts.filter((o) => picked.includes(o.value));
      if (!opts.length) {
        const source = questions.find((x) => x.id === q.options_from);
        box.className = "empty-hint";
        box.textContent = `Choose at least one option in “${source?.prompt || q.options_from}” first.`;
        return box;
      }
    }
    box.className = "options";
    for (const o of opts) box.append(option("radio", name, o.value, o.label, value === o.value));
  }
  return box;
}

// "Choose up to 3": once the limit is reached, the remaining boxes are disabled.
function applyMaxSelected(q, root) {
  if (q.type !== "multi" || q.max_selected == null) return;
  const inputs = [...root.querySelectorAll("input[type=checkbox]")];
  const full = inputs.filter((i) => i.checked).length >= q.max_selected;
  for (const input of inputs) {
    input.disabled = full && !input.checked;
    input.closest(".option").classList.toggle("disabled", input.disabled);
  }
}

function updateSelectionLimit(q, container, value) {
  if (q.type !== "multi" || !q.max_selected || !container) return;
  const count = (value || []).length;
  for (const input of container.querySelectorAll('input[type="checkbox"]')) {
    input.disabled = !input.checked && count >= q.max_selected;
  }
  const hint = container.querySelector(".selection-limit");
  if (hint) hint.textContent = `${count} of ${q.max_selected} selected.`;
}

function missingNote(q) {
  if (q.type === "multi" && (q.min_selected ?? 1) > 1) return `Select at least ${q.min_selected}.`;
  if (q.type === "grid") return q.allow_na ? "Rate every row (or choose N/A)." : "Rate every row.";
  if (q.type === "marks") return "Mark at least one spot on the website, or tick the box below.";
  return "Please answer this question.";
}

function renderQuestion(q, number, a, questions) {
  const fieldset = document.createElement("fieldset");
  fieldset.className = "q" + (q.id === "ai_appearance" ? " q-primary" : "") +
    (["seen_before", "technical_issue"].includes(q.id) ? " q-secondary" : "");
  fieldset.dataset.qid = q.id;
  const legend = document.createElement("legend");
  legend.textContent = q.prompt;
  fieldset.append(legend);
  if (q.help) {
    const help = document.createElement("p");
    help.className = "help";
    help.textContent = q.help;
    fieldset.append(help);
  }
  fieldset.append(renderInputs(q, a, questions));
  const note = document.createElement("p");
  note.className = "missing-note";
  note.textContent = missingNote(q);
  fieldset.append(note);
  return fieldset;
}

function renderQuestions() {
  const { key, questions, form } = ctx();
  const a = answersFor(key);
  if (state.mode !== "site") {
    form.replaceChildren(...questions.map((q, i) => renderQuestion(q, i + 1, a, questions)));
    form.scrollTop = 0;
    return;
  }
  const grouped = questions.filter(q => state.phase === "followup"
    ? q.type === "annotation" : ["seen_before", "technical_issue"].includes(q.id));
  form.replaceChildren(...questions.filter(q => !grouped.includes(q))
    .map((q, i) => renderQuestion(q, i + 1, a, questions)));
  if (grouped.length) {
    const details = document.createElement("details");
    details.className = state.phase === "followup" ? "review-notes" : "review-checks";
    const summary = document.createElement("summary");
    const label = document.createElement("span");
    label.textContent = state.phase === "followup" ? "Page notes " : "Review checks ";
    const meta = document.createElement("span");
    meta.className = "section-meta";
    summary.append(label, meta);
    details.open = state.phase === "followup" ? Boolean(annotationTool?.draft || annotationTool?.armed)
      : !blank(a.ai_appearance) || grouped.some(q => !blank(a[q.id]));
    if (state.phase === "followup") details.addEventListener("toggle", () => {
      if (annotationTool?.draft || annotationTool?.armed) details.open = true;
    });
    details.append(summary, ...grouped.map((q, i) => renderQuestion(q, i + 1, a, questions)));
    form.append(details);
  }
  form.scrollTop = 0;
  els.rating.hidden = state.phase !== "followup";
  if (state.phase === "followup") {
    els.rating.textContent = a.ai_appearance == null ? "Your earlier rating is saved."
      : `Your earlier AI-appearance rating: ${a.ai_appearance} out of 5. This rating is saved and cannot be changed.`;
  }
}

function renderDots() {
  els.dots.replaceChildren(...state.sites.map((site, i) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.className = "dot" + (site.completed ? " done" : "") + (i === state.index ? " current" : "");
    dot.textContent = state.phase === "followup" ? i + 1 : site.position;
    dot.disabled = !site.unlocked;
    dot.setAttribute("aria-label", `${site.label}${site.completed ? " (done)" : ""}`);
    if (i === state.index) dot.setAttribute("aria-current", "step");
    dot.addEventListener("click", () => !els.next.disabled && i !== state.index && goTo(i));
    return dot;
  }));
}

const plural = (n) => `Answer ${n} more question${n === 1 ? "" : "s"}`;

function updateProgress() {
  const { key, questions, form } = ctx();
  const a = answersFor(key);
  const missing = missingIds(a, questions);
  if (state.mode === "site") {
    const last = state.index === state.sites.length - 1;
    els.prev.disabled = state.index === 0 && (state.phase === "followup" || !state.sections.background.length);
    // The button remains an active shortcut to the first unanswered question.
    els.next.setAttribute("aria-disabled", "false");
    let nextAction = plural(missing.length);
    if (state.phase === "review" && missing.includes("ai_appearance")) nextAction = "Choose a rating";
    else if (state.phase === "review" && missing.length &&
             missing.every(id => ["seen_before", "technical_issue"].includes(id))) {
      nextAction = "Complete review checks";
    } else if (state.phase === "followup" && missing[0] === "cues" && state.byId.cues?.max_selected) {
      nextAction = `Select ${state.byId.cues.min_selected ?? 1}–${state.byId.cues.max_selected} cues`;
    }
    els.next.textContent = annotationTool?.draft ? "Return to note" : missing.length ? nextAction
      : !last ? "Next website"
      : state.phase === "review" && state.followupSites.length ? "Continue to final questions"
      : state.sections.closing.length ? "Continue" : "Finish";

    const checks = form.querySelector(".review-checks");
    if (checks) {
      const remaining = [...checks.querySelectorAll("fieldset.q")]
        .filter(fieldset => missing.includes(fieldset.dataset.qid)).length;
      checks.querySelector(".section-meta").textContent = remaining ? `${remaining} remaining` : "Complete";
    }
    const annotationQuestions = questions.filter(q => q.type === "annotation");
    const count = annotationQuestions.reduce((total, q) => total + (a[q.id] || []).length, 0);
    els.notesLink.hidden = !annotationQuestions.length;
    els.notesCount.textContent = count;
    els.notesLink.setAttribute("aria-label", `Page notes, ${count} saved note${count === 1 ? "" : "s"}, optional`);
    const notes = form.querySelector(".review-notes");
    if (notes) {
      notes.querySelector(".section-meta").textContent = `${count} note${count === 1 ? "" : "s"} · Optional`;
      if (annotationTool?.draft || annotationTool?.armed) notes.open = true;
    }
  } else {
    els.surveyNext.setAttribute("aria-disabled", String(missing.length > 0));
    els.surveyNext.textContent = missing.length ? plural(missing.length)
      : state.mode === "closing" ? "Finish" : "Start the websites";
  }
  for (const fieldset of form.querySelectorAll("fieldset.q")) {
    const isMissing = state.showMissing && missing.includes(fieldset.dataset.qid);
    fieldset.classList.toggle("missing", isMissing);
    for (const row of fieldset.querySelectorAll(".grid-row")) {
      row.classList.toggle("missing", isMissing && !(row.dataset.row in (a[fieldset.dataset.qid] || {})));
    }
  }
  renderStatus();
  return missing;
}

function revealQuestion(id) {
  const fieldset = els.questions.querySelector(`fieldset[data-qid="${id}"]`);
  if (!fieldset) return;
  els.layout.classList.toggle("collapsed", false);
  const details = fieldset.closest("details");
  if (details) details.open = true;
  fieldset.scrollIntoView({ behavior: "smooth", block: "start" });
  fieldset.querySelector("input:not(:disabled), textarea, button")?.focus({ preventScroll: true });
}

function revealAnnotation() {
  const question = siteQuestions().find(q => q.type === "annotation");
  if (question) revealQuestion(question.id);
}

function revealMissing(missing, form) {
  state.showMissing = true;
  updateProgress();
  const fieldset = form.querySelector(`fieldset[data-qid="${missing[0]}"]`);
  if (!fieldset) return;
  const details = fieldset.closest("details");
  if (details) details.open = true;
  fieldset.scrollIntoView({ behavior: "smooth", block: "start" });
  fieldset.querySelector("input:not(:disabled), textarea, button")?.focus({ preventScroll: true });
}

// Warnings and save failures stay visible above note guidance and save confirmations.
const status = { save: "", saveBad: false, warning: "" };

function renderStatus() {
  const noteStatus = annotationTool?.draft ? "Note not saved. Save note or Cancel to continue."
    : annotationTool?.armed ? "Select a detail on the webpage. Esc cancels." : "";
  els.status.textContent = status.warning || (status.saveBad ? status.save : noteStatus || status.save);
  els.status.classList.toggle("bad", Boolean(status.warning) || status.saveBad);
  els.status.classList.toggle("pending", Boolean(noteStatus) && !status.warning && !status.saveBad);
  els.surveyStatus.textContent = status.warning || status.save;
  els.surveyStatus.classList.toggle("bad", Boolean(status.warning) || status.saveBad);
}

function setStatus(text, bad = false) {
  Object.assign(status, { save: text, saveBad: bad });
  renderStatus();
}

function warn(text) {
  status.warning = text;
  renderStatus();
}

// ---------------------------------------------------------------- the website frame

function loadFrame(site) {
  annotationTool?.stopSelecting();
  if (annotationTool) {
    annotationTool.pending = null;
    annotationTool.refresh();
  }
  state.frame?.remove();
  els.loading.hidden = false;
  // A fresh iframe per visit also gives each site its own clean back/forward history.
  const frame = document.createElement("iframe");
  frame.title = site.label;
  // Same-origin copies run normally, but may not navigate the whole study page away.
  frame.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms allow-popups " +
    "allow-popups-to-escape-sandbox allow-modals allow-downloads allow-pointer-lock allow-presentation");
  frame.setAttribute("allow", "fullscreen; autoplay; clipboard-write");
  frame.addEventListener("load", () => onFrameLoad(frame, site));
  frame.src = site.src;
  els.frameWrap.append(frame);
  state.frame = frame;
  updateNavButtons();
}

function onFrameLoad(frame, site) {
  if (frame !== state.frame) return;
  els.loading.hidden = true;
  try {
    const win = frame.contentWindow;
    if (!win.location.pathname.startsWith(site.home)) {
      // A link escaped the site's folder (e.g. href="/"), which would show the study app itself.
      win.location.replace(site.src);
      return;
    }
    win.document.addEventListener("click", (e) => openOutsideLinksInNewTab(e, site), true);
    win.navigation?.addEventListener("currententrychange", updateNavButtons);
    annotationTool?.attach(frame, site);
    installMarker(win, site);
  } catch {
    // The participant followed a link to another website; nothing to hook into.
  }
  updateNavButtons();
}

function openOutsideLinksInNewTab(event, site) {
  const link = event.target.closest?.("a[href]");
  if (!link) return;
  const url = new URL(link.getAttribute("href"), link.ownerDocument.baseURI);
  if (!url.protocol.startsWith("http")) return;
  if (url.origin !== location.origin || !url.pathname.startsWith(site.home)) {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  }
}

function frameNavigation() {
  try {
    return state.frame?.contentWindow?.navigation ?? null;
  } catch {
    return null; // cross-origin page
  }
}

function updateNavButtons() {
  const nav = frameNavigation();
  els.back.disabled = !nav?.canGoBack;
  els.forward.disabled = !nav?.canGoForward;
}

// ---------------------------------------------------------------- time on site

const timer = {
  since: null,
  stopped: false,
  start() {
    if (this.stopped || state.mode !== "site" || document.visibilityState !== "visible") return;
    if (this.since === null) this.since = performance.now();
  },
  flush(beacon = false) {
    if (this.since === null) return;
    const seconds = (performance.now() - this.since) / 1000;
    this.since = null;
    const site = currentSite();
    if (!site || seconds < 0.5) return;
    const url = `/api/sessions/${sessionId}/sites/${site.id}/time`;
    const body = JSON.stringify({ seconds, phase: state.phase });
    if (beacon) navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
    else fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body }).catch(() => {});
  },
};

// ---------------------------------------------------------------- marking spots on the website
//
// A "marks" question lets participants click the website itself. While marking is on, clicks
// inside the site are intercepted (so links and charts don't react) and the clicked element is
// recorded; scrolling still works. Marked spots stay outlined and numbered on the site.

const OVERLAY_ID = "__aiornot-marks";
const STYLE_ID = "__aiornot-marks-style";
const MARK_COLOR = "#e8590c";
const marker = {
  active: false,
  hover: null,       // element under the cursor while marking
  cache: new Map(),  // mark id -> element on the current page
};

const marksQuestion = () => siteQuestions().find((q) => q.type === "marks");

function siteMarks() {
  const q = marksQuestion();
  if (!q || state.mode !== "site" || !currentSite()) return [];
  const value = answersFor(currentSite().id)[q.id];
  return Array.isArray(value) ? value : [];
}

function frameWindow() {
  try {
    const win = state.frame?.contentWindow;
    return win && win.document ? win : null;
  } catch {
    return null; // a page from another website
  }
}

function pageOf(win, site) {
  let path = win.location.pathname;
  if (path.startsWith(site.home)) path = path.slice(site.home.length);
  return path.replace(/(^|\/)index\.html$/, "$1");
}

function cssPath(el) {
  const parts = [];
  for (let node = el; node && node.nodeType === 1 && node.localName !== "html"; node = node.parentElement) {
    if (node.id && node.ownerDocument.querySelectorAll(`#${CSS.escape(node.id)}`).length === 1) {
      parts.unshift(`#${CSS.escape(node.id)}`);
      break;
    }
    let part = CSS.escape(node.localName);
    const siblings = node.parentElement ? [...node.parentElement.children].filter((c) => c.localName === node.localName) : [];
    if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
    parts.unshift(part);
  }
  return parts.join(" > ");
}

function kindOf(el) {
  const t = el.localName;
  if (el.closest("svg, canvas")) return "Chart or graphic";
  if (/^h[1-6]$/.test(t)) return "Heading";
  if (el.closest("button, [role=button]")) return "Button";
  if (el.closest("input, select, textarea, label")) return "Control";
  if (el.closest("a")) return "Link";
  if (["img", "picture", "video", "figure"].includes(t)) return "Image";
  if (el.closest("nav")) return "Navigation";
  if (["p", "li", "blockquote", "span", "em", "strong", "b", "i", "small", "label"].includes(t)) return "Text";
  if (["body", "main", "html"].includes(t)) return "Whole page";
  return "Section";
}

function textOf(el) {
  const raw = el.innerText ?? el.textContent ?? "";
  const text = raw || el.getAttribute("aria-label") || el.getAttribute("alt") || el.getAttribute("title") || "";
  return text.replace(/\s+/g, " ").trim().slice(0, 120);
}

function describeElement(el, win) {
  const r = el.getBoundingClientRect();
  return {
    selector: cssPath(el), tag: el.localName, kind: kindOf(el), text: textOf(el),
    box: { x: Math.round(r.left + win.scrollX), y: Math.round(r.top + win.scrollY),
           w: Math.round(r.width), h: Math.round(r.height) },
  };
}

function resolveMark(mark, doc) {
  const cached = marker.cache.get(mark.id);
  if (cached?.isConnected && cached.ownerDocument === doc) return cached;
  let el = null;
  try { el = doc.querySelector(mark.selector); } catch { /* selector from an older page */ }
  if (el) marker.cache.set(mark.id, el);
  return el;
}

function outline(doc, el, label, kind) {
  const r = el.getBoundingClientRect();
  const box = doc.createElement("div");
  const color = kind === "mark" ? MARK_COLOR : "#2f5d8a";
  box.style.cssText = `position:fixed;box-sizing:border-box;left:${r.left}px;top:${r.top}px;` +
    `width:${r.width}px;height:${r.height}px;border:2px ${kind === "mark" ? "solid" : "dashed"} ${color};` +
    `background:${kind === "mark" ? "rgba(232,89,12,.08)" : "rgba(47,93,138,.08)"};border-radius:3px;`;
  if (label) {
    const badge = doc.createElement("div");
    badge.textContent = label;
    badge.style.cssText = `position:absolute;left:-2px;top:-2px;transform:translate(-40%,-40%);` +
      `min-width:20px;height:20px;padding:0 5px;box-sizing:border-box;border-radius:10px;background:${color};` +
      `color:#fff;font:600 12px/20px -apple-system,BlinkMacSystemFont,sans-serif;text-align:center;`;
    box.append(badge);
  }
  return box;
}

function drawOverlay() {
  const win = frameWindow();
  const site = currentSite();
  if (!win || !site || state.mode !== "site" || !win.location.pathname.startsWith(site.home)) return;
  const doc = win.document;
  if (!doc.documentElement) return;
  let root = doc.getElementById(OVERLAY_ID);
  if (!root) {
    root = doc.createElement("div");
    root.id = OVERLAY_ID;
    root.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:2147483647;";
    doc.documentElement.append(root);
  }
  let style = doc.getElementById(STYLE_ID);
  if (!style) {
    style = doc.createElement("style");
    style.id = STYLE_ID;
    doc.documentElement.append(style);
  }
  style.textContent = marker.active ? "*, *::before, *::after { cursor: crosshair !important; }" : "";

  const page = pageOf(win, site);
  const boxes = [];
  siteMarks().forEach((m, i) => {
    if (m.page !== page) return;
    const el = resolveMark(m, doc);
    if (el) boxes.push(outline(doc, el, String(i + 1), "mark"));
  });
  if (marker.active && marker.hover?.isConnected && marker.hover !== doc.documentElement) {
    boxes.push(outline(doc, marker.hover, "", "hover"));
  }
  root.replaceChildren(...boxes);
}

function installMarker(win, site) {
  marker.cache.clear();
  marker.hover = null;
  const swallow = (e) => {
    if (!marker.active) return;
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    if (e.type === "click") addMark(e, win, site);
  };
  for (const type of ["click", "dblclick", "auxclick", "contextmenu", "mousedown", "mouseup",
                      "pointerdown", "pointerup", "touchstart", "touchend", "submit"]) {
    win.addEventListener(type, swallow, { capture: true, passive: false });
  }
  win.addEventListener("mousemove", (e) => {
    if (!marker.active || e.target === marker.hover) return;
    marker.hover = e.target.nodeType === 1 ? e.target : e.target.parentElement;
    drawOverlay();
  }, true);
  win.addEventListener("keydown", (e) => e.key === "Escape" && setMarking(false), true);
  win.addEventListener("scroll", () => drawOverlay(), { capture: true, passive: true });
  win.addEventListener("resize", () => drawOverlay());
  drawOverlay();
}

function setMarking(on, { quiet = false } = {}) {
  if (marker.active === on) return;
  marker.active = on;
  marker.hover = null;
  els.markBanner.hidden = !on;
  els.frameWrap.classList.toggle("marking", on);
  if (quiet) return;
  const q = marksQuestion();
  if (q) rerenderQuestion(q);
  drawOverlay();
}

function addMark(event, win, site) {
  const q = marksQuestion();
  let el = event.target;
  if (el.nodeType !== 1) el = el.parentElement;
  if (!q || !el || el.id === OVERLAY_ID) return;
  const mark = {
    id: Math.random().toString(36).slice(2, 10),
    page: pageOf(win, site),
    ...describeElement(el, win),
    x: Math.round(event.pageX), y: Math.round(event.pageY),
    scroll_y: Math.round(win.scrollY), viewport_w: win.innerWidth, viewport_h: win.innerHeight,
    created_at: new Date().toISOString(),
  };
  marker.cache.set(mark.id, el);
  updateMarks(q, [...siteMarks(), mark]);
}

function updateMarks(q, marks) {
  setAnswer(q, marks.length ? marks : null);
  rerenderQuestion(q);
  drawOverlay();
}

function showMark(mark) {
  const win = frameWindow();
  const site = currentSite();
  if (!win) return;
  if (mark.page !== pageOf(win, site)) {
    win.location.href = site.home + mark.page;
    return;
  }
  resolveMark(mark, win.document)?.scrollIntoView({ behavior: "smooth", block: "center" });
}

function onMarksClick(e) {
  const btn = e.target.closest("button[data-action]");
  const q = marksQuestion();
  if (!btn || !q) return;
  if (btn.dataset.action === "toggle") return setMarking(!marker.active);
  const mark = siteMarks().find((m) => m.id === btn.closest("li")?.dataset.mark);
  if (!mark) return;
  if (btn.dataset.action === "remove") updateMarks(q, siteMarks().filter((m) => m !== mark));
  else if (btn.dataset.action === "show") showMark(mark);
}

function onNoneMarked(q, checkbox) {
  const marks = siteMarks();
  if (checkbox.checked && marks.length &&
      !confirm(`Remove your ${marks.length} mark${marks.length === 1 ? "" : "s"} on this website?`)) {
    checkbox.checked = false;
    return;
  }
  if (checkbox.checked) setMarking(false, { quiet: true });
  updateMarks(q, []);
  if (checkbox.checked) {
    setAnswer(q, "none");
    rerenderQuestion(q);
  }
}

function renderMarks(q, value) {
  const box = document.createElement("div");
  box.className = "marks";
  const marks = Array.isArray(value) ? value : [];
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.dataset.action = "toggle";
  toggle.className = "mark-toggle" + (marker.active ? " primary" : "");
  toggle.textContent = marker.active ? "Done marking" : marks.length ? "Mark more spots" : "Start marking";
  box.append(toggle);

  if (marks.length) {
    const list = document.createElement("ol");
    list.className = "mark-list";
    marks.forEach((m, i) => {
      const li = document.createElement("li");
      li.dataset.mark = m.id;
      const num = document.createElement("span");
      num.className = "mark-num";
      num.textContent = i + 1;
      const desc = document.createElement("button");
      Object.assign(desc, { type: "button", className: "mark-desc", title: "Show it on the website" });
      desc.dataset.action = "show";
      desc.textContent = m.kind + (m.text ? `: ${m.text}` : "");
      const remove = document.createElement("button");
      Object.assign(remove, { type: "button", className: "mark-small", textContent: "×",
                              title: "Remove this mark" });
      remove.setAttribute("aria-label", `Remove mark ${i + 1}`);
      remove.dataset.action = "remove";
      li.append(num, desc, remove);
      list.append(li);
    });
    box.append(list);
  }
  if (q.none_label) box.append(option("checkbox", `q-${q.id}-none`, "none", q.none_label, value === "none"));
  return box;
}

function rerenderQuestion(q) {
  const { key, questions, form } = ctx();
  const index = questions.indexOf(q);
  const old = form.querySelector(`fieldset[data-qid="${q.id}"]`);
  if (index === -1 || !old) return;
  old.replaceWith(renderQuestion(q, index + 1, answersFor(key), questions));
  updateProgress();
}

// ---------------------------------------------------------------- navigation

// Editing a finished website must not leave it half-answered.
function canLeaveSite() {
  if (annotationTool?.draft) {
    warn("Save or cancel your note before changing websites.");
    revealAnnotation();
    return false;
  }
  const site = state.mode === "site" ? currentSite() : null;
  if (site && site.completed && missingIds(answersFor(site.id), siteQuestions()).length) {
    state.showMissing = true;
    revealQuestion(updateProgress()[0]);
    warn("Please finish these answers before leaving this website.");
    return false;
  }
  return true;
}

async function goTo(index) {
  if (index !== state.index && !canLeaveSite()) return;
  const changedWebsite = state.index >= 0 && index !== state.index;
  els.next.disabled = true;
  try {
    await saver.flush();
  } catch (err) {
    warn(err.message);
    els.next.disabled = false;
    return;
  }
  timer.flush();
  annotationTool?.stopSelecting();
  setMarking(false, { quiet: true });
  state.mode = "site";
  state.index = index;
  if (els.websiteNavigation) els.websiteNavigation.open = false;
  state.showMissing = false;
  warn("");
  const site = currentSite();
  els.eyebrow.textContent = `${state.practice ? "Practice · " : ""}${state.phase === "followup" ? "Final questions" : "Review"} ${index + 1} of ${state.sites.length}`;
  els.toolbarLabel.textContent = site.label;
  renderDots();
  renderQuestions();
  updateProgress();
  setStatus(missingIds(answersFor(site.id), siteQuestions()).length ? "" : "All answers saved");
  loadFrame(site);
  if (changedWebsite) els.title.focus({preventScroll:true});
  api(`/api/sessions/${sessionId}/sites/${site.id}/open`, { method: "POST" }).catch(() => {});
  timer.start();
  els.next.disabled = false;
}

async function showSurvey(part) {
  if (!canLeaveSite()) return;
  await saver.flush();
  timer.flush();
  setMarking(false, { quiet: true });
  state.frame?.remove();
  state.frame = null;
  state.mode = part;
  state.showMissing = false;
  warn("");
  const info = SURVEY[part];
  els.surveyEyebrow.textContent = info.eyebrow;
  els.surveyTitle.textContent = info.title;
  els.surveyLede.textContent = info.lede;
  els.surveyBack.hidden = part !== "closing";
  els.layout.hidden = true;
  els.survey.hidden = false;
  renderQuestions();
  els.survey.scrollTop = 0;
  updateProgress();
  setStatus(missingIds(answersFor(info.key), state.sections[part]).length ? "" : "All answers saved");
}

async function backToSites(index) {
  await saver.flush();
  state.mode = "site";
  els.survey.hidden = true;
  els.layout.hidden = false;
  state.index = -1; // nothing to "leave": we're coming from the survey screen
  await goTo(index);
}

async function onNext() {
  if (els.next.disabled) return;
  if (annotationTool?.draft) {
    warn("");
    revealAnnotation();
    return;
  }
  const site = currentSite();
  const missing = missingIds(answersFor(site.id), siteQuestions());
  if (missing.length) return revealMissing(missing, els.questions);
  const last = state.index === state.sites.length - 1;
  const nextPhase = last && state.phase === "review" && state.followupSites.length > 0;
  const closing = state.sections.closing.length > 0;
  els.next.disabled = true;
  let restoreNextFocus = false;
  try {
    const finishing = last && !nextPhase && !closing;
    if (last && (nextPhase || finishing) && !await confirmAction(nextPhase ? {
      title: "Continue to final questions?",
      message: "Your webpage ratings will be saved and cannot be changed.",
      confirmLabel: "Continue to final questions",
    } : {
      title: "Finish the study?",
      message: "You won't be able to change your answers after this.",
      confirmLabel: "Finish study",
    })) {
      restoreNextFocus = true;
      return;
    }
    await saver.flush();
    const res = await api(`/api/sessions/${sessionId}/sites/${site.id}/complete`, { method: "POST" });
    state.sites = res.sites;
    if (last) {
      timer.flush();
      if (nextPhase) {
        await api(`/api/sessions/${sessionId}/followup`, { method: "POST" });
        try {
          applySession(await api(`/api/sessions/${sessionId}`));
        } catch (err) {
          showScreen("load-error", `Your webpage ratings are saved. Reload this session to continue to the final questions. ${err.message}`);
          return;
        }
        state.index = -1;
        await goTo(0);
        els.title.focus({preventScroll:true});
      } else if (closing) {
        await showSurvey("closing");
      } else {
        await finish();
      }
    } else {
      await goTo(state.index + 1);
    }
  } catch (err) {
    const missing = err.status === 422 ? updateProgress()[0] : null;
    if (missing) {
      state.showMissing = true;
      updateProgress();
      revealQuestion(missing);
    } else {
      restoreNextFocus = true;
    }
    warn(err.message);
  } finally {
    els.next.disabled = false;
    if (restoreNextFocus) els.next.focus({preventScroll:true});
  }
}

async function onSurveyNext() {
  const { questions, key } = ctx();
  const missing = missingIds(answersFor(key), questions);
  if (missing.length) return revealMissing(missing, els.surveyQuestions);
  if (state.mode === "closing" &&
      !confirm("Finish the study? You won't be able to change your answers after this.")) return;

  els.surveyNext.disabled = true;
  try {
    await saver.flush();
    if (state.mode === "closing") {
      await finish();
      return;
    }
    // Answering the background questions unlocks the first website.
    state.sites = (await api(`/api/sessions/${sessionId}`)).sites;
    const firstOpen = state.sites.findIndex((s) => !s.completed);
    await backToSites(firstOpen !== -1 ? firstOpen : state.sites.length - 1);
  } catch (err) {
    warn(err.message);
  } finally {
    els.surveyNext.disabled = false;
  }
}

async function finish() {
  timer.flush();
  await api(`/api/sessions/${sessionId}/finish`, { method: "POST" });
  showScreen("done");
}

function showScreen(id, message) {
  setMarking(false, { quiet: true });
  timer.flush();
  timer.stopped = true;
  state.frame?.remove();
  if (message) $("load-error-text").textContent = message;
  els.layout.hidden = true;
  els.survey.hidden = true;
  $(id).hidden = false;
}

function onChange(e) {
  const fieldset = e.target.closest("fieldset.q");
  if (!fieldset) return;
  const q = state.byId[fieldset.dataset.qid];
  if (q.type === "marks") return onNoneMarked(q, e.target);
  if (q.type === "multi" && e.target.checked) {
    // An exclusive option ("None") can't be combined with the others.
    const exclusive = e.target.dataset.exclusive === "true";
    for (const input of fieldset.querySelectorAll("input[type=checkbox]:checked")) {
      if (input !== e.target && (exclusive || input.dataset.exclusive === "true")) input.checked = false;
    }
  }
  applyMaxSelected(q, fieldset);
  setAnswer(q, readValue(q, fieldset));
}

function wireEvents() {
  const onAnswer = (e) => {
    const fieldset = e.target.closest("fieldset.q");
    if (!fieldset) return;
    const q = state.byId[fieldset.dataset.qid];
    if (q.type === "annotation") return;
    onChange(e);
  };
  els.questions.addEventListener("change", (e) => e.target.tagName !== "TEXTAREA" && onAnswer(e));
  els.questions.addEventListener("input", (e) => e.target.tagName === "TEXTAREA" && onAnswer(e));
  els.questions.addEventListener("click", onMarksClick);
  els.markDone.addEventListener("click", () => setMarking(false));
  document.addEventListener("keydown", (e) => e.key === "Escape" && setMarking(false));
  setInterval(() => drawOverlay(), 1000);
  els.surveyQuestions.addEventListener("change", onChange);
  els.next.addEventListener("click", onNext);
  els.reviewHelp?.addEventListener("click", () => revealQuestion("technical_issue"));
  els.notesLink.addEventListener("click", revealAnnotation);
  els.prev.addEventListener("click", () => {
    if (state.index > 0) goTo(state.index - 1);
    else if (state.phase === "review" && state.sections.background.length) showSurvey("background");
  });
  els.surveyNext.addEventListener("click", onSurveyNext);
  els.surveyBack.addEventListener("click", () => backToSites(state.sites.length - 1));

  els.back.addEventListener("click", () => frameNavigation()?.back());
  els.forward.addEventListener("click", () => frameNavigation()?.forward());
  els.reload.addEventListener("click", () => {
    try { state.frame.contentWindow.location.reload(); } catch { loadFrame(currentSite()); }
  });
  els.home.addEventListener("click", () => loadFrame(currentSite()));

  const setCollapsed = (collapsed) => {
    els.layout.classList.toggle("collapsed", collapsed);
    $(collapsed ? "expand" : "collapse").focus({preventScroll:true});
    if (!collapsed && (annotationTool?.draft || annotationTool?.armed)) revealAnnotation();
  };
  $("collapse").addEventListener("click", () => setCollapsed(true));
  $("expand").addEventListener("click", () => setCollapsed(false));
  $("expand-label").addEventListener("click", () => setCollapsed(false));

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") timer.flush(true);
    else timer.start();
  });
  window.addEventListener("pagehide", () => timer.flush(true));
  // Bank time periodically so a crash or closed lid loses at most a minute.
  setInterval(() => { timer.flush(); timer.start(); }, 60_000);
  window.addEventListener("beforeunload", (e) => {
    if (saver.busy || annotationTool?.draft) e.preventDefault();
  });
}

function applySession(data) {
  state.practice = Boolean(data.session?.practice);
  state.phase = data.phase || "review";
  state.followupSites = data.followup_sites || [];
  state.sites = state.phase === "followup" ? state.followupSites : data.sites;
  const activeQuestions = state.phase === "followup"
    ? data.followup_questions || data.questions : data.review_questions || data.questions;
  state.sections = {
    questions: activeQuestions,
    background: data.background || [],
    closing: data.closing || [],
  };
  state.questions = activeQuestions;
  state.byId = Object.fromEntries(
    [...state.sections.background, ...activeQuestions, ...state.sections.closing]
      .map((q) => [q.id, q]));
  state.answers = data.answers;
  els.title.textContent = state.phase === "followup" ? "Reflect on your ratings" : "Your impressions";
  if (els.reviewHelp) els.reviewHelp.hidden = state.phase === "followup";
  els.guidance.textContent = state.phase === "followup"
    ? "Revisit these webpages and tell us what influenced your ratings."
    : "Browse the webpage, then answer based on your overall impression.";
}

async function init() {
  annotationTool = new AnnotationTool({
    change: setAnswer,
    warn,
    refresh() {
      const questions = siteQuestions();
      const index = questions.findIndex(q => q.type === "annotation");
      if (index === -1 || !currentSite()) return;
      const q = questions[index];
      if (annotationTool.draft) els.layout.classList.toggle("collapsed", false);
      els.questions.querySelector(`fieldset[data-qid="${q.id}"]`)?.replaceWith(
        renderQuestion(q, index + 1, answersFor(currentSite().id), questions));
      updateProgress();
    },
  });
  $("reload-session").addEventListener("click", () => window.location.reload());
  let data;
  try {
    data = await api(`/api/sessions/${sessionId}`);
  } catch (err) {
    showScreen("load-error", err.message);
    return;
  }
  applySession(data);
  if (data.session.finished_at) {
    showScreen("done");
    return;
  }
  wireEvents();
  if (state.phase === "review" &&
      missingIds(answersFor(SURVEY.background.key), state.sections.background).length) {
    await showSurvey("background");
    return;
  }
  // Resume where they left off, but first on any finished site they left half-edited.
  const q = state.sections.questions;
  const halfEdited = state.sites.findIndex((s) => s.completed && missingIds(answersFor(s.id), q).length);
  const firstOpen = state.sites.findIndex((s) => !s.completed);
  if (state.phase === "followup" && halfEdited === -1 && firstOpen === -1 &&
      state.sections.closing.length) {
    state.index = state.sites.length - 1;
    await showSurvey("closing");
    return;
  }
  state.index = -1;
  await goTo(halfEdited !== -1 ? halfEdited : firstOpen !== -1 ? firstOpen : state.sites.length - 1);
  if (halfEdited !== -1) {
    state.showMissing = true;
    revealQuestion(updateProgress()[0]);
    warn("Some answers on this website were cleared. Please finish them.");
  }
}

init();
