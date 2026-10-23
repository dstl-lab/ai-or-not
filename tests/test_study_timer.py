"""Exercise the real browser timer without a browser or extra dependencies."""
import subprocess
from pathlib import Path


def test_completion_stops_timer_and_prevents_restart():
    source = (Path(__file__).parents[1] / "web" / "study.js").read_text()
    source = source.replace('import { api } from "./api.js";', '').removesuffix('init();\n')
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
    source = source.replace('import { api } from "./api.js";', '').removesuffix('init();\n')
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
