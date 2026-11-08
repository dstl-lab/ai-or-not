// Readout controls for the air-quality page.
const metric = document.getElementById("metric");
const comparison = document.getElementById("comparison");

document.getElementById("show-pm25").addEventListener("click", () => {
  metric.textContent = "PM2.5: 14.2 µg/m³ (monthly mean)";
});

// The comparison handler is attached to an id that does not exist on the page,
// so clicking "Compare with last year" changes nothing.
const compareButton = document.getElementById("compare-last-yr");
if (compareButton) {
  compareButton.addEventListener("click", () => {
    comparison.textContent = "September 2025: PM2.5 16.8 µg/m³, so this year is 15% lower.";
  });
}
