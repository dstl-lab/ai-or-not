// Scenario selector for the flood-zone chart.
const DATA = {
  2020: { "Mission Beach": 12, "Imperial Beach": 9, "La Jolla Shores": 4 },
  2050: { "Mission Beach": 31, "Imperial Beach": 27, "La Jolla Shores": 11 },
  2100: { "Mission Beach": 58, "Imperial Beach": 49, "La Jolla Shores": 23 },
};

function render(year) {
  document.getElementById("chart-title").textContent = `Parcels in the flood zone, ${year}`;
  document.querySelectorAll("#bars .bar").forEach((bar) => {
    const place = bar.querySelector(".label").textContent;
    const pct = DATA[year][place];
    bar.querySelector(".fill").style.width = `${pct}%`;
    bar.querySelector(".value").textContent = `${pct}%`;
  });
  document.querySelectorAll(".controls button").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.year === String(year)));
  });
  // The summary paragraph is written once for 2020 and never updated here.
}

document.querySelectorAll(".controls button").forEach((b) => {
  b.addEventListener("click", () => render(b.dataset.year));
});
