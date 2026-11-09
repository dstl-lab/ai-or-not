// Page-side discovery for site_capture.py. The adapter prepends one line,
//   const CONFIG = {...};
// and runs the file with `$B eval`. Read-only: it never clicks, types, or
// navigates. It lists the page's links, its top-level sections (which become
// regions), and the controls a capture could exercise, and returns JSON text.
// Page content is returned as data.
(() => {
  const cfg = CONFIG;
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "LINK", "META"]);
  const collapse = (s) => (s || "").replace(/\s+/g, " ").trim();
  const sx = window.scrollX, sy = window.scrollY;

  function visible(el) {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const cs = getComputedStyle(el);
    return cs.display !== "none" && cs.visibility !== "hidden" && Number(cs.opacity) > 0;
  }

  // Same selector format as extract.js, so regions and elements line up.
  function cssPath(el) {
    if (el.id && document.querySelectorAll("#" + CSS.escape(el.id)).length === 1) return "#" + CSS.escape(el.id);
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && node !== document.body && node !== document.documentElement) {
      if (node.id && document.querySelectorAll("#" + CSS.escape(node.id)).length === 1) {
        parts.unshift("#" + CSS.escape(node.id));
        break;
      }
      const tag = node.tagName.toLowerCase();
      const sibs = node.parentNode ? [...node.parentNode.children].filter((c) => c.tagName === node.tagName) : [];
      parts.unshift(sibs.length > 1 ? `${tag}:nth-of-type(${sibs.indexOf(node) + 1})` : tag);
      node = node.parentElement;
    }
    if (!parts.length || !parts[0].startsWith("#")) parts.unshift("body");
    return parts.join(" > ");
  }

  function rect(el) {
    const r = el.getBoundingClientRect();
    return { x: r.left + sx, y: r.top + sy, w: r.width, h: r.height };
  }

  // --- links -------------------------------------------------------------
  const links = [...document.querySelectorAll("a[href]")].map((a) => ({
    href: a.href, text: collapse(a.innerText).slice(0, 80), target: a.getAttribute("target") || "",
    download: a.hasAttribute("download"),
  }));

  // --- sections (become regions) -----------------------------------------
  const minH = cfg.min_region_h || 80;
  const blockKids = (node) => [...node.children].filter((c) => !SKIP.has(c.tagName) && visible(c) && c.getBoundingClientRect().height >= minH);
  let root = document.body;
  for (let i = 0; i < 8; i++) {           // unwrap single full-page wrappers (div#app > div.container > ...)
    const kids = blockKids(root);
    if (kids.length === 1) root = kids[0]; else break;
  }
  let candidates = [];
  for (const c of blockKids(root)) {
    const isMain = c.tagName === "MAIN" || c.getAttribute("role") === "main";
    const kids = isMain ? blockKids(c) : [];
    if (isMain && kids.length >= 2) candidates.push(...kids); else candidates.push(c);
  }
  if (!candidates.length && root !== document.body) candidates = [root];
  const nameOf = (el, i) => {
    const h = el.querySelector("h1, h2, h3");
    const label = (h && collapse(h.innerText)) || el.getAttribute("aria-label") || el.id || "";
    const tag = el.tagName.toLowerCase();
    const landmark = ["header", "footer", "nav", "main", "aside"].includes(tag);
    return (label ? `${tag}: ${label}` : landmark ? tag : `${tag} ${i + 1}`).slice(0, 80);
  };
  const sections = candidates.slice(0, cfg.max_regions || 14).map((el, i) => ({
    selector: cssPath(el), name: nameOf(el, i), tag: el.tagName.toLowerCase(), rect: rect(el),
  }));
  const sectionNodes = sections.map((s) => document.querySelector(s.selector));
  const sectionOf = (el) => {
    let best = -1;
    sectionNodes.forEach((n, i) => { if (n && n.contains(el) && (best < 0 || sectionNodes[best].contains(n))) best = i; });
    return best;
  };

  // --- controls ----------------------------------------------------------
  const CONTROL = "button, [role=button], [role=tab], [role=switch], [role=checkbox], [role=radio], [role=menuitem], " +
    "select, summary, input[type=checkbox], input[type=radio], input[type=button], [aria-expanded]";
  const UNTESTABLE = "input[type=range], input[type=text], input[type=number], input[type=search], input[type=email], " +
    "input[type=date], input[type=color], input:not([type]), textarea, [contenteditable=true]";
  const textOf = (el) => collapse(el.innerText || el.getAttribute("aria-label") || el.getAttribute("title") || el.value || "").slice(0, 100);
  const seen = new Set();
  const controls = [];
  for (const el of document.querySelectorAll(CONTROL)) {
    if (!visible(el)) continue;
    if (el.tagName === "A" && !(el.getAttribute("href") || "").startsWith("#")) continue;  // real links are pages, not controls
    const key = cssPath(el);
    if (seen.has(key)) continue;
    seen.add(key);
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();
    const form = el.closest("form");
    const submits = (tag === "button" && !!form && (type === "" || type === "submit")) ||
      (tag === "input" && ["submit", "reset", "image", "file"].includes(type));
    const kind = tag === "select" ? "select" : el.getAttribute("role") || (tag === "input" ? type : tag);
    const c = { selector: key, tag, type, kind, text: textOf(el), section: sectionOf(el), rect: rect(el),
      in_form: !!form, submits, disabled: !!el.disabled || el.getAttribute("aria-disabled") === "true",
      download: el.hasAttribute("download") };
    if (tag === "select") c.options = [...el.options].slice(0, 40).map((o) => ({ value: o.value, text: collapse(o.text).slice(0, 60), selected: o.selected }));
    controls.push(c);
  }
  const untestable = [...document.querySelectorAll(UNTESTABLE)].filter(visible).slice(0, 40).map((el) => ({
    selector: cssPath(el), kind: el.tagName === "TEXTAREA" ? "textarea" : (el.getAttribute("type") || "text"),
    text: textOf(el) || collapse(el.getAttribute("placeholder") || ""), section: sectionOf(el),
  }));

  const big = (el) => { const r = el.getBoundingClientRect(); return visible(el) && r.width * r.height >= 20000; };
  return JSON.stringify({
    href: location.href, title: collapse(document.title).slice(0, 200),
    metrics: { vw: window.innerWidth, vh: window.innerHeight, page_h: document.documentElement.scrollHeight },
    links, sections, controls, untestable,
    signals: { charts: [...document.querySelectorAll("svg, canvas")].filter(big).length,
      forms: document.querySelectorAll("form").length },
  });
})()
