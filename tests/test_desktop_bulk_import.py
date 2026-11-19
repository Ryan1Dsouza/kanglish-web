"""Synthetic controls for parsing and atomic desktop dictionary imports."""
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.run_desktop import Store, make_handler, merge_word_meanings, parse_sentence_batch


SAMPLE = """1.
Kanglish: Neevu hegiddeera?
English: How are you?
Word Mapping: Neevu -> You, hegiddeera -> how are you

2.
Kanglish: Nanna hesaru Rahul.
English: My name is Rahul.
Word Mapping: Nanna -> My, hesaru -> name, Rahul -> Rahul
"""

# User-reported phrases reproduced only as labelled synthetic regression controls.
CONTEXT_BATCH = """1.
Kanglish: Iga samaya eshtu aagide?
English: What is the time now?
Word Mapping: Iga -> Now, samaya -> time, eshtu -> how much / what, aagide -> has become / is
2.
Kanglish: Nange neeru beku.
English: I want water.
Word Mapping: Nange -> I / To me, neeru -> water, beku -> want
3.
Kanglish: Bega banni, bus barthide.
English: Come quickly, the bus is coming.
Word Mapping: Bega -> Quickly, banni -> come, bus -> bus, barthide -> is coming
4.
Kanglish: Ee raste yelli hoguththe?
English: Where does this road go?
Word Mapping: Ee -> This, raste -> road, yelli -> where, hoguththe -> goes
5.
Kanglish: Neenu yaake late bande?
English: Why did you come late?
Word Mapping: Neenu -> You, yaake -> why, late -> late, bande -> came
6.
Kanglish: Ivathu thumba sheke ide.
English: It is very hot today.
Word Mapping: Ivathu -> Today, thumba -> very, sheke -> hot, ide -> is
7.
Kanglish: Nimma phone number kodi.
English: Please give your phone number.
Word Mapping: Nimma -> Your, phone number -> phone number, kodi -> give
8.
Kanglish: Nanage idu thumba ishta aayithu.
English: I liked this very much.
Word Mapping: Nanage -> To me / I, idu -> this, thumba -> very much, ishta aayithu -> liked
9.
Kanglish: Mundhe nillisi, nanu ilithini.
English: Stop ahead, I will get down.
Word Mapping: Mundhe -> Ahead, nillisi -> stop, nanu -> I, ilithini -> will get down
10.
Kanglish: Matte sigona, hushaaragi hogi.
English: See you again, go safely.
Word Mapping: Matte -> Again, sigona -> let's meet, hushaaragi -> safely / carefully, hogi -> go
"""


class BulkImportTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(__file__).resolve().parents[1] / "tmp"
        self.temp = tempfile.TemporaryDirectory(dir=self.temp_root)
        self.store = Store(Path(self.temp.name) / "memory.sqlite3")

    def tearDown(self):
        self.assertTrue(Path(self.temp.name).resolve().is_relative_to(self.temp_root.resolve()))
        self.temp.cleanup()

    def import_text(self, text, replace=False):
        return self.store.import_sentence_batch(parse_sentence_batch(text), replace, source_label="synthetic_control")

    def test_user_format_saves_both_kinds_and_links_survive_restart(self):
        parsed = parse_sentence_batch(SAMPLE)
        self.assertEqual((parsed["sentences"], parsed["word_meanings"]), (2, 5))
        result = self.import_text(SAMPLE)
        self.assertEqual(result["added"], 7)
        reopened = Store(self.store.path)
        exported = reopened.export()
        self.assertEqual(len(exported), 7)
        self.assertTrue(all(row["source_label"] == "synthetic_control" for row in exported))
        self.assertTrue(all(row["review_status"] == "user_approved" for row in exported))
        word = next(row for row in exported if row["original"] == "Rahul")
        self.assertEqual(word["parent_originals"], ["Nanna hesaru Rahul."])
        self.assertEqual(word["kind"], "glossary")
        self.assertEqual(len(reopened.glossary_for("Neevu hegiddeera?")), 2)
        self.assertEqual(self.import_text(SAMPLE)["unchanged"], 7)

    def test_wrapped_mappings_markdown_and_sentence_only_items(self):
        parsed = parse_sentence_batch("""```text
1)
**Kanglish:** WhatsApp-alli maadu
**English:** Do it on WhatsApp.
**Word Mappings:**
- WhatsApp-alli -> on WhatsApp
- maadu → do, make

2)
Kanglish: naale sigona
English: See you tomorrow.
```""")
        self.assertEqual(parsed["items"][0]["terms"][1]["english"], "do, make")
        self.assertEqual(parsed["items"][1]["terms"], [])

    def test_english_first_and_mixed_order_preserve_numbered_items(self):
        # Supplied phrases are labelled synthetic controls, not accuracy claims.
        text = '''313.
English: Alarm rang, wake up and wash face.
Kanglish: Alarm aayithu, yedhu mukha tholko.
Word Mapping: Alarm aayithu -> Alarm rang, yedhu -> waking up, mukha tholko -> wash face

314.
Kanglish: Ondhu cup bisi black tea kudi.
English: Drink a hot cup of black tea.
Word Mapping: Ondhu cup -> One cup, bisi black tea -> hot black tea, kudi -> drink'''
        parsed = parse_sentence_batch(text)
        self.assertEqual([item['item'] for item in parsed['items']], [313, 314])
        self.import_text(text)
        self.assertEqual(len(self.store.export()), 8)
        self.assertTrue(all(row['source_label'] == 'synthetic_control' for row in self.store.export()))
        no_numbers = '\n'.join(line for line in text.splitlines() if line not in ('313.', '314.'))
        self.assertEqual(len(parse_sentence_batch(no_numbers)['items']), 2)
        with self.assertRaisesRegex(ValueError, 'Item 322'):
            parse_sentence_batch(text + '\n322.\nEnglish: Incomplete synthetic control.')
        with self.assertRaisesRegex(ValueError, 'Item 486'):
            parse_sentence_batch(text + '\n486.')

    def test_delete_dictionary_removes_links_only_for_selected_dictionary(self):
        self.import_text(SAMPLE)
        self.store.save('separate control', 'Separate meaning.', 'synthetic', 'synthetic_control', dialect='other')
        info = self.store.dictionary_info()
        self.store.save('new control', 'New meaning.', 'synthetic', 'synthetic_control')
        with self.assertRaisesRegex(ValueError, 'dictionary changed'):
            self.store.remove_dictionary('kanglish', info['version'])
        self.assertTrue(self.store.export())
        self.store.remove_dictionary('kanglish', self.store.dictionary_info()['version'])
        self.assertEqual(self.store.export(), [])
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM glossary_links WHERE dialect='kanglish'").fetchone()[0], 0)
        self.assertEqual(len(self.store.export('other')), 1)

    def test_missing_fields_and_malformed_mappings_reject_the_whole_batch(self):
        self.import_text(SAMPLE)
        before = self.store.export()
        for suffix in ("Kanglish: naale sigona", "English: Tomorrow.",
                       "Kanglish: naale sigona\nEnglish: See you tomorrow.\nWord Mapping: unknown ->",
                       "Kanglish: naale sigona\nEnglish: Tomorrow.\nEnglish: Yesterday.",
                       "Kanglish: naale sigona\nEnglish: Tomorrow.\nWord Mapping:"):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                self.import_text(SAMPLE + "\n" + suffix)
            self.assertEqual(self.store.export(), before)

    def test_noncontiguous_mapping_in_item_95_is_skipped_and_rest_saves(self):
        blocks = []
        for index in range(1, 101):
            if index == 95:
                blocks.append("""95.
Kanglish: Mane kitchen drainage trap hair trap filter clear maadi rinse maadi.
English: Clear and rinse the hair trap filter in the house kitchen drain trap.
Word Mapping: Mane kitchen drainage trap filter -> Kitchen drainage trap filter, clear maadi rinse maadi -> clear and rinse""")
            else:
                blocks.append(f"{index}.\nKanglish: control{index} test sentence\nEnglish: Synthetic control.\nWord Mapping: control{index} -> control")
        text = "\n\n".join(blocks)
        parsed = parse_sentence_batch(text)
        self.assertEqual((parsed["sentences"], parsed["word_meanings"], parsed["skipped_mapping_count"]), (100, 100, 1))
        self.assertEqual(parsed["skipped_mappings"][0]["item"], 95)
        self.assertEqual(parsed["skipped_mappings"][0]["original"], "Mane kitchen drainage trap filter")
        self.assertEqual(parsed["items"][94]["terms"][0]["original"], "clear maadi rinse maadi")
        saved = self.import_text(text)
        self.assertEqual((saved["sentences"], saved["word_meanings"], saved["skipped_mapping_count"], saved["added"]), (100, 100, 1, 200))
        self.assertFalse(any(row["original"] == "Mane kitchen drainage trap filter" for row in self.store.export()))
        parent = "Mane kitchen drainage trap hair trap filter clear maadi rinse maadi."
        self.assertEqual(self.store.glossary_for(parent)[0]["english"], "clear and rinse")

    def test_sentence_saves_when_all_well_formed_word_mappings_are_unmatched(self):
        text = "Kanglish: naale sigona\nEnglish: See you tomorrow.\nWord Mapping: unknown -> unknown meaning"
        saved = self.import_text(text)
        self.assertEqual((saved["sentences"], saved["word_meanings"], saved["skipped_mapping_count"], saved["added"]), (1, 0, 1, 1))
        self.assertEqual(self.store.export()[0]["english"], "See you tomorrow.")

    def test_duplicate_shared_words_have_all_parent_links(self):
        self.import_text("""Kanglish: nanna hesaru Rahul
English: My name is Rahul.
Word Mapping: hesaru -> name
Kanglish: avara hesaru Vihana
English: Their name is Vihana.
Word Mapping: hesaru -> name""")
        word = next(row for row in self.store.export() if row["kind"] == "glossary")
        self.assertEqual(len(word["parent_originals"]), 2)

    def test_existing_sentence_conflict_is_skipped_and_remaining_entries_saved(self):
        self.store.save("Nanna hesaru Rahul.", "Existing meaning", "curated", "supplied_label")
        before = self.store.export()[0]
        result = self.import_text(SAMPLE)
        self.assertEqual((result["added"], result["skipped"], result["sentences"], result["word_meanings"]), (6, 1, 1, 5))
        self.assertEqual(next(row for row in self.store.export() if row["original"] == "Nanna hesaru Rahul."), before)
        self.assertEqual(self.store.glossary_for("Nanna hesaru Rahul."), [], "Skipped parent must not gain contextual links")
        self.assertEqual(len(self.store.glossary_for("Neevu hegiddeera?")), 2)

    def test_replacement_retains_supplied_labels_review_and_existing_links(self):
        self.import_text(SAMPLE)
        with self.store.connect() as db:
            db.execute("UPDATE corrections SET source_label='supplied_label',review_status='human_reviewed' WHERE key='hesaru'")
        result = self.import_text(SAMPLE.replace("hesaru -> name", "hesaru -> a name"), True)
        self.assertEqual(result["updated"], 1)
        word = next(row for row in self.store.export() if row["original"] == "hesaru")
        self.assertEqual((word["english"], word["source_label"], word["review_status"]), ("a name", "supplied_label", "human_reviewed"))
        self.assertEqual(word["parent_originals"], ["Nanna hesaru Rahul."])

    def test_sql_failure_rolls_back_all_imported_rows(self):
        with self.store.connect() as db:
            db.execute("CREATE TRIGGER abort_control BEFORE INSERT ON corrections WHEN NEW.key='rahul' BEGIN SELECT RAISE(ABORT,'synthetic control'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.import_text(SAMPLE)
        self.assertEqual(self.store.export(), [])

    def test_conflicting_batch_meanings_and_entry_types_are_skipped(self):
        for text in (SAMPLE + "\nKanglish: Nanna hesaru Rahul.\nEnglish: Your name is Rahul.",
                     SAMPLE + "\nKanglish: hesaru\nEnglish: name"):
            with self.subTest(text=text):
                parsed = parse_sentence_batch(text)
                self.assertEqual((parsed["sentences"], parsed["word_meanings"], parsed["batch_conflict_count"]), (2, 5, 1))
                self.assertEqual(parsed["batch_conflicts"][0]["item"], 3)
                self.assertEqual(len(parsed["items"]), 2)
        self.store.save("Neevu hegiddeera?", "How are you?", "control", "synthetic_control", kind="glossary")
        before = self.store.export()[0]
        saved = self.import_text(SAMPLE, True)
        self.assertEqual((saved["skipped"], saved["added"]), (1, 6))
        self.assertEqual(next(row for row in self.store.export() if row["original"] == "Neevu hegiddeera?"), before)
        self.assertEqual(self.store.glossary_for("Neevu hegiddeera?"), [])

    def test_reported_duplicates_in_five_hundred_item_synthetic_batch(self):
        # Reported pairs retained verbatim only as synthetic parser controls.
        pairs = [
            (113, 163, "Auto rickshaw fair meter ride safe.", "Safe ride with auto rickshaw fair meter.", "Safe auto rickshaw ride with fair meter.", "Auto rickshaw -> Auto rickshaw, fair meter ride -> fair meter ride, safe -> safe"),
            (117, 167, "Filter coffee brass dabara morning boost.", "Morning boost from filter coffee in brass dabara.", "Morning boost with filter coffee in brass dabara.", "Filter coffee -> Filter coffee, brass dabara -> brass dabara, morning boost -> morning boost"),
            (134, 184, "Tender coconut sweet water morning thirst.", "Morning thirst quenched with sweet tender coconut water.", "Quenching morning thirst with sweet tender coconut water.", "Tender coconut sweet water -> Sweet tender coconut water, morning thirst -> morning thirst"),
            (141, 191, "Moodbidri Jain basadi thousand granite pillars.", "Thousand granite pillars in Moodbidri Jain basadi.", "Thousand granite pillars at Moodbidri Jain basadi.", "Moodbidri Jain basadi -> Moodbidri Jain basadi, thousand granite pillars -> thousand granite pillars"),
        ]
        blocks = {i: f"{i}.\nTuluglish: control{i} test sentence\nEnglish: Synthetic control.\nWord Mapping: control{i} -> control" for i in range(1, 501)}
        for first, later, original, english, alternative, mappings in pairs:
            for index, meaning in ((first, english), (later, alternative)):
                blocks[index] = f"{index}.\nTuluglish: {original}\nEnglish: {meaning}\nWord Mapping: {mappings}"
        text = "\n\n".join(blocks.values())
        parsed = parse_sentence_batch(text)
        self.assertEqual((parsed["sentences"], parsed["batch_conflict_count"]), (496, 4))
        self.assertEqual([(r["first_item"], r["item"]) for r in parsed["batch_conflicts"]], [(p[0], p[1]) for p in pairs])
        saved = self.store.import_sentence_batch(parsed, source_label="synthetic_control", dialect="tuluglish")
        self.assertEqual((saved["sentences"], saved["batch_conflict_count"]), (496, 4))
        rows = self.store.export("tuluglish")
        self.assertEqual(len(rows), saved["added"])
        self.assertTrue(all(row["source_label"] == "synthetic_control" and row["source_language"] == "tcy-Latn" for row in rows))
        for _, _, original, english, alternative, _ in pairs:
            self.assertEqual(next(row["english"] for row in rows if row["original"] == original), english)
        repeated = self.store.import_sentence_batch(parsed, True, source_label="synthetic_control", dialect="tuluglish")
        self.assertEqual((repeated["added"], repeated["updated"], repeated["batch_conflict_count"]), (0, 0, 4))

    def test_skipped_sentence_contributes_no_words_or_contextual_alternatives(self):
        text = """Tuluglish: Auto rickshaw fair meter ride safe.
English: Safe ride with auto rickshaw fair meter.
Word Mapping: safe -> safe
Tuluglish: Auto rickshaw fair meter ride safe.
English: Safe auto rickshaw ride with fair meter.
Word Mapping: safe -> different meaning, meter -> discarded word
Tuluglish: Other control sentence.
English: Other synthetic control.
Word Mapping: Other -> Other"""
        result = self.import_text(text, True)
        self.assertEqual((result["sentences"], result["word_meanings"], result["batch_conflict_count"]), (2, 2, 1))
        rows = self.store.export()
        self.assertFalse(any(row["original"] == "meter" for row in rows))
        self.assertEqual(self.store.glossary_for("Auto rickshaw fair meter ride safe.")[0]["english"], "safe")

    def test_sentence_first_type_collision_skips_only_mapping_and_keeps_item_numbers(self):
        text = """Kanglish: hesaru
English: name
Kanglish: hesaru
English: different sentence meaning
Kanglish: nanna hesaru Rahul
English: My name is Rahul.
Word Mapping: nanna -> my, hesaru -> a name"""
        parsed = parse_sentence_batch(text)
        self.assertEqual([item["item"] for item in parsed["items"]], [1, 3])
        self.assertEqual((parsed["sentences"], parsed["word_meanings"], parsed["batch_conflict_count"]), (2, 1, 2))
        self.import_text(text)
        self.assertEqual(self.store.glossary_for("nanna hesaru Rahul")[0]["original"], "nanna")
        self.assertEqual(next(row["kind"] for row in self.store.export() if row["original"] == "hesaru"), "sentence")

    def test_identical_duplicate_sentences_can_add_contextual_words(self):
        text = """Kanglish: nanna hesaru Rahul
English: My name is Rahul.
Word Mapping: nanna -> my
Kanglish: nanna hesaru Rahul
English: My name is Rahul.
Word Mapping: hesaru -> name, nanna -> mine"""
        result = self.import_text(text)
        self.assertEqual((result["sentences"], result["word_meanings"], result["batch_conflict_count"]), (1, 2, 0))
        words = self.store.glossary_for("nanna hesaru Rahul")
        self.assertEqual(next(row["english"] for row in words if row["original"] == "nanna"), "my / mine")

    def test_existing_neeru_sentence_is_skipped_as_a_word_and_rest_imports(self):
        self.store.save("neeru", "Water.", "curated", "supplied_label", kind="sentence")
        before = self.store.export()[0]
        saved = self.import_text(CONTEXT_BATCH)
        self.assertEqual((saved["sentences"], saved["word_meanings"], saved["skipped"], saved["added"]), (10, 36, 1, 46))
        self.assertEqual(saved["skipped_entries"][0]["original"], "neeru")
        self.assertEqual(next(row for row in self.store.export() if row["original"] == "neeru"), before)
        self.assertCountEqual([row["original"] for row in self.store.glossary_for("Nange neeru beku.")], ["Nange", "beku"])
        self.assertEqual(self.import_text(CONTEXT_BATCH)["added"], 0)

    def test_all_existing_conflicts_are_reported_without_changes(self):
        self.store.save("naale sigona", "Existing translation.", "curated", "synthetic_control")
        before = self.store.export()
        saved = self.import_text("Kanglish: naale sigona\nEnglish: See you tomorrow.")
        self.assertEqual((saved["added"], saved["updated"], saved["skipped"], saved["sentences"]), (0, 0, 1, 0))
        self.assertEqual(self.store.export(), before)

    def test_contextual_word_alternatives_keep_exact_parent_meanings(self):
        text = """Kanglish: Ivathu thumba sheke ide.
English: It is very hot today.
Word Mapping: Ivathu -> Today, thumba -> very, sheke -> hot, ide -> is
Kanglish: Nanage idu thumba ishta aayithu.
English: I liked this very much.
Word Mapping: Nanage -> To me / I, idu -> this, thumba -> very much, ishta aayithu -> liked"""
        parsed = parse_sentence_batch(text)
        self.assertIn({"original": "thumba", "english": "very / very much"}, parsed["word_alternatives"])
        self.import_text(text)
        word = next(row for row in self.store.export() if row["original"] == "thumba")
        self.assertEqual(word["english"], "very / very much")
        self.assertEqual(word["parent_meanings"], [{"parent_original": "Ivathu thumba sheke ide.", "english": "very"},
                                                  {"parent_original": "Nanage idu thumba ishta aayithu.", "english": "very much"}])
        for parent, expected in (("Ivathu thumba sheke ide.", "very"), ("Nanage idu thumba ishta aayithu.", "very much")):
            entry = next(row for row in self.store.glossary_for(parent) if row["original"] == "thumba")
            self.assertEqual(entry["english"], expected)
        self.assertEqual(self.import_text(text)["updated"], 0, "Repeated imports must not duplicate alternatives")

    def test_complete_reported_ten_item_batch_imports_and_exports(self):
        parsed = parse_sentence_batch(CONTEXT_BATCH)
        self.assertEqual(parsed["sentences"], 10)
        saved = self.import_text(CONTEXT_BATCH)
        exported = self.store.export()
        self.assertEqual(saved["added"], 10 + parsed["word_meanings"])
        self.assertEqual(sum(row["kind"] == "sentence" for row in exported), 10)
        self.assertEqual(next(row["english"] for row in exported if row["original"] == "thumba"), "very / very much")

    def test_existing_word_alternatives_are_extended_without_losing_metadata(self):
        self.store.save("thumba", "Very / VERY", "supplied", "supplied_label", kind="glossary")
        with self.store.connect() as db:
            db.execute("UPDATE corrections SET review_status='human_reviewed' WHERE key='thumba'")
        self.import_text("Kanglish: thumba ishta\nEnglish: Like it very much.\nWord Mapping: thumba -> very much")
        word = next(row for row in self.store.export() if row["original"] == "thumba")
        self.assertEqual((word["english"], word["source_label"], word["review_status"]), ("Very / very much", "supplied_label", "human_reviewed"))
        self.assertEqual(merge_word_meanings("To me / I", "i / to me"), "To me / I")

    def test_legacy_glossary_links_migrate_without_inventing_context(self):
        path = Path(self.temp.name) / "legacy.sqlite3"
        db = sqlite3.connect(path)
        db.execute("CREATE TABLE glossary_links (parent_key TEXT NOT NULL, term_key TEXT NOT NULL, parent_original TEXT NOT NULL, PRIMARY KEY(parent_key,term_key))")
        db.execute("INSERT INTO glossary_links VALUES ('thumba ishta','thumba','thumba ishta')")
        db.commit()
        db.close()
        migrated = Store(path)
        migrated.save("thumba", "very", "supplied", "supplied_label", kind="glossary")
        word = migrated.export()[0]
        self.assertEqual(word["parent_originals"], ["thumba ishta"])
        self.assertNotIn("parent_meanings", word)

    def test_batch_size_and_mapping_limits(self):
        with self.assertRaisesRegex(ValueError, "500"):
            parse_sentence_batch("\n".join(f"Kanglish: control{i}\nEnglish: Control {i}." for i in range(501)))
        blocks = []
        for i in range(500):
            words = [f"term{i}x{j}" for j in range(21)]
            blocks.append("Kanglish: " + " ".join(words) + "\nEnglish: Synthetic control.\nWord Mapping: " + ", ".join(word + " -> control" for word in words))
        with self.assertRaisesRegex(ValueError, "10,000"):
            parse_sentence_batch("\n".join(blocks))

    def test_five_hundred_item_paste_exceeding_old_text_limit_saves_and_exports(self):
        text = "\n\n".join(f"{i + 1}.\nKanglish: control{i} test sentence\nEnglish: Synthetic parser control. " + "meaning " * 32 +
            f"\nWord Mapping: control{i} -> control {i}" for i in range(500))
        self.assertGreater(len(text), 128000)
        saved = self.import_text(text)
        self.assertEqual((saved["sentences"], saved["word_meanings"], saved["added"]), (500, 500, 1000))
        exported = self.store.export()
        self.assertEqual(len(exported), 1000)
        self.assertTrue(all(row["source_label"] == "synthetic_control" for row in exported))
        self.assertEqual(next(row["parent_originals"] for row in exported if row["original"] == "control499"), ["control499 test sentence"])

    def test_http_preview_import_validation_and_authentication(self):
        app = SimpleNamespace(config={"port": 0}, token="synthetic-test-token", store=self.store)
        handler = make_handler(app)
        handler.log_message = lambda *_: None
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        app.config["port"] = server.server_port
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()

        def post(path, body, token=app.token):
            request = Request(f"http://127.0.0.1:{server.server_port}" + path, json.dumps(body).encode(),
                {"Content-Type": "application/json", "X-Kanglish-Token": token})
            try:
                with urlopen(request, timeout=5) as response:
                    return response.status, json.load(response)
            except HTTPError as error:
                return error.code, json.load(error)

        original_import = self.store.import_sentence_batch
        try:
            with patch.object(self.store, "import_sentence_batch", side_effect=lambda parsed, replace, **kwargs: original_import(parsed, replace, source_label="synthetic_control", **kwargs)):
                code, preview = post("/api/dictionary/bulk-preview", {"text": SAMPLE})
                self.assertEqual((code, preview["sentences"], preview["word_meanings"]), (200, 2, 5))
                self.assertEqual(self.store.export(), [])
                self.assertEqual(post("/api/dictionary/bulk-import", {"text": SAMPLE}, token="wrong")[0], 403)
                self.assertEqual(post("/api/dictionary/bulk-import", {"text": SAMPLE, "replace_existing": "false"})[0], 400)
                self.assertEqual(self.store.export(), [])
                code, saved = post("/api/dictionary/bulk-import", {"text": SAMPLE})
                self.assertEqual((code, saved["added"]), (200, 7))
                before = self.store.export()
                code, error = post("/api/dictionary/bulk-import", {"text": SAMPLE + "\nKanglish: incomplete"})
                self.assertEqual(code, 400)
                self.assertIn("Item 3", error["error"])
                self.assertEqual(self.store.export(), before)
                large_text = "\n\n".join(f"Kanglish: control{i} test sentence\nEnglish: Synthetic control. " + "é" * 600 for i in range(500))
                self.assertGreater(len(json.dumps({"text": large_text}).encode()), 1_000_000)
                code, large_preview = post("/api/dictionary/bulk-preview", {"text": large_text})
                self.assertEqual((code, large_preview["sentences"]), (200, 500))
                self.assertEqual(self.store.export(), before, "Large previews cannot modify dictionary memory")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
