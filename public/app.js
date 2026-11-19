"use strict";
const $ = id => document.getElementById(id);
let token = window.KanglishAuth.csrf, status = {}, current = null, busy = false, batchRunning = false, stopRequested = false;
let dictionary = [];
let activeDialect = "kanglish";
let view_name = "translate";const examples = [
  ["neeru", "Water.", "single word"],
  ["oota aayta", "Have you eaten?", "everyday question"],
  ["ninna hesaru Rachit", "Your name is Rachit.", "person name"],
  ["Rachit naale beligge elu gantege Mysurige hogona ivattu beda", "Rachit, let's go to Mysuru tomorrow morning at seven, not today.", "names and time"],
  ["neenu ninne yaake baralilla", "Why didn't you come yesterday?", "past negation"],
  ["naanu ivattu baruvudilla", "I won't come today.", "future negation"],
  ["nan ivat baralla", "I won't come today.", "phonetic variation"],
  ["nanage hasivu aagide aadre maneyalli oota illa", "I'm hungry, but there's no food at home.", "multiple clauses"],
  ["sumne iru bevarsi", "Be quiet, you bastard. (Colloquial insult; severity depends on usage.)", "profanity"],
  ["sari", "Context needed: okay, correct, or another sense.", "ambiguity"]
];
function notice(message, error = false) {
  $("notice").textContent = message; $("notice").hidden = !message;
  $("notice").classList.toggle("error", error);
}
async function api(path, body) {
  let response = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json", "X-Kanglish-Token": token}, body: JSON.stringify(body)
  });
  if (response.status === 401) {
    const refreshed = await window.KanglishAuth.refresh();
    token = refreshed.csrf;
    response = await fetch(path, body === undefined ? {} : {
      method: "POST", headers: {"Content-Type": "application/json", "X-Kanglish-Token": token}, body: JSON.stringify(body)
    });
  }
  const result = await response.json();
  if (!response.ok || (result.error && !result.id)) throw new Error(result.error || "Request failed.");
  return result;
}
function view(name) {
  view_name = name;
  document.querySelectorAll(".view").forEach(section => {section.hidden = section.id !== `${name}-view`;});
  document.querySelectorAll(".nav").forEach(button => button.classList.toggle("active", button.dataset.view === name));
  $("breadcrumb").textContent = {translate: "TRANSLATE", batch: "BATCH TESTS", dictionary: "MY DICTIONARY"}[name];
  if (name === "dictionary") loadDictionary();
}
async function loadDialects() {
  try {
    const dialects = await api("/api/dictionaries");
    renderDialectSwitcher(dialects);
  } catch {}
}
function renderDialectSwitcher(dialects) {
  const container = $("dialect-switcher");
  container.replaceChildren();
  const labels = {kanglish: "Kanglish", tuluglish: "Tuluglish"};
  Object.entries(dialects).sort(([a], [b]) => a.localeCompare(b)).forEach(([name, count]) => {
    const btn = document.createElement("button");
    btn.className = "dialect-pill" + (name === activeDialect ? " active" : "");
    btn.textContent = (labels[name] || name) + (count ? ` (${count})` : "");
    btn.addEventListener("click", () => {
      activeDialect = name;
      loadDialects();
      if (view_name === "dictionary") loadDictionary();
    });
    container.append(btn);
  });
  const add = document.createElement("button");
  add.className = "dialect-add"; add.textContent = "+ New";
  add.addEventListener("click", () => {
    const name = prompt("New dictionary name (lowercase letters, numbers, hyphens; e.g. tuluglish):");
    if (!name) return;
    if (!/^[a-z][a-z0-9_-]{1,39}$/.test(name)) { notice("Dictionary name: start with a letter, then lowercase letters, numbers or hyphens only.", true); return; }
    activeDialect = name; loadDialects(); if (view_name === "dictionary") loadDictionary();
  });
  container.append(add);
}
function setControls() {
  $("translate-button").disabled = !status.ready || busy || batchRunning;
  $("run-batch").disabled = true;
  const available = Boolean(current && !current.error && current.translation && !busy && !batchRunning);
  ["copy-button", "save-local-button", "verify-button", "save-own-button"].forEach(id => {$(id).disabled = !available;});
  $("save-verified-button").disabled = !available;
  ["split-words-button", "add-glossary-row", "save-glossary-button", "extract-word-meanings"].forEach(id => {$(id).disabled = !available || !current?.saved_english;});
  $("message").readOnly = busy; $("context").readOnly = busy;
  $("translate-button").textContent = busy ? "Working…" : "Translate ↗";
  $("verify-button").disabled = !available || !status.verification_configured;
  $("verify-button").title = status.verification_configured ? "Send this message and relevant context for cloud review" : "Verification is unavailable for this deployment";
  ["dictionary-bulk-preview-button", "dictionary-bulk-import-button"].forEach(id => {$(id).disabled = !token || busy || batchRunning;});
  $("dictionary-bulk-text").readOnly = busy || batchRunning;
  $("dictionary-bulk-replace").disabled = busy || batchRunning;
}
function showReview(review) {
  $("verification-card").hidden = !review;
  if (!review) return;
  $("verdict").textContent = {match: "Agrees with translation", mismatch: "Suggests a correction", uncertain: "Needs context"}[review.verdict];
  $("verified-translation").textContent = review.translation;
  $("verified-translation").hidden = !review.translation;
  $("verification-explanation").textContent = review.explanation;
  $("verification-timing").textContent = `Verification: ${review.seconds.toFixed(2)} s`;
  $("save-verified-button").hidden = review.verdict === "uncertain" || !review.translation;
}
function showResult(row) {
  current = row;
  $("message").value = row.input; $("context").value = row.context || "";
  $("char-count").textContent = `${row.input.length.toLocaleString()} / 1,000`;
  $("translation").textContent = row.error || row.translation;
  $("translation").classList.remove("placeholder");
  $("result-engine").textContent = row.engine === "Saved translation" ? "Saved meaning" : "Online model";
  $("timing").textContent = row.error ? "" : `${row.seconds.toFixed(3)} s · ${row.engine}`;
  $("result-warning").textContent = row.warning || ""; $("result-warning").hidden = !row.warning;
  $("own-correction").value = ""; $("saved-status").textContent = row.saved_english ? "Saved in your private account." : "";
  $("glossary-card").hidden = true; $("glossary-editor").replaceChildren(); $("glossary-status").textContent = "";
  $("bulk-word-input").hidden = true; $("bulk-word-meanings").value = "";
  showReview(row.verification); setControls();
}
function invalidateInput() {
  current = null; showReview(null); $("saved-status").textContent = "";
  $("glossary-card").hidden = true; $("glossary-editor").replaceChildren();
  $("bulk-word-input").hidden = true; $("bulk-word-meanings").value = "";
  $("translation").textContent = "Your translation will appear here.";
  $("translation").classList.add("placeholder"); $("timing").textContent = "";
  $("result-warning").hidden = true;
  $("char-count").textContent = `${$("message").value.length.toLocaleString()} / 1,000`;
  setControls();
}
async function translate() {
  if (!$("message").value.trim()) return notice("Enter a Kanglish message first.", true);
  busy = true; notice(""); setControls();
  try {
    const row = await api("/api/translate", {text: $("message").value, context: $("context").value, use_memory: $("use-memory").checked, dialect: activeDialect});
    showResult(row);
  } catch (error) {notice(error.message, true);}
  finally {busy = false; setControls();}
}
async function verify() {
  if (!current) return;
  busy = true; setControls(); $("verify-button").textContent = "Checking…"; notice("");
  const id = current.id;
  try {
    const review = await api("/api/verify", {id});
    if (current && current.id === id) {current.verification = review; showReview(review);}
  } catch (error) {notice(error.message, true);}
  finally {busy = false; $("verify-button").textContent = "Verify translation"; setControls();}
}
async function save(choice) {
  if (!current) return;
  busy = true; setControls();
  try {
    const saved = await api("/api/save", {id: current.id, choice, english: $("own-correction").value});
    current.saved_english = saved.english;
    $("saved-status").textContent = "Saved in your private account for next time.";
    notice(`Saved: ${saved.english}`);
    if (choice === "own") await openGlossary();
  } catch (error) {notice(error.message, true);}
  finally {busy = false; setControls();}
}
function addGlossaryRow(original = "", english = "", origin = "manual") {
  if ($("glossary-editor").children.length >= 80) return notice("Use at most 80 word or phrase rows.", true);
  const row = document.createElement("div"); row.className = "glossary-row"; row.mappingOrigin = origin;
  const sourceLabel = document.createElement("label"), meaningLabel = document.createElement("label");
  sourceLabel.textContent = "Kanglish word or phrase"; meaningLabel.textContent = "English meaning";
  const source = document.createElement("input"), meaning = document.createElement("input"), arrow = document.createElement("span"), remove = document.createElement("button");
  source.className = "glossary-original"; source.maxLength = 120; source.value = original; source.placeholder = "hesaru";
  meaning.className = "glossary-english"; meaning.maxLength = 400; meaning.value = english; meaning.placeholder = "name";
  arrow.className = "meaning-arrow"; arrow.textContent = "→";
  remove.textContent = "Remove"; remove.addEventListener("click", () => row.remove());
  sourceLabel.append(source); meaningLabel.append(meaning); row.append(sourceLabel, arrow, meaningLabel, remove);
  $("glossary-editor").append(row);
  return row;
}
function addManualGlossaryRow() {
  const blank = [...$("glossary-editor").children].find(row => !row.querySelector(".glossary-original").value.trim() && !row.querySelector(".glossary-english").value.trim());
  const row = blank || addGlossaryRow();
  if (!row) {
    $("glossary-status").textContent = "This sentence has 80 rows. Edit an existing row to combine words into a phrase.";
    return;
  }
  row.querySelector(".glossary-original").focus({preventScroll: true});
  row.scrollIntoView({behavior: "smooth", block: "center"});
}
async function openGlossary() {
  const id = current?.id;
  if (!id) return;
  $("glossary-card").hidden = false;
  $("glossary-parent").textContent = `${current.input}\n${current.saved_english}`;
  $("glossary-editor").replaceChildren(); $("glossary-status").textContent = "";
  const rows = await api(`/api/glossary/${id}`);
  if (current?.id !== id) return;
  rows.forEach(row => addGlossaryRow(row.original, row.english, row.source === "desktop_user_glossary_from_paste" ? "pasted_mapping" : "manual"));
  if (!rows.length) addGlossaryRow();
}
function glossaryWords(text) {
  return text.match(/(?<![\p{L}\p{M}\p{N}_.@/+#])[.@]?[\p{L}\p{M}\p{N}_]+(?:[-'’./@][\p{L}\p{M}\p{N}_]+)*(?:\+\+|#|\+)?(?![\p{L}\p{M}\p{N}_@/+#]|[.-](?=[\p{L}\p{M}\p{N}_]))/gu) || [];
}
function mergeGlossaryDraft(draft, terms) {
  const parts = text => glossaryWords(text.toLowerCase()).map(word => /[./@+#_]/.test(word) ? word : word.replace(/[-'’]/g, " ")).join(" ");
  for (const term of terms) {
    let position;
    const phrase = ` ${parts(term.original)} `;
    const kept = [];
    for (const row of draft) {
      const same = row.original.trim().toLowerCase() === term.original.trim().toLowerCase();
      const coveredBlank = !row.english.trim() && parts(row.original) && phrase.includes(` ${parts(row.original)} `);
      if (same || coveredBlank) { if (position === undefined) position = kept.length; }
      else kept.push(row);
    }
    draft = kept;
    draft.splice(position === undefined ? draft.length : position, 0, term);
  }
  return draft;
}
function splitWords() {
  if (!current) return;
  $("bulk-word-input").hidden = false;
  const words = [...new Set(glossaryWords(current.input))];
  const existing = [...$("glossary-editor").children].map(row => ({original: row.querySelector(".glossary-original").value.trim(), english: row.querySelector(".glossary-english").value, origin: row.mappingOrigin || "manual"})).filter(row => row.original && row.english.trim());
  const draft = mergeGlossaryDraft(words.slice(0, 80).map(original => ({original, english: "", origin: "manual"})), existing);
  if (draft.length > 80) return notice("The combined draft has more than 80 rows. Remove some before splitting.", true);
  $("glossary-editor").replaceChildren();
  draft.forEach(row => addGlossaryRow(row.original, row.english, row.origin));
  if (words.length > 80) notice("Split the first 80 words. Add meanings for a shorter sentence if needed.", true);
}
async function extractWordMeanings() {
  if (!current) return;
  const id = current.id; busy = true; setControls();
  try {
    const result = await api("/api/glossary/parse", {id, text: $("bulk-word-meanings").value});
    if (current?.id !== id) return;
    // A phrase mapping replaces its blank component rows, preserving manually
    // entered meanings rather than guessing meanings for individual suffixes.
    const draft = [...$("glossary-editor").children].map(row => ({
      original: row.querySelector(".glossary-original").value.trim(), english: row.querySelector(".glossary-english").value.trim(), origin: row.mappingOrigin || "manual"
    })).filter(row => row.original);
    const merged = mergeGlossaryDraft(draft, result.terms);
    if (merged.length > 80) throw new Error("The combined draft has more than 80 rows. Remove some before extracting.");
    $("glossary-editor").replaceChildren();
    merged.forEach(row => addGlossaryRow(row.original, row.english, row.origin));
    const ignored = result.ignored.length ? ` Ignored words outside this sentence: ${result.ignored.join(", ")}.` : "";
    $("glossary-status").textContent = `Extracted ${result.terms.length} meanings. Review, then Save word meanings.${ignored}`;
    notice(result.notes.join(" ") || "Pasted meanings extracted for review. Nothing has been saved yet.");
  } catch (error) {notice(error.message, true);}
  finally {busy = false; setControls();}
}
async function saveGlossary() {
  if (!current) return;
  const terms = [...$("glossary-editor").children].map(row => ({original: row.querySelector(".glossary-original").value.trim(), english: row.querySelector(".glossary-english").value.trim(), origin: row.mappingOrigin || "manual"})).filter(row => row.original || row.english);
  if (terms.some(row => !row.original && row.english)) return notice("A meaning needs its original word or phrase.", true);
  const filled = terms.filter(row => row.original && row.english);
  if (!filled.length) return notice("Enter at least one word meaning. Blank meanings are skipped.", true);
  busy = true; setControls();
  const id = current.id;
  try {
    const result = await api("/api/glossary/save", {id, terms: filled});
    if (current?.id === id) $("glossary-status").textContent = `Saved ${result.count} word meanings. Included in dictionary export.`;
    notice("Word meanings saved. The sentence correction is preserved.");
  } catch (error) {notice(error.message, true);}
  finally {busy = false; setControls();}
}
function cell(text, small) {
  const td = document.createElement("td"); td.textContent = text;
  if (small) {const detail = document.createElement("small"); detail.textContent = small; td.append(detail);}
  return td;
}
function addBatchRow(row) {
  $("batch-empty").hidden = true;
  const tr = document.createElement("tr"), review = row.verification;
  tr.append(cell(row.input, row.expected_meaning), cell(row.error || row.translation, row.engine),
    cell(row.verification_error || (review ? review.translation || review.explanation : "Not requested"), review?.verdict),
    cell(`${row.seconds.toFixed(3)} s`, review ? `Check: ${review.seconds.toFixed(2)} s` : ""));
  const action = document.createElement("td"), button = document.createElement("button");
  button.textContent = "Review"; button.disabled = Boolean(row.error);
  button.addEventListener("click", () => {view("translate"); showResult(row); window.scrollTo({top: 0, behavior: "smooth"});});
  action.append(button); tr.append(action); $("batch-rows").append(tr);
}
async function runBatch() {
  const lines = $("batch-input").value.split(/\r?\n/).filter(line => line.trim());
  const maxCases = status.batch_case_limit || 500;
  if (!lines.length || lines.length > maxCases) return notice(`Enter between 1 and ${maxCases} test cases.`, true);
  const seconds = Number($("interval").value), minutes = Number($("duration").value);
  if (!Number.isFinite(seconds) || seconds < 0 || seconds > 60 || !Number.isFinite(minutes) || minutes < 1 || minutes > 60) return notice("Use an interval of 0–60 seconds and duration of 1–60 minutes.", true);
  if ($("batch-verify").checked && !status.verification_configured) return notice("Configure your verification key before enabling cloud checks.", true);
  batchRunning = true; stopRequested = false; setControls(); notice("");
  $("stop-batch").hidden = false; $("batch-rows").replaceChildren(); $("batch-empty").hidden = false;
  const deadline = Date.now() + minutes * 60000; let completed = 0, verificationFailures = 0;
  const useMemory = $("batch-memory").checked, doVerify = $("batch-verify").checked;
  try {
    for (let i = 0; i < lines.length && !stopRequested && Date.now() < deadline; i++) {
      const [text, ...reference] = lines[i].split("\t");
      const example = examples.find(example => example[0] === text.trim() && example[1] === reference.join("\t").trim());
      $("batch-progress").textContent = `Translating ${i + 1} of ${lines.length}…`;
      const row = await api("/api/translate", {text: text.trim(), context: "", expected: reference.join("\t").trim(),
        category: example ? example[2] : "batch input", synthetic: Boolean(example), use_memory: useMemory, batch: true});
      if (!row.error && doVerify && verificationFailures < 2 && Date.now() < deadline) {
        $("batch-progress").textContent = `Verifying ${i + 1} of ${lines.length}…`;
        try {row.verification = await api("/api/verify", {id: row.id}); verificationFailures = 0;}
        catch (error) {row.verification_error = error.message; verificationFailures++;}
      }
      addBatchRow(row); completed++;
      $("batch-progress").textContent = `Completed ${completed}/${lines.length}`;
      if (verificationFailures >= 2) notice("Cloud verification failed twice. Continuing local tests; corrections remain unsaved.", true);
      if (seconds > 0 && i + 1 < lines.length) {
        const until = Math.min(Date.now() + seconds * 1000, deadline);
        while (!stopRequested && Date.now() < until) await new Promise(resolve => setTimeout(resolve, 200));
      }
    }
    $("batch-progress").textContent = `${completed}/${lines.length} completed${stopRequested ? " · stopped" : Date.now() >= deadline ? " · timer reached" : ""}. Review results to save corrections.`;
  } catch (error) {notice(error.message, true); $("batch-progress").textContent = `${completed}/${lines.length} completed · stopped after error.`;}
  finally {batchRunning = false; $("stop-batch").hidden = true; setControls();}
}
async function loadDictionary() {
  try {dictionary = await api(`/api/dictionary?dialect=${encodeURIComponent(activeDialect)}`); renderDictionary();}
  catch (error) {notice(error.message, true);}
}
function renderDictionary() {
  $("dictionary-count").textContent = `(${dictionary.length}) · ${activeDialect}`;
  const exportLink = $("export-dict-link");
  if (exportLink) { exportLink.href = `/api/corrections.json?dialect=${encodeURIComponent(activeDialect)}`; exportLink.download = `kanglish-${activeDialect}-corrections.json`; }
  const container = $("dictionary-rows"), query = $("dictionary-search").value.toLowerCase();
  container.replaceChildren();
  const srcLabel = {kanglish: "Kanglish → English", tuluglish: "Tuluglish → English"}[activeDialect] || `${activeDialect} → English`;
  for (const row of dictionary.filter(row => `${row.original} ${row.english}`.toLowerCase().includes(query))) {
    const element = document.createElement("div"); element.className = "dictionary-row";
    const original = document.createElement("div"), english = document.createElement("div"), remove = document.createElement("button");
    original.textContent = row.original; english.textContent = row.english;
    const detail = document.createElement("small"); detail.textContent = `${srcLabel} · ${row.kind === "glossary" ? "word / phrase" : "sentence"} · approved by you`; original.append(detail);
    remove.textContent = "Remove";
    remove.addEventListener("click", async () => {
      try {await api("/api/dictionary/delete", {original: row.original, dialect: activeDialect}); await loadDictionary(); notice("Saved meaning removed.");}
      catch (error) {notice(error.message, true);}
    });
    element.append(original, english, remove); container.append(element);
  }
  if (!container.children.length) {const p = document.createElement("p"); p.className = "subtle"; p.textContent = dictionary.length ? "No matching translations." : "Save a correction to start your dictionary."; container.append(p);}
}
function clearDictionaryBulkPreview() {
  $("dictionary-bulk-preview").replaceChildren(); $("dictionary-bulk-preview").hidden = true;
  $("dictionary-bulk-status").textContent = "";
  $("dictionary-bulk-status").classList.remove("error");
}
async function dictionaryBulkAction(importNow) {
  if (busy || batchRunning) return;
  clearDictionaryBulkPreview();
  busy = true; setControls();
  $("dictionary-bulk-status").textContent = importNow ? "Importing batch…" : "Checking batch…";
  try {
    const result = await api(importNow ? "/api/dictionary/bulk-import" : "/api/dictionary/bulk-preview", {
      text: $("dictionary-bulk-text").value, replace_existing: $("dictionary-bulk-replace").checked, dialect: activeDialect
    });
    const conflicts = result.batch_conflict_count ? ` ${result.batch_conflict_count} conflicting batch entries ${importNow ? "skipped" : "will be skipped"}; first occurrences kept.` : "";
    if (importNow) {
      const skipped = result.skipped ? ` ${result.skipped} skipped; existing meanings kept.` : "";
      const unmatched = result.skipped_mapping_count ? ` ${result.skipped_mapping_count} unmatched word mappings skipped.` : "";
      $("dictionary-bulk-status").textContent = `Saved ${result.sentences} sentences and ${result.word_meanings} word meanings: ${result.added} added, ${result.updated} updated, ${result.unchanged} already saved.${skipped}${unmatched}${conflicts} Included in Export dictionary.`;
      if (result.skipped_entries?.length || result.skipped_mappings?.length) {
        const details = $("dictionary-bulk-preview"); details.hidden = false;
        (result.skipped_entries || []).forEach(entry => {
          const line = document.createElement("p"); line.className = "subtle";
          line.textContent = `Skipped ${entry.original}: ${entry.reason}`;
          details.append(line);
        });
        (result.skipped_mappings || []).forEach(entry => {
          const line = document.createElement("p"); line.className = "subtle";
          line.textContent = `Item ${entry.item}: skipped mapping ${entry.original}. ${entry.reason}`;
          details.append(line);
        });
      }
      await loadDictionary();
    } else {
      const unmatched = result.skipped_mapping_count ? ` ${result.skipped_mapping_count} unmatched word mappings will be skipped.` : "";
      $("dictionary-bulk-status").textContent = `${result.sentences} sentences and ${result.word_meanings} word meanings parsed.${unmatched}${conflicts} Nothing saved yet.`;
      const preview = $("dictionary-bulk-preview"); preview.hidden = false;
      result.items.forEach((item, index) => {
        const entry = document.createElement("div"); entry.className = "dictionary-import-item";
        const original = document.createElement("strong"), english = document.createElement("p"), mappings = document.createElement("p");
        original.textContent = `${item.item || index + 1}. ${item.original}`; english.textContent = item.english;
        mappings.className = "subtle"; mappings.textContent = item.terms.map(term => `${term.original} → ${term.english}`).join("; ") || (item.skipped_mappings?.length ? "Unmatched word mappings skipped; the sentence can still be saved." : "Sentence only; no word mappings.");
        entry.append(original, english, mappings);
        if (item.notes.length) {const notes = document.createElement("p"); notes.className = "subtle"; notes.textContent = item.notes.join(" "); entry.append(notes);}
        preview.append(entry);
      });
      if (result.word_alternatives?.length) {
        const alternatives = document.createElement("p"); alternatives.className = "subtle";
        alternatives.textContent = "Shared word alternatives: " + result.word_alternatives.map(term => `${term.original} → ${term.english}`).join("; ") + ". Exact mappings stay linked to each sentence.";
        preview.append(alternatives);
      }
    }
    if (result.batch_conflicts?.length) {
      const details = $("dictionary-bulk-preview"); details.hidden = false;
      result.batch_conflicts.forEach(entry => {
        const line = document.createElement("p"); line.className = "subtle";
        line.textContent = `Item ${entry.item}: ${importNow ? "skipped" : "will skip"} ${entry.kind} ${entry.original} → ${entry.english}. ${entry.reason}`;
        details.append(line);
      });
    }
  } catch (error) {
    $("dictionary-bulk-status").textContent = error.message;
    $("dictionary-bulk-status").classList.add("error");
  } finally {busy = false; setControls();}
}
document.querySelectorAll(".nav").forEach(button => button.addEventListener("click", () => view(button.dataset.view)));
$("message").addEventListener("input", invalidateInput); $("context").addEventListener("input", invalidateInput);
$("translate-button").addEventListener("click", translate); $("verify-button").addEventListener("click", verify);
$("save-local-button").addEventListener("click", () => save("local")); $("save-verified-button").addEventListener("click", () => save("verified"));
$("save-own-button").addEventListener("click", () => save("own"));
$("split-words-button").addEventListener("click", splitWords);
$("add-glossary-row").addEventListener("click", addManualGlossaryRow);
$("save-glossary-button").addEventListener("click", saveGlossary);
$("extract-word-meanings").addEventListener("click", extractWordMeanings);
$("copy-button").addEventListener("click", async () => {try {await navigator.clipboard.writeText(current.translation); notice("Translation copied.");} catch {notice("Copy is unavailable. Select the translation and copy it manually.", true);}});
$("load-examples").addEventListener("click", () => {$("batch-input").value = examples.map(([text, expected]) => `${text}\t${expected}`).join("\n");});
$("run-batch").addEventListener("click", runBatch);
$("stop-batch").addEventListener("click", () => {stopRequested = true; $("batch-progress").textContent = "Stopping after the current case…";});
$("dictionary-search").addEventListener("input", renderDictionary);
$("dictionary-bulk-text").addEventListener("input", clearDictionaryBulkPreview);
$("dictionary-bulk-preview-button").addEventListener("click", () => dictionaryBulkAction(false));
$("dictionary-bulk-import-button").addEventListener("click", () => dictionaryBulkAction(true));
$("dictionary-save").addEventListener("click", async () => {
  try {await api("/api/dictionary/save", {original: $("dictionary-original").value, english: $("dictionary-english").value, dialect: activeDialect});
    $("dictionary-original").value = ""; $("dictionary-english").value = ""; await loadDictionary(); notice("Meaning saved.");}
  catch (error) {notice(error.message, true);}
});
async function pollStatus() {
  try {
    status = await api("/api/status"); token = status.token;
    $("engine-state").textContent = status.ready ? "Online ready" : status.error ? "Model unavailable" : "Connecting…";
    $("runtime-badge").textContent = status.ready ? "Online ready" : "Connecting";
    $("ready-dot").classList.toggle("ready", status.ready);
    $("log-location").textContent = "History is private to your account";
    $("log-location").title = status.session_log;
    if (status.error) notice(status.error, true);
    setControls();
  } catch {$("engine-state").textContent = "Server disconnected"; status.ready = false; setControls();}
}
pollStatus(); setInterval(pollStatus, 30000); loadDialects();
