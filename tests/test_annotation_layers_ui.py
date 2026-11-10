from test_annotation_labels_ui import run_checks


LAYER_SETUP = r'''
const listeners={}, frames=new Map();
let frameId=0,stack=[],semantic=[],rendered,entries=[],warning='';
page.documentElement=element('HTML');
page.head=element('HEAD');
page.body=element('BODY');
page.addEventListener=(type,listener)=>listeners[type]=listener;
page.removeEventListener=(type,listener)=>{assert.equal(listeners[type],listener);delete listeners[type]};
page.elementsFromPoint=()=>stack;
page.elementFromPoint=()=>stack[0] || null;
page.querySelectorAll=selector=>selector==='.annotation-list .annotation-target' ? [] : semantic.filter(el=>el.matches(selector));
win.requestAnimationFrame=callback=>{frames.set(++frameId,callback);return frameId};
win.cancelAnimationFrame=id=>frames.delete(id);
function node(tag,id,text,rect,css={}) {
  const value=element(tag,{id},text);
  value.isConnected=true;
  value.scrollIntoView=()=>{};
  value.getBoundingClientRect=()=>({...rect,right:rect.left+rect.width,bottom:rect.top+rect.height});
  value.css=css;
  targets[`#${id}`]=value;
  return value;
}
win.getComputedStyle=el=>({visibility:'visible',display:'block',opacity:'1',...el.css,
  getPropertyValue:key=>el.css?.[key] || ''});
const tool=new AnnotationTool({change(question,value){entries=value},
  refresh(){rendered=tool.render({max_annotations:3},entries)},warn(value){warning=value}});
tool.frame={contentWindow:win};
tool.site={home:'/sites/alpha/'};
const editor=()=>rendered.children.find(el=>el.className==='annotation-editor');
const find=(root,tag)=>root.children.flatMap(child=>[...(child.tagName.toLowerCase()===tag?[child]:[]),...find(child,tag)]);
const picker=()=>find(editor(),'select')[0];
const note=()=>find(editor(),'textarea')[0];
const action=text=>find(editor(),'button').find(el=>el.textContent===text).click();
function event(target,x=50,y=50,extra={}) {
  return {target,clientX:x,clientY:y,button:0,isPrimary:true,pointerId:1,detail:1,
    preventDefault(){this.prevented=true},stopImmediatePropagation(){this.stopped=true},...extra};
}
function pick(target=stack[0]) {tool.start();listeners.click(event(target))}
function tick(){const pending=[...frames.values()];frames.clear();for(const callback of pending)callback()}
const full={left:0,top:0,width:900,height:700};
const small={left:20,top:30,width:200,height:40};
'''


def test_pointer_ignored_content_is_selectable_and_layer_choice_changes_saved_metadata():
    # Omitting semantic content or retaining the first layer's capture loses the chosen clue.
    run_checks(LAYER_SETUP + r'''
const cover=node('CANVAS','cover','Visual background',full,{'background-color':'rgb(0, 0, 0)'});
cover.setPointerCapture=()=>{};
cover.hasPointerCapture=()=>false;
const heading=node('H1','heading','A meaningful heading',small,{pointerEvents:'none',color:'rgb(12, 34, 56)'});
const hidden=node('P','hidden','Hidden text',small,{visibility:'hidden'});
const transparent=node('SECTION','transparent','',full,{opacity:'0'});
const child=node('P','hidden-child','Also hidden',small);
attach(transparent,child);
stack=[cover,page.body];
semantic=[heading,hidden,child];
tool.start();
listeners.pointerdown(event(cover));
listeners.pointerup(event(cover));
listeners.click(event(cover));
assert.equal(tool.draft.selector,'#heading','compact visible content must win over a broad layer');
let layers=picker();
assert.equal(layers.getAttribute('aria-label'),'Selected element layer');
assert.equal(layers.parentElement.tagName,'label');
assert.equal(layers.children.length,2,'invisible content and page ancestors are not layer choices');
note().value='  The wording and color.  ';
note().listeners.input();
const headingOption=layers.children.find(option=>option.selected);
const backgroundOption=layers.children.find(option=>option!==headingOption);
layers.value=backgroundOption.value;
layers.listeners.change({target:layers});
assert.equal(tool.draft.selector,'#cover');
assert.equal(tool.draft.styles['background-color'],'rgb(0, 0, 0)');
layers.value=headingOption.value;
layers.listeners.change({target:layers});
action('Save note');
assert.equal(entries[0].selector,'#heading');
assert.equal(entries[0].quote,'A meaningful heading');
assert.deepEqual(entries[0].rect,{x:20,y:30,width:200,height:40});
assert.equal(entries[0].styles.color,'rgb(12, 34, 56)');
assert.equal(entries[0].note,'The wording and color.');
assert.equal(tool.draft,null);
assert.equal(warning,'');
''')


def test_captured_styles_are_a_bounded_snapshot_of_the_selected_element():
    # Unbounded CSS values reject otherwise valid notes; live references corrupt saved evidence.
    run_checks(LAYER_SETUP + r'''
const target=node('BUTTON','cta','Continue',small,{
  'background-color':'rgb(20, 30, 40)','background-image':'url('+ 'x'.repeat(500)+')',
  color:'rgb(255, 255, 255)','font-family':'Inter','font-size':'16px','font-weight':'600',
  'border-radius':'8px','box-shadow':'none',display:'inline-flex',gap:'12px',
});
const snapshot=captureTarget(target,win,tool.site);
assert.deepEqual(Object.keys(snapshot.styles).sort(),['background-color','background-image','border-radius',
  'box-shadow','color','display','font-family','font-size','font-weight','gap'].sort());
assert.equal(snapshot.styles['background-image'].length,300);
assert.equal(snapshot.styles['font-size'],'16px');
target.css['font-size']='24px';
assert.equal(snapshot.styles['font-size'],'16px');
''')


def test_compact_control_wins_over_a_large_overlay_and_nested_text():
    # Selecting the decorative child instead of its button makes the clue ambiguous.
    run_checks(LAYER_SETUP + r'''
const cover=node('DIV','cover','',full);
const button=node('BUTTON','cta','Continue',small);
const span=node('SPAN','cta-text','Continue',small);
attach(button,span);
stack=[cover,span,button,page.body];
semantic=[button];
pick();
assert.equal(tool.draft.selector,'#cta');
assert.equal(picker().children.length,2,'a control and its nested text are one choice');
''')


def test_single_target_has_no_layer_picker_and_interactions_resume_after_save_and_cancel():
    # Leaving selection listeners installed blocks the site's clicks and chart gestures.
    run_checks(LAYER_SETUP + r'''
const target=node('BUTTON','cta','Continue',small);
stack=[target];
semantic=[target];
for(const finish of ['Save note','Cancel']) {
  pick();
  assert.equal(picker(),undefined);
  note().value='The button.';
  note().listeners.input();
  action(finish);
  for(const type of ['pointerdown','pointerup','mousedown','mouseup','click','touchstart','touchmove','touchend']) {
    const interaction=event(target);
    listeners[type]?.(interaction);
    assert.ok(!interaction.prevented && !interaction.stopped,`${type} must reach the site after ${finish}`);
  }
  for(const marker of page.documentElement.children)assert.equal(marker.style.pointerEvents,'none');
  assert.equal(page.head.children.length,0,'selection cursor must be removed');
}
''')


def test_svg_mark_is_preferred_to_its_outer_chart_and_remains_a_layer_choice():
    # Grouping SVG nodes as one chart would lose point-level annotations from the reviewer tool.
    run_checks(LAYER_SETUP + r'''
const chart=node('svg','chart','',full);
chart.setAttribute('aria-label','Population');
const point=node('circle','point','',{left:45,top:45,width:10,height:10});
attach(chart,point);
stack=[point,chart];
semantic=[chart,point];
pick();
assert.equal(tool.draft.selector,'#point');
assert.equal(tool.draft.quote,'Chart point · Population');
assert.equal(picker().children.length,2);
''')


def test_canvas_area_remains_one_target_despite_overlapping_layers():
    # A layer choice must not silently replace a deliberately drawn chart region.
    run_checks(LAYER_SETUP + r'''
const canvas=node('CANVAS','canvas','',{left:0,top:0,width:400,height:200});
const backdrop=node('DIV','backdrop','Background',full);
const heading=node('H1','heading','A heading behind the canvas',{left:90,top:40,width:100,height:30});
const captured=new Set();
canvas.setPointerCapture=id=>captured.add(id);
canvas.hasPointerCapture=id=>captured.has(id);
canvas.releasePointerCapture=id=>captured.delete(id);
stack=[canvas,backdrop];
semantic=[canvas,heading];
tool.start();
listeners.pointerdown(event(canvas,100,50));
listeners.pointermove(event(canvas,300,150));
listeners.pointerup(event(canvas,300,150));
listeners.click(event(canvas,300,150));
assert.equal(picker(),undefined);
assert.equal(tool.draft.selector,'#canvas');
assert.deepEqual(tool.draft.rect,{x:100,y:50,width:200,height:100});
assert.equal(captured.size,0);
action('Cancel');
assert.deepEqual(Object.keys(listeners),[]);
''')


def test_embedded_chart_is_selectable_when_frame_pointer_events_are_disabled():
    # Child-frame clicks cannot bubble to the study page; select its outer element instead.
    run_checks(LAYER_SETUP + r'''
const surrounding=node('SECTION','chapter','Storm trends',full);
const embedded=node('IFRAME','storms-iframe','',full);
embedded.setAttribute('title','Storm Timeline');
attach(surrounding,embedded);
stack=[surrounding];
semantic=[embedded];
pick();
assert.equal(tool.draft.selector,'#storms-iframe');
assert.equal(tool.draft.quote,'Storm Timeline');
note().value='The embedded storm chart.';
note().listeners.input();
action('Save note');
assert.equal(entries[0].selector,'#storms-iframe');
assert.equal(Object.keys(entries[0].styles).length,10);
assert.equal(page.head.children.length,0,'temporary selection rules must be removed');
assert.deepEqual(Object.keys(listeners),[]);
''')


def test_modal_layers_exclude_obscured_controls_behind_the_dialog():
    # Enlarged photos must not be mistaken for their clickable thumbnail behind the modal.
    run_checks(LAYER_SETUP + r'''
const thumbnail=node('BUTTON','thumbnail','Enlarge photo',small);
const dialog=node('DIV','lightbox','',full);
dialog.setAttribute('aria-modal','true');
const photo=node('IMG','lb-img','',{left:0,top:0,width:700,height:500});
attach(dialog,photo);
stack=[photo,dialog,thumbnail,page.body];
semantic=[thumbnail,photo];
pick(photo);
assert.equal(tool.draft.selector,'#lb-img');
assert.equal(picker().children.length,2);
assert.ok(picker().children.every(option=>!option.textContent.includes('Enlarge photo')));
action('Cancel');
''')


def test_stroked_svg_lines_have_selectable_bounds_and_saved_highlights():
    # A line's geometry has zero width or height even though its stroke is visible.
    run_checks(LAYER_SETUP + r'''
const chart=node('svg','chart','',full);
const line=node('line','axis','',{left:50,top:30,width:0,height:100},
  {stroke:'rgb(0, 0, 0)',strokeWidth:'2px'});
line.namespaceURI='http://www.w3.org/2000/svg';
line.getScreenCTM=()=>({a:2,b:0,c:0,d:2});
attach(chart,line);
stack=[line,chart];
semantic=[line,chart];
pick(line);
assert.equal(tool.draft.selector,'#axis');
assert.deepEqual(tool.draft.rect,{x:48,y:30,width:4,height:100});
note().value='The thin axis.';
note().listeners.input();
action('Save note');
assert.equal(page.documentElement.children.at(-1).style.width,'4px');
assert.equal(warning,'');
line.css.vectorEffect='non-scaling-stroke';
assert.equal(captureTarget(line,win,tool.site).rect.width,2);
line.css.stroke='none';
assert.throws(()=>captureTarget(line,win,tool.site),/visible/);
''')
