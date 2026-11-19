// Hosted-only controls, inserted before event registration by build_web.py.
const hostedLanguages = {'en':['english','English'], 'kn-Latn':['kanglish','Kanglish'], 'tcy-Latn':['tuluglish','Tuluglish'], 'kn-Knda':['kannada','Kannada'], 'tcy-Knda':['tulu','Tulu']};
const hostedDefaults = Object.entries(hostedLanguages).flatMap(([source, [slug, label]]) => Object.entries(hostedLanguages).filter(([target]) => target !== source).map(([target,[other,targetLabel]]) => ({name:target === 'en' ? slug : `${slug}-${other}`,label:`${label} → ${targetLabel}`,source_language:source,target_language:target,count:0})));
let hostedCatalog = [...hostedDefaults], hostedRecording = false, hostedRecorder = null, hostedStream = null, hostedTimer = null, hostedAudio = null, hostedAudioUrl = null;
const hostedName = code => hostedLanguages[code]?.[1] || code;
const hostedPair = () => hostedCatalog.find(d => d.name === activeDialect) || hostedDefaults.find(d => d.name === 'kanglish');
function hostedFill(id, selected) {
  const select = $(id); select.replaceChildren();
  Object.entries(hostedLanguages).forEach(([code,[,label]]) => {const option=document.createElement('option'); option.value=code; option.textContent=label + (code === 'tcy-Knda' ? ' (Kannada script)' : ''); select.append(option);});
  select.value=selected;
}
function hostedLabels() {
  const pair=hostedPair();
  $('source-language').value=pair.source_language; $('target-language').value=pair.target_language;
  $('source-heading').textContent=hostedName(pair.source_language); $('target-heading').textContent=hostedName(pair.target_language);
  $('source-script').textContent=pair.source_language.endsWith('Knda') ? 'Kannada script' : 'English letters';
  $('selected-direction').textContent=pair.label;
  $('correction-label').textContent=`The correct ${hostedName(pair.target_language)} translation`;
  $('dictionary-source-label').textContent=hostedName(pair.source_language); $('dictionary-target-label').textContent=hostedName(pair.target_language);
  $('message').placeholder={'en':'Try: I want water.','kn-Latn':'Try: naale beligge sigona','tcy-Latn':'Try: Yenku neer korla.','kn-Knda':'ನನಗೆ ನೀರು ಬೇಕು.','tcy-Knda':'ಯೆಂಕ್ ನೀರ್ ಬೋಡು.'}[pair.source_language];
  $('dictionary-bulk-text').placeholder=`${hostedName(pair.source_language)}: Source sentence\n${hostedName(pair.target_language)}: Translation\nWord Mapping: source word -> target meaning`;
}
const oldHostedSetControls=setControls;
setControls=function() {
  oldHostedSetControls();
  const locked=busy || batchRunning || hostedRecording;
  ['source-language','target-language','swap-languages','create-dictionary','new-dictionary-source','new-dictionary-target','dictionary-save','dictionary-delete-button'].forEach(id => {$(id).disabled=locked;});
  $('translate-button').disabled=!status.ready || locked;
  ['copy-button','save-local-button','verify-button','save-own-button','save-verified-button','split-words-button','add-glossary-row','save-glossary-button','extract-word-meanings'].forEach(id => {if (hostedRecording) $(id).disabled=true;});
  $('message').readOnly=locked; $('context').readOnly=locked;
  $('dictionary-bulk-text').readOnly=locked;
  ['dictionary-bulk-preview-button','dictionary-bulk-import-button','dictionary-bulk-replace'].forEach(id => {if (hostedRecording) $(id).disabled=true;});
  $('record-audio').disabled=locked || !navigator.mediaDevices?.getUserMedia || !window.MediaRecorder;
  $('audio-file').disabled=locked; $('discard-audio').disabled=busy;
  $('translate-audio').disabled=locked || !hostedAudio || !status.audio_configured;
  $('read-aloud').disabled=!current?.translation || busy || !window.speechSynthesis;
  document.querySelectorAll('.dialect-pill,.dialect-add').forEach(button => {button.disabled=locked;});
};
function hostedStopPlayback() {window.speechSynthesis?.cancel(); $('playback-status').textContent='';}
const oldHostedInvalidate=invalidateInput;
invalidateInput=function() {hostedStopPlayback(); oldHostedInvalidate();};
const oldHostedShowResult=showResult;
showResult=function(row) {
  hostedStopPlayback();
  if (row.dialect) {
    activeDialect=row.dialect;
    if (!hostedCatalog.some(d => d.name === row.dialect) && row.source_language && row.target_language) hostedCatalog.push({name:row.dialect,source_language:row.source_language,target_language:row.target_language,label:`${hostedName(row.source_language)} → ${hostedName(row.target_language)}`,count:0});
    hostedLabels();
    renderDialectSwitcher(hostedCatalog);
  }
  oldHostedShowResult(row);
};
async function hostedSelect(name) {
  if (busy || batchRunning || hostedRecording) return;
  activeDialect=name; hostedDiscard(); invalidateInput(); clearDictionaryBulkPreview(); hostedLabels(); renderDialectSwitcher(hostedCatalog);
  try {window.localStorage?.setItem('kanglish-hosted-dictionary',name);} catch {}
  if (view_name === 'dictionary') await loadDictionary();
}
function hostedChoose(source,target) {
  const pair=hostedDefaults.find(d => d.source_language === source && d.target_language === target);
  if (pair) return hostedSelect(pair.name);
}
loadDialects=async function() {
  try {
    const entries=await api('/api/dictionaries/details');
    if (Array.isArray(entries)) hostedCatalog=entries;
    if (!hostedCatalog.some(d => d.name === activeDialect)) activeDialect='kanglish';
    hostedLabels(); renderDialectSwitcher(hostedCatalog);
  } catch (error) {notice(error.message,true);}
};
renderDialectSwitcher=function(entries) {
  const container=$('dialect-switcher'); container.replaceChildren();
  entries.filter(d => d.count || d.name === activeDialect || d.source_language === 'en' || d.target_language === 'en' || !hostedDefaults.some(default_ => default_.name === d.name)).forEach(d => {
    const button=document.createElement('button'); button.className='dialect-pill' + (d.name === activeDialect ? ' active' : ''); button.textContent=d.label + (d.count ? ` (${d.count})` : ''); button.disabled=busy || hostedRecording;
    button.addEventListener('click',()=>hostedSelect(d.name)); container.append(button);
  });
  const add=document.createElement('button'); add.className='dialect-add'; add.textContent='+ New'; add.disabled=busy || hostedRecording;
  add.addEventListener('click',()=>{view('dictionary'); $('create-dictionary-panel').open=true; $('new-dictionary-source').value=hostedPair().source_language; $('new-dictionary-target').value=hostedPair().target_language; $('new-dictionary-name').focus();}); container.append(add);
};
translate=async function() {
  if (busy || hostedRecording) return;
  if (!$('message').value.trim()) return notice('Enter a message first.',true);
  busy=true; notice(''); setControls();
  try {showResult(await api('/api/translate',{text:$('message').value,context:$('context').value,use_memory:$('use-memory').checked,dialect:activeDialect,source_language:hostedPair().source_language,target_language:hostedPair().target_language}));}
  catch (error) {notice(error.message,true);}
  finally {busy=false;setControls();}
};
$('source-language').addEventListener('change',()=>{const source=$('source-language').value; let target=$('target-language').value; if (source === target) target=hostedPair().source_language; hostedChoose(source,target);});
$('target-language').addEventListener('change',()=>{const target=$('target-language').value; let source=$('source-language').value; if (source === target) source=hostedPair().target_language; hostedChoose(source,target);});
$('swap-languages').addEventListener('click',async()=>{
  if (busy || hostedRecording) return;
  const pair=hostedPair(), input=$('message').value, translated=current?.translation;
  await hostedChoose(pair.target_language,pair.source_language);
  if (translated) {$('message').value=translated; invalidateInput(); $('translation').textContent=input; $('translation').classList.remove('placeholder'); $('timing').textContent='Languages and text swapped. Click Translate for the new direction.';}
});
$('create-dictionary').addEventListener('click',async()=>{
  if (busy || hostedRecording) return;
  busy=true;setControls();
  try {
    const label=$('new-dictionary-name').value.trim(), name=label.toLowerCase().replace(/[^a-z0-9_-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,40);
    const created=await api('/api/dictionaries/create',{name,label,source_language:$('new-dictionary-source').value,target_language:$('new-dictionary-target').value});
    await loadDialects(); busy=false; await hostedSelect(created.name); $('new-dictionary-name').value=''; notice('Dictionary saved in your account.');
  } catch(error) {notice(error.message,true);} finally {busy=false;setControls();}
});
function hostedDiscard() {
  hostedAudio=null; if (hostedAudioUrl) URL.revokeObjectURL(hostedAudioUrl); hostedAudioUrl=null;
  $('audio-preview').removeAttribute?.('src'); $('audio-draft').hidden=true;
  $('audio-status').textContent='Record up to 30 seconds or choose an audio file under 1 MB. Audio is sent only when you click Translate audio.';
}
function hostedPreview(blob) {
  hostedDiscard();
  if (!blob.size || blob.size > 1000000) {notice('Use an audio file under 1 MB.',true);setControls();return;}
  hostedAudio=blob; hostedAudioUrl=URL.createObjectURL(blob); $('audio-preview').src=hostedAudioUrl; $('audio-draft').hidden=false;
  $('audio-status').textContent='Ready. Translate audio sends this recording to Google and returns a transcript and translation. Nothing is saved to your dictionary automatically.';setControls();
}
function hostedFinishCapture() {
  clearTimeout(hostedTimer);hostedStream?.getTracks().forEach(track=>track.stop());hostedStream=null;hostedRecorder=null;hostedRecording=false;$('stop-recording').hidden=true;setControls();
}
$('record-audio').addEventListener('click',async()=>{
  if (busy || hostedRecording) return;
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) return notice('Microphone recording is unavailable. Choose an audio file instead.',true);
  hostedRecording=true;setControls();hostedDiscard();
  try {
    hostedStream=await navigator.mediaDevices.getUserMedia({audio:true});
    hostedRecorder=new window.MediaRecorder(hostedStream,{audioBitsPerSecond:64000}); const chunks=[];
    hostedRecorder.ondataavailable=event=>{if(event.data.size)chunks.push(event.data);};
    hostedRecorder.onstop=()=>{const mime=hostedRecorder.mimeType || 'audio/webm';hostedFinishCapture();if(chunks.length)hostedPreview(new Blob(chunks,{type:mime}));};
    hostedRecorder.onerror=()=>{if(hostedRecorder)hostedRecorder.onstop=null;hostedFinishCapture();notice('Recording failed. Try again or choose a file.',true);};
    hostedRecorder.start();$('stop-recording').hidden=false;$('audio-status').textContent='Recording microphone… Stop when finished. It will stop automatically after 30 seconds.';
    hostedTimer=setTimeout(()=>{if(hostedRecorder?.state === 'recording')hostedRecorder.stop();},30000);
  } catch(error) {hostedFinishCapture();notice(error.name === 'NotAllowedError' ? 'Microphone access was denied. Allow it in your browser or choose an audio file.' : 'Microphone could not start. Choose an audio file instead.',true);}
});
$('stop-recording').addEventListener('click',()=>{if(hostedRecorder?.state === 'recording')hostedRecorder.stop();});
$('audio-file').addEventListener('change',()=>{
  if(busy || hostedRecording)return;
  const file=$('audio-file').files?.[0];if(!file)return;
  const mime=file.type || ({wav:'audio/wav',mp3:'audio/mpeg',m4a:'audio/mp4',webm:'audio/webm',ogg:'audio/ogg',flac:'audio/flac'}[file.name.split('.').at(-1).toLowerCase()]);
  if (!mime || !['audio/wav','audio/x-wav','audio/mpeg','audio/mp3','audio/mp4','audio/x-m4a','audio/webm','audio/ogg','audio/flac','audio/x-flac'].includes(mime.split(';')[0])) {$('audio-file').value='';return notice('Choose a WAV, MP3, M4A, WebM, Ogg or FLAC audio file.',true);}
  hostedPreview(new Blob([file],{type:mime}));$('audio-file').value='';
});
$('discard-audio').addEventListener('click',()=>{hostedDiscard();setControls();});
$('translate-audio').addEventListener('click',async()=>{
  if(!hostedAudio || busy || hostedRecording)return;
  busy=true;setControls();$('audio-status').textContent='Transcribing and translating audio…';
  try {
    const audio=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(hostedAudio);});
    const row=await api('/api/audio/translate',{audio,mime_type:hostedAudio.type,dialect:activeDialect,source_language:hostedPair().source_language,target_language:hostedPair().target_language,context:$('context').value});
    showResult(row);$('audio-status').textContent='Transcript and translation ready. Review both before saving.';
  }catch(error){$('audio-status').textContent=error.message;notice(error.message,true);}finally{busy=false;setControls();}
});
$('read-aloud').addEventListener('click',()=>{
  if(!current?.translation || !window.speechSynthesis)return;
  hostedStopPlayback();const code=current.target_language || hostedPair().target_language, language=code === 'en' ? 'en' : code.startsWith('tcy') ? 'tcy' : 'kn';
  const voice=window.speechSynthesis.getVoices().find(v=>v.lang.toLowerCase().startsWith(language));
  if(language !== 'en' && !voice){$('playback-status').textContent=`No ${language === 'tcy' ? 'Tulu' : 'Kannada'} voice is installed in this browser. Audio translation remains available.`;return;}
  const utterance=new window.SpeechSynthesisUtterance(current.translation);utterance.lang=voice?.lang || 'en-IN';if(voice)utterance.voice=voice;
  utterance.onerror=()=>{$('playback-status').textContent='Playback is unavailable. Check the browser voices.';};
  $('playback-status').textContent=`Reading with ${voice?.name || 'English voice'}. Pronunciation of English-letter spellings may vary.`;window.speechSynthesis.speak(utterance);
});
$('stop-playback').addEventListener('click',hostedStopPlayback);
window.addEventListener?.('beforeunload',()=>{hostedStream?.getTracks().forEach(track=>track.stop());hostedStopPlayback();});
hostedFill('source-language','kn-Latn');hostedFill('target-language','en');hostedFill('new-dictionary-source','en');hostedFill('new-dictionary-target','kn-Latn');
try {activeDialect=window.localStorage?.getItem('kanglish-hosted-dictionary') || 'kanglish';}catch{}
hostedLabels();
