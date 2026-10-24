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
      <button type="button" class="mark-toggle" aria-pressed="${this.mode}" ${!ready || value.marks.length >= 3 || this.draft ? 'disabled' : ''}>${this.mode ? 'Stop marking' : 'Mark an element'}</button>
      <p class="mark-help">${this.mode ? 'Marking mode: clicks select elements instead of opening links. Press Escape to stop.' : 'Exploring mode: the website works normally. Marking is optional.'}</p>
      ${this.draft ? `<div class="mark-draft"><strong>Selected: ${h(this.draft.label)}</strong>
        <p>What about this element looks AI-designed?</p>
        <div class="mark-reasons">${Object.entries(reasons).map(([key, label]) => `<button type="button" data-reason="${key}">${h(label)}</button>`).join('')}</div>
        <button type="button" data-cancel>Cancel selection</button></div>` : ''}
      <ol class="mark-list">${value.marks.map((mark, i) => `<li><span><strong>${i + 1}. ${h(mark.label)}</strong><br>${h(reasons[mark.reason])}</span><button type="button" data-remove="${i}" aria-label="Remove mark ${i + 1}">Remove</button></li>`).join('')}</ol>
      <label class="mark-none"><input type="checkbox" ${value.none ? 'checked' : ''} ${!ready || value.marks.length || this.draft ? 'disabled' : ''}> Nothing specific stood out</label>
      <p class="mark-save" role="status">${h(this.error || (this.dirty.size || this.pendingSaves ? 'Saving marks…' : ''))}</p>
      ${this.error ? '<button type="button" data-retry>Retry saving</button>' : ''}`;
    host.querySelector('.mark-toggle').onclick = () => { this.mode = !this.mode; this.render(); this.paint(); };
    host.querySelector('[data-cancel]')?.addEventListener('click', () => this.cancel());
    host.querySelectorAll('[data-reason]').forEach(button => button.onclick = () => {
      this.value().marks.push({...this.draft, reason: button.dataset.reason});
      this.value().none = false;
      this.draft = null;
      this.save();
      this.paint();
    });
    host.querySelectorAll('[data-remove]').forEach(button => button.onclick = () => {
      this.value().marks.splice(Number(button.dataset.remove), 1);
      this.save(); this.paint();
    });
    host.querySelector('.mark-none input').onchange = e => { this.value().none = e.target.checked; this.save(); };
    host.querySelector('[data-retry]')?.addEventListener('click', () => this.save());
  }
  cancel() { this.mode = false; this.draft = null; this.render(); this.paint(); }
  save() {
    this.dirty.add(this.context().site.id);
    this.flush().catch(() => {});
    this.render();
  }
  async flush() {
    if (this.draft) throw new Error('Choose a reason for the selected element, or cancel the selection.');
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
    const click = event => {
      if (!this.mode) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      // A label inside a button/link belongs to the control; canvas remains one selectable object.
      // A transparent selection layer also captures clicks over embedded frames.
      overlay.style.pointerEvents = 'none';
      const target = doc.elementFromPoint(event.clientX, event.clientY);
      overlay.style.pointerEvents = 'auto';
      let el = target?.closest?.('button,a,label') || target;
      if (!el?.getBoundingClientRect) return;
      const rect = el.getBoundingClientRect();
      const style = win.getComputedStyle(el);
      const tag = el.localName;
      const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ');
      const styles = {};
      for (const key of ['background-color', 'background-image', 'color', 'font-family', 'font-size', 'font-weight', 'border-radius', 'box-shadow', 'display', 'gap']) {
        styles[key] = style.getPropertyValue(key).slice(0, 300);
      }
      this.draft = {
        page: pageKey(win.location),
        selector: selectorFor(el), tag, label: `${tag}: ${text.slice(0, 100) || 'visual element'}`,
        rect: [Math.max(0, rect.x + win.scrollX), Math.max(0, rect.y + win.scrollY), rect.width, rect.height],
        viewport: [win.innerWidth, win.innerHeight], styles,
        ai_judgment: this.context().answers.ai_generated,
      };
      this.mode = false;
      this.render(); this.paint();
      document.querySelector('[data-reason]')?.focus();
    };
    const suppress = event => { if (this.mode) { event.preventDefault(); event.stopImmediatePropagation(); } };
    const escape = event => { if (event.key === 'Escape') this.cancel(); };
    // Window capture runs before the site's usual document/element listeners.
    win.addEventListener('click', click, true);
    for (const type of ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'dblclick', 'auxclick']) win.addEventListener(type, suppress, true);
    win.addEventListener('keydown', escape, true);
    document.addEventListener('keydown', escape);
    const paint = () => this.paint();
    win.addEventListener('scroll', paint, true);
    win.addEventListener('resize', paint);
    const refresh = setInterval(paint, 300);
    this.cleanup = () => {
      clearInterval(refresh); overlay.remove();
      win.removeEventListener('click', click, true);
      for (const type of ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'dblclick', 'auxclick']) win.removeEventListener(type, suppress, true);
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
      this.overlay.replaceChildren();
      const marks = [...this.value().marks, ...(this.draft ? [this.draft] : [])];
      marks.forEach((mark, i) => {
        if (mark.page !== page) return;
        const el = win.document.querySelector(mark.selector);
        if (!el) return;
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height) return;
        const box = win.document.createElement('div');
        box.style.cssText = `position:fixed;left:${r.left}px;top:${r.top}px;width:${r.width}px;height:${r.height}px;box-sizing:border-box;border:3px solid #c2410c;pointer-events:none;background:transparent;`;
        const badge = win.document.createElement('span');
        badge.textContent = String(i + 1);
        badge.style.cssText = 'position:absolute;top:0;left:0;background:#c2410c;color:white;padding:2px 6px;font:600 12px sans-serif;';
        box.append(badge); this.overlay.append(box);
      });
    } catch { /* Cross-origin navigation cannot be annotated. */ }
  }
  detach() { this.cleanup?.(); this.cleanup = null; this.overlay = null; this.mode = false; this.draft = null; }
}
