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
