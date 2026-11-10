"""Exercise in-page confirmation results and cleanup without extra packages."""
import subprocess
from pathlib import Path

MODULE = (Path(__file__).parents[1] / "web" / "confirm.js").as_uri()
SETUP = r"""
import assert from 'node:assert/strict';
import { confirmAction } from MODULE;
class Element extends EventTarget {
  constructor(tag) {super();this.tagName=tag;this.children=[];this.attributes={};this.returnValue='';}
  append(...nodes) {for(const node of nodes){node.parent=this;this.children.push(node)}}
  setAttribute(name,value) {this.attributes[name]=value}
  getAttribute(name) {return this.attributes[name]}
  showModal() {this.open=true}
  close(value='') {this.returnValue=value;this.open=false;this.dispatchEvent(new Event('close'))}
  focus() {document.activeElement=this}
  click() {this.dispatchEvent(new Event('click'))}
  remove() {this.parent.children=this.parent.children.filter(child=>child!==this)}
}
const document={createElement:tag=>new Element(tag),body:new Element('body')};
globalThis.document=document;
const options={title:'Finish the study?',message:'Your answers cannot be changed after this.',confirmLabel:'Finish study'};
""".replace('MODULE', repr(MODULE))


def run_confirmation(checks):
    subprocess.run(['node', '--input-type=module', '-e', SETUP + checks], check=True)


def test_escape_cancels_without_committing_and_removes_the_modal():
    run_confirmation(r"""
const pending=confirmAction(options);
const dialog=document.body.children[0];
assert.equal(dialog.tagName,'dialog');
assert.equal(dialog.open,true);
const [title,message,actions]=dialog.children;
assert.equal(title.textContent,options.title);
assert.equal(message.textContent,options.message);
assert.equal(dialog.getAttribute('aria-labelledby'),title.id);
assert.equal(dialog.getAttribute('aria-describedby'),message.id);
assert.equal(document.activeElement,actions.children[0]);
assert.equal(document.activeElement.textContent,'Cancel');
const escape=new Event('cancel',{cancelable:true});
dialog.dispatchEvent(escape);
assert.equal(await pending,false);
assert.equal(escape.defaultPrevented,true);
assert.equal(document.body.children.length,0);
""")


def test_accept_then_reopen_and_cancel_does_not_reuse_the_previous_answer():
    run_confirmation(r"""
const first=confirmAction(options);
let dialog=document.body.children[0];
dialog.children[2].children[1].click();
assert.equal(await first,true);
assert.equal(document.body.children.length,0);
const second=confirmAction({...options,message:'<img src=x onerror=alert(1)>'});
dialog=document.body.children[0];
assert.equal(dialog.children[1].textContent,'<img src=x onerror=alert(1)>');
assert.equal(document.activeElement.textContent,'Cancel');
dialog.children[2].children[0].click();
assert.equal(await second,false);
assert.equal(document.body.children.length,0);
""")


def test_backdrop_click_does_not_accept_an_irreversible_action():
    run_confirmation(r"""
let settled=false;
const pending=confirmAction(options);
pending.then(()=>settled=true);
const dialog=document.body.children[0];
dialog.click();
await Promise.resolve();
assert.equal(settled,false);
dialog.children[2].children[0].click();
assert.equal(await pending,false);
""")
