"""Run the researcher setup logic against a small DOM harness."""
import subprocess
from pathlib import Path


def test_setup_requires_cohort_and_agentic_course_background():
    source = (Path(__file__).parents[1] / 'web' / 'start.js').read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { confirmAction } from "./confirm.js";', '').removesuffix('init();\n')
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



def run_submit_checks(checks):
    source = (Path(__file__).parents[1] / 'web' / 'start.js').read_text()
    source = source.replace('import { api } from "./api.js";', '').replace('import { confirmAction } from "./confirm.js";', '').removesuffix('init();\n')
    harness = r"""
const assert = require('node:assert/strict');
const requests = [], redirects = [], confirmations = [], fields = {};
let activeElement, apiImpl = async () => ({id:'session-1'}), confirmImpl = async () => false;
for (const id of ['start-form','participant','practice','error','start','cohort','course-background','excluded-sites']) {
  fields[id] = {value:'',checked:false,disabled:false,listeners:{},
    addEventListener(type, listener){this.listeners[type]=listener},
    focus(){assert.equal(this.disabled,false); activeElement=this}};
}
const document = {getElementById:id=>fields[id],querySelector:()=>null,querySelectorAll:()=>[]};
const window = {screen:{width:1400,height:900},location:{replace:path=>redirects.push(path)}};
const api = async (path, options) => {requests.push([path,options]); return apiImpl(path,options)};
const confirmAction = async options => {confirmations.push(options); return confirmImpl(options)};
const confirm = () => false;
const duplicate = Object.assign(new Error('This participant already has a session.'),{status:409});
const submit = () => fields['start-form'].listeners.submit({preventDefault(){}});
"""
    setup = r"""
fields.participant.value='P01';
fields.cohort.value='dsc106';
const deadline=setTimeout(()=>{console.error('Setup submission did not finish');process.exitCode=1},1000);
(async()=>{
"""
    end = r"""
})().catch(error=>{console.error(error);process.exitCode=1}).finally(()=>clearTimeout(deadline));
"""
    subprocess.run(['node', '-e', harness + source + setup + checks + end], check=True)


def test_duplicate_cancel_keeps_setup_and_restores_start_focus():
    run_submit_checks(r"""
apiImpl=async()=>{throw duplicate};
await submit();
assert.equal(requests.length,1);
assert.equal(confirmations.length,1);
assert.equal(confirmations[0].message,duplicate.message);
assert.deepEqual(redirects,[]);
assert.equal(fields.start.disabled,false);
assert.equal(activeElement,fields.start);
assert.equal(fields.error.hidden,true);
""")


def test_duplicate_acceptance_retries_once_with_explicit_permission():
    run_submit_checks(r"""
apiImpl=async()=>{if(requests.length===1)throw duplicate;return {id:'second-session'}};
confirmImpl=async()=>true;
await submit();
assert.deepEqual(requests.map(([,options])=>options.body.allow_duplicate),[false,true]);
assert.deepEqual(redirects,['/study/second-session']);
assert.equal(fields.start.disabled,false);
""")


def test_setup_and_duplicate_retry_errors_reset_button_without_stealing_validation_focus():
    run_submit_checks(r"""
fields.cohort.value='';
await submit();
assert.match(fields.error.textContent,/background group/);
assert.equal(activeElement,fields.participant);
assert.equal(fields.start.disabled,false);
fields.cohort.value='dsc106';
apiImpl=async()=>{throw new Error('Network unavailable')};
await submit();
assert.equal(fields.error.textContent,'Network unavailable');
assert.equal(fields.start.disabled,false);
apiImpl=async()=>{if(requests.length===2)throw duplicate;throw new Error('Retry failed')};
confirmImpl=async()=>true;
await submit();
assert.equal(fields.error.textContent,'Retry failed');
assert.equal(fields.start.disabled,false);
assert.equal(activeElement,fields.start);
""")


def test_repeated_submits_are_ignored_while_request_or_duplicate_dialog_is_pending():
    run_submit_checks(r"""
let finishRequest;
apiImpl=()=>new Promise(resolve=>finishRequest=resolve);
const request=submit();
assert.equal(fields.start.disabled,true);
const repeatedRequest=submit();
assert.equal(requests.length,1);
await repeatedRequest;
finishRequest({id:'session-1'});
await request;
let decide, opened;
const dialogOpened=new Promise(resolve=>opened=resolve);
apiImpl=async()=>{throw duplicate};
confirmImpl=()=>{opened();return new Promise(resolve=>decide=resolve)};
const duplicateRequest=submit();
await dialogOpened;
const repeatedDialogSubmit=submit();
assert.equal(requests.length,2);
await repeatedDialogSubmit;
assert.equal(confirmations.length,1);
assert.equal(fields.start.disabled,true);
decide(false);
await duplicateRequest;
assert.equal(fields.start.disabled,false);
assert.equal(activeElement,fields.start);
""")
