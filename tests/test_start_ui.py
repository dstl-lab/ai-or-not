"""Run the researcher setup logic against a small DOM harness."""
import subprocess
from pathlib import Path


def test_setup_requires_cohort_and_agentic_course_background():
    source = (Path(__file__).parents[1] / 'web' / 'start.js').read_text()
    source = source.replace('import { api } from "./api.js";', '').removesuffix('init();\n')
    harness = '''
const assert = require('node:assert/strict');
const requests = [], redirects = [];
const fields = {};
const element = () => ({value: '', checked: false, addEventListener() {}, focus() {}});
for (const id of ['start-form', 'participant', 'practice', 'error', 'start', 'cohort',
  'course-background', 'excluded-sites']) fields[id] = element();
let courseAnswer = null;
const document = {getElementById: id => fields[id],
 querySelector: () => courseAnswer,
 querySelectorAll: () => [{value: 'own-project'}]};
const window = {screen: {width: 1400, height: 900}, location: {replace: path => redirects.push(path)}};
const api = async (path, opts) => {requests.push([path, opts]); return {id: 'session-1'};};
'''
    checks = '''
(async () => {
 fields.participant.value = ' P01 ';
 await assert.rejects(start(), /group/i);
 assert.equal(requests.length, 0);
 fields.cohort.value = 'agentic_internship';
 await assert.rejects(start(), /DSC106/i);
 assert.equal(requests.length, 0);
 courseAnswer = {value: 'false'};
 await start();
 assert.equal(requests[0][1].body.cohort, 'agentic_internship');
 assert.equal(requests[0][1].body.dsc106_completed, false);
 assert.deepEqual(requests[0][1].body.excluded_site_ids, ['own-project']);
 assert.equal(requests[0][1].body.participant_id, 'P01');
 assert.deepEqual(redirects, ['/study/session-1']);
 fields.cohort.value = 'dsc106';
 await start();
 assert.equal(requests[1][1].body.dsc106_completed, true);
 fields.cohort.value = 'lower_division';
 await start();
 assert.equal(requests[2][1].body.dsc106_completed, false);
})().catch(err => {console.error(err); process.exitCode = 1;});
'''
    subprocess.run(['node', '-e', harness + source + checks], check=True)
