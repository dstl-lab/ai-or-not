from test_annotation_hover_ui import HOVER_SETUP
from test_annotation_labels_ui import run_checks
from test_annotation_tracking_ui import run as check_tracking


DRAW_SETUP = HOVER_SETUP + r'''
let warning='',shown;
tool.warn=value=>warning=value;
tool.show=(...args)=>shown=args;
const canvas=element('CANVAS', {id:'chart','aria-label':'Population'});
let canvasRect={left:100,top:100,width:200,height:100};
canvas.getBoundingClientRect=()=>canvasRect;
const captured=new Set();
canvas.setPointerCapture=id=>captured.add(id);
canvas.hasPointerCapture=id=>captured.has(id);
canvas.releasePointerCapture=id=>{
  captured.delete(id);
  listeners.lostpointercapture?.({pointerId:id});
};
hit=canvas;
const event=(x,y,extra={})=>({target:canvas,clientX:x,clientY:y,pointerId:1,
  button:0,isPrimary:true,preventDefault(){},stopImmediatePropagation(){},...extra});
function drag(x1,y1,x2,y2){
  listeners.pointerdown(event(x1,y1));
  listeners.pointermove(event(x2,y2));
  tick();
  listeners.pointerup(event(x2,y2));
  listeners.click(event(x2,y2,{detail:1}));
}
'''


def test_canvas_drag_creates_a_specific_area_and_shows_it_while_writing():
    run_checks(DRAW_SETUP + r'''
listeners.pointermove(event(120,110));
assert.equal(label.textContent,'Drag to draw an area');
listeners.pointerdown(event(120,110));
assert.ok(captured.has(1));
listeners.pointermove(event(260,180));
tick();
assert.equal(outline.style.left,'120px');
assert.equal(outline.style.width,'140px');
assert.equal(outline.style.height,'70px');
listeners.pointerup(event(260,180));
listeners.click(event(260,180,{detail:1}));
assert.equal(tool.draft.selector,'#chart');
assert.equal(tool.draft.quote,'Chart area · Population');
for(const [key,value] of Object.entries({x:0.1,y:0.1,width:0.7,height:0.7}))
  assert.ok(Math.abs(tool.draft.region[key]-value)<1e-9);
assert.deepEqual(tool.draft.rect,{x:120,y:110,width:140,height:70});
assert.equal(shown[0],tool.draft);
assert.equal(shown[1],false,'drawing must not scroll the page on release');
assert.equal(captured.size,0);
assert.equal(frames.size,0);
assert.deepEqual(Object.keys(listeners),[]);
''')


def test_reverse_drag_is_clipped_to_original_canvas_even_outside_its_edges():
    run_checks(DRAW_SETUP + r'''
listeners.pointerdown(event(280,190));
hit=element('DIV');
listeners.pointerout({relatedTarget:null});
listeners.pointermove(event(50,40));
tick();
assert.equal(outline.style.left,'100px');
assert.equal(outline.style.top,'100px');
assert.equal(outline.style.width,'180px');
listeners.pointerup(event(50,40));
listeners.click(event(50,40,{detail:1}));
assert.deepEqual(tool.draft.region,{x:0,y:0,width:0.9,height:0.9});
assert.deepEqual(tool.draft.rect,{x:100,y:100,width:180,height:90});
''')


def test_tiny_drag_stays_in_selection_mode_and_escape_cleans_up_capture():
    run_checks(DRAW_SETUP + r'''
drag(120,110,122,113);
assert.equal(tool.draft,null);
assert.equal(tool.armed,true);
assert.match(warning,/larger area/);
listeners.pointerdown(event(130,120));
assert.ok(captured.has(1));
listeners.keydown({key:'Escape'});
assert.equal(tool.armed,false);
assert.equal(tool.draft,null);
assert.equal(captured.size,0);
assert.equal(frames.size,0);
assert.equal(page.documentElement.children.length,0);
assert.deepEqual(Object.keys(listeners),[]);
''')


def test_drag_start_stays_attached_when_canvas_moves_or_resizes():
    run_checks(DRAW_SETUP + r'''
listeners.pointerdown(event(120,110));
canvasRect={left:50,top:200,width:400,height:200};
win.scrollY=300;
listeners.pointermove(event(250,300));
tick();
assert.equal(outline.style.left,'90px');
assert.equal(outline.style.top,'220px');
listeners.pointerup(event(250,300));
listeners.click(event(250,300,{detail:1}));
assert.deepEqual(tool.draft.region,{x:0.1,y:0.1,width:0.4,height:0.4});
assert.deepEqual(tool.draft.rect,{x:90,y:520,width:160,height:80});
''')


def test_interrupted_drag_does_not_commit_and_secondary_pointers_do_not_replace_it():
    run_checks(DRAW_SETUP + r'''
listeners.pointerdown(event(120,110,{button:2}));
assert.equal(captured.size,0);
listeners.pointerdown(event(120,110));
listeners.pointerdown(event(250,180,{pointerId:2,isPrimary:false}));
listeners.pointerup(event(250,180,{pointerId:2,isPrimary:false}));
assert.ok(captured.has(1));
listeners.pointercancel(event(250,180));
assert.equal(captured.size,0);
assert.equal(tool.draft,null);
assert.equal(tool.armed,true);
drag(120,110,260,180);
assert.equal(tool.draft.selector,'#chart');
''')


def test_saved_canvas_area_scales_and_follows_scrolling_without_changing_data():
    check_tracking(r'''
entry.region={x:0.25,y:0.5,width:0.5,height:0.25};
const original=JSON.stringify(entry);
rect={left:100,top:200,width:400,height:200};
tool.show(entry);
const marker=markers.at(-1);
assert.equal(marker.style.left,'200px');
assert.equal(marker.style.top,'400px');
assert.equal(marker.style.width,'200px');
assert.equal(marker.style.height,'50px');
rect={left:20,top:-40,width:200,height:100};
win.scrollY=500;
flush();
assert.equal(marker.style.left,'70px');
assert.equal(marker.style.top,'510px');
assert.equal(marker.style.width,'100px');
assert.equal(marker.style.height,'25px');
assert.equal(JSON.stringify(entry),original);
tool.stopSelecting();
assert.equal(frames.size,0);
''')


def test_valid_text_selection_clears_a_previous_tiny_area_warning():
    run_checks(DRAW_SETUP + r'''
drag(120,110,122,113);
assert.match(warning,/larger area/);
const text=element('P', {}, 'A chart explanation');
listeners.click(event(50,50,{target:text,detail:1}));
assert.equal(tool.draft.quote,'A chart explanation');
assert.equal(warning,'');
''')


def test_another_pointer_click_cannot_commit_during_an_active_drag():
    run_checks(DRAW_SETUP + r'''
listeners.pointerdown(event(120,110));
listeners.click(event(50,50,{target:element('P'),pointerId:2,detail:1}));
assert.equal(tool.draft,null);
assert.ok(captured.has(1));
listeners.pointerup(event(260,180));
listeners.click(event(260,180,{detail:1}));
assert.equal(tool.draft.quote,'Chart area · Population');
''')
