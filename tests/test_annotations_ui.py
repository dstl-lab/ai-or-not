import subprocess
from pathlib import Path


def test_annotation_capture_records_visible_target_and_rejects_outside_pages():
    module = (Path(__file__).parents[1] / "web" / "annotations.js").as_uri()
    checks = r'''
import assert from 'node:assert/strict';
import { captureTarget } from MODULE;
const target = {tagName:'H2', id:'story', innerText:'A visible chart heading',
  parentElement:null, getBoundingClientRect:()=>({left:20,top:40,width:240,height:32})};
const win = {location:{pathname:'/sites/alpha/index.html',search:'?year=2026',hash:'#chart'},
  getComputedStyle:()=>({getPropertyValue:()=>''}),
  scrollX:0,scrollY:150,innerWidth:900,innerHeight:700,CSS:{escape:s=>s}};
const capture = captureTarget(target, win, {home:'/sites/alpha/'});
assert.equal(capture.page_path,'/sites/alpha/index.html?year=2026#chart');
assert.equal(capture.selector,'#story');
assert.equal(capture.quote,'A visible chart heading');
assert.deepEqual(capture.rect,{x:20,y:190,width:240,height:32});
assert.deepEqual(capture.viewport,{width:900,height:700});
win.location.pathname='/sites/beta/';
assert.throws(()=>captureTarget(target,win,{home:'/sites/alpha/'}), /assigned webpage/);
'''.replace('MODULE', repr(module))
    subprocess.run(['node', '--input-type=module', '-e', checks], check=True)


def test_reloading_a_frame_stops_selection_without_discarding_a_typed_note():
    module = (Path(__file__).parents[1] / "web" / "annotations.js").as_uri()
    checks = r'''
import assert from 'node:assert/strict';
import { AnnotationTool } from MODULE;
globalThis.document={addEventListener(){},querySelector:()=>null};
let cleaned=0;
const tool=new AnnotationTool({change(){},refresh(){},warn(){}});
tool.draft={note:'Still writing this note'};
tool.armed=true;
tool.cleanup=()=>cleaned++;
tool.stopSelecting();
assert.equal(cleaned,1);
assert.equal(tool.armed,false);
assert.equal(tool.draft.note,'Still writing this note');
tool.pending={selector:'h1'};
tool.cancel();
assert.equal(tool.draft,null);
assert.equal(tool.pending,null);
'''.replace('MODULE', repr(module))
    subprocess.run(['node', '--input-type=module', '-e', checks], check=True)


def test_showing_a_target_after_an_anchor_jump_does_not_wait_for_a_frame_reload():
    module = (Path(__file__).parents[1] / "web" / "annotations.js").as_uri()
    checks = r'''
import assert from 'node:assert/strict';
import { AnnotationTool } from MODULE;
globalThis.document={addEventListener(){}};
let navigations=0,markers=0,scrolled=0;
const target={isConnected:true,scrollIntoView(){scrolled++},getBoundingClientRect:()=>({left:10,top:20,width:300,height:40})};
const win={location:{pathname:'/sites/alpha/',search:'',hash:'#intro'},scrollX:0,scrollY:0,
 getComputedStyle:()=>({visibility:'visible',opacity:'1',display:'block'}),requestAnimationFrame(){return 1},cancelAnimationFrame(){},
 document:{querySelector:()=>target,createElement:()=>({style:{},setAttribute(){},remove(){}}),
 documentElement:{append(){markers++}}}};
const tool=new AnnotationTool({change(){},refresh(){},warn(message){if(message)throw Error(message)}});
tool.frame={contentWindow:win,set src(value){navigations++}};
tool.show({page_path:'/sites/alpha/#chart',selector:'#chart'});
assert.equal(navigations,0);
assert.equal(win.location.hash,'#chart');
assert.equal(markers,1);
assert.equal(scrolled,1);
'''.replace('MODULE', repr(module))
    subprocess.run(['node', '--input-type=module', '-e', checks], check=True)
