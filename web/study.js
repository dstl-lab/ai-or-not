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
};

const state = {
  sites: [],        // [{id, position, label, src, home, completed, unlocked}]
  questions: [],
  byId: {},
  answers: {},      // {siteId: {questionId: value}}
  index: 0,
  frame: null,
  showMissing: false,
  phase: "review",
  practice: false,
  followupSites: [],
};

const blank = (v) => v === null || v === undefined || (typeof v === "string" && !v.trim()) || (Array.isArray(v) && v.length === 0);
const currentSite = () => state.sites[state.index];
const answersFor = (siteId) => (state.answers[siteId] ??= {});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------------------------------------------------------------- answers

function missingIds(a) {
  // Mirrors missing_answers() on the server, so the Next button reacts instantly.
  return state.questions
    .filter((q) => {
      const v = a[q.id];
      if (blank(v)) return q.required !== false &&
        !(q.required_unless && a[q.required_unless.question_id] === q.required_unless.value);
      if (q.type === "multi" && v.length < (q.min_selected ?? 1)) return true;
      if (q.type === "multi" && q.max_selected && v.length > q.max_selected) return true;
      if (q.options_from && !(a[q.options_from] || []).includes(v)) return true;
      return false;
    })
    .map((q) => q.id);
}

function readValue(q, fieldset) {
  if (q.type === "text") return fieldset.querySelector("textarea").value;
  if (q.type === "multi") return [...fieldset.querySelectorAll("input:checked")].map((i) => i.value);
  const checked = fieldset.querySelector("input:checked");
  if (!checked) return null;
  if (q.type === "boolean") return checked.value === "true";
  if (q.type === "scale") return Number(checked.value);
  return checked.value;
}

function setAnswer(q, value) {
  const site = currentSite();
  const a = answersFor(site.id);
  const firstRating = q.id === "ai_appearance" && blank(a[q.id]) && !blank(value);
  a[q.id] = blank(value) ? null : value;
  warn("");
  // A question that offers "which of those mattered most" must track this one.
  state.questions.forEach((dep) => {
    if (dep.options_from !== q.id) return;
    if (a[dep.id] != null && !(a[q.id] || []).includes(a[dep.id])) a[dep.id] = null;
    const old = els.questions.querySelector(`fieldset[data-qid="${dep.id}"]`);
    old?.replaceWith(renderQuestion(dep, a));
  });
  const checks = els.questions.querySelector(".review-checks");
  if (firstRating && checks) checks.open = true;
  updateSelectionLimit(q, els.questions.querySelector(`fieldset[data-qid="${q.id}"]`), a[q.id]);
  saver.mark(site.id);
  updateProgress();
}

// Autosave: every change is written to the server shortly after it happens, in order.
const saver = {
  dirty: new Set(),
  timer: null,
  chain: Promise.resolve(),
  pending: 0,
  failing: false,

  mark(siteId) {
    this.dirty.add(siteId);
    setStatus("Saving…");
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.flush().catch(() => {}), 350);
  },

  flush() {
    clearTimeout(this.timer);
    for (const siteId of this.dirty) {
      const payload = {};
      for (const q of state.questions) payload[q.id] = answersFor(siteId)[q.id] ?? null;
      this.pending++;
      this.chain = this.chain.then(() => this.send(siteId, payload), () => this.send(siteId, payload))
        .finally(() => { this.pending--; });
    }
    this.dirty.clear();
    return this.chain;
  },

  async send(siteId, answers) {
    for (let attempt = 0; ; attempt++) {
      try {
        await api(`/api/sessions/${sessionId}/sites/${siteId}/answers`, { method: "PUT", body: { answers } });
        this.failing = false;
        if (!this.dirty.size && this.pending === 1) setStatus("All answers saved");
        return;
      } catch (err) {
        if (err.status && err.status < 500) {
          this.dirty.add(siteId);
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

function updateSelectionLimit(q, container, value) {
  if (q.type !== "multi" || !q.max_selected || !container) return;
  const count = (value || []).length;
  for (const input of container.querySelectorAll('input[type="checkbox"]')) {
    input.disabled = !input.checked && count >= q.max_selected;
  }
  container.querySelector(".selection-limit").textContent = `${count} of ${q.max_selected} selected.`;
}

function renderInputs(q, a) {
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
      const ends = document.createElement("div");
      ends.className = "scale-ends";
      ends.innerHTML = "<span></span><span></span>";
      ends.children[0].textContent = q.min_label ?? "";
      ends.children[1].textContent = q.max_label ?? "";
      box.append(ends);
    }
  } else if (q.type === "multi") {
    box.className = "options";
    for (const o of q.options) box.append(option("checkbox", name, o.value, o.label, (value || []).includes(o.value)));
    if (q.max_selected) {
      const hint = document.createElement("p");
      hint.className = "help selection-limit";
      hint.setAttribute("aria-live", "polite");
      box.append(hint);
      updateSelectionLimit(q, box, value);
    }
  } else {
    let opts = q.options;
    if (q.options_from) {
      const picked = a[q.options_from] || [];
      opts = opts.filter((o) => picked.includes(o.value));
      if (!opts.length) {
        const source = state.questions.find((x) => x.id === q.options_from);
        box.className = "empty-hint";
        box.textContent = `Choose at least one option in “${source.prompt}” first.`;
        return box;
      }
    }
    box.className = "options";
    for (const o of opts) box.append(option("radio", name, o.value, o.label, value === o.value));
  }
  return box;
}

function renderQuestion(q, a) {
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
  fieldset.append(renderInputs(q, a));
  const note = document.createElement("p");
  note.className = "missing-note";
  note.textContent = q.type === "multi" && (q.min_selected ?? 1) > 1
    ? `Select at least ${q.min_selected}.` : "Please answer this question.";
  fieldset.append(note);
  return fieldset;
}

function renderQuestions() {
  const a = answersFor(currentSite().id);
  const grouped = state.questions.filter(q => state.phase === "followup"
    ? q.type === "annotation" : ["seen_before", "technical_issue"].includes(q.id));
  els.questions.replaceChildren(...state.questions.filter(q => !grouped.includes(q)).map(q => renderQuestion(q, a)));
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
    details.append(summary, ...grouped.map(q => renderQuestion(q, a)));
    els.questions.append(details);
  }
  els.questions.scrollTop = 0;
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

function updateProgress() {
  const site = currentSite();
  const a = answersFor(site.id);
  const missing = missingIds(a);
  const last = state.index === state.sites.length - 1;
  els.prev.disabled = state.index === 0;
  let nextAction = "Complete required questions";
  if (state.phase === "review") {
    if (missing.includes("ai_appearance")) nextAction = "Choose a rating";
    else if (missing.every(id => ["seen_before", "technical_issue"].includes(id))) nextAction = "Complete review checks";
  } else if (missing[0] === "cues" && state.byId.cues?.max_selected) {
    nextAction = `Select ${state.byId.cues.min_selected ?? 1}–${state.byId.cues.max_selected} cues`;
  }
  els.next.textContent = annotationTool?.draft ? "Return to note" : missing.length ? nextAction
    : last ? (state.phase === "review" && state.followupSites.length ? "Continue to final questions" : "Finish") : "Next website";
  const checks = els.questions.querySelector?.(".review-checks");
  if (checks) {
    const remaining = [...checks.querySelectorAll("fieldset.q")].filter(fieldset => missing.includes(fieldset.dataset.qid)).length;
    checks.querySelector(".section-meta").textContent = remaining ? `${remaining} remaining` : "Complete";
  }
  const annotationQuestions = state.questions.filter(q => q.type === "annotation");
  const count = annotationQuestions.reduce((total, q) => total + (a[q.id] || []).length, 0);
  els.notesLink.hidden = !annotationQuestions.length;
  els.notesCount.textContent = count;
  els.notesLink.setAttribute("aria-label", `Page notes, ${count} saved note${count === 1 ? "" : "s"}, optional`);
  const notes = els.questions.querySelector?.(".review-notes");
  if (notes) {
    notes.querySelector(".section-meta").textContent = `${count} note${count === 1 ? "" : "s"} · Optional`;
    if (annotationTool?.draft || annotationTool?.armed) notes.open = true;
  }
  for (const fieldset of els.questions.querySelectorAll("fieldset.q")) {
    fieldset.classList.toggle("missing", state.showMissing && missing.includes(fieldset.dataset.qid));
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
  const question = state.questions.find(q => q.type === "annotation");
  if (question) revealQuestion(question.id);
}

// Warnings and save failures stay visible above note guidance and save confirmations.
const status = { save: "", saveBad: false, warning: "" };

function renderStatus() {
  const noteStatus = annotationTool?.draft ? "Note not saved. Save note or Cancel to continue."
    : annotationTool?.armed ? "Select a detail on the webpage. Esc cancels." : "";
  els.status.textContent = status.warning || (status.saveBad ? status.save : noteStatus || status.save);
  els.status.classList.toggle("bad", Boolean(status.warning) || status.saveBad);
  els.status.classList.toggle("pending", Boolean(noteStatus) && !status.warning && !status.saveBad);
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
    if (!this.stopped && document.visibilityState === "visible" && this.since === null) this.since = performance.now();
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

// ---------------------------------------------------------------- navigation

async function goTo(index) {
  if (annotationTool?.draft) {
    warn("Save or cancel your note before changing websites.");
    revealAnnotation();
    return;
  }
  const changedWebsite = state.index >= 0 && index !== state.index;
  const leaving = currentSite();
  if (leaving && index !== state.index && leaving.completed && missingIds(answersFor(leaving.id)).length) {
    // Editing a finished website must not leave it half-answered.
    state.showMissing = true;
    revealQuestion(updateProgress()[0]);
    warn("Please finish these answers before leaving this website.");
    return;
  }
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
  setStatus(missingIds(answersFor(site.id)).length ? "" : "All answers saved");
  loadFrame(site);
  if (changedWebsite) els.title.focus({preventScroll:true});
  api(`/api/sessions/${sessionId}/sites/${site.id}/open`, { method: "POST" }).catch(() => {});
  timer.start();
  els.next.disabled = false;
}

async function onNext() {
  if (els.next.disabled) return;
  if (annotationTool?.draft) {
    warn("");
    revealAnnotation();
    return;
  }
  const site = currentSite();
  const missing = missingIds(answersFor(site.id));
  if (missing.length) {
    state.showMissing = true;
    updateProgress();
    revealQuestion(missing[0]);
    return;
  }
  const last = state.index === state.sites.length - 1;
  const nextPhase = last && state.phase === "review" && state.followupSites.length > 0;
  els.next.disabled = true;
  let restoreNextFocus = false;
  try {
    if (last && !await confirmAction(nextPhase ? {
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
      } else {
        await api(`/api/sessions/${sessionId}/finish`, { method: "POST" });
        showScreen("done");
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

function showScreen(id, message) {
  timer.flush();
  timer.stopped = true;
  state.frame?.remove();
  if (message) $("load-error-text").textContent = message;
  els.layout.hidden = true;
  $(id).hidden = false;
}

function wireEvents() {
  const onAnswer = (e) => {
    const fieldset = e.target.closest("fieldset.q");
    if (!fieldset) return;
    const q = state.byId[fieldset.dataset.qid];
    if (q.type === "annotation") return;
    setAnswer(q, readValue(q, fieldset));
  };
  els.questions.addEventListener("change", (e) => e.target.tagName !== "TEXTAREA" && onAnswer(e));
  els.questions.addEventListener("input", (e) => e.target.tagName === "TEXTAREA" && onAnswer(e));
  els.next.addEventListener("click", onNext);
  els.reviewHelp?.addEventListener("click", () => revealQuestion("technical_issue"));
  els.notesLink.addEventListener("click", revealAnnotation);
  els.prev.addEventListener("click", () => !els.next.disabled && state.index > 0 && goTo(state.index - 1));

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
  state.questions = state.phase === "followup"
    ? data.followup_questions || data.questions : data.review_questions || data.questions;
  state.byId = Object.fromEntries(state.questions.map((q) => [q.id, q]));
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
      const index = state.questions.findIndex(q => q.type === "annotation");
      if (index === -1 || !currentSite()) return;
      const q = state.questions[index];
      if (annotationTool.draft) els.layout.classList.toggle("collapsed", false);
      els.questions.querySelector(`fieldset[data-qid="${q.id}"]`)?.replaceWith(renderQuestion(q, answersFor(currentSite().id)));
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
  // Resume where they left off, but first on any finished site they left half-edited.
  const halfEdited = state.sites.findIndex((s) => s.completed && missingIds(answersFor(s.id)).length);
  const firstOpen = state.sites.findIndex((s) => !s.completed);
  state.index = -1;
  await goTo(halfEdited !== -1 ? halfEdited : firstOpen !== -1 ? firstOpen : state.sites.length - 1);
  if (halfEdited !== -1) {
    state.showMissing = true;
    revealQuestion(updateProgress()[0]);
    warn("Some answers on this website were cleared. Please finish them.");
  }
}

init();
