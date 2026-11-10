import subprocess
from pathlib import Path


MODULE = (Path(__file__).parents[1] / "web" / "annotations.js").as_uri()
SETUP = r'''
import assert from 'node:assert/strict';
import { AnnotationTool } from MODULE;
globalThis.document = {addEventListener(){}};
let rect = {left:10, top:20, width:30, height:40};
let connected = true;
let available = true;
let warning = '';
const markers = [];
const styles = new Map();
const frames = new Map();
let frameId = 0;
const target = {
  get isConnected() { return connected; },
  scrollIntoView() {},
  getBoundingClientRect: () => rect,
};
const doc = Object.assign(new EventTarget(), {
  body: {},
  querySelector: () => available ? target : null,
  createElement: () => ({style:{}, setAttribute(){}, remove(){this.removed = true;}}),
  documentElement: {append(marker){markers.push(marker);}},
});
const win = Object.assign(new EventTarget(), {
  document: doc, location: {pathname:'/sites/alpha/', search:'', hash:''},
  scrollX:0, scrollY:100,
  getComputedStyle:node => styles.get(node) || {visibility:'visible', opacity:'1', display:'block'},
  requestAnimationFrame(callback) { const id = ++frameId; frames.set(id, callback); return id; },
  cancelAnimationFrame(id) { frames.delete(id); },
});
const tool = new AnnotationTool({change(){}, refresh(){}, warn(value){warning = value;}});
tool.frame = {contentWindow:win};
const entry = {page_path:'/sites/alpha/', selector:'#chart circle'};
function flush() {
  for (const [id, callback] of [...frames]) { frames.delete(id); callback(); }
}
'''.replace("MODULE", repr(MODULE))


def run(checks):
    subprocess.run(["node", "--input-type=module", "-e", SETUP + checks], check=True)


def test_highlight_follows_chart_movement_and_nested_scrolling():
    run(r'''
tool.show(entry);
const marker = markers.at(-1);
assert.equal(marker.style.left, '10px');
assert.equal(marker.style.top, '120px');
rect = {left:50, top:60, width:20, height:15};
flush();
assert.equal(marker.style.left, '50px');
assert.equal(marker.style.top, '160px');
assert.equal(marker.style.width, '20px');
rect = {...rect, top:35};
doc.dispatchEvent(new Event('scroll'));
flush();
assert.equal(marker.style.top, '135px');
rect = {...rect, left:80};
win.dispatchEvent(new Event('resize'));
flush();
assert.equal(marker.style.left, '80px');
''')


def test_redrawing_a_chart_removes_the_stale_highlight_and_can_be_reopened():
    run(r'''
tool.show(entry);
const marker = markers.at(-1);
connected = false;
available = false;
flush();
assert.equal(marker.removed, true);
assert.match(warning, /note is still saved/);
assert.equal(frames.size, 0);
connected = true;
available = true;
tool.show(entry);
assert.equal(warning, '');
assert.notEqual(markers.at(-1), marker);
assert.notEqual(markers.at(-1).removed, true);
''')


def test_hidden_targets_are_not_highlighted_and_failed_lookup_clears_old_marker():
    run(r'''
tool.show(entry);
const marker = markers.at(-1);
rect = {...rect, width:0, height:0};
flush();
assert.equal(marker.removed, true);
assert.match(warning, /note is still saved/);
tool.show(entry);
assert.equal(markers.length, 1);
rect = {...rect, width:30, height:40};
tool.show(entry);
const recovered = markers.at(-1);
assert.equal(warning, '');
available = false;
tool.show(entry);
assert.equal(recovered.removed, true);
assert.match(warning, /note is still saved/);
''')


def test_stopping_a_highlight_cancels_pending_tracking_and_keeps_other_warnings():
    run(r'''
tool.show(entry);
warning = 'Finish your answers before continuing.';
flush();
assert.equal(warning, 'Finish your answers before continuing.');
assert.ok(frames.size > 0);
tool.stopSelecting();
assert.equal(markers.at(-1).removed, true);
assert.equal(frames.size, 0);
rect = {...rect, left:100};
flush();
assert.equal(markers.at(-1).style.left, '10px');
''')


def test_css_hidden_targets_and_hidden_ancestors_cannot_keep_a_highlight():
    run(r'''
const parent = {};
target.parentElement = parent;
for (const [node, style] of [
  [target, {visibility:'hidden', opacity:'1', display:'block'}],
  [parent, {visibility:'visible', opacity:'0', display:'block'}],
]) {
  tool.show(entry);
  const marker = markers.at(-1);
  styles.set(node, style);
  flush();
  assert.equal(marker.removed, true);
  assert.match(warning, /note is still saved/);
  const count = markers.length;
  tool.show(entry);
  assert.equal(markers.length, count);
  styles.clear();
  tool.show(entry);
  assert.equal(warning, '');
}
''')


def test_highlight_follows_animation_between_dom_events():
    run(r'''
tool.show(entry);
const marker = markers.at(-1);
rect = {...rect, left:75, top:90};
flush();
assert.equal(marker.style.left, '75px');
assert.equal(marker.style.top, '190px');
''')


def test_clipped_carousel_note_warns_until_its_slide_is_visible_again():
    run(r'''
const viewport={getBoundingClientRect:()=>({left:0,top:0,width:100,height:100})};
target.parentElement=viewport;
styles.set(viewport,{visibility:'visible',opacity:'1',display:'block',overflowX:'hidden',overflowY:'hidden'});
tool.show(entry);
const marker=markers.at(-1);
rect={left:-90,top:20,width:30,height:40};
flush();
assert.equal(marker.removed,true);
assert.match(warning,/not currently visible/);
const count=markers.length;
tool.show(entry);
assert.equal(markers.length,count);
rect={left:10,top:20,width:30,height:40};
tool.show(entry);
assert.equal(warning,'');
assert.equal(markers.length,count+1);
''')
