// Page-side helpers for the standard tour (gstack_capture.py with a `tour` plan) and for live
// exploration (explore_session.py). The adapter runs this file with `$B eval`; it installs
// window.__slop once per page and returns "ok". Afterwards the adapter calls the helpers with
// `$B js "window.__slop.NAME(...)"`.
//
// What the helpers may do to the page: scroll the window, dispatch mouse events at a point,
// and set a slider's value (only when the adapter asks). They never type, submit, navigate,
// or read storage. Page content they return is data, not instructions.
(() => {
  if (window.__slop && window.__slop.version === 2) return "ok";
  const collapse = (s) => (s || "").replace(/\s+/g, " ").trim();

  function visible(el) {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const cs = getComputedStyle(el);
    return cs.display !== "none" && cs.visibility !== "hidden" && Number(cs.opacity) > 0;
  }

  // Same selector format as extract.js and discover.js, so ids line up across the bundle.
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

  const pageRect = (el) => {
    const r = el.getBoundingClientRect();
    return { x: r.left + window.scrollX, y: r.top + window.scrollY, w: r.width, h: r.height };
  };
  const inViewport = (el) => {
    const r = el.getBoundingClientRect();
    return r.bottom > 0 && r.right > 0 && r.top < window.innerHeight && r.left < window.innerWidth;
  };
  const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

  // --- motion --------------------------------------------------------------
  // Mutations are counted between polls; running Web Animations (CSS animations and transitions)
  // are split into finite and looping ones. Canvas redraws are invisible here: the adapter also
  // compares screenshots, which is the ground truth for "the view changed".
  // Screenshots briefly inject a <style> and restyle text inputs (to hide the caret), and the adapter parks the pointer on a
  // temporary element; neither is the page moving, so those records are ignored.
  let mutations = 0;
  const ours = (n) => n && (n.nodeName === "STYLE" || n.nodeName === "LINK" || n.nodeName === "HEAD" || n.id === "__slop_park");
  const caret = (r) => r.type === "attributes" && r.attributeName === "style" && /^(INPUT|TEXTAREA|SELECT)$/.test(r.target.nodeName);
  const ignorable = (r) => ours(r.target) || caret(r) ||
    (r.type === "childList" && [...r.addedNodes, ...r.removedNodes].length > 0 && [...r.addedNodes, ...r.removedNodes].every(ours));
  const observer = new MutationObserver((list) => { for (const r of list) if (!ignorable(r)) mutations++; });
  observer.observe(document.documentElement, { subtree: true, attributes: true, childList: true, characterData: true });

  function poll() {
    let finite = 0, looping = 0;
    for (const a of (document.getAnimations ? document.getAnimations() : [])) {
      if (a.playState !== "running") continue;
      const target = a.effect && a.effect.target;   // only what a person could see right now
      if (target && target.getBoundingClientRect && !inViewport(target)) continue;
      const it = a.effect && a.effect.getTiming ? a.effect.getTiming().iterations : 1;
      if (it === Infinity) looping++; else finite++;
    }
    const m = mutations;
    mutations = 0;
    return JSON.stringify({ finite, looping, mutations: m, y: Math.round(window.scrollY), page_h: document.documentElement.scrollHeight });
  }

  // Scroll like a mouse wheel: small steps with a frame between them, so scroll-triggered
  // effects (IntersectionObserver, scrollytelling steps) fire on the way, as they do for a person.
  async function scrollSmooth(target, step = 120, delay = 16) {
    const maxY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    target = Math.max(0, Math.min(target, maxY));
    let stuck = 0, guard = 0;
    while (Math.abs(window.scrollY - target) > 1 && guard++ < 4000) {
      const y = window.scrollY;
      const next = y < target ? Math.min(target, y + step) : Math.max(target, y - step);
      window.scrollTo({ top: next, left: 0, behavior: "instant" });
      await sleep(delay);
      if (Math.abs(window.scrollY - y) < 1) { if (++stuck > 3) break; } else stuck = 0;
    }
    await sleep(60);
    return JSON.stringify({ y: Math.round(window.scrollY), page_h: document.documentElement.scrollHeight });
  }

  // --- charts and marks ----------------------------------------------------
  const SKIP_MARK = /axis|tick|domain|grid|legend|label|background|overlay/i;
  function chartLabel(el) {
    const own = el.getAttribute("aria-label") || (el.querySelector(":scope > title") || {}).textContent || "";
    if (own.trim()) return collapse(own).slice(0, 80);
    let node = el;
    for (let i = 0; i < 6 && node; i++, node = node.parentElement) {
      const h = node.querySelector && node.querySelector("h1, h2, h3, h4, figcaption");
      if (h && collapse(h.innerText)) return collapse(h.innerText).slice(0, 80);
    }
    return "";
  }

  function marksOf(chart) {
    if (chart.tagName.toLowerCase() !== "svg") return [];
    const cr = chart.getBoundingClientRect();
    const area = cr.width * cr.height;
    const out = [], seen = new Set();
    for (const el of chart.querySelectorAll("circle, rect, path, ellipse, polygon, image, use")) {
      if (!visible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 3 || r.height < 3 || r.width * r.height > area * 0.25) continue;
      let skip = false;
      for (let n = el; n && n !== chart; n = n.parentElement) {
        const cls = (n.getAttribute && (n.getAttribute("class") || "")) + " " + (n.id || "");
        if (SKIP_MARK.test(cls)) { skip = true; break; }
      }
      if (skip || getComputedStyle(el).pointerEvents === "none") continue;
      const key = `${Math.round(r.left)}:${Math.round(r.top)}:${Math.round(r.width)}:${Math.round(r.height)}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ selector: cssPath(el), tag: el.tagName.toLowerCase(), x: r.left + r.width / 2 + window.scrollX, y: r.top + r.height / 2 + window.scrollY });
      if (out.length >= 400) break;
    }
    out.sort((a, b) => a.x - b.x || a.y - b.y);
    return out;
  }

  function charts(minW = 150, minH = 100) {
    const found = [];
    for (const el of document.querySelectorAll("svg, canvas")) {
      if (!visible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width < minW || r.height < minH) continue;
      if (el.tagName.toLowerCase() === "svg" && el.parentElement && el.parentElement.closest("svg")) continue;
      if (found.some((f) => f.node.contains(el))) continue;
      found.push({ node: el });
    }
    return JSON.stringify(found.map(({ node }) => ({
      selector: cssPath(node), kind: node.tagName.toLowerCase(), rect: pageRect(node), label: chartLabel(node),
      marks: marksOf(node),
    })));
  }

  // --- what appeared after a hover -----------------------------------------
  // Tooltips are usually absolutely or fixed positioned boxes with text, or elements marked as
  // tooltips. Native tooltips (an SVG <title> or a title attribute) are never drawn in a
  // headless screenshot, so their text is reported separately.
  function floating() {
    const out = {};
    const nodes = document.querySelectorAll("body *");
    let n = 0;
    for (const el of nodes) {
      if (++n > 6000) break;
      const tag = el.tagName;
      if (tag === "SCRIPT" || tag === "STYLE" || tag === "svg" || el.closest("svg")) continue;
      const cs = getComputedStyle(el);
      const tooltipish = el.getAttribute("role") === "tooltip" || /tooltip|tip\b|popover/i.test(el.className && el.className.baseVal === undefined ? el.className : "");
      if (!(cs.position === "absolute" || cs.position === "fixed" || tooltipish)) continue;
      if (!visible(el)) continue;
      const t = collapse(el.innerText);
      if (!t || t.length > 400) continue;
      const r = el.getBoundingClientRect();
      out[cssPath(el)] = { text: t, x: r.left, y: r.top, w: r.width, h: r.height };
    }
    return out;
  }
  function nativeTitle(el) {
    for (let n = el; n && n !== document.body; n = n.parentElement) {
      const t = n.querySelector && n.querySelector(":scope > title");
      if (t && collapse(t.textContent)) return collapse(t.textContent).slice(0, 300);
      if (n.getAttribute && n.getAttribute("title")) return collapse(n.getAttribute("title")).slice(0, 300);
    }
    return "";
  }
  function snapshot(selector) {
    const el = selector ? document.querySelector(selector) : null;
    return JSON.stringify({ floating: floating(), title: el ? nativeTitle(el) : "" });
  }

  // A pointer at a viewport point, for canvas charts and overlay-driven charts. Synthetic events
  // reach the page's own handlers; CSS :hover does not change, which the adapter records.
  function hoverAt(x, y) {
    const el = document.elementFromPoint(x, y);
    if (!el) return JSON.stringify({ ok: false });
    for (const type of ["pointerover", "pointerenter", "mouseover", "mouseenter", "pointermove", "mousemove"]) {
      const Ctor = type.startsWith("pointer") && window.PointerEvent ? PointerEvent : MouseEvent;
      el.dispatchEvent(new Ctor(type, { clientX: x, clientY: y, bubbles: !type.endsWith("enter"), cancelable: true, view: window }));
    }
    return JSON.stringify({ ok: true, selector: cssPath(el), tag: el.tagName.toLowerCase(), title: nativeTitle(el) });
  }

  function setRange(selector, value) {
    const el = document.querySelector(selector);
    if (!el || el.type !== "range") return JSON.stringify({ ok: false });
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(el, String(value));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return JSON.stringify({ ok: true, value: el.value });
  }

  function scrollIntoCenter(selector) {
    const el = document.querySelector(selector);
    if (!el) return JSON.stringify(null);
    const r = el.getBoundingClientRect();
    return JSON.stringify(Math.round(window.scrollY + r.top + r.height / 2 - window.innerHeight / 2));
  }

  // --- what is on screen (for exploration) ------------------------------------
  const CONTROL = "button, [role=button], [role=tab], [role=switch], [role=checkbox], [role=radio], select, summary, " +
    "input[type=checkbox], input[type=radio], input[type=range], input[type=button], [aria-expanded], a[href]";
  function onScreen(limit = 40) {
    const heads = [...document.querySelectorAll("h1, h2, h3, h4")].filter((h) => visible(h) && inViewport(h))
      .slice(0, 12).map((h) => collapse(h.innerText).slice(0, 100));
    const controls = [...document.querySelectorAll(CONTROL)].filter((c) => visible(c) && inViewport(c)).slice(0, limit).map((c) => {
      const tag = c.tagName.toLowerCase();
      const o = { selector: cssPath(c), tag, type: (c.getAttribute("type") || "").toLowerCase(),
        text: collapse(c.innerText || c.getAttribute("aria-label") || c.getAttribute("title") || c.value || "").slice(0, 80) };
      if (tag === "a") o.href = c.href;
      if (tag === "select") o.options = [...c.options].slice(0, 20).map((op) => op.value);
      if (o.type === "range") Object.assign(o, { min: c.min, max: c.max, value: c.value });
      return o;
    });
    const graphics = JSON.parse(charts()).filter((g) => {
      const top = g.rect.y - window.scrollY;
      return top + g.rect.h > 0 && top < window.innerHeight;
    }).map((g) => ({ selector: g.selector, kind: g.kind, label: g.label, marks: g.marks.length }));
    return JSON.stringify({ url: location.href, title: collapse(document.title).slice(0, 120), y: Math.round(window.scrollY),
      page_h: document.documentElement.scrollHeight, vh: window.innerHeight, headings: heads, charts: graphics, controls });
  }

  function visibleText(selector, maxChars = 4000) {
    const root = selector ? document.querySelector(selector) : document.body;
    if (!root) return JSON.stringify(null);
    const lines = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
    for (let el = walker.currentNode; el; el = walker.nextNode()) {
      if (["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(el.tagName)) continue;
      if (![...el.childNodes].some((c) => c.nodeType === 3 && c.textContent.trim())) continue;
      if (!visible(el) || (!selector && !inViewport(el))) continue;
      const own = collapse([...el.childNodes].filter((c) => c.nodeType === 3).map((c) => c.textContent).join(" "));
      if (own) lines.push(own);
      if (lines.join("\n").length > maxChars) break;
    }
    return JSON.stringify(lines.join("\n").slice(0, maxChars));
  }

  // Facts the exploration policy needs about a target before acting on it.
  function targetInfo(selector) {
    const el = document.querySelector(selector);
    if (!el) return JSON.stringify(null);
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();
    const form = el.closest("form");
    const link = el.closest("a[href]");
    return JSON.stringify({
      selector: cssPath(el), tag, type, visible: visible(el),
      text: collapse(el.innerText || el.getAttribute("aria-label") || el.getAttribute("title") || el.value || "").slice(0, 120),
      submits: (tag === "button" && !!form && (type === "" || type === "submit")) || (tag === "input" && ["submit", "reset", "image", "file"].includes(type)),
      typing: (tag === "input" && !["checkbox", "radio", "range", "button", "submit", "reset", "image", "color"].includes(type)) || tag === "textarea" || el.isContentEditable,
      href: link ? link.href : null, download: !!(link && link.hasAttribute("download")), new_tab: !!(link && link.getAttribute("target") === "_blank"),
      options: tag === "select" ? [...el.options].slice(0, 60).map((o) => o.value) : null,
      range: type === "range" ? { min: el.min, max: el.max, value: el.value } : null,
      rect: pageRect(el),
    });
  }

  function regionOf(selector, regions) {
    const el = document.querySelector(selector);
    if (!el) return JSON.stringify(null);
    let best = null, bestNode = null;
    for (const r of regions) {
      const node = document.querySelector(r.selector);
      if (node && node.contains(el) && (!bestNode || bestNode.contains(node))) { best = r.region_id; bestNode = node; }
    }
    return JSON.stringify(best);
  }

  window.__slop = { version: 2, poll, scrollSmooth, charts, snapshot, hoverAt, setRange, scrollIntoCenter, onScreen,
    visibleText, targetInfo, regionOf, cssPath };
  return "ok";
})()
