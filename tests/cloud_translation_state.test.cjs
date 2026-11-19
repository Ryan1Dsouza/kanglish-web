// Generated hosted UI, using labelled synthetic responses and fake audio devices.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor() {this.children=[];this.value='';this.hidden=false;this.listeners={};this.classList={toggle(){},remove(){},add(){}};}
  append(...children) {this.children.push(...children);}
  replaceChildren(...children) {this.children=children;}
  addEventListener(name, callback) {this.listeners[name]=callback;}
  removeAttribute(name) {delete this[name];}
  focus() {}
  querySelectorAll() {return [];}
}
const elements = new Map();
for (const match of fs.readFileSync('public/index.html','utf8').matchAll(/<[^>]*\bid="([^"]+)"[^>]*>/g)) {
  assert.ok(!elements.has(match[1]), `Duplicate HTML id ${match[1]}`);
  const element=new Element();element.hidden=/\bhidden\b/.test(match[0]);elements.set(match[1],element);
}
let catalog=null, denyMicrophone=false, stoppedTracks=0, recorder=null, revoked=0, spoken=[];
const calls=[];
const voices=[{lang:'en-IN',name:'Synthetic English voice'}];
class Recorder {
  constructor() {this.state='inactive';this.mimeType='audio/webm;codecs=opus';recorder=this;}
  start() {this.state='recording';}
  stop() {this.state='inactive';this.ondataavailable({data:new Blob(['synthetic control '.repeat(20)],{type:this.mimeType})});this.onstop();}
}
class Reader {
  async readAsDataURL(blob) {this.result='data:'+blob.type+';base64,'+Buffer.from(await blob.arrayBuffer()).toString('base64');this.onload();}
}
const context=vm.createContext({
  Blob, FileReader:Reader, URL:{createObjectURL:()=> 'blob:synthetic-preview',revokeObjectURL:()=>revoked++},
  document:{getElementById:id=>{assert.ok(elements.has(id),`Missing HTML id ${id}`);return elements.get(id);},createElement:()=>new Element(),querySelectorAll:()=>[]},
  navigator:{mediaDevices:{async getUserMedia(){if(denyMicrophone)throw {name:'NotAllowedError'};return {getTracks:()=>[{stop(){stoppedTracks++;}}]};}}},
  window:{KanglishAuth:{csrf:'synthetic-csrf'},MediaRecorder:Recorder,addEventListener(){},scrollTo(){},
    localStorage:{getItem(){return null;},setItem(){}},speechSynthesis:{cancel(){},getVoices:()=>voices,speak(value){spoken.push(value);}},SpeechSynthesisUtterance:class {constructor(text){this.text=text;}}},
  setInterval(){},setTimeout(){return 1;},clearTimeout(){},
  async fetch(path, options) {
    const body=options?.body ? JSON.parse(options.body):null;calls.push({path,body});
    let result={};
    if(path==='/api/status')result={ready:true,audio_configured:true,verification_configured:true};
    else if(path==='/api/dictionaries/details')result=catalog||vm.runInContext('hostedDefaults',context);
    else if(path==='/api/dictionaries/create') {result={...body,count:0};catalog=[...vm.runInContext('hostedDefaults',context),result];}
    else if(path.startsWith('/api/dictionary?'))result=[];
    else if(path==='/api/translate'||path==='/api/audio/translate')result={id:'synthetic-result',input:body.text||'Synthetic transcript.',translation:body.target_language.endsWith('Knda')?'ನೀರ್':'Synthetic translation.',dialect:body.dialect,source_language:body.source_language,target_language:body.target_language,seconds:.01,engine:'Synthetic control'};
    return {ok:true,status:200,json:async()=>result};
  }
});
const el=id=>elements.get(id), run=code=>vm.runInContext(code,context);
vm.runInContext(fs.readFileSync('public/app.js','utf8'),context);

(async()=>{
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(el('source-language').children.length,5);
  assert.equal(el('target-language').children.length,5);
  assert.equal(el('record-audio').disabled,false);
  const defaults=run('hostedDefaults');assert.equal(defaults.length,20);
  for(const pair of defaults){
    await run(`hostedChoose(${JSON.stringify(pair.source_language)},${JSON.stringify(pair.target_language)})`);
    el('message').value='Synthetic source.';await run('translate()');
    const request=calls.at(-1);assert.equal(request.path,'/api/translate');
    assert.equal(request.body.source_language,pair.source_language);assert.equal(request.body.target_language,pair.target_language);
    assert.equal(el('source-language').value,pair.source_language);assert.equal(el('target-language').value,pair.target_language);
  }
  await run(`hostedChoose('en','kn-Latn')`);el('message').value='Synthetic original.';await run('translate()');
  await el('swap-languages').listeners.click();
  assert.equal(el('source-language').value,'kn-Latn');assert.equal(el('target-language').value,'en');
  assert.equal(el('message').value,'Synthetic translation.');assert.equal(el('translation').textContent,'Synthetic original.');
  assert.equal(run('current'),null);assert.equal(el('save-own-button').disabled,true);
  el('source-language').value='en';await el('source-language').listeners.change();
  assert.notEqual(el('source-language').value,el('target-language').value);
  el('new-dictionary-name').value='Synthetic travel';el('new-dictionary-source').value='en';el('new-dictionary-target').value='tcy-Knda';
  await el('create-dictionary').listeners.click();
  assert.equal(run('activeDialect'),'synthetic-travel');assert.equal(el('target-heading').textContent,'Tulu');
  assert.ok(el('dialect-switcher').children.some(button=>button.textContent==='Synthetic travel'));
  denyMicrophone=true;await el('record-audio').listeners.click();
  assert.match(el('notice').textContent,/denied/);assert.equal(run('hostedRecording'),false);assert.equal(el('source-language').disabled,false);
  denyMicrophone=false;await el('record-audio').listeners.click();
  assert.equal(run('hostedRecording'),true);assert.equal(el('swap-languages').disabled,true);assert.equal(el('stop-recording').hidden,false);
  el('stop-recording').listeners.click();
  assert.equal(stoppedTracks,1);assert.equal(run('hostedRecording'),false);assert.equal(el('audio-draft').hidden,false);
  assert.equal(calls.filter(call=>call.path==='/api/audio/translate').length,0,'Preview must not send audio');
  await el('translate-audio').listeners.click();
  const audio=calls.at(-1);assert.equal(audio.path,'/api/audio/translate');assert.equal(audio.body.target_language,'tcy-Knda');
  assert.ok(audio.body.audio.length>100);assert.equal(el('message').value,'Synthetic transcript.');
  assert.equal(calls.filter(call=>call.path==='/api/save').length,0,'Audio must not automatically save dictionary');
  el('read-aloud').listeners.click();assert.match(el('playback-status').textContent,/No Tulu voice/);assert.equal(spoken.length,0);
  await run(`hostedChoose('kn-Latn','en')`);el('message').value='Synthetic';await run('translate()');el('read-aloud').listeners.click();assert.equal(spoken.length,1);
  el('audio-file').files=[{type:'video/mp4',name:'invalid.mp4'}];el('audio-file').listeners.change();assert.match(el('notice').textContent,/Choose a WAV/);
  run(`hostedPreview(new Blob(['x'.repeat(1000001)],{type:'audio/wav'}))`);assert.equal(run('hostedAudio'),null);assert.equal(el('translate-audio').disabled,true);
  el('audio-file').files=[new Blob(['synthetic '.repeat(30)],{type:'audio/wav'})];el('audio-file').listeners.change();
  assert.equal(el('audio-draft').hidden,false);assert.equal(el('audio-preview').src,'blob:synthetic-preview');
  el('discard-audio').listeners.click();assert.equal(el('audio-draft').hidden,true);assert.ok(revoked>=2);
  await el('record-audio').listeners.click();recorder.onerror();assert.equal(run('hostedRecording'),false);assert.equal(stoppedTracks,2);
  console.log('Hosted selectors, all 20 directions, swap, dictionary creation, recording/upload and playback state checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
