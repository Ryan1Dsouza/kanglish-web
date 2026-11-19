// Browser-independent UI state checks. No browser, Windows input, or model calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor() { this.children = []; this.value = ''; this.hidden = false; this.className = ''; this.listeners = {}; this.classList = {toggle() {}, remove() {}, add() {}}; }
  append(...children) { for (const child of children) { child.parent = this; this.children.push(child); } }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  addEventListener(name, action) { this.listeners[name] = action; }
  focus(options) { this.focusOptions = options; this.focused = true; }
  scrollIntoView(options) { this.scrollOptions = options; }
  querySelector(selector) {
    for (const child of this.children) {
      if (child.className === selector.slice(1)) return child;
      const nested = child.querySelector?.(selector); if (nested) return nested;
    }
    return null;
  }
  remove() { this.parent.children = this.parent.children.filter(child => child !== this); }
}
const html = fs.readFileSync('mobile/desktop/index.html', 'utf8'), elements = new Map();
for (const match of html.matchAll(/<[^>]*\bid="([^"]+)"[^>]*>/g)) {
  const element = new Element(); element.hidden = /\bhidden\b/.test(match[0]); elements.set(match[1], element);
}
const calls = []; let rejectSave = false;
let rejectBulkImport = false;
let stopAtTranslation = 0;
let confirmed = false, confirmationMessages = [], rejectDelete = false;
let bulkImportResult = {saved:true,sentences:2,word_meanings:2,added:4,updated:0,unchanged:0,skipped:0,skipped_entries:[]};
const bulkPreview = {sentences: 2, word_meanings: 2, items: [
  {original:'ninna hesaru Rachit',english:'Your name is Rachit.',terms:[{original:'hesaru',english:'name'}],notes:[]},
  {original:'WhatsApp-alli maadu',english:'Do it on WhatsApp.',terms:[{original:'WhatsApp-alli',english:'on WhatsApp'}],notes:[]}
]};
let parsedTerms = [{original:'ninna',english:'your',origin:'pasted_mapping'},{original:'hesaru',english:'name',origin:'pasted_mapping'},{original:'Rachit',english:'Rachit',origin:'pasted_mapping'}];
const context = vm.createContext({
  document: {getElementById: id => {assert.ok(elements.has(id), `Missing HTML id ${id}`); return elements.get(id);}, querySelectorAll: () => [], createElement: () => new Element()},
  fetch: async (path, options) => {
    const body = options?.body ? JSON.parse(options.body) : null; calls.push({path, body});
    if (path === '/api/translate' && stopAtTranslation && calls.filter(call => call.path === '/api/translate').length === stopAtTranslation) elements.get('stop-batch').listeners.click();
    const result = path === '/api/status' ? {ready: true, token: 'local-test', verification_configured: true, gpu_layers: 99} :
      path === '/api/translate' ? {id:'synthetic-control',input:body.text,translation:'Water.',seconds:.01,engine:'Mocked control',source_label:'synthetic_control'} :
      path === '/api/save' ? rejectSave ? {error: 'Save failed'} : {saved: true, english: 'Your name is Rachit.'} :
      path === '/api/dictionary' ? [] :
      path.startsWith('/api/dictionary?') ? [] :
      path.startsWith('/api/dictionary/info?') ? {entries:8,version:17} :
      path === '/api/dictionaries/delete' ? rejectDelete ? {error:'The dictionary changed.'} : {removed:true} :
      path === '/api/dictionary/bulk-preview' ? bulkPreview :
      path === '/api/dictionary/bulk-import' ? rejectBulkImport ? {error:'Conflicting meaning. Nothing was imported.'} : bulkImportResult :
      path === '/api/glossary/parse' ? {terms:parsedTerms,ignored:[],notes:[]} :
      path.startsWith('/api/glossary/') && path !== '/api/glossary/save' ? [] :
      path === '/api/glossary/save' ? {saved: true, count: body.terms.length} : {};
    return {ok: !(rejectSave && path === '/api/save') && !(rejectBulkImport && path === '/api/dictionary/bulk-import') && !(rejectDelete && path === '/api/dictionaries/delete'), json: async () => result};
  },
  setInterval() {}, setTimeout, navigator: {}, window: {scrollTo() {}, confirm(message) {confirmationMessages.push(message); return confirmed;}}
});
vm.runInContext(fs.readFileSync('mobile/desktop/app.js', 'utf8'), context);

(async () => {
  await new Promise(resolve => setTimeout(resolve, 0));
  vm.runInContext(`showResult({id:'fixture',input:'ninna hesaru Rachit',context:'',translation:'What is your name?',seconds:.1});`, context);
  assert.equal(elements.get('glossary-card').hidden, true);
  elements.get('own-correction').value = 'Your name is Rachit.';
  rejectSave = true;
  await vm.runInContext(`save('own')`, context);
  assert.equal(elements.get('glossary-card').hidden, true, 'Failed save must not reveal a word editor');
  rejectSave = false;
  await vm.runInContext(`save('own')`, context);
  assert.equal(elements.get('glossary-card').hidden, false);
  vm.runInContext(`splitWords()`, context);
  let rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.map(row => row.querySelector('.glossary-original').value), ['ninna', 'hesaru', 'Rachit']);
  assert.equal(elements.get('bulk-word-input').hidden, false);
  elements.get('bulk-word-meanings').value = 'ninna->your, hesaru->name, Rachit->Rachit';
  const savesBeforeExtract = calls.filter(call => call.path === '/api/glossary/save').length;
  await vm.runInContext(`extractWordMeanings()`, context);
  rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.map(row => row.querySelector('.glossary-english').value), ['your', 'name', 'Rachit']);
  assert.equal(calls.filter(call => call.path === '/api/glossary/save').length, savesBeforeExtract, 'Extraction must not auto-save');
  await vm.runInContext(`saveGlossary()`, context);
  const request = calls.findLast(call => call.path === '/api/glossary/save');
  assert.equal(request.body.id, 'fixture');
  assert.deepEqual(request.body.terms, [{original:'ninna',english:'your',origin:'pasted_mapping'}, {original:'hesaru',english:'name',origin:'pasted_mapping'}, {original:'Rachit',english:'Rachit',origin:'pasted_mapping'}]);
  assert.match(elements.get('glossary-status').textContent, /Saved 3/);
  vm.runInContext(`showResult({id:'whatsapp',input:'WhatsApp-alli maadu',translation:'Do it on WhatsApp.',saved_english:'Do it on WhatsApp.',seconds:.1}); splitWords();`, context);
  rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.map(row => row.querySelector('.glossary-original').value), ['WhatsApp-alli', 'maadu'], 'Hyphenated words must stay together');
  parsedTerms = [{original:'WhatsApp-alli',english:'on WhatsApp',origin:'pasted_mapping'}];
  elements.get('bulk-word-meanings').value = 'WhatsApp-alli -> on WhatsApp';
  await vm.runInContext(`extractWordMeanings()`, context);
  rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.map(row => [row.querySelector('.glossary-original').value, row.querySelector('.glossary-english').value]), [['WhatsApp-alli','on WhatsApp'],['maadu','']]);
  await vm.runInContext(`saveGlossary()`, context);
  assert.deepEqual(calls.findLast(call => call.path === '/api/glossary/save').body.terms, parsedTerms);
  vm.runInContext(`showResult({id:'spaced',input:'WhatsApp alli maadu',translation:'Do it on WhatsApp.',saved_english:'Do it on WhatsApp.',seconds:.1}); splitWords();`, context);
  parsedTerms = [{original:'WhatsApp alli',english:'on WhatsApp',origin:'pasted_mapping'}];
  await vm.runInContext(`extractWordMeanings()`, context);
  vm.runInContext(`splitWords()`, context);
  rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.map(row => [row.querySelector('.glossary-original').value, row.querySelector('.glossary-english').value]), [['WhatsApp alli','on WhatsApp'],['maadu','']], 'Phrase mappings replace blank components and survive splitting again');
  vm.runInContext(`showResult({id:'manual',input:'WhatsApp alli maadu',translation:'Do it on WhatsApp.',saved_english:'Do it on WhatsApp.',seconds:.1}); splitWords();`, context);
  elements.get('glossary-editor').children[1].querySelector('.glossary-english').value = 'in / on';
  await vm.runInContext(`extractWordMeanings()`, context);
  rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.map(row => [row.querySelector('.glossary-original').value, row.querySelector('.glossary-english').value]), [['WhatsApp alli','on WhatsApp'],['alli','in / on'],['maadu','']], 'Manual suffix meanings must be preserved');
  const previousRows = rows.map(row => [row.querySelector('.glossary-original').value, row.querySelector('.glossary-english').value]);
  elements.get('add-glossary-row').listeners.click();
  rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.slice(0,-1).map(row => [row.querySelector('.glossary-original').value, row.querySelector('.glossary-english').value]), previousRows, 'Adding a phrase must preserve existing rows');
  assert.equal(rows.at(-1).querySelector('.glossary-original').focused, true, 'New phrase input receives focus');
  assert.equal(rows.at(-1).scrollOptions.block, 'center', 'New row is brought into view');
  const rowCount = rows.length;
  elements.get('add-glossary-row').listeners.click();
  assert.equal(elements.get('glossary-editor').children.length, rowCount, 'An existing completely blank row is reused');
  vm.runInContext(`showResult({id:'milkshake',input:'Ee milk shake thumba chill aagide.',translation:'This milkshake is very chilled.',saved_english:'This milkshake is very chilled.',seconds:.1}); splitWords();`, context);
  parsedTerms = [{original:'Ee milk shake',english:'This milkshake',origin:'pasted_mapping'}];
  elements.get('bulk-word-meanings').value = 'Ee milkshake -> This milkshake';
  await vm.runInContext(`extractWordMeanings()`, context);
  rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.map(row => [row.querySelector('.glossary-original').value, row.querySelector('.glossary-english').value]), [['Ee milk shake','This milkshake'],['thumba',''],['chill',''],['aagide','']], 'Aligned compound fills one row and replaces blank split components');
  vm.runInContext(`showResult({id:'technical',input:'Environment variables file .env C++ pointer check maadi.',translation:'Synthetic technical control.',saved_english:'Synthetic technical control.',seconds:.1}); splitWords();`, context);
  rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.map(row => row.querySelector('.glossary-original').value), ['Environment','variables','file','.env','C++','pointer','check','maadi'], 'Technical tokens retain dots and programming symbols');
  parsedTerms = [{original:'Environment variables file .env',english:'Environment variables .env file',origin:'pasted_mapping'}, {original:'C++ pointer',english:'C++ pointer',origin:'pasted_mapping'}];
  elements.get('bulk-word-meanings').value = 'Environment variables file .env -> Environment variables .env file, C++ pointer -> C++ pointer';
  await vm.runInContext(`extractWordMeanings()`, context);
  rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.map(row => [row.querySelector('.glossary-original').value, row.querySelector('.glossary-english').value]), [['Environment variables file .env','Environment variables .env file'],['C++ pointer','C++ pointer'],['check',''],['maadi','']], 'Technical phrase meanings fill combined rows without symbol-free leftovers');
  vm.runInContext(`showResult({id:'symbol-distinction',input:'env .env C C++ check maadi',translation:'Synthetic technical control.',saved_english:'Synthetic technical control.',seconds:.1}); splitWords();`, context);
  parsedTerms = [{original:'env',english:'environment',origin:'pasted_mapping'}, {original:'C',english:'C language',origin:'pasted_mapping'}];
  await vm.runInContext(`extractWordMeanings()`, context);
  rows = elements.get('glossary-editor').children;
  assert.deepEqual(rows.map(row => [row.querySelector('.glossary-original').value, row.querySelector('.glossary-english').value]), [['env','environment'],['.env',''],['C','C language'],['C++',''],['check',''],['maadi','']], 'Mapping plain terms must preserve distinct technical draft rows');
  vm.runInContext(`invalidateInput()`, context);
  assert.equal(elements.get('glossary-card').hidden, true, 'A changed input must hide the old sentence editor');
  elements.get('dictionary-bulk-text').value = 'Kanglish: ninna hesaru Rachit\nEnglish: Your name is Rachit.\nWord Mapping: hesaru -> name';
  const importsBefore = calls.filter(call => call.path === '/api/dictionary/bulk-import').length;
  await vm.runInContext(`dictionaryBulkAction(false)`, context);
  assert.equal(elements.get('dictionary-bulk-preview').hidden, false);
  assert.equal(elements.get('dictionary-bulk-preview').children.length, 2);
  assert.equal(calls.filter(call => call.path === '/api/dictionary/bulk-import').length, importsBefore, 'Preview never saves');
  assert.match(elements.get('dictionary-bulk-status').textContent, /Nothing saved/);
  bulkPreview.word_alternatives = [{original:'thumba',english:'very / very much'}];
  await vm.runInContext(`dictionaryBulkAction(false)`, context);
  assert.match(elements.get('dictionary-bulk-preview').children.at(-1).textContent, /thumba → very \/ very much/);
  assert.match(elements.get('dictionary-bulk-preview').children.at(-1).textContent, /Exact mappings stay linked/);
  bulkPreview.skipped_mapping_count = 1;
  bulkPreview.items[1].skipped_mappings = ['Mane kitchen drainage trap filter'];
  bulkPreview.items[1].notes = ['Skipped mappings that are not shorter contiguous phrases: Mane kitchen drainage trap filter'];
  await vm.runInContext(`dictionaryBulkAction(false)`, context);
  assert.match(elements.get('dictionary-bulk-status').textContent, /1 unmatched word mappings will be skipped/);
  assert.match(elements.get('dictionary-bulk-preview').children[1].children.at(-1).textContent, /Mane kitchen drainage trap filter/);
  bulkPreview.items[1].item = 164;
  bulkPreview.batch_conflict_count = 1;
  bulkPreview.batch_conflicts = [{item:163,original:'Auto rickshaw fair meter ride safe.',english:'Safe auto rickshaw ride with fair meter.',kind:'sentence',first_item:113,kept_english:'Safe ride with auto rickshaw fair meter.',reason:'Conflicts with item 113 (sentence: Safe ride with auto rickshaw fair meter.); first occurrence kept.'}];
  await vm.runInContext(`dictionaryBulkAction(false)`, context);
  assert.match(elements.get('dictionary-bulk-status').textContent, /1 conflicting batch entries will be skipped; first occurrences kept/);
  assert.match(elements.get('dictionary-bulk-preview').children[1].children[0].textContent, /^164\./, 'Preview preserves input numbering after skips');
  const conflictText = elements.get('dictionary-bulk-preview').children.at(-1).textContent;
  assert.match(conflictText, /Item 163: will skip sentence Auto rickshaw/);
  assert.match(conflictText, /Safe auto rickshaw ride with fair meter/);
  assert.match(conflictText, /Conflicts with item 113/);
  elements.get('dictionary-bulk-text').listeners.input();
  assert.equal(elements.get('dictionary-bulk-preview').hidden, true, 'Editing batch text invalidates preview');
  elements.get('dictionary-bulk-replace').checked = true;
  await vm.runInContext(`dictionaryBulkAction(true)`, context);
  assert.equal(calls.findLast(call => call.path === '/api/dictionary/bulk-import').body.replace_existing, true);
  assert.match(elements.get('dictionary-bulk-status').textContent, /Saved 2 sentences and 2 word meanings/);
  assert.notEqual(elements.get('dictionary-bulk-text').value, '', 'Keep pasted text available after importing');
  bulkImportResult = {saved:true,sentences:2,word_meanings:1,added:3,updated:0,unchanged:0,skipped:1,skipped_entries:[{original:'neeru',reason:'Already saved as a sentence entry; existing meaning kept.'}]};
  await vm.runInContext(`dictionaryBulkAction(true)`, context);
  assert.match(elements.get('dictionary-bulk-status').textContent, /1 skipped; existing meanings kept/);
  assert.equal(elements.get('dictionary-bulk-preview').hidden, false);
  assert.match(elements.get('dictionary-bulk-preview').children[0].textContent, /Skipped neeru:/);
  bulkImportResult = {saved:true,sentences:2,word_meanings:1,added:3,updated:0,unchanged:0,skipped:0,skipped_entries:[],skipped_mapping_count:1,skipped_mappings:[{item:95,original:'Mane kitchen drainage trap filter',reason:'Not a shorter contiguous word or phrase in this sentence.'}]};
  await vm.runInContext(`dictionaryBulkAction(true)`, context);
  assert.match(elements.get('dictionary-bulk-status').textContent, /1 unmatched word mappings skipped/);
  assert.match(elements.get('dictionary-bulk-preview').children[0].textContent, /Item 95: skipped mapping Mane kitchen drainage trap filter/);
  bulkImportResult = {saved:true,sentences:1,word_meanings:1,added:2,updated:0,unchanged:0,skipped:0,skipped_entries:[],batch_conflict_count:1,batch_conflicts:bulkPreview.batch_conflicts};
  await vm.runInContext(`dictionaryBulkAction(true)`, context);
  assert.match(elements.get('dictionary-bulk-status').textContent, /1 conflicting batch entries skipped; first occurrences kept/);
  assert.match(elements.get('dictionary-bulk-preview').children[0].textContent, /Item 163: skipped sentence Auto rickshaw/);
  rejectBulkImport = true;
  const refreshesBefore = calls.filter(call => call.path === '/api/dictionary').length;
  await vm.runInContext(`dictionaryBulkAction(true)`, context);
  assert.match(elements.get('dictionary-bulk-status').textContent, /Nothing was imported/);
  assert.equal(calls.filter(call => call.path === '/api/dictionary').length, refreshesBefore, 'A rejected import does not report success or refresh saved rows');
  assert.equal(elements.get('dictionary-bulk-import-button').disabled, false, 'Import remains available after a failure');
  elements.get('batch-input').value = Array(500).fill('neeru\tWater.').join('\n');
  elements.get('interval').value = '0'; elements.get('duration').value = '60';
  elements.get('batch-verify').checked = false; elements.get('batch-memory').checked = false;
  await vm.runInContext(`runBatch()`, context);
  assert.equal(calls.filter(call => call.path === '/api/translate').length, 500, 'All 500 mocked cases are accepted');
  assert.equal(elements.get('batch-rows').children.length, 500);
  assert.match(elements.get('batch-progress').textContent, /500\/500 completed/);
  assert.equal(calls.filter(call => call.path === '/api/save').length, 2, 'Batch tests do not automatically save corrections');
  elements.get('batch-input').value += '\nneeru\tWater.';
  await vm.runInContext(`runBatch()`, context);
  assert.equal(calls.filter(call => call.path === '/api/translate').length, 500, '501 cases are rejected before any requests');
  assert.match(elements.get('notice').textContent, /1 and 500/);
  elements.get('batch-input').value = Array(500).fill('neeru\tWater.').join('\n');
  stopAtTranslation = 503;
  await vm.runInContext(`runBatch()`, context);
  assert.equal(calls.filter(call => call.path === '/api/translate').length, 503, 'Stop completes current case and prevents further requests');
  assert.match(elements.get('batch-progress').textContent, /3\/500 completed.*stopped/);
  vm.runInContext(`activeDialect = 'custom';`, context);
  await vm.runInContext(`deleteDictionary()`, context);
  assert.equal(calls.filter(call => call.path === '/api/dictionaries/delete').length, 0, 'Cancelling sends no delete request');
  assert.match(confirmationMessages.at(-1), /custom.*8 saved entries/);
  confirmed = true; rejectDelete = true;
  await vm.runInContext(`deleteDictionary()`, context);
  assert.equal(vm.runInContext('activeDialect', context), 'custom', 'Failed deletion keeps the selected dictionary');
  assert.match(elements.get('notice').textContent, /dictionary changed/);
  rejectDelete = false;
  await vm.runInContext(`deleteDictionary()`, context);
  assert.deepEqual(calls.findLast(call => call.path === '/api/dictionaries/delete').body, {dialect:'custom',confirm_name:'custom',version:17});
  assert.equal(vm.runInContext('activeDialect', context), 'kanglish');
  assert.equal(elements.get('dictionary-delete-button').disabled, false);
  vm.runInContext(`dictionary = [{original:'control',english:'Synthetic.',kind:'glossary'}]; renderDictionary();`, context);
  confirmed = false;
  await elements.get('dictionary-rows').children[0].children[2].listeners.click();
  assert.equal(calls.filter(call => call.path === '/api/dictionary/delete').length, 0);
  confirmed = true;
  await elements.get('dictionary-rows').children[0].children[2].listeners.click();
  assert.equal(calls.filter(call => call.path === '/api/dictionary/delete').length, 1);
  console.log('Desktop word-editor state checks passed.');
})().catch(error => {console.error(error); process.exitCode = 1;});
