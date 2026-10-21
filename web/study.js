import { api } from "./api.js";

const sessionId = location.pathname.split("/").filter(Boolean).pop();
const $ = (id) => document.getElementById(id);
const els = {
  layout: $("layout"), frameWrap: $("frame-wrap"), loading: $("frame-loading"),
  back: $("nav-back"), forward: $("nav-forward"), reload: $("nav-reload"), home: $("nav-home"),
  toolbarLabel: $("toolbar-label"), eyebrow: $("panel-eyebrow"), dots: $("dots"),
  questions: $("questions"), status: $("status"), prev: $("prev"), next: $("next"),
};

const state = {
  sites: [],        // [{id, position, label, src, home, completed, unlocked}]
  questions: [],
  byId: {},
  answers: {},      // {siteId: {questionId: value}}
  index: 0,
  frame: null,
  showMissing: false,
};

const blank = (v) => v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);
const currentSite = () => state.sites[state.index];
const answersFor = (siteId) => (state.answers[siteId] ??= {});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------------------------------------------------------------- answers

function missingIds(a) {
  // Mirrors missing_answers() on the server, so the Next button reacts instantly.
  return state.questions
    .filter((q) => {
      const v = a[q.id];
      if (blank(v)) return q.required !== false;
      if (q.type === "multi" && v.length < (q.min_selected ?? 1)) return true;
      if (q.options_from && !(a[q.options_from] || []).includes(v)) return true;
      return false;
    })
    .map((q) => q.id);
}

function readValue(q, fieldset) {
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
  a[q.id] = blank(value) ? null : value;
  warn("");
  // A question that offers "which of those mattered most" must track this one.
  state.questions.forEach((dep, i) => {
    if (dep.options_from !== q.id) return;
    if (a[dep.id] != null && !(a[q.id] || []).includes(a[dep.id])) a[dep.id] = null;
    const old = els.questions.querySelector(`fieldset[data-qid="${dep.id}"]`);
    old?.replaceWith(renderQuestion(dep, i + 1, a));
  });
  saver.mark(site.id);
  updateProgress();
}

// Autosave: every change is written to the server shortly after it happens, in order.
const saver = {
  dirty: new Set(),
  timer: null,
  chain: Promise.resolve(),
  failing: false,

  mark(siteId) {
    this.dirty.add(siteId);
    setStatus("Saving…");
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.flush(), 350);
  },

  flush() {
    clearTimeout(this.timer);
    for (const siteId of this.dirty) {
      const payload = {};
      for (const q of state.questions) payload[q.id] = answersFor(siteId)[q.id] ?? null;
      this.chain = this.chain.then(() => this.send(siteId, payload));
    }
    this.dirty.clear();
    return this.chain;
  },

  async send(siteId, answers) {
    for (let attempt = 0; ; attempt++) {
      try {
        await api(`/api/sessions/${sessionId}/sites/${siteId}/answers`, { method: "PUT", body: { answers } });
        this.failing = false;
        if (!this.dirty.size) setStatus("All answers saved");
        return;
      } catch (err) {
        if (err.status && err.status < 500) {
          setStatus(`Not saved: ${err.message}`, true);
          return;
        }
        this.failing = true;
        setStatus("Couldn't reach the study server. Retrying…", true);
        await sleep(Math.min(8000, 1000 * 2 ** attempt));
      }
    }
  },

  get busy() {
    return this.dirty.size > 0 || this.failing;
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

function renderInputs(q, a) {
  const value = a[q.id];
  const name = `q-${q.id}`;
  const box = document.createElement("div");

  if (q.type === "boolean") {
    box.className = "options pair";
    box.append(option("radio", name, true, q.true_label, value === true),
               option("radio", name, false, q.false_label, value === false));
  } else if (q.type === "scale") {
    box.className = "scale";
    const row = document.createElement("div");
    row.className = "scale-row";
    row.style.setProperty("--steps", q.max - q.min + 1);
    for (let n = q.min; n <= q.max; n++) row.append(option("radio", name, n, String(n), value === n));
    const ends = document.createElement("div");
    ends.className = "scale-ends";
    ends.innerHTML = "<span></span><span></span>";
    ends.children[0].textContent = q.min_label ?? "";
    ends.children[1].textContent = q.max_label ?? "";
    box.append(row, ends);
  } else if (q.type === "multi") {
    box.className = "options";
    for (const o of q.options) box.append(option("checkbox", name, o.value, o.label, (value || []).includes(o.value)));
  } else {
    let opts = q.options;
    if (q.options_from) {
      const picked = a[q.options_from] || [];
      opts = opts.filter((o) => picked.includes(o.value));
      if (!opts.length) {
        const source = state.questions.findIndex((x) => x.id === q.options_from) + 1;
        box.className = "empty-hint";
        box.textContent = `Choose at least one option in question ${source} first.`;
        return box;
      }
    }
    box.className = "options";
    for (const o of opts) box.append(option("radio", name, o.value, o.label, value === o.value));
  }
  return box;
}

function renderQuestion(q, number, a) {
  const fieldset = document.createElement("fieldset");
  fieldset.className = "q";
  fieldset.dataset.qid = q.id;
  const legend = document.createElement("legend");
  legend.innerHTML = `<span class="qnum">${number}</span><span></span>`;
  legend.lastChild.textContent = q.prompt;
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
  els.questions.replaceChildren(...state.questions.map((q, i) => renderQuestion(q, i + 1, a)));
  els.questions.scrollTop = 0;
}

function renderDots() {
  els.dots.replaceChildren(...state.sites.map((site, i) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.className = "dot" + (site.completed ? " done" : "") + (i === state.index ? " current" : "");
    dot.textContent = site.position;
    dot.disabled = !site.unlocked;
    dot.setAttribute("aria-label", `${site.label}${site.completed ? " (done)" : ""}`);
    if (i === state.index) dot.setAttribute("aria-current", "step");
    dot.addEventListener("click", () => i !== state.index && goTo(i));
    return dot;
  }));
}

function updateProgress() {
  const site = currentSite();
  const missing = missingIds(answersFor(site.id));
  const last = state.index === state.sites.length - 1;
  els.prev.disabled = state.index === 0;
  els.next.setAttribute("aria-disabled", String(missing.length > 0));
  els.next.textContent = missing.length
    ? `Answer ${missing.length} more question${missing.length === 1 ? "" : "s"}`
    : last ? "Finish" : "Next website";
  for (const fieldset of els.questions.querySelectorAll("fieldset.q")) {
    fieldset.classList.toggle("missing", state.showMissing && missing.includes(fieldset.dataset.qid));
  }
  return missing;
}

// The status line shows a warning if there is one, otherwise the autosave state,
// so a background save finishing can't hide a warning the participant needs to see.
const status = { save: "", saveBad: false, warning: "" };

function renderStatus() {
  els.status.textContent = status.warning || status.save;
  els.status.classList.toggle("bad", Boolean(status.warning) || status.saveBad);
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
  start() {
    if (document.visibilityState === "visible" && this.since === null) this.since = performance.now();
  },
  flush(beacon = false) {
    if (this.since === null) return;
    const seconds = (performance.now() - this.since) / 1000;
    this.since = null;
    const site = currentSite();
    if (!site || seconds < 0.5) return;
    const url = `/api/sessions/${sessionId}/sites/${site.id}/time`;
    const body = JSON.stringify({ seconds });
    if (beacon) navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
    else fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body }).catch(() => {});
  },
};

// ---------------------------------------------------------------- navigation

async function goTo(index) {
  const leaving = currentSite();
  if (leaving && index !== state.index && leaving.completed && missingIds(answersFor(leaving.id)).length) {
    // Editing a finished website must not leave it half-answered.
    state.showMissing = true;
    updateProgress();
    warn("Please finish these answers before leaving this website.");
    return;
  }
  await saver.flush();
  timer.flush();
  state.index = index;
  state.showMissing = false;
  warn("");
  const site = currentSite();
  els.eyebrow.textContent = site.label;
  els.toolbarLabel.textContent = site.label;
  renderDots();
  renderQuestions();
  updateProgress();
  setStatus(missingIds(answersFor(site.id)).length ? "" : "All answers saved");
  loadFrame(site);
  api(`/api/sessions/${sessionId}/sites/${site.id}/open`, { method: "POST" }).catch(() => {});
  timer.start();
}

async function onNext() {
  const site = currentSite();
  const missing = missingIds(answersFor(site.id));
  if (missing.length) {
    state.showMissing = true;
    updateProgress();
    els.questions.querySelector(`fieldset[data-qid="${missing[0]}"]`)?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  const last = state.index === state.sites.length - 1;
  if (last && !confirm("Finish the study? You won't be able to change your answers after this.")) return;

  els.next.disabled = true;
  try {
    await saver.flush();
    const res = await api(`/api/sessions/${sessionId}/sites/${site.id}/complete`, { method: "POST" });
    state.sites = res.sites;
    if (last) {
      timer.flush();
      await api(`/api/sessions/${sessionId}/finish`, { method: "POST" });
      showScreen("done");
    } else {
      await goTo(state.index + 1);
    }
  } catch (err) {
    if (err.status === 422) {
      state.showMissing = true;
      updateProgress();
    }
    warn(err.message);
  } finally {
    els.next.disabled = false;
  }
}

function showScreen(id, message) {
  timer.flush();
  state.frame?.remove();
  if (message) $("load-error-text").textContent = message;
  els.layout.hidden = true;
  $(id).hidden = false;
}

function wireEvents() {
  els.questions.addEventListener("change", (e) => {
    const fieldset = e.target.closest("fieldset.q");
    if (!fieldset) return;
    const q = state.byId[fieldset.dataset.qid];
    setAnswer(q, readValue(q, fieldset));
  });
  els.next.addEventListener("click", onNext);
  els.prev.addEventListener("click", () => state.index > 0 && goTo(state.index - 1));

  els.back.addEventListener("click", () => frameNavigation()?.back());
  els.forward.addEventListener("click", () => frameNavigation()?.forward());
  els.reload.addEventListener("click", () => {
    try { state.frame.contentWindow.location.reload(); } catch { loadFrame(currentSite()); }
  });
  els.home.addEventListener("click", () => loadFrame(currentSite()));

  const setCollapsed = (collapsed) => els.layout.classList.toggle("collapsed", collapsed);
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
    if (saver.busy) e.preventDefault();
  });
}

async function init() {
  let data;
  try {
    data = await api(`/api/sessions/${sessionId}`);
  } catch (err) {
    showScreen("load-error", err.message);
    return;
  }
  state.sites = data.sites;
  state.questions = data.questions;
  state.byId = Object.fromEntries(data.questions.map((q) => [q.id, q]));
  state.answers = data.answers;
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
    updateProgress();
    warn("Some answers on this website were cleared. Please finish them.");
  }
}

init();
