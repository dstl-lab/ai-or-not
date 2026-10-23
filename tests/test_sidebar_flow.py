"""Exercise sidebar task order and disclosure behavior using the real browser code."""
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
HARNESS = r"""
const assert = require('node:assert/strict');
class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {};
    this.attributes = {}; this.style = {setProperty() {}}; this.events = {};
    this.className = ''; this.open = false; this.hidden = false; this.disabled = false;
    this.classList = {toggle: (name, force) => {
      const values = new Set(this.className.split(/\s+/).filter(Boolean));
      const add = force ?? !values.has(name);
      if (add) values.add(name); else values.delete(name);
      this.className = [...values].join(' ');
    }};
  }
  append(...nodes) {for (const node of nodes) {node.parentElement = this; this.children.push(node);}}
  replaceChildren(...nodes) {this.children = []; this._text = ''; this.append(...nodes);}
  replaceWith(node) {
    const parent = this.parentElement;
    parent.children[parent.children.indexOf(this)] = node; node.parentElement = parent;
  }
  set textContent(value) {this._text = String(value); this.children = [];}
  get textContent() {return (this._text || '') + this.children.map(child => child.textContent).join('');}
  set innerHTML(value) {this.replaceChildren(...[...value.matchAll(/<span[^>]*>(.*?)<\/span>/g)].map(match => {
    const node = new Element('span'); node.textContent = match[1]; return node;
  }));}
  get firstChild() {return this.children[0];}
  get lastChild() {return this.children.at(-1);}
  setAttribute(name, value) {this.attributes[name] = String(value);}
  getAttribute(name) {return this.attributes[name] ?? null;}
  addEventListener(name, fn) {this.events[name] = fn;}
  matches(selector) {
    if (selector.includes(',')) return selector.split(',').some(item => this.matches(item.trim()));
    if (selector.includes(':not(:disabled)') && this.disabled) return false;
    selector = selector.replace(':not(:disabled)', '');
    if (selector.includes(':checked') && !this.checked) return false;
    selector = selector.replace(':checked', '');
    const attr = selector.match(/\[([^=\]]+)(?:="([^"]*)")?\]/);
    if (attr) {
      const value = attr[1] === 'data-qid' ? this.dataset.qid : this[attr[1]] ?? this.attributes[attr[1]];
      if (value == null || (attr[2] !== undefined && String(value) !== attr[2])) return false;
      selector = selector.replace(attr[0], '');
    }
    const [tag, ...classes] = selector.split('.');
    return (!tag || this.tagName === tag.toUpperCase()) && classes.every(name => this.className.split(/\s+/).includes(name));
  }
  querySelectorAll(selector) {
    return this.children.flatMap(child => [...(child.matches(selector) ? [child] : []), ...child.querySelectorAll(selector)]);
  }
  querySelector(selector) {return this.querySelectorAll(selector)[0] || null;}
  closest(selector) {return this.matches(selector) ? this : this.parentElement?.closest(selector) || null;}
  scrollIntoView() {
    assert.ok(!this.closest('details') || this.closest('details').open, 'reveal before scrolling');
    this.scrolled = true;
  }
  focus() {document.activeElement = this;}
  remove() {}
}
const elements = new Map();
const document = {visibilityState: 'visible', activeElement: null,
  createElement: tag => new Element(tag),
  getElementById: id => {
    if (!elements.has(id)) elements.set(id, new Element(id === 'website-navigation' ? 'details' : 'div'));
    return elements.get(id);
  }, addEventListener() {}};
const window = {addEventListener() {}};
const location = {pathname: '/study/test'};
const performance = {now: () => 0};
const setInterval = () => {};
const confirm = () => false;
let calls = [], annotationOptions, sessionData;
const api = async (...args) => {calls.push(args); return sessionData;};
class AnnotationTool {
  constructor(options) {annotationOptions = options; this.draft = null; this.armed = false;}
  render() {return new Element('div');}
  stopSelecting() {this.armed = false;}
}
"""


def run_sidebar(checks):
    source = (ROOT / "web" / "study.js").read_text()
    source = source.replace('import { api } from "./api.js";', '').replace(
        'import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    questions = json.loads((ROOT / "config" / "questions.json").read_text())["questions"]
    legacy = json.loads((ROOT / "tests" / "fixtures" / "questions-legacy.json").read_text())["questions"]
    setup = f"""
const questions = {json.dumps(questions)};
const legacyQuestions = {json.dumps(legacy)};
function setup(phase = 'review', answers = {{}}) {{
  state.phase = phase; state.sites = [{{id: 'alpha', label: 'Alpha', unlocked: true}}, {{id: 'beta'}}];
  state.index = 0; state.showMissing = false; state.answers = {{alpha: answers}};
  state.questions = questions.filter(q => (q.phase || 'review') === phase);
  state.byId = Object.fromEntries(state.questions.map(q => [q.id, q]));
  annotationTool = new AnnotationTool({{}}); saver.mark = () => {{}};
  renderQuestions(); updateProgress();
}}
"""
    result = subprocess.run(["node", "-e", HARNESS + source + setup + checks], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_review_checks_reveal_after_rating_and_keep_question_content():
    run_sidebar("""
setup();
const primary = els.questions.querySelector('fieldset[data-qid="ai_appearance"]');
const checks = els.questions.querySelector('details.review-checks');
assert.ok(checks, 'context questions must have a Review checks disclosure');
assert.equal(els.questions.firstChild, primary);
assert.equal(checks.querySelector('summary').textContent, 'Review checks 2 remaining');
assert.equal(checks.open, false);
assert.deepEqual(checks.querySelectorAll('fieldset').map(node => node.dataset.qid), ['seen_before', 'technical_issue']);
for (const question of state.questions) {
  const fieldset = els.questions.querySelector(`fieldset[data-qid="${question.id}"]`);
  assert.equal(fieldset.querySelector('legend').textContent, question.prompt);
}
assert.deepEqual(state.answers.alpha, {});
const chosen = primary.querySelector('input'); chosen.focus();
setAnswer(state.byId.ai_appearance, 3);
assert.equal(checks.open, true);
assert.equal(document.activeElement, chosen, 'revealing checks must not steal rating focus');
setAnswer(state.byId.seen_before, 'no'); setAnswer(state.byId.technical_issue, 'no');
assert.equal(checks.querySelector('.section-meta').textContent, 'Complete');
assert.equal(els.next.textContent, 'Next website');
setup('review', {seen_before: 'no'});
assert.equal(els.questions.querySelector('details.review-checks').open, true);
state.questions = legacyQuestions.map(q => q.options_from ? {...q, options: legacyQuestions.find(x => x.id === q.options_from).options} : q);
renderQuestions();
assert.deepEqual(els.questions.querySelectorAll('fieldset').map(node => node.dataset.qid), legacyQuestions.map(q => q.id));
""")


def test_validation_reveals_missing_checks_before_scrolling_and_blocks_navigation():
    run_sidebar("""
(async () => {
  setup('review', {ai_appearance: 3});
  const checks = els.questions.querySelector('details.review-checks');
  assert.equal(els.next.textContent, 'Complete review checks');
  assert.equal(els.next.disabled, false, 'the guidance action must remain enabled');
  assert.notEqual(els.next.getAttribute('aria-disabled'), 'true', 'missing-answer guidance is actionable');
  checks.open = false;
  await onNext();
  assert.equal(checks.open, true);
  const missing = els.questions.querySelector('fieldset[data-qid="seen_before"]');
  assert.equal(missing.scrolled, true);
  assert.equal(document.activeElement, missing.querySelector('input'));
  assert.equal(calls.length, 0, 'missing answers cannot submit');
  checks.open = false; state.sites[0].completed = true;
  await goTo(1);
  assert.equal(state.index, 0);
  assert.equal(checks.open, true, 'leaving an incomplete completed page must reveal what is missing');
  wireEvents(); checks.open = false;
  elements.get('review-help').events.click();
  assert.equal(checks.open, true);
  const technical = els.questions.querySelector('fieldset[data-qid="technical_issue"]');
  assert.equal(technical.scrolled, true);
  assert.equal(document.activeElement, technical.querySelector('input'));
})().catch(err => {console.error(err); process.exitCode = 1;});
""")


def test_unavailable_page_checks_are_accessible_without_forcing_a_rating():
    run_sidebar("""
setup();
assert.equal(els.next.textContent, 'Choose a rating');
assert.equal(els.next.disabled, false);
assert.notEqual(els.next.getAttribute('aria-disabled'), 'true');
assert.ok(els.questions.querySelector('details.review-checks').querySelector('summary'));
setAnswer(state.byId.technical_issue, 'unable');
setAnswer(state.byId.seen_before, 'no');
assert.deepEqual(missingIds(state.answers.alpha), []);
assert.equal(state.answers.alpha.ai_appearance, undefined);
assert.equal(els.next.textContent, 'Next website');
""")


def test_followup_keeps_required_cues_before_optional_saved_notes_and_refreshes_count():
    run_sidebar("""
(async () => {
  const answers = {ai_appearance: 4, annotations: [{id: 'one', note: 'A chart'}]};
  setup('followup', answers);
  assert.equal(els.questions.firstChild.dataset.qid, 'cues', 'required cues must precede optional note history');
  const notes = els.questions.querySelector('details.review-notes');
  assert.ok(notes);
  assert.equal(notes.open, false, 'saved notes must not expand over the required cues');
  assert.equal(notes.querySelector('summary').textContent, 'Page notes 1 note · Optional');
  assert.equal(els.next.textContent, 'Choose up to 3 cues');
  assert.match(els.rating.textContent, /4 out of 5/);
  assert.equal(els.questions.querySelector('fieldset[data-qid="ai_appearance"]'), null);
  sessionData = {phase: 'followup', sites: state.sites, followup_sites: state.sites,
    followup_questions: state.questions, answers: {alpha: answers}, session: {}};
  goTo = async index => {state.index = index; renderQuestions(); updateProgress();};
  await init();
  const savedNotes = els.questions.querySelector('details.review-notes');
  savedNotes.open = true;
  answers.annotations.push({id: 'two', note: 'The heading'});
  annotationOptions.refresh();
  assert.equal(savedNotes.open, true);
  assert.equal(savedNotes.querySelector('.section-meta').textContent, '2 notes · Optional');
  savedNotes.open = false; annotationTool.armed = true;
  annotationOptions.refresh();
  assert.equal(savedNotes.open, true, 'active selection keeps notes visible');
  savedNotes.open = false; savedNotes.events.toggle?.();
  assert.equal(savedNotes.open, true, 'collapsing notes cannot hide active selection controls');
  savedNotes.open = false; annotationTool.armed = false; annotationTool.draft = {note: ''};
  els.layout.classList.toggle('collapsed', true);
  annotationOptions.refresh();
  assert.equal(els.layout.className.includes('collapsed'), false, 'a new note editor must be visible even if questions were hidden');
  assert.equal(savedNotes.open, true, 'active draft keeps notes visible');
  savedNotes.open = false; savedNotes.events.toggle?.();
  assert.equal(savedNotes.open, true, 'collapsing notes cannot hide Save or Cancel');
  assert.equal(answers.ai_appearance, 4);
})().catch(err => {console.error(err); process.exitCode = 1;});
""")


def test_changing_websites_ends_selection_before_rendering_new_optional_notes():
    run_sidebar("""
(async () => {
  setup('followup');
  annotationTool.armed = true;
  saver.flush = async () => {}; loadFrame = () => {};
  await goTo(1);
  assert.equal(annotationTool.armed, false);
  assert.equal(els.questions.querySelector('details.review-notes').open, false);
})().catch(err => {console.error(err); process.exitCode = 1;});
""")


def test_selecting_a_website_collapses_website_navigation():
    run_sidebar("""
(async () => {
  setup();
  const navigation = document.getElementById('website-navigation');
  navigation.open = true;
  saver.flush = async () => {}; loadFrame = () => {};
  await goTo(0);
  assert.equal(navigation.open, false);
})().catch(err => {console.error(err); process.exitCode = 1;});
""")



def test_page_notes_shortcut_is_available_only_with_notes_and_reveals_them():
    run_sidebar("""
setup();
assert.equal(els.notesLink.hidden, true);
setup('followup', {annotations: [{id: 'one'}, {id: 'two'}]});
assert.equal(els.notesLink.hidden, false);
assert.equal(els.notesCount.textContent, '2');
const notes = els.questions.querySelector('.review-notes');
assert.equal(notes.open, false);
wireEvents();
els.notesLink.events.click();
assert.equal(notes.open, true);
assert.equal(notes.querySelector('fieldset').scrolled, true);
setAnswer(state.byId.annotations, [{id: 'one'}]);
assert.equal(els.notesCount.textContent, '1');
assert.match(els.notesLink.getAttribute('aria-label'), /1 saved note/);
assert.equal(state.answers.alpha.annotations.length, 1);
""")


def test_unsaved_note_status_wins_over_saved_answers_but_not_save_failures():
    run_sidebar("""
setup('followup');
setStatus('All answers saved');
assert.equal(els.status.textContent, 'All answers saved');
annotationTool.draft = {note: ''};
updateProgress();
assert.match(els.status.textContent, /Note not saved/);
assert.equal(els.next.textContent, 'Return to note');
setStatus('All answers saved');
assert.match(els.status.textContent, /Note not saved/, 'a background save must not imply the note was saved');
setStatus('Could not save answers. Retrying…', true);
assert.equal(els.status.textContent, 'Could not save answers. Retrying…');
setStatus('All answers saved');
warn('Return to the assigned webpage.');
assert.equal(els.status.textContent, 'Return to the assigned webpage.');
warn(''); annotationTool.draft = null; annotationTool.armed = true;
updateProgress();
assert.match(els.status.textContent, /Select a detail/);
annotationTool.armed = false; updateProgress();
assert.equal(els.status.textContent, 'All answers saved');
""")


def test_blocked_navigation_reopens_and_focuses_the_unsaved_note():
    run_sidebar("""
(async () => {
  setup('followup');
  annotationTool.draft = {note: 'Keep my draft'};
  updateProgress();
  const notes = els.questions.querySelector('.review-notes');
  const fieldset = notes.querySelector('fieldset');
  const input = new Element('textarea'); fieldset.append(input);
  notes.open = false; els.layout.classList.toggle('collapsed', true);
  await onNext();
  assert.equal(notes.open, true);
  assert.equal(fieldset.scrolled, true);
  assert.equal(document.activeElement, input);
  assert.match(els.status.textContent, /Note not saved/, 'returning to the editor is guidance, not an error');
  assert.equal(els.layout.className.includes('collapsed'), false);
  assert.equal(state.index, 0);
  notes.open = false; document.activeElement = null;
  await goTo(1);
  assert.equal(notes.open, true);
  assert.equal(document.activeElement, input);
  assert.equal(state.index, 0);
  assert.equal(calls.length, 0, 'a draft must not be submitted or leave this website');
  assert.equal(annotationTool.draft.note, 'Keep my draft');
})().catch(err => {console.error(err); process.exitCode = 1;});
""")


def test_collapsing_and_expanding_moves_focus_to_visible_controls():
    run_sidebar("""
setup(); wireEvents();
elements.get('collapse').events.click();
assert.equal(els.layout.className.includes('collapsed'), true);
assert.equal(document.activeElement, elements.get('expand'));
elements.get('expand').events.click();
assert.equal(els.layout.className.includes('collapsed'), false);
assert.equal(document.activeElement, elements.get('collapse'));
elements.get('collapse').events.click();
elements.get('expand-label').events.click();
assert.equal(document.activeElement, elements.get('collapse'));
""")


def test_changing_websites_lands_focus_at_the_new_panel_heading():
    run_sidebar("""
(async () => {
  setup(); saver.flush = async () => {}; loadFrame = () => {};
  await goTo(1);
  assert.equal(state.index, 1);
  assert.equal(document.activeElement, els.title);
})().catch(err => {console.error(err); process.exitCode = 1;});
""")
