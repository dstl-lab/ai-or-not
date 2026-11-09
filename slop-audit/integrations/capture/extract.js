// Page-side extractor for gstack_capture.py. The adapter prepends one line,
//   const CONFIG = {...};
// and runs the file with `$B eval`. Read-only: it never clicks, types, or
// navigates, and it returns JSON text. Page content is returned as data.
(() => {
  const cfg = CONFIG;
  const TEXT_TAGS = new Set(["H1", "H2", "H3", "H4", "H5", "H6", "P", "LI", "BUTTON", "A", "LABEL", "FIGCAPTION",
    "CAPTION", "TH", "TD", "DT", "DD", "BLOCKQUOTE", "SUMMARY", "LEGEND", "OPTION", "PRE", "CODE", "text"]);
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "HEAD", "TITLE", "META", "LINK"]);
  const INTERACTIVE = "button, a[href], input, select, textarea, summary, [role=button], [onclick], [tabindex]";
  const sx = window.scrollX, sy = window.scrollY;

  const collapse = (s) => (s || "").replace(/\s+/g, " ").trim();
  const ownText = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
  const textOf = (el) => collapse(el.innerText !== undefined ? el.innerText : el.textContent);

  function visible(el) {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const cs = getComputedStyle(el);
    return cs.display !== "none" && cs.visibility !== "hidden" && Number(cs.opacity) > 0;
  }

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

  const regionNodes = (cfg.regions || []).map((r) => ({ id: r.region_id, node: document.querySelector(r.selector) }));
  // Regions can nest (a caption region inside a story region): the innermost one wins.
  const regionOf = (el) => {
    let best = null;
    for (const r of regionNodes) {
      if (r.node && r.node.contains(el) && (!best || best.node.contains(r.node))) best = r;
    }
    return best ? best.id : null;
  };

  const fontFaces = document.fonts ? [...document.fonts] : [];
  const metrics = {
    vw: window.innerWidth, vh: window.innerHeight, sx, sy,
    page_w: document.documentElement.scrollWidth, page_h: document.documentElement.scrollHeight,
    dpr: window.devicePixelRatio, ready_state: document.readyState,
    fonts_status: document.fonts ? document.fonts.status : "unknown",
    fonts_failed: fontFaces.filter((f) => f.status === "error").map((f) => f.family),
    fonts_loading: fontFaces.filter((f) => f.status === "loading").map((f) => f.family),
    busy: !!document.querySelector('[aria-busy="true"]'),
    images_incomplete: [...document.images].filter((i) => !i.complete).length,
    href: location.href,
  };

  const regions = regionNodes.map((r) => ({ region_id: r.id, found: !!r.node, rect: r.node ? rect(r.node) : null }));

  if (cfg.mode === "regions_only") return JSON.stringify({ metrics, regions });

  // Leaf text blocks in document order; an element inside an already-kept block is skipped.
  const kept = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  for (let el = walker.currentNode; el; el = walker.nextNode()) {
    if (el === document.body || SKIP.has(el.tagName)) continue;
    if (!(TEXT_TAGS.has(el.tagName) || ownText(el))) continue;
    if (kept.some((k) => k.contains(el))) continue;
    if (!visible(el)) continue;
    const t = textOf(el);
    if (!t) continue;
    kept.push(el);
    if (kept.length >= (cfg.max_spans || 400)) break;
  }
  const spans = kept.map((el) => ({ key: cssPath(el), tag: el.tagName.toLowerCase(), text: textOf(el).slice(0, 4000),
    rect: rect(el), region_id: regionOf(el) }));

  if (cfg.mode === "spans") return JSON.stringify({ metrics, spans });

  if (cfg.mode === "text_map") {
    const map = {}, regions_of = {};
    for (const s of spans) { map[s.key] = s.text; regions_of[s.key] = s.region_id; }
    const pressed = [...document.querySelectorAll("[aria-pressed],[aria-expanded],[aria-selected],input,select")]
      .map((e) => `${cssPath(e)}=${e.getAttribute("aria-pressed") || e.getAttribute("aria-expanded") || e.getAttribute("aria-selected") || e.value || ""}`);
    return JSON.stringify({ metrics, map, regions_of, state_attrs: pressed });
  }

  const props = cfg.style_props || [];
  const styleOf = (el) => {
    const cs = getComputedStyle(el);
    const out = {};
    for (const p of props) out[p] = cs.getPropertyValue(p).slice(0, 500);
    return out;
  };
  const seen = new Set();
  const elements = [];
  const addEl = (el, kind) => {
    const key = cssPath(el);
    if (seen.has(key) || elements.length >= (cfg.max_elements || 400)) return;
    seen.add(key);
    elements.push({ key, kind, tag: el.tagName.toLowerCase(), role: el.getAttribute("role"),
      region_id: regionOf(el), style: styleOf(el), visible: visible(el) });
  };
  for (const r of regionNodes) if (r.node) addEl(r.node, "region");
  kept.forEach((el) => addEl(el, "text"));
  document.querySelectorAll(INTERACTIVE).forEach((el) => { if (visible(el)) addEl(el, "interactive"); });
  return JSON.stringify({ metrics, regions, spans, elements });
})()
