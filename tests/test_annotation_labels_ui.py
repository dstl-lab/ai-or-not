import subprocess
from pathlib import Path


def run_checks(checks):
    module = (Path(__file__).parents[1] / "web" / "annotations.js").as_uri()
    fixtures = r'''
import assert from 'node:assert/strict';
import { captureTarget, AnnotationTool } from MODULE;
function element(tag, attributes={}, text='') {
  return {tagName:tag, id:attributes.id || '', children:[], parentElement:null,
    innerText:text, textContent:text, style:{}, attributes,
    getAttribute(name){return this.attributes[name] ?? null},
    setAttribute(name,value){this.attributes[name]=value},
    append(...children){for(const child of children){this.children.push(child);child.parentElement=this}},
    get firstChild(){return this.children[0]},
    addEventListener(type,listener){(this.listeners ||= {})[type]=listener},
    click(){if(!this.disabled)this.listeners?.click?.()},
    focus(){if(!this.disabled){page.activeElement=this;(page.focusHistory ||= []).push(this)}},
    remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(child=>child!==this)},
    getBoundingClientRect:()=>({left:10,top:20,width:100,height:40})};
}
const page={addEventListener(){}, createElement:tag=>element(tag),
  getElementById:id=>named[id] || null, querySelector:selector=>targets[selector] || null,
  querySelectorAll:()=>[]};
const named={}, targets={};
function attach(parent, ...children) {
  parent.ownerDocument=page;
  parent.append(...children);
  for(const child of children) child.ownerDocument=page;
  return parent;
}
const win={location:{pathname:'/sites/alpha/',search:'',hash:''}, document:page,
  scrollX:0,scrollY:0,innerWidth:900,innerHeight:700,CSS:{escape:value=>value}};
const capture=target=>captureTarget(target,win,{home:'/sites/alpha/'});
const cards=box=>box.children.find(child=>child.className==='annotation-list').children
  .filter(child=>child.className==='annotation-card');
globalThis.document=page;
'''
    subprocess.run(
        ['node', '--input-type=module', '-e', (fixtures + checks).replace('MODULE', repr(module))],
        check=True,
    )


def test_chart_marks_include_the_nearest_chart_name():
    # A bare SVG tag or an outer chart name must not hide the selected chart.
    run_checks(r'''
const outer=element('DIV', {'role':'img','aria-label':'All charts'});
const chart=element('svg', {'aria-label':'Change in temperature'});
const point=element('circle');
attach(outer, attach(chart, point));
assert.equal(capture(point).quote,'Chart point · Change in temperature');
assert.equal(capture(chart).quote,'Chart · Change in temperature');
''')


def test_chart_names_use_accessible_labels_and_svg_titles():
    # Lost label references or ignored titles would make the selected marks ambiguous.
    run_checks(r'''
named['chart-title']=element('H2', {}, 'Monthly rainfall');
named['chart-subtitle']=element('P', {}, 'in millimeters');
const referenced=element('svg', {'aria-labelledby':'chart-title chart-subtitle'});
const line=element('line');
attach(referenced,line);
assert.equal(capture(line).quote,'Chart line · Monthly rainfall in millimeters');
const titled=element('svg');
const shape=element('path');
attach(titled,element('title', {}, 'Share by region'),shape);
assert.equal(capture(shape).quote,'Chart shape · Share by region');
const canvas=element('CANVAS', {'aria-label':'Daily sales'});
assert.equal(capture(canvas).quote,'Chart · Daily sales');
const chartWithTitle=element('svg', {'title':'Audience size'});
const area=element('polygon');
attach(chartWithTitle,area);
assert.equal(capture(area).quote,'Chart shape · Audience size');
''')


def test_unlabeled_graphics_have_readable_names_and_text_quotes_stay_normal():
    # Graphic fallback must not leak a tag name, alter real text, or exceed the API limit.
    run_checks(r'''
for(const [tag,label] of [['circle','Chart point'],['ellipse','Chart point'],
  ['line','Chart line'],['polyline','Chart line'],['path','Chart shape'],
  ['rect','Chart shape'],['polygon','Chart shape'],['g','Chart element'],
  ['svg','Chart'],['CANVAS','Chart']]) {
  assert.equal(capture(element(tag)).quote,label);
}
assert.equal(capture(element('H2', {}, '  A useful heading  ')).quote,'A useful heading');
assert.equal(capture(element('text', {}, '2026')).quote,'2026');
const chart=element('svg', {'aria-label':'x'.repeat(400)});
const point=element('circle');
attach(chart,point);
const quote=capture(point).quote;
assert.equal(quote.length,300);
assert.ok(quote.startsWith('Chart point · '));
''')


def test_legacy_graphic_labels_render_with_context_without_changing_saved_data():
    # Displaying a saved annotation must improve old labels without rewriting study data.
    run_checks(r'''
const chart=element('svg', {'aria-label':'Population by year'});
const point=element('circle');
attach(chart,point);
targets['#point']=point;
targets['#heading']=element('H2', {}, 'circle');
const entries=[
  {id:'one',page_path:'/sites/alpha/#chart',selector:'#point',quote:'circle',note:'A dense cluster.'},
  {id:'two',page_path:'/sites/alpha/',selector:'#missing',quote:'path',note:'The line.'},
  {id:'three',page_path:'/sites/alpha/',selector:'#heading',quote:'circle',note:'The wording.'},
];
const before=JSON.stringify(entries);
const tool=new AnnotationTool({change(){},refresh(){},warn(){}});
tool.frame={contentWindow:win};
let rendered=tool.render({max_annotations:3},entries);
assert.equal(cards(rendered)[0].firstChild.textContent,'1. Chart point · Population by year');
assert.equal(cards(rendered)[1].firstChild.textContent,'2. Chart shape');
assert.equal(cards(rendered)[2].firstChild.textContent,'3. circle');
assert.equal(cards(rendered)[0].children[1].textContent,'A dense cluster.');
assert.equal(JSON.stringify(entries),before);
tool.draft={...entries[0]};
rendered=tool.render({max_annotations:3},entries);
assert.equal(rendered.firstChild.firstChild.textContent,'Chart point · Population by year');
assert.equal(tool.draft.quote,'circle');
win.location.pathname='/sites/beta/';
rendered=tool.render({max_annotations:3},entries);
assert.equal(cards(rendered)[0].firstChild.textContent,'1. Chart point');
''')


def test_clicking_a_legacy_target_updates_its_label_when_the_chart_loads_later():
    # Reusing the existing button keeps keyboard focus when late chart context appears.
    run_checks(r'''
const entry={id:'one',page_path:'/sites/alpha/',selector:'#point',quote:'circle',note:'The cluster.'};
const chart=element('svg', {'aria-label':'Population by year'});
const point=element('circle');
attach(chart,point);
const tool=new AnnotationTool({change(){},refresh(){throw Error('The focused button must stay mounted')},warn(){}});
tool.frame={contentWindow:win};
tool.show=selected=>{
  assert.equal(selected,entry);
  targets['#point']=point;
};
const rendered=tool.render({max_annotations:3},[entry]);
const control=cards(rendered)[0].firstChild;
assert.equal(control.textContent,'1. Chart point');
page.activeElement=control;
control.click();
assert.equal(control.textContent,'1. Chart point · Population by year');
assert.equal(cards(rendered)[0].firstChild,control);
assert.equal(page.activeElement,control);
assert.equal(entry.quote,'circle');
''')
