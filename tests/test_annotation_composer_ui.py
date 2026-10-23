from test_annotation_labels_ui import run_checks


FOCUS_SETUP = r'''
page.documentElement=element('HTML');
page.head=element('HEAD');
page.removeEventListener=()=>{};
function mount(entries,limit=3) {
  const question={max_annotations:limit};
  let rendered;
  const tool=new AnnotationTool({change(q,value){entries=value},refresh(){
    page.activeElement=null;
    rendered=tool.render(question,entries);
  },warn(){}});
  tool.frame={contentWindow:win};
  tool.site={home:'/sites/alpha/'};
  tool.show=()=>{};
  tool.refresh();
  const targets=()=>rendered.children.some(child=>child.className==='annotation-list')
    ? cards(rendered).map(card=>card.firstChild) : [];
  page.querySelectorAll=selector=>selector==='.annotation-list .annotation-target' ? targets() : [];
  page.querySelector=selector=>{
    const mode=rendered.children.find(child=>child.className==='annotation-mode');
    const editor=rendered.children.find(child=>child.className==='annotation-editor');
    if(selector==='.annotation-mode button') return mode?.children[2];
    if(selector==='.annotation-editor textarea') return editor?.children[1].firstChild;
    if(selector==='.annotation-add, .annotation-list .annotation-target' || selector==='.annotation-add, .annotation-target') {
      return rendered.children.find(child=>child.className==='annotation-add') || targets()[0];
    }
    return null;
  };
  return {tool,view:()=>rendered};
}
const saved=[1,2,3].map(id=>({id:String(id),page_path:'/sites/alpha/',selector:'#point',quote:'Chart point',note:`Note ${id}`}));
'''


def test_annotation_action_precedes_saved_notes():
    run_checks(r'''
const entry={id:'one',page_path:'/sites/alpha/',selector:'#point',quote:'Chart point',note:'The cluster.'};
const tool=new AnnotationTool({change(){},refresh(){},warn(){}});
const rendered=tool.render({max_annotations:3},[entry]);
assert.equal(rendered.firstChild.className,'annotation-add');
assert.equal(rendered.firstChild.textContent,'Annotate webpage');
assert.equal(rendered.children[1].className,'annotation-list');
assert.equal(rendered.children[1].firstChild.textContent,'Saved notes (1)');
assert.equal(cards(rendered)[0].children[1].textContent,'The cluster.');
assert.equal(cards(rendered)[0].firstChild.disabled,false);
''')


def test_selection_mode_precedes_history_and_cancel_restores_idle_state():
    run_checks(r'''
const entry={id:'one',page_path:'/sites/alpha/',selector:'#point',quote:'Chart point',note:'The cluster.'};
let refreshed=0,cleaned=0;
const tool=new AnnotationTool({change(){},refresh(){refreshed++},warn(){}});
tool.armed=true;
tool.cleanup=()=>cleaned++;
const rendered=tool.render({max_annotations:3},[entry]);
const mode=rendered.firstChild;
assert.equal(mode.className,'annotation-mode');
assert.equal(mode.firstChild.tagName,'h4');
assert.equal(mode.firstChild.textContent,'Select a detail on the webpage');
assert.equal(mode.children[1].getAttribute('role'),'status');
assert.match(mode.children[1].textContent,/Press Esc to cancel/);
const card=cards(rendered)[0];
for(const control of [card.firstChild,...card.children[2].children]) assert.equal(control.disabled,true);
const cancel=mode.children[2];
assert.equal(cancel.textContent,'Cancel selection');
cancel.click();
assert.equal(tool.armed,false);
assert.equal(cleaned,1);
assert.equal(refreshed,1);
''')


def test_editor_precedes_history_and_saving_preserves_existing_target_values():
    run_checks(r'''
const question={max_annotations:3};
const entry={id:'one',page_path:'/sites/alpha/',selector:'#point',quote:'Chart point',
  rect:{x:10,y:20,width:5,height:5},viewport:{width:900,height:700},note:'The cluster.'};
let changed,shown;
const tool=new AnnotationTool({change(q,value){assert.equal(q,question);changed=value},refresh(){},warn(){}});
tool.show=value=>shown=value;
tool.draft={...entry};
const rendered=tool.render(question,[entry]);
const editor=rendered.firstChild;
assert.equal(editor.className,'annotation-editor');
assert.equal(editor.firstChild.textContent,'Chart point');
assert.equal(rendered.children[1].className,'annotation-list');
const card=cards(rendered)[0];
for(const control of [card.firstChild,...card.children[2].children]) assert.equal(control.disabled,true);
const input=editor.children[1].firstChild;
input.value='  The updated cluster.  ';
input.listeners.input();
editor.children[2].children[1].click();
assert.deepEqual(changed,[{...entry,note:'The updated cluster.'}]);
assert.deepEqual(shown,changed[0]);
assert.equal(entry.note,'The cluster.');
assert.equal(tool.draft,null);
''')


def test_note_limit_explains_next_action_and_removal_allows_another_note():
    run_checks(r'''
const entries=[1,2,3].map(id=>({id:String(id),page_path:'/sites/alpha/',selector:'#point',quote:'Chart point',note:`Note ${id}`}));
let changed;
const tool=new AnnotationTool({change(q,value){changed=value},refresh(){},warn(){}});
let rendered=tool.render({max_annotations:3},entries);
assert.equal(rendered.firstChild.className,'annotation-limit');
assert.match(rendered.firstChild.textContent,/3 note limit/);
assert.match(rendered.firstChild.textContent,/Edit or remove/);
assert.equal(rendered.children.some(child=>child.className==='annotation-add'),false);
assert.equal(rendered.children[1].firstChild.textContent,'Saved notes (3)');
const card=cards(rendered)[0];
for(const control of [card.firstChild,...card.children[2].children]) assert.equal(control.disabled,false);
card.children[2].children[1].click();
assert.deepEqual(changed,entries.slice(1));
rendered=tool.render({max_annotations:3},changed);
assert.equal(rendered.firstChild.textContent,'Annotate webpage');
assert.equal(cards(rendered).length,2);
''')


def test_empty_annotations_offer_a_real_action_and_concise_instruction():
    run_checks(r'''
let started=0;
const tool=new AnnotationTool({change(){},refresh(){},warn(){}});
tool.start=()=>started++;
const rendered=tool.render({max_annotations:3},[]);
assert.equal(rendered.firstChild.className,'annotation-add');
assert.equal(rendered.firstChild.textContent,'Annotate webpage');
assert.equal(rendered.children[1].className,'annotation-empty');
assert.equal(rendered.children[1].textContent,'Select a detail on the webpage, then add a note.');
assert.equal(rendered.children.length,2);
rendered.firstChild.click();
assert.equal(started,1);
''')


def test_selection_start_and_cancel_keep_focus_on_current_controls():
    run_checks(FOCUS_SETUP + r'''
const {tool,view}=mount([]);
const add=view().firstChild;
add.focus();
add.click();
let cancel=view().firstChild.children[2];
assert.equal(page.activeElement,cancel);
assert.deepEqual(page.focusHistory,[add,cancel], 'start must not refocus the old add button during cancel(false)');
cancel.click();
assert.equal(page.activeElement,view().firstChild);
assert.equal(page.activeElement.textContent,'Annotate webpage');
view().firstChild.click();
tool.onKey({key:'Escape'});
assert.equal(page.activeElement,view().firstChild);
assert.equal(page.activeElement.textContent,'Annotate webpage');
''')


def test_saving_a_new_note_focuses_its_current_saved_target():
    run_checks(FOCUS_SETUP + r'''
const {tool,view}=mount(saved.slice(0,1));
tool.draft={...saved[1]};
tool.refresh();
const save=view().firstChild.children[2].children[1];
save.focus();
save.click();
assert.equal(page.activeElement,cards(view())[1].firstChild);
assert.equal(page.activeElement.textContent,'2. Chart point');
assert.notEqual(page.activeElement,save);
''')


def test_removing_a_note_focuses_the_current_add_action():
    run_checks(FOCUS_SETUP + r'''
const {view}=mount(saved);
const remove=cards(view())[1].children[2].children[1];
remove.focus();
remove.click();
assert.equal(cards(view()).length,2);
assert.equal(page.activeElement,view().firstChild);
assert.equal(page.activeElement.textContent,'Annotate webpage');
assert.notEqual(page.activeElement,remove);
''')


def test_canceling_an_edit_at_the_limit_focuses_a_remaining_target():
    run_checks(FOCUS_SETUP + r'''
const {tool,view}=mount(saved);
tool.draft={...saved[1]};
tool.refresh();
const cancel=view().firstChild.children[2].firstChild;
cancel.focus();
cancel.click();
assert.equal(page.activeElement,cards(view())[0].firstChild);
assert.notEqual(page.activeElement,cancel);
''')
