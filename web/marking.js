import { api, escapeHtml as h } from './api.js';

const reasons = {shape: 'Shape or rounded corners', color: 'Colors or background',
  font: 'Font or typography', spacing: 'Layout or spacing', wording: 'Wording', other: 'Another visual detail'};

function pageKey(location) {
  return location.pathname.replace(/\/index\.html$/, '/') + location.search + location.hash;
}

// Stable within the pinned copy; geometry and styles preserve additional evidence for dynamic pages.
export function selectorFor(el) {
  const parts = [];
  while (el?.nodeType === 1) {
    const tag = el.localName;
    const siblings = el.parentElement ? [...el.parentElement.children].filter(e => e.localName === tag) : [el];
    parts.unshift(`${tag}:nth-of-type(${siblings.indexOf(el) + 1})`);
    el = el.parentElement;
  }
  return parts.join(' > ');
}

const controls = 'button,a,label,input,select,textarea,[role="button"]';

export function elementLabel(el) {
  const kind = ({h1: 'Heading', h2: 'Heading', h3: 'Heading', h4: 'Heading',
    p: 'Text', span: 'Text', em: 'Text', strong: 'Text', button: 'Button', a: 'Link',
    canvas: 'Graphic', svg: 'Graphic', img: 'Image', iframe: 'Embedded content',
    section: 'Section', div: 'Area', body: 'Page background', html: 'Page background'})[el.localName] || 'Element';
  const text = (el.getAttribute('aria-label') || el.getAttribute('alt') || el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ');
  return text ? `${kind}: ${text.slice(0, 100)}` : kind;
}

// Broad animation layers may sit above text. Keep every layer available, but prefer
// a compact piece of content when the top layer covers most of the viewport.
export function preferredTarget(elements, width, height) {
  if (!elements.length) return null;
  const area = el => {
    const box = el.getBoundingClientRect();
    return box.width * box.height;
  };
  const compact = elements.filter(el => area(el) < width * height * .6);
  const interactive = compact.filter(el => el.matches(controls));
  if (interactive.length) return interactive.sort((a, b) => area(a) - area(b))[0];
  const content = compact.filter(el => {
    const r = el.getBoundingClientRect();
    return el.matches('h1,h2,h3,h4,h5,h6,p,img,svg,canvas') && r.width && r.height;
  });
  if (content.length) return content.sort((a, b) => area(a) - area(b))[0];
  return compact[0] || elements[0];
}

export class ElementMarker {
  constructor(context) {
    this.context = context;
    this.data = {};
    this.dirty = new Set();
    this.chain = Promise.resolve();
    this.pendingSaves = 0;
    this.mode = false;
    this.draft = null;
    this.error = '';
    this.cleanup = null;
    this.frame = null;
    this.siteId = null;
    this.candidates = [];
    this.boxes = new Map();
  }
  get busy() { return this.dirty.size > 0 || this.pendingSaves > 0 || !!this.draft; }
  value() { return this.data[this.context().site.id] ??= {marks: [], none: false}; }
  render() {
    const host = document.getElementById('element-marks');
    if (!host) return;
    const value = this.value();
    const ready = typeof this.context().answers.ai_generated === 'boolean';
    host.innerHTML = `<h2>Mark visual clues <span class="mark-count">${value.marks.length}/3</span></h2>
      <p>${ready ? 'Click “Mark an element”, then click a part of the website that looks AI-designed to you.' : 'Answer the AI-generated question first, then you can mark specific visual clues.'}</p>
      <button type="button" class="mark-toggle" aria-pressed="${this.mode}" ${!ready || (!this.mode && !this.draft && value.marks.length >= 3) ? 'disabled' : ''}>${this.draft ? 'Cancel selection' : this.mode ? 'Cancel marking' : 'Mark an element'}</button>
      <p class="mark-help">${this.draft ? 'Choose a reason, or cancel. Double-click the outlined area to unselect it.' : this.mode ? 'Click an element to select it. Press Escape or Cancel marking to stop.' : 'Double-click a marked area to remove its mark. Other areas work normally.'}</p>
      ${this.draft ? `<div class="mark-draft"><strong>Selected: ${h(this.draft.label)}</strong>
        ${this.candidates.length > 1 ? `<label class="mark-layer">Overlapping elements
          <select aria-label="Selected element layer">${this.candidates.map((el, i) => `<option value="${i}" ${selectorFor(el) === this.draft.selector ? 'selected' : ''}>${h(elementLabel(el))}</option>`).join('')}</select></label>` : ''}
        <p>What about this element looks AI-designed?</p>
        <div class="mark-reasons">${Object.entries(reasons).map(([key, label]) => `<button type="button" data-reason="${key}">${h(label)}</button>`).join('')}</div>
</div>` : ''}
      <ol class="mark-list">${value.marks.map((mark, i) => `<li><span><strong>${i + 1}. ${h(mark.label)}</strong><br>${h(reasons[mark.reason])}</span><button type="button" data-remove="${i}" aria-label="Remove mark ${i + 1}">Remove</button></li>`).join('')}</ol>
      <label class="mark-none"><input type="checkbox" ${value.none ? 'checked' : ''} ${!ready || value.marks.length || this.draft ? 'disabled' : ''}> Nothing specific stood out</label>
      <p class="mark-save" role="status">${h(this.error || (this.dirty.size || this.pendingSaves ? 'Saving marks…' : ''))}</p>
      ${this.error ? '<button type="button" data-retry>Retry saving</button>' : ''}`;
    host.querySelector('.mark-toggle').onclick = () => {
      if (this.mode || this.draft) this.cancel();
      else { this.mode = true; this.render(); this.paint(); }
    };
    host.querySelector('.mark-layer select')?.addEventListener('change', e => {
      this.select(this.candidates[Number(e.target.value)]);
    });
    host.querySelectorAll('[data-reason]').forEach(button => button.onclick = () => {
      this.value().marks.push({...this.draft, reason: button.dataset.reason});
      this.value().none = false;
      this.draft = null;
      this.save();
      this.paint();
    });
    host.querySelectorAll('[data-remove]').forEach(button => button.onclick = () => {
      this.remove(Number(button.dataset.remove));
    });
    host.querySelector('.mark-none input').onchange = e => { this.value().none = e.target.checked; this.save(); };
    host.querySelector('[data-retry]')?.addEventListener('click', () => this.save());
  }
  cancel() { this.mode = false; this.draft = null; this.candidates = []; this.render(); this.paint(); }
  remove(index) {
    this.value().marks.splice(index, 1);
    this.save(); this.paint();
  }
  select(el) {
    if (!el?.getBoundingClientRect) return;
    const win = this.frame.contentWindow;
    const rect = el.getBoundingClientRect();
    const style = win.getComputedStyle(el);
    const styles = {};
    for (const key of ['background-color', 'background-image', 'color', 'font-family', 'font-size', 'font-weight', 'border-radius', 'box-shadow', 'display', 'gap']) {
      styles[key] = style.getPropertyValue(key).slice(0, 300);
    }
    this.draft = {
      page: pageKey(win.location), selector: selectorFor(el), tag: el.localName,
      label: elementLabel(el),
      rect: [Math.max(0, rect.x + win.scrollX), Math.max(0, rect.y + win.scrollY), rect.width, rect.height],
      viewport: [win.innerWidth, win.innerHeight], styles,
      ai_judgment: this.context().answers.ai_generated,
    };
    this.mode = false;
    this.render(); this.paint();
    // Avoid scrolling the survey away from its always-available Cancel control.
    document.querySelector('.mark-toggle')?.focus({preventScroll: true});
  }
  targetsAt(x, y) {
    const win = this.frame.contentWindow;
    this.overlay.style.setProperty('display', 'none', 'important');
    try {
      const stack = win.document.elementsFromPoint(x, y);
      // elementsFromPoint omits nodes with pointer-events:none. Many visual sites use
      // that rule on headings and chart labels, even though those are exactly the
      // details a participant may want to identify.
      const semantic = [...win.document.querySelectorAll(
        `${controls},h1,h2,h3,h4,h5,h6,p,img,svg,canvas`,
      )].filter(el => {
        const r = el.getBoundingClientRect();
        return r.width && r.height && x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
      });
      const elements = [];
      for (const target of [...semantic, ...stack]) {
        const el = target.closest(controls) || target.closest('h1,h2,h3,h4,h5,h6,p') || target;
        if (elements.includes(el) || ['html', 'body'].includes(el.localName) || el.closest('[data-study-marks]')) continue;
        let visible = true;
        for (let ancestor = el; ancestor; ancestor = ancestor.parentElement) {
          const style = win.getComputedStyle(ancestor);
          if (style.visibility === 'hidden' || style.display === 'none' || Number(style.opacity) === 0) { visible = false; break; }
        }
        if (visible) elements.push(el);
      }
      return elements.length ? elements : [win.document.body];
    } finally { this.overlay.style.removeProperty('display'); }
  }
  save() {
    this.dirty.add(this.context().site.id);
    this.flush(true).catch(() => {});
    this.render();
  }
  async flush(allowDraft = false) {
    if (this.draft && !allowDraft) throw new Error('Choose a reason for the selected element, or cancel the selection.');
    for (const siteId of this.dirty) {
      const payload = JSON.parse(JSON.stringify(this.data[siteId]));
      this.dirty.delete(siteId);
      this.pendingSaves++;
      this.chain = this.chain.catch(() => {}).then(async () => {
        try {
          // The first-impression answer must reach SQLite before the mark.
          await this.context().saveAnswers();
          await api(`/api/sessions/${this.context().sessionId}/sites/${siteId}/marks`, {method: 'PUT', body: payload});
          this.error = '';
        } catch (e) {
          this.dirty.add(siteId);
          this.error = `Marks not saved: ${e.message}`;
          throw e;
        } finally { this.pendingSaves--; this.render(); }
      });
    }
    await this.chain;
    if (this.dirty.size) throw new Error('Some marks have not saved. Use Retry saving.');
  }
  attach(frame, site) {
    this.cleanup?.();
    this.mode = false;
    this.draft = null;
    this.frame = frame;
    this.siteId = site.id;
    const win = frame.contentWindow;
    const doc = win.document;
    const overlay = doc.createElement('div');
    overlay.setAttribute('data-study-marks', '');
    overlay.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2147483647;';
    doc.documentElement.append(overlay);
    this.overlay = overlay;
    this.boxes = new Map();
    const stop = event => { event.preventDefault(); event.stopImmediatePropagation(); };
    const markedBox = event => event.target.closest?.('[data-mark-key]');
    const click = event => {
      const box = markedBox(event);
      if (box && !this.mode) { stop(event); return; } // Consume the first click so links cannot navigate before dblclick.
      if (!this.mode) return;
      stop(event);
      this.candidates = this.targetsAt(event.clientX, event.clientY);
      const el = preferredTarget(this.candidates, win.innerWidth, win.innerHeight);
      // Clicking an already marked element does not create duplicate observations.
      const index = this.value().marks.findIndex(mark => mark.page === pageKey(win.location) && mark.selector === selectorFor(el));
      if (index !== -1) { this.mode = false; this.render(); this.paint(); return; }
      this.select(el);
    };
    const doubleClick = event => {
      const box = markedBox(event);
      if (!box) { if (this.mode) stop(event); return; }
      stop(event);
      if (box.dataset.markKey === 'draft') this.cancel();
      else this.remove(Number(box.dataset.markKey));
    };
    const suppress = event => { if (this.mode || markedBox(event)) stop(event); };
    const escape = event => { if (event.key === 'Escape') this.cancel(); };
    // Window capture runs before the site's usual document/element listeners.
    win.addEventListener('click', click, true);
    win.addEventListener('dblclick', doubleClick, true);
    for (const type of ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'auxclick']) win.addEventListener(type, suppress, true);
    win.addEventListener('keydown', escape, true);
    document.addEventListener('keydown', escape);
    const paint = () => this.paint();
    win.addEventListener('scroll', paint, true);
    win.addEventListener('resize', paint);
    const refresh = setInterval(paint, 300);
    this.cleanup = () => {
      clearInterval(refresh); overlay.remove();
      win.removeEventListener('click', click, true);
      win.removeEventListener('dblclick', doubleClick, true);
      for (const type of ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'auxclick']) win.removeEventListener(type, suppress, true);
      win.removeEventListener('keydown', escape, true);
      document.removeEventListener('keydown', escape);
      win.removeEventListener('scroll', paint, true); win.removeEventListener('resize', paint);
    };
    this.render(); this.paint();
  }
  paint() {
    if (!this.overlay || this.siteId !== this.context().site?.id) return;
    const win = this.frame.contentWindow;
    try {
      const page = pageKey(win.location);
      this.overlay.style.pointerEvents = this.mode ? 'auto' : 'none';
      this.overlay.style.cursor = this.mode ? 'crosshair' : 'default';
      const present = new Set();
      const marks = this.value().marks.map((mark, i) => [String(i), mark]);
      if (this.draft) marks.push(['draft', this.draft]);
      for (const [key, mark] of marks) {
        if (mark.page !== page) continue;
        let el;
        try { el = win.document.querySelector(mark.selector); } catch { continue; }
        if (!el) continue;
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        present.add(key);
        let box = this.boxes.get(key);
        if (!box) {
          box = win.document.createElement('div');
          box.dataset.markKey = key;
          box.title = 'Double-click to remove this mark';
          const badge = win.document.createElement('span');
          badge.style.cssText = 'all:initial;position:absolute;top:0;left:0;background:#c2410c;color:white;padding:2px 6px;font:600 12px sans-serif;pointer-events:none;';
          box.append(badge);
          this.overlay.append(box);
          this.boxes.set(key, box);
        }
        box.firstChild.textContent = key === 'draft' ? 'Selected' : String(Number(key) + 1);
        // Keep nodes stable between paints: rebuilding them interrupts double-clicks.
        const area = r.width * r.height;
        const z = Math.max(1, 1000000 - Math.round(Math.min(area, 999999)));
        box.style.cssText = `all:initial;position:fixed;left:${r.left}px;top:${r.top}px;width:${r.width}px;height:${r.height}px;box-sizing:border-box;border:3px solid #c2410c;pointer-events:auto;cursor:pointer;background:transparent;z-index:${z};`;
      }
      for (const [key, box] of this.boxes) {
        if (!present.has(key)) { box.remove(); this.boxes.delete(key); }
      }
    } catch { /* Cross-origin navigation cannot be annotated. */ }
  }
  detach() { this.cleanup?.(); this.cleanup = null; this.overlay = null; this.boxes.clear(); this.mode = false; this.draft = null; }
}
