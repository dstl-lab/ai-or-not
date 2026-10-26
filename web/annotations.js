/** Optional element-and-note annotations on the frozen project pages. */
const chartLabels = {
  circle:"Chart point", ellipse:"Chart point", line:"Chart line", polyline:"Chart line",
  path:"Chart shape", rect:"Chart shape", polygon:"Chart shape", g:"Chart element",
  svg:"Chart", canvas:"Chart",
};
const controls = 'button,a,label,input,select,textarea,[role="button"]';
const textTargets = "h1,h2,h3,h4,h5,h6,p";
const contentTargets = `${textTargets},img,iframe,text,${Object.keys(chartLabels).join(",")}`;

function elementBounds(target, win) {
  const rect = target.getBoundingClientRect();
  if (rect.width && rect.height || !(rect.width || rect.height) || target.namespaceURI !== "http://www.w3.org/2000/svg") return rect;
  const style = win.getComputedStyle(target);
  const matrix = target.getScreenCTM();
  const scale = style.vectorEffect === "non-scaling-stroke" ? 1 : matrix && Math.max(Math.hypot(matrix.a, matrix.b), Math.hypot(matrix.c, matrix.d));
  const stroke = style.stroke !== "none" && parseFloat(style.strokeWidth) * scale;
  if (!(stroke > 0)) return rect;
  const width = rect.width || stroke, height = rect.height || stroke;
  const left = rect.left - (width - rect.width) / 2, top = rect.top - (height - rect.height) / 2;
  return {left, top, width, height, right:left + width, bottom:top + height};
}

function visibleBounds(target, win, region = null) {
  const rect = areaBounds(elementBounds(target, win), region);
  let left = rect.left, top = rect.top, right = left + rect.width, bottom = top + rect.height;
  for (let node = target; node; node = node.parentElement) {
    const style = win.getComputedStyle(node);
    if (["hidden", "collapse"].includes(style.visibility) || style.display === "none" || style.opacity === "0") return null;
    if (node === target || node === win.document.documentElement || node === win.document.body) continue;
    const clipX = ["hidden", "clip"].includes(style.overflowX), clipY = ["hidden", "clip"].includes(style.overflowY);
    if (clipX || clipY) {
      const clip = node.getBoundingClientRect();
      if (clipX) { left = Math.max(left, clip.left); right = Math.min(right, clip.left + clip.width); }
      if (clipY) { top = Math.max(top, clip.top); bottom = Math.min(bottom, clip.top + clip.height); }
    }
  }
  return right > left && bottom > top ? {left, top, right, bottom, width:right - left, height:bottom - top} : null;
}

function targetsAt(win, x, y) {
  if (!Number.isFinite(x) || !Number.isFinite(y)) return [];
  const doc = win.document;
  const stack = doc.elementsFromPoint(x, y);
  const modal = stack[0]?.closest('[aria-modal="true"],dialog');
  // Hit testing omits visible headings and chart labels with pointer-events:none.
  const semantic = [...doc.querySelectorAll(`${controls},${contentTargets}`)].filter(target => {
    const rect = elementBounds(target, win);
    return rect.width && rect.height && x >= rect.left && x <= rect.left + rect.width && y >= rect.top && y <= rect.top + rect.height;
  });
  const elements = [];
  for (const target of [...stack, ...semantic]) {
    const element = target.closest(controls) || target.closest(textTargets) || target;
    if (modal && !modal.contains(element)) continue;
    if (elements.includes(element)) continue;
    const rect = visibleBounds(element, win);
    if (rect && x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) elements.push(element);
  }
  const content = elements.filter(element => !["html", "body"].includes(element.tagName.toLowerCase()));
  return content.length ? content : elements.slice(0, 1);
}

function preferredTarget(elements, win) {
  const area = element => {
    const rect = elementBounds(element, win);
    return rect.width * rect.height;
  };
  const compact = elements.filter(element => area(element) < win.innerWidth * win.innerHeight * .6);
  for (const selector of [controls, contentTargets]) {
    const useful = compact.filter(element => element.matches(selector));
    if (useful.length) return useful.sort((a, b) => area(a) - area(b))[0];
  }
  return elements.find(element => element.matches("iframe")) || compact[0] || elements[0];
}

function targetLabel(target) {
  const tag = target.tagName.toLowerCase();
  if (tag === "iframe") return (target.getAttribute("title") || "Embedded content").slice(0, 300);
  if (!Object.hasOwn(chartLabels, tag)) {
    return (target.innerText || target.textContent || target.getAttribute?.("aria-label") || target.tagName).trim().slice(0, 300);
  }
  for (let chart = target; chart; chart = chart.parentElement) {
    const chartTag = chart.tagName.toLowerCase();
    if (chartTag !== "svg" && chartTag !== "canvas" && !["img", "graphics-document"].includes(chart.getAttribute?.("role"))) continue;
    const referenced = (chart.getAttribute?.("aria-labelledby") || "").trim().split(/\s+/)
      .map(id => chart.ownerDocument?.getElementById(id)?.textContent?.trim()).filter(Boolean).join(" ");
    const name = referenced || chart.getAttribute?.("aria-label")?.trim()
      || [...chart.children].find(child => child.tagName.toLowerCase() === "title")?.textContent?.trim()
      || chart.getAttribute?.("title")?.trim();
    if (name) return `${chartLabels[tag]} · ${name}`.slice(0, 300);
  }
  return chartLabels[tag];
}

function annotationLabel(entry, frame) {
  const quote = entry.quote || "";
  if (!Object.hasOwn(chartLabels, quote.toLowerCase())) return quote || "Selected element";
  try {
    const win = frame?.contentWindow;
    if (win && win.location.pathname + win.location.search === entry.page_path.split("#")[0]) {
      const target = win.document.querySelector(entry.selector);
      if (target) return targetLabel(target);
    }
  } catch {}
  return chartLabels[quote.toLowerCase()];
}

function areaBounds(rect, region) {
  return region ? {
    left:rect.left + region.x * rect.width, top:rect.top + region.y * rect.height,
    width:region.width * rect.width, height:region.height * rect.height,
  } : rect;
}

export function captureTarget(target, win, site, region = null) {
  if (!win.location.pathname.startsWith(site.home)) throw new Error("Return to the assigned webpage before annotating.");
  const parts = [];
  for (let node = target; node && parts.length < 12; node = node.parentElement) {
    if (node.id) { parts.unshift(`#${win.CSS.escape(node.id)}`); break; }
    const tag = node.tagName.toLowerCase();
    const siblings = node.parentElement ? [...node.parentElement.children].filter(el => el.tagName === node.tagName) : [node];
    parts.unshift(`${tag}:nth-of-type(${siblings.indexOf(node) + 1})`);
  }
  const rect = areaBounds(elementBounds(target, win), region);
  if (!rect.width || !rect.height) throw new Error("Choose a visible part of the webpage.");
  const style = win.getComputedStyle(target);
  const styles = {};
  for (const key of ["background-color", "background-image", "color", "font-family", "font-size", "font-weight", "border-radius", "box-shadow", "display", "gap"]) {
    styles[key] = style.getPropertyValue(key).slice(0, 300);
  }
  return {
    page_path: win.location.pathname + win.location.search + win.location.hash,
    selector: parts.join(" > ").slice(0, 1000),
    quote: region ? targetLabel(target).replace(/^Chart/, "Chart area").slice(0, 300) : targetLabel(target),
    rect: {x: rect.left + win.scrollX, y: rect.top + win.scrollY, width: rect.width, height: rect.height},
    viewport: {width: win.innerWidth, height: win.innerHeight},
    styles,
    ...(region ? {region} : {}),
  };
}

function button(label, action, className = "") {
  const el = document.createElement("button");
  el.type = "button";
  el.textContent = label;
  el.className = className;
  el.addEventListener("click", action);
  return el;
}

export class AnnotationTool {
  constructor({change, refresh, warn}) {
    Object.assign(this, {change, refresh, warn});
    this.draft = null;
    this.armed = false;
    this.cleanup = null;
    this.frame = null;
    this.pending = null;
    this.candidates = [];
    this.onKey = event => { if (event.key === "Escape" && this.armed) this.cancel(); };
    document.addEventListener("keydown", this.onKey);
  }

  attach(frame, site) {
    this.stopSelecting();
    this.candidates = [];
    this.frame = frame;
    this.site = site;
    this.refresh();
    if (this.pending) {
      const entry = this.pending;
      this.pending = null;
      this.show(entry);
    }
  }

  cancel(refresh = true) {
    this.stopSelecting();
    this.draft = null;
    this.candidates = [];
    this.pending = null;
    this.warn("");
    if (refresh) {
      this.refresh();
      document.querySelector(".annotation-add, .annotation-target")?.focus();
    }
  }

  stopSelecting() {
    this.cleanup?.();
    this.cleanup = null;
    this.armed = false;
  }

  start() {
    this.cancel(false);
    try {
      const win = this.frame.contentWindow;
      const doc = win.document;
      if (!win.location.pathname.startsWith(this.site.home)) throw new Error("Return to the assigned webpage before annotating.");
      this.armed = true;
      const outline = doc.createElement("div");
      outline.setAttribute("aria-hidden", "true");
      Object.assign(outline.style, {
        position:"fixed", pointerEvents:"none", zIndex:"2147483647", display:"none",
        boxSizing:"border-box", border:"3px solid #2563eb", borderRadius:"4px",
        boxShadow:"0 0 0 2px #fff", backgroundColor:"rgba(37, 99, 235, 0.12)",
      });
      const label = doc.createElement("div");
      label.textContent = "Click to annotate";
      label.setAttribute("aria-hidden", "true");
      Object.assign(label.style, {
        all:"initial", position:"fixed", pointerEvents:"none", zIndex:"2147483647", display:"none",
        boxSizing:"border-box", padding:"6px 8px", borderRadius:"4px", maxWidth:"calc(100vw - 16px)",
        font:"600 12px/1.2 system-ui, sans-serif", color:"#fff", backgroundColor:"#1d4ed8",
        boxShadow:"0 0 0 1px #fff",
      });
      doc.documentElement.append(outline, label);
      const cursor = doc.createElement("style");
      // Child-frame events do not bubble; select the frame itself until browsing resumes.
      cursor.textContent = "* { cursor: crosshair !important; } canvas { touch-action: none !important; } iframe { pointer-events: none !important; }";
      doc.head.append(cursor);
      let pointer = null, pendingFrame = null, drawing = null, selection = null;
      const canvasPoint = (target, point) => {
        const rect = target.getBoundingClientRect();
        return {x:Math.max(0, Math.min(1, (point.x - rect.left) / rect.width)),
          y:Math.max(0, Math.min(1, (point.y - rect.top) / rect.height))};
      };
      const drawnRegion = () => {
        const end = canvasPoint(drawing.target, pointer);
        return {x:Math.min(drawing.start.x, end.x), y:Math.min(drawing.start.y, end.y),
          width:Math.abs(end.x - drawing.start.x), height:Math.abs(end.y - drawing.start.y)};
      };
      const release = () => {
        const current = drawing;
        drawing = null;
        if (current?.target.hasPointerCapture?.(current.id)) current.target.releasePointerCapture(current.id);
      };
      const update = () => {
        pendingFrame = null;
        const target = drawing?.target || selection?.target || doc.elementFromPoint(pointer.x, pointer.y);
        if (target) {
          const rect = areaBounds(elementBounds(target, win), drawing ? drawnRegion() : selection?.region);
          Object.assign(outline.style, {display:"block", left:`${rect.left}px`, top:`${rect.top}px`, width:`${rect.width}px`, height:`${rect.height}px`});
          label.textContent = drawing || selection ? "Release to add a note"
            : target.tagName.toLowerCase() === "canvas" ? "Drag to draw an area" : "Click to annotate";
          label.style.display = "block";
          const hint = label.getBoundingClientRect();
          const top = rect.top >= hint.height + 14 ? rect.top - hint.height - 6 : rect.top + 6;
          Object.assign(label.style, {
            left:`${Math.max(8, Math.min(rect.left, win.innerWidth - hint.width - 8))}px`,
            top:`${Math.max(8, Math.min(top, win.innerHeight - hint.height - 8))}px`,
          });
        } else {
          outline.style.display = label.style.display = "none";
        }
        // Scrolling and chart animation can change the target under a stationary pointer.
        pendingFrame = win.requestAnimationFrame(update);
      };
      const hover = event => {
        if (drawing && event.pointerId !== drawing.id) return;
        pointer = {x:event.clientX, y:event.clientY};
        if (pendingFrame === null) update();
      };
      const leave = event => {
        if (event.relatedTarget || drawing) return;
        if (pendingFrame !== null) win.cancelAnimationFrame(pendingFrame);
        pendingFrame = null;
        outline.style.display = label.style.display = "none";
      };
      const block = event => {
        event.preventDefault();
        event.stopImmediatePropagation();
      };
      const begin = event => {
        block(event);
        if (drawing || event.button !== 0 || event.isPrimary === false || event.target.tagName.toLowerCase() !== "canvas") return;
        pointer = {x:event.clientX, y:event.clientY};
        selection = null;
        drawing = {target:event.target, id:event.pointerId, start:canvasPoint(event.target, pointer)};
        event.target.setPointerCapture(event.pointerId);
        this.warn("");
        if (pendingFrame === null) update();
      };
      const end = event => {
        block(event);
        if (!drawing || event.pointerId !== drawing.id) return;
        pointer = {x:event.clientX, y:event.clientY};
        const region = drawnRegion();
        const rect = areaBounds(drawing.target.getBoundingClientRect(), region);
        selection = rect.width >= 6 && rect.height >= 6 ? {target:drawing.target, region} : null;
        release();
        if (!selection) this.warn("Drag a larger area on the chart, or press Esc to cancel.");
      };
      const interrupt = event => {
        if (!drawing || event.pointerId !== drawing.id) return;
        release();
        selection = null;
      };
      const pick = event => {
        block(event);
        if (drawing) return;
        const candidates = selection ? [selection.target] : event.detail === 0 ? [event.target]
          : targetsAt(win, event.clientX, event.clientY);
        const target = preferredTarget(candidates, win) || event.target;
        if (target.tagName.toLowerCase() === "canvas" && !selection && event.detail !== 0) {
          this.warn("Drag a larger area on the chart, or press Esc to cancel.");
          return;
        }
        try {
          this.draft = {...captureTarget(target, win, this.site, selection?.region), id:crypto.randomUUID(), note:""};
          this.candidates = candidates;
          this.layerIndex = candidates.indexOf(target);
          this.warn("");
          this.stopSelecting();
          this.refresh();
          if (this.draft.region || candidates.length > 1) this.show(this.draft, false);
          document.querySelector(".annotation-editor textarea")?.focus();
        } catch (err) { this.warn(err.message); }
      };
      const touch = event => {
        const finished = !drawing && selection && !event.touches.length;
        if (event.target.tagName.toLowerCase() !== "canvas" && !finished) return;
        block(event);
        if (event.type === "touchcancel") {
          release();
          selection = null;
        }
        // A touch drag may not produce the click used by mouse selection.
        if (event.type === "touchend" && finished) pick(event);
      };
      const touchEvents = ["touchstart", "touchmove", "touchend", "touchcancel"];
      for (const type of touchEvents) doc.addEventListener(type, touch, {capture:true, passive:false});
      doc.addEventListener("pointermove", hover, true);
      doc.addEventListener("pointerout", leave, true);
      // Some canvas charts activate on mouseup before the click used to select a note.
      const pressEvents = ["mousedown", "mouseup"];
      for (const type of pressEvents) doc.addEventListener(type, block, true);
      doc.addEventListener("pointerdown", begin, true);
      doc.addEventListener("pointerup", end, true);
      doc.addEventListener("pointercancel", interrupt, true);
      doc.addEventListener("lostpointercapture", interrupt, true);
      doc.addEventListener("click", pick, true);
      doc.addEventListener("keydown", this.onKey, true);
      this.cleanup = () => {
        if (pendingFrame !== null) win.cancelAnimationFrame(pendingFrame);
        for (const type of touchEvents) doc.removeEventListener(type, touch, true);
        doc.removeEventListener("pointermove", hover, true);
        doc.removeEventListener("pointerout", leave, true);
        for (const type of pressEvents) doc.removeEventListener(type, block, true);
        doc.removeEventListener("pointerdown", begin, true);
        doc.removeEventListener("pointerup", end, true);
        doc.removeEventListener("pointercancel", interrupt, true);
        doc.removeEventListener("lostpointercapture", interrupt, true);
        doc.removeEventListener("click", pick, true);
        doc.removeEventListener("keydown", this.onKey, true);
        release();
        outline.remove(); label.remove(); cursor.remove();
      };
      this.refresh();
      document.querySelector(".annotation-mode button")?.focus();
    } catch (err) {
      this.armed = false;
      this.warn(err.message || "This page cannot be annotated. Return to the start of the website and try again.");
    }
  }

  show(entry, scroll = true) {
    this.stopSelecting();
    try {
      const win = this.frame.contentWindow;
      const doc = win.document;
      const unavailable = "This element is not currently visible. Recreate the page interaction to find it; your note is still saved.";
      const hashAt = entry.page_path.indexOf("#");
      const page = hashAt === -1 ? entry.page_path : entry.page_path.slice(0, hashAt);
      const hash = hashAt === -1 ? "" : entry.page_path.slice(hashAt);
      if (win.location.pathname + win.location.search !== page) {
        this.pending = entry;
        this.frame.src = entry.page_path;
        return;
      }
      if (win.location.hash !== hash) win.location.hash = hash;
      const target = doc.querySelector(entry.selector);
      const bounds = () => {
        if (!target?.isConnected) return null;
        return visibleBounds(target, win, entry.region);
      };
      if (!bounds()) throw new Error(unavailable);
      if (scroll) target.scrollIntoView({block:"center", behavior:"instant"});
      const marker = doc.createElement("div");
      marker.setAttribute("aria-hidden", "true");
      Object.assign(marker.style, {position:"absolute", pointerEvents:"none", zIndex:"2147483647", border:"2px solid #2f5d8a", borderRadius:"3px"});
      if (entry.region) Object.assign(marker.style, {boxSizing:"border-box", border:"3px solid #2563eb", boxShadow:"0 0 0 2px #fff", backgroundColor:"rgba(37, 99, 235, 0.12)"});
      doc.documentElement.append(marker);
      let pendingFrame = null;
      this.cleanup = () => {
        if (pendingFrame !== null) win.cancelAnimationFrame(pendingFrame);
        marker.remove();
      };
      const update = () => {
        pendingFrame = null;
        const rect = bounds();
        if (!rect) {
          this.stopSelecting();
          this.warn(unavailable);
          return false;
        }
        Object.assign(marker.style, {left:`${rect.left+win.scrollX}px`, top:`${rect.top+win.scrollY}px`, width:`${rect.width}px`, height:`${rect.height}px`});
        // CSS animations can move chart marks without DOM mutations or resize events.
        pendingFrame = win.requestAnimationFrame(update);
        return true;
      };
      if (update()) this.warn("");
    } catch (err) { this.warn(err.message); }
  }

  render(question, entries) {
    const box = document.createElement("div");
    box.className = "annotations";
    const limit = question.max_annotations || 3;
    if (this.draft) {
      const editor = document.createElement("div");
      editor.className = "annotation-editor";
      const target = document.createElement("p");
      target.className = "annotation-target";
      target.textContent = annotationLabel(this.draft, this.frame);
      const label = document.createElement("label");
      label.textContent = "What influenced your rating here?";
      const input = document.createElement("textarea");
      input.rows = 3;
      input.maxLength = 500;
      input.value = this.draft.note;
      input.setAttribute("aria-label", "Annotation note");
      const save = button("Save note", () => {
        const entry = {...this.draft, note:input.value.trim()};
        if (!entry.note) return;
        const existing = entries.some(item => item.id === entry.id);
        const updated = existing ? entries.map(item => item.id === entry.id ? entry : item) : [...entries, entry];
        this.draft = null;
        this.candidates = [];
        this.change(question, updated);
        this.refresh();
        this.show(entry);
        document.querySelectorAll(".annotation-list .annotation-target")[updated.findIndex(item => item.id === entry.id)]?.focus();
      }, "primary");
      save.disabled = !input.value.trim();
      input.addEventListener("input", () => { this.draft.note = input.value; save.disabled = !input.value.trim(); });
      label.append(input);
      const actions = document.createElement("div");
      actions.className = "annotation-actions";
      actions.append(button("Cancel", () => this.cancel()), save);
      editor.append(target);
      if (this.candidates.length > 1) {
        const layers = document.createElement("label");
        layers.className = "annotation-layer";
        layers.textContent = "Overlapping elements";
        const select = document.createElement("select");
        select.setAttribute("aria-label", "Selected element layer");
        for (const [index, element] of this.candidates.entries()) {
          const option = document.createElement("option");
          option.value = String(index);
          option.textContent = `${targetLabel(element).slice(0, 100)} (${element.tagName.toLowerCase()})`;
          option.selected = index === this.layerIndex;
          select.append(option);
        }
        select.addEventListener("change", () => {
          try {
            const index = Number(select.value);
            this.draft = {...captureTarget(this.candidates[index], this.frame.contentWindow, this.site),
              id:this.draft.id, note:this.draft.note};
            this.layerIndex = index;
            target.textContent = annotationLabel(this.draft, this.frame);
            this.show(this.draft, false);
          } catch (err) {
            select.value = String(this.layerIndex);
            this.warn(err.message);
          }
        });
        layers.append(select);
        editor.append(layers);
      }
      editor.append(label, actions);
      if (this.draft.region) {
        const hint = document.createElement("p");
        hint.className = "annotation-region-help";
        hint.textContent = "This box marks an area of the chart. Zooming or rotating can change what appears inside it.";
        editor.append(hint);
      }
      box.append(editor);
    } else if (this.armed) {
      const mode = document.createElement("div");
      mode.className = "annotation-mode";
      const heading = document.createElement("h4");
      heading.className = "annotation-mode-heading";
      heading.textContent = "Select a detail on the webpage";
      const hint = document.createElement("p");
      hint.className = "annotation-mode-description";
      hint.setAttribute("role", "status");
      hint.textContent = "Click a detail on the webpage. When prompted, drag to draw a box. Press Esc to cancel.";
      mode.append(heading, hint, button("Cancel selection", () => this.cancel()));
      box.append(mode);
    } else if (entries.length < limit) {
      box.append(button("Annotate webpage", () => this.start(), "annotation-add"));
      if (!entries.length && !question.help) {
        const hint = document.createElement("p");
        hint.className = "annotation-empty";
        hint.textContent = "Select a detail on the webpage, then add a note.";
        box.append(hint);
      }
    } else {
      const hint = document.createElement("p");
      hint.className = "annotation-limit";
      hint.textContent = `You’ve reached the ${limit} note limit. Edit or remove a saved note to add another.`;
      box.append(hint);
    }
    if (entries.length) {
      const list = document.createElement("div");
      list.className = "annotation-list";
      const heading = document.createElement("h4");
      heading.className = "annotation-list-heading";
      heading.textContent = `Saved notes (${entries.length})`;
      list.append(heading);
      for (const [index, entry] of entries.entries()) {
        const card = document.createElement("div");
        card.className = "annotation-card";
        const targetButton = button(`${index+1}. ${annotationLabel(entry, this.frame)}`, () => {
          this.show(entry);
          targetButton.textContent = `${index+1}. ${annotationLabel(entry, this.frame)}`;
        }, "annotation-target");
        card.append(targetButton);
        const note = document.createElement("p");
        note.className = "annotation-note";
        note.textContent = entry.note;
        const actions = document.createElement("div");
        actions.className = "annotation-actions";
        actions.append(button("Edit note", () => {
          this.candidates = [];
          this.draft = {...entry}; this.refresh();
          if (entry.region) this.show(entry);
          document.querySelector(".annotation-editor textarea")?.focus();
        }), button("Remove", () => {
          this.cleanup?.(); this.cleanup = null;
          this.change(question, entries.filter(item => item.id !== entry.id));
          this.refresh();
          document.querySelector(".annotation-add, .annotation-target")?.focus();
        }));
        for (const control of [card.firstChild, ...actions.children]) control.disabled = Boolean(this.draft || this.armed);
        card.append(note, actions);
        list.append(card);
      }
      box.append(list);
    }
    return box;
  }
}
