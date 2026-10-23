from test_annotation_labels_ui import run_checks


HOVER_SETUP = r'''
const listeners={};
const frames=new Map();
let frameId=0,hit=null;
win.requestAnimationFrame=callback=>{frames.set(++frameId,callback);return frameId};
win.cancelAnimationFrame=id=>frames.delete(id);
function tick(){const pending=[...frames.values()];frames.clear();for(const callback of pending)callback()}
page.elementFromPoint=()=>hit;
page.documentElement=element('HTML');
page.head=element('HEAD');
page.addEventListener=(type,listener)=>listeners[type]=listener;
page.removeEventListener=(type,listener)=>{
  assert.equal(listeners[type],listener);
  delete listeners[type];
};
const tool=new AnnotationTool({change(){},refresh(){},warn(message){if(message)throw Error(message)}});
tool.frame={contentWindow:win};
tool.site={home:'/sites/alpha/'};
tool.start();
const [outline,label]=page.documentElement.children;
assert.equal(label?.textContent,'Click to annotate');
label.getBoundingClientRect=()=>({width:132,height:28});
const target=element('circle', {id:'point'});
hit=target;
const move=()=>listeners.pointermove({target:hit,clientX:50,clientY:100});
'''


def test_hover_hint_stays_visible_for_small_targets_and_viewport_edges():
    run_checks(HOVER_SETUP + r'''
assert.equal(label.attributes['aria-hidden'],'true');
assert.equal(label.style.pointerEvents,'none');
assert.equal(label.style.display,'none');
for(const [left,top,expectedLeft,expectedTop] of [
  [50,100,50,66], [890,1,760,8], [-20,-200,8,8], [890,720,760,664],
]) {
  target.getBoundingClientRect=()=>({left,top,width:1,height:1});
  move();
  tick();
  assert.equal(outline.style.width,'1px');
  assert.equal(label.style.display,'block');
  assert.equal(label.style.left,`${expectedLeft}px`);
  assert.equal(label.style.top,`${expectedTop}px`);
}
''')


def test_hover_hint_is_removed_on_selection_and_escape():
    run_checks(HOVER_SETUP + r'''
move();
let prevented=false,stopped=false;
listeners.click({target,preventDefault(){prevented=true},stopImmediatePropagation(){stopped=true}});
assert.ok(prevented && stopped);
assert.equal(tool.draft.selector,'#point');
assert.equal(tool.armed,false);
assert.equal(page.documentElement.children.length,0);
assert.equal(page.head.children.length,0);
assert.equal(frames.size,0);
assert.deepEqual(Object.keys(listeners),[]);
tool.start();
assert.equal(page.documentElement.children.length,2);
move();
listeners.keydown({key:'Escape'});
assert.equal(tool.armed,false);
assert.equal(page.documentElement.children.length,0);
assert.equal(page.head.children.length,0);
assert.equal(frames.size,0);
assert.deepEqual(Object.keys(listeners),[]);
''')


def test_hover_tracks_scroll_and_chart_motion_without_another_pointer_move():
    run_checks(HOVER_SETUP + r'''
move();
assert.equal(outline.style.top,'20px');
target.getBoundingClientRect=()=>({left:80,top:140,width:8,height:8});
tick();
assert.equal(outline.style.top,'140px');
assert.equal(outline.style.left,'80px');
assert.equal(label.style.top,'106px');
const revealed=element('CANVAS');
revealed.getBoundingClientRect=()=>({left:30,top:60,width:400,height:200});
hit=revealed;
tick();
assert.equal(outline.style.top,'60px');
assert.equal(outline.style.width,'400px');
assert.equal(label.style.top,'26px');
for(let i=0;i<5;i++)move();
assert.equal(frames.size,1);
hit=null;
tick();
assert.equal(outline.style.display,'none');
assert.equal(label.style.display,'none');
tool.cancel(false);
assert.equal(frames.size,0);
''')


def test_hover_clears_on_leaving_the_frame_and_returns_on_reentry():
    run_checks(HOVER_SETUP + r'''
move();
assert.equal(label.style.display,'block');
listeners.pointerout?.({relatedTarget:element('DIV')});
assert.equal(label.style.display,'block');
listeners.pointerout?.({relatedTarget:null});
assert.equal(outline.style.display,'none');
assert.equal(label.style.display,'none');
assert.equal(frames.size,0);
move();
assert.equal(outline.style.display,'block');
assert.equal(label.style.display,'block');
assert.equal(frames.size,1);
tool.cancel(false);
''')


def test_selecting_a_canvas_does_not_also_trigger_its_pointer_or_mouse_actions():
    run_checks(HOVER_SETUP + r'''
hit=element('CANVAS', {id:'globe-canvas'});
move();
for(const type of ['pointerdown','mousedown','pointerup','mouseup']) {
  let prevented=false,stopped=false;
  listeners[type]?.({preventDefault(){prevented=true},stopImmediatePropagation(){stopped=true}});
  assert.ok(prevented && stopped,`${type} must not reach the chart while selecting`);
}
listeners.click({target:hit,detail:0,preventDefault(){},stopImmediatePropagation(){}});
assert.equal(tool.draft.selector,'#globe-canvas');
assert.equal(tool.draft.quote,'Chart');
assert.equal(page.documentElement.children.length,0);
assert.equal(frames.size,0);
assert.deepEqual(Object.keys(listeners),[]);
''')
