import { api, escapeHtml as h, formatDuration, formatTime } from "./api.js";

const $ = (id) => document.getElementById(id);
const TABLES = [
  ["responses_wide", "Answers (one row per site)"],
  ["responses_long", "Answers (one row per question)"],
  ["sessions", "Sessions"],
  ["site_visits", "Time per site"],
];

function renderExports() {
  const practice = $("include-practice").checked;
  $("exports").innerHTML = TABLES.map(([name, label]) =>
    `<a class="button" href="/api/export/${name}.csv?practice=${practice}" download>${h(label)}</a>`
  ).join("");
}

function renderSheet(sheet) {
  if (!sheet.configured) {
    $("sheet").innerHTML = `
      <p><span class="pill">Not linked</span></p>
      <p class="muted">Answers are safe in the local database. To mirror them to a Google Sheet, run
      <code>uv run aiornot sheet create</code> and restart the server.</p>`;
    return;
  }
  const status = sheet.last_error && sheet.pending
    ? `<span class="pill warn">Sync problem</span>`
    : sheet.pending ? `<span class="pill">Syncing ${sheet.pending}…</span>` : `<span class="pill ok">Up to date</span>`;
  $("sheet").innerHTML = `
    <p>${status} <a href="${h(sheet.link.url)}" target="_blank" rel="noopener">Open sheet</a></p>
    <p class="muted">${sheet.rows_synced} row${sheet.rows_synced === 1 ? "" : "s"} synced${
      sheet.last_synced_at ? `, last ${h(formatTime(sheet.last_synced_at))}` : ""}</p>
    ${sheet.last_error && sheet.pending ? `<p class="error-text">${h(sheet.last_error)}</p>` : ""}
    <div class="row"><button type="button" id="sync-now">Sync now</button></div>`;
  $("sync-now").addEventListener("click", async () => {
    await api("/api/admin/sheet/sync", { method: "POST" });
    setTimeout(refresh, 1500);
  });
}

function renderSessions(sessions, siteCount) {
  if (!sessions.length) {
    $("sessions").innerHTML = `<tr><td colspan="7" class="muted">No sessions yet. Start one from the <a href="/">start page</a>.</td></tr>`;
    return;
  }
  $("sessions").innerHTML = sessions.map((s) => {
    const pct = Math.round((100 * s.sites_completed) / siteCount);
    const status = s.finished_at
      ? `<span class="pill ok">Finished ${h(formatTime(s.finished_at))}</span>`
      : `<span class="pill">In progress</span>`;
    return `<tr>
      <td><strong>${h(s.participant_id)}</strong></td>
      <td>${h(formatTime(s.started_at))}</td>
      <td class="num"><span class="bar"><span style="width:${pct}%"></span></span>${s.sites_completed}/${siteCount}</td>
      <td class="num">${formatDuration(s.total_seconds)}</td>
      <td>${status}</td>
      <td><input type="checkbox" data-practice="${h(s.id)}" ${s.practice ? "checked" : ""} aria-label="Practice session"></td>
      <td>${s.finished_at ? "" : `<a href="/study/${h(s.id)}">Resume</a>`}</td>
    </tr>`;
  }).join("");
}

function renderSites(sites) {
  $("sites").innerHTML = sites.map((s) => `<tr>
    <td class="num">${s.position}</td>
    <td><a href="${h(s.url)}" target="_blank" rel="noopener" title="Live site on GitHub Pages">${h(s.title)}</a></td>
    <td>${s.award ? h(s.award) : ""}</td>
    <td><code>${h((s.commit || "not pinned").slice(0, 7))}</code></td>
    <td>${s.mirrored ? `<span class="pill ok">Yes</span>` : `<span class="pill warn">Missing</span>`}</td>
    <td><a href="${h(s.preview)}" target="_blank" rel="noopener">Preview</a></td>
  </tr>`).join("");
}

async function refresh() {
  try {
    const data = await api("/api/admin/overview");
    const real = data.sessions.filter((s) => !s.practice);
    const participants = new Set(real.map((s) => s.participant_id));
    $("stat-participants").textContent = participants.size;
    $("stat-participants-note").textContent =
      `${real.filter((s) => s.finished_at).length} finished · ${data.sessions.length - real.length} practice session(s)`;
    renderSheet(data.sheet);
    renderSessions(data.sessions, data.site_count);
    renderSites(data.sites);
    $("versions").textContent = `· questions ${data.questions_version}`;
    $("updated").textContent = `Updated ${new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" })}`;
  } catch (err) {
    $("updated").textContent = `Couldn't refresh: ${err.message}`;
  }
}

$("sessions").addEventListener("change", async (e) => {
  const id = e.target.dataset.practice;
  if (!id) return;
  await api(`/api/sessions/${id}`, { method: "PATCH", body: { practice: e.target.checked } });
  refresh();
});
$("include-practice").addEventListener("change", renderExports);

renderExports();
refresh();
setInterval(refresh, 5000);
