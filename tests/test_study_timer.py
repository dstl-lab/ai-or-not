"""Exercise the real browser timer without a browser or extra dependencies."""
import subprocess
from pathlib import Path


def test_completion_stops_timer_and_prevents_restart():
    source = (Path(__file__).parents[1] / "web" / "study.js").read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
let clock = 0, reports = [], interval, events = {};
const element = {hidden: false, addEventListener() {}};
const document = {visibilityState: 'visible', getElementById: () => element,
  addEventListener: (name, fn) => events[name] = fn};
const window = {addEventListener() {}};
const location = {pathname: '/study/test'};
const performance = {now: () => clock};
const navigator = {sendBeacon: (...args) => reports.push(args)};
const fetch = (...args) => { reports.push(args); return Promise.resolve(); };
const setInterval = fn => { interval = fn; };
'''
    checks = '''
state.sites = [{id: 'alpha'}];
wireEvents();
timer.start();
clock = 10000;
showScreen('done');
assert.equal(reports.length, 1);
assert.equal(JSON.parse(reports[0][1].body).seconds, 10);
clock = 70000;
interval();
events.visibilitychange();
clock = 130000;
interval();
assert.equal(reports.length, 1);
assert.equal(timer.since, null);
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)


def test_close_warning_covers_queued_and_in_flight_saves():
    source = (Path(__file__).parents[1] / "web" / "study.js").read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
const events = {}, requests = [];
const element = {addEventListener() {}, classList: {toggle() {}}};
const document = {getElementById: () => element, addEventListener() {}};
const window = {addEventListener: (name, fn) => events[name] = fn};
const location = {pathname: '/study/test'};
const setInterval = () => {};
const api = () => new Promise(resolve => requests.push(resolve));
'''
    checks = '''
(async () => {
 wireEvents();
 state.questions = [{id: 'confidence'}];
 state.answers.alpha = {confidence: 4};
 const warns = () => {
   let prevented = false;
   events.beforeunload({preventDefault() {prevented = true;}});
   return prevented;
 };
 saver.mark('alpha');
 assert.equal(warns(), true);
 const first = saver.flush();
 assert.equal(warns(), true); // queued, before the request starts
 await Promise.resolve();
 assert.equal(requests.length, 1);
 assert.equal(warns(), true); // request still pending
 state.answers.alpha.confidence = 5;
 saver.mark('alpha');
 const second = saver.flush();
 requests[0]();
 await first;
 assert.equal(warns(), true); // second save is still queued or in flight
 await Promise.resolve();
 assert.equal(requests.length, 2);
 requests[1]();
 await second;
 assert.equal(warns(), false);
})().catch(err => {console.error(err); process.exitCode = 1;});
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)


def test_followup_uses_its_own_sites_and_preserves_primary_answers():
    source = (Path(__file__).parents[1] / "web" / "study.js").read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
const element = {textContent: '', hidden: false};
const document = {getElementById: () => element};
const location = {pathname: '/study/test'};
'''
    checks = '''
const primary = [{id: 'alpha', completed: true}, {id: 'beta', completed: true}];
const followups = [{id: 'beta', completed: false}];
const answers = {alpha: {ai_appearance: 2}, beta: {ai_appearance: 4}};
applySession({phase: 'followup', sites: primary, followup_sites: followups,
  questions: [{id: 'cues'}], review_questions: [{id: 'ai_appearance'}],
  followup_questions: [{id: 'cues'}], answers});
assert.deepEqual(state.sites, followups);
assert.equal(state.phase, 'followup');
assert.equal(state.byId.ai_appearance, undefined);
assert.equal(state.questions[0].id, 'cues');
assert.equal(answersFor('beta').ai_appearance, 4);
applySession({phase: 'review', sites: primary, followup_sites: followups,
  questions: [{id: 'ai_appearance'}], answers});
assert.deepEqual(state.sites, primary);
assert.equal(state.phase, 'review');
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)


def test_last_review_starts_followup_before_finishing():
    source = (Path(__file__).parents[1] / "web" / "study.js").read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
const calls = [];
const element = {addEventListener() {}, textContent: '', hidden: false,
  classList: {toggle() {}}, setAttribute() {}, querySelectorAll: () => []};
const document = {getElementById: () => element};
const location = {pathname: '/study/test'};
const confirm = () => true;
const data = {phase: 'followup', sites: [{id: 'alpha', completed: true}],
 followup_sites: [{id: 'alpha', completed: false}], questions: [{id: 'cues'}],
 followup_questions: [{id: 'cues'}], answers: {alpha: {ai_appearance: 4}}};
const api = async (path, opts = {}) => {
 calls.push([path, opts]);
 return path.endsWith('/complete') ? {sites: data.sites} : data;
};
'''
    checks = '''
(async () => {
 state.phase = 'review';
 state.sites = [{id: 'alpha', completed: false}];
 state.followupSites = [{id: 'alpha', completed: false}];
 state.questions = [{id: 'ai_appearance'}];
 state.answers = {alpha: {ai_appearance: 4}};
 saver.flush = async () => {};
 goTo = async index => {state.index = index;};
 await onNext();
 assert.equal(calls.some(([path]) => path.endsWith('/followup')), true);
 assert.equal(calls.some(([path]) => path.endsWith('/finish')), false);
 assert.equal(state.phase, 'followup');
 assert.equal(state.questions[0].id, 'cues');
})().catch(err => {console.error(err); process.exitCode = 1;});
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)


def test_rejected_save_stays_pending_and_can_be_retried():
    source = (Path(__file__).parents[1] / "web" / "study.js").read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
const element = {textContent: '', classList: {toggle() {}}};
const document = {getElementById: () => element};
const location = {pathname: '/study/test'};
let rejected = true;
const api = async () => {if (rejected) throw Object.assign(new Error('Try again'), {status: 422});};
'''
    checks = '''
(async () => {
 state.questions = [{id: 'ai_appearance'}];
 state.answers = {alpha: {ai_appearance: 4}};
 saver.mark('alpha');
 await assert.rejects(saver.flush(), /Try again/);
 assert.equal(saver.busy, true);
 rejected = false;
 await saver.flush();
 assert.equal(saver.busy, false);
})().catch(err => {console.error(err); process.exitCode = 1;});
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)


def test_next_cannot_submit_twice_while_a_save_is_pending():
    source = (Path(__file__).parents[1] / "web" / "study.js").read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
const element = {textContent: '', hidden: false, classList: {toggle() {}}};
const document = {getElementById: () => element};
const location = {pathname: '/study/test'};
const confirm = () => true;
let saves = 0, release;
const api = async () => ({sites: state.sites});
'''
    checks = '''
(async () => {
 state.questions = [{id: 'ai_appearance'}];
 state.sites = [{id: 'alpha'}, {id: 'beta'}];
 state.answers = {alpha: {ai_appearance: 4}};
 saver.flush = () => {saves++; return new Promise(resolve => release = resolve);};
 goTo = async index => {state.index = index;};
 const first = onNext();
 const second = onNext();
 assert.equal(saves, 1);
 release();
 await first;
 await second;
 assert.equal(state.index, 1);
})().catch(err => {console.error(err); process.exitCode = 1;});
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)


def test_unviewable_page_does_not_require_an_invented_appearance_rating():
    source = (Path(__file__).parents[1] / 'web' / 'study.js').read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
const document = {getElementById: () => ({})};
const location = {pathname: '/study/test'};
'''
    checks = '''
state.questions = [{id: 'ai_appearance', required_unless: {question_id: 'technical_issue', value: 'unable'}},
 {id: 'technical_issue'}];
assert.deepEqual(missingIds({technical_issue: 'unable'}), []);
assert.deepEqual(missingIds({technical_issue: 'no'}), ['ai_appearance']);
assert.deepEqual(missingIds({ai_appearance: 3}), ['technical_issue']);
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)


def test_multi_selection_limit_leaves_selected_options_available_to_untick():
    source = (Path(__file__).parents[1] / 'web' / 'study.js').read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
const document = {getElementById: () => ({})};
const location = {pathname: '/study/test'};
'''
    checks = '''
const inputs = [{checked: true}, {checked: true}, {checked: true}, {checked: false}];
const hint = {};
const container = {querySelectorAll: () => inputs, querySelector: () => hint};
const question = {type: 'multi', max_selected: 3};
updateSelectionLimit(question, container, ['writing', 'charts', 'layout']);
assert.deepEqual(inputs.map(input => input.disabled), [false, false, false, true]);
assert.equal(hint.textContent, '3 of 3 selected.');
inputs[1].checked = false;
updateSelectionLimit(question, container, ['writing', 'layout']);
assert.deepEqual(inputs.map(input => input.disabled), [false, false, false, false]);
assert.equal(hint.textContent, '2 of 3 selected.');
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)


def test_text_answer_is_saved_on_input_without_waiting_for_blur():
    source = (Path(__file__).parents[1] / 'web' / 'study.js').read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
const events = {}, requests = [];
const element = {textContent: '', addEventListener: (name, fn) => events[name] = fn,
 querySelectorAll: () => [], querySelector: () => null, classList: {toggle() {}}, setAttribute() {}};
const document = {getElementById: () => element, addEventListener() {}};
const window = {addEventListener() {}};
const location = {pathname: '/study/test'};
const setInterval = () => {};
const api = async (path, options) => requests.push([path, options]);
'''
    checks = '''
(async () => {
 wireEvents();
 const question = {id: 'example', type: 'text', required: false};
 state.questions = [question];
 state.byId = {example: question};
 state.sites = [{id: 'alpha'}];
 const fieldset = {dataset: {qid: 'example'}, querySelector: () => ({value: 'The chart labels'})};
 events.input({target: {tagName: 'TEXTAREA', closest: () => fieldset}});
 await saver.flush();
 assert.equal(requests[0][1].body.answers.example, 'The chart labels');
})().catch(err => {console.error(err); process.exitCode = 1;});
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)


def test_scale_options_show_each_caption_and_accessible_numeric_rating():
    source = (Path(__file__).parents[1] / 'web' / 'study.js').read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { AnnotationTool } from "./annotations.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
class Element {
 constructor(tag) {this.tagName = tag; this.children = []; this.attributes = {}; this.style = {setProperty() {}};}
 append(...nodes) {this.children.push(...nodes);}
 replaceChildren(...nodes) {this.children = nodes;}
 setAttribute(name, value) {this.attributes[name] = value;}
 get firstChild() {return this.children[0];}
 get lastChild() {return this.children.at(-1);}
 set innerHTML(value) {this.children = [new Element('span'), new Element('span')];}
}
const document = {getElementById: () => new Element('div'), createElement: tag => new Element(tag)};
const location = {pathname: '/study/test'};
'''
    checks = '''
const labels = ['Not at all', 'Slightly', 'Moderately', 'Very', 'Extremely'];
const question = {id: 'ai_appearance', type: 'scale', min: 1, max: 5,
 options: labels.map((label, i) => ({value: String(i + 1), label}))};
const choices = renderInputs(question, {ai_appearance: 3}).firstChild.children;
assert.equal(choices.length, 5);
for (let i = 0; i < 5; i++) {
 assert.equal(choices[i].firstChild.attributes['aria-label'], `${i + 1} — ${labels[i]}`);
 assert.equal(choices[i].lastChild.lastChild.textContent, labels[i]);
}
assert.equal(choices[2].firstChild.checked, true);
const fallback = renderInputs({id: 'confidence', type: 'scale', min: 1, max: 5}, {}).firstChild;
assert.deepEqual(fallback.children.map(choice => choice.firstChild.value), ['1', '2', '3', '4', '5']);
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)
