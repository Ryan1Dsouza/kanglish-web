"""Durability and boundary checks for the desktop translation workbench."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts.run_desktop import App, Store, parse_review, parse_word_mappings, key


def response(verdict, translation, explanation="", finish="STOP"):
    return {"candidates": [{"finishReason": finish, "content": {"parts": [{"text": json.dumps({
        "verdict": verdict, "teacherTranslation": translation, "explanation": explanation})}]}}]}


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).resolve().parents[1]
        self.temp = tempfile.TemporaryDirectory(dir=self.workspace / "tmp")
        self.store = Store(Path(self.temp.name) / "memory.sqlite3")

    def tearDown(self):
        self.assertTrue(Path(self.temp.name).resolve().is_relative_to((self.workspace / "tmp").resolve()))
        self.temp.cleanup()

    def app(self):
        app = object.__new__(App)
        app.store = self.store
        app.record = lambda *args, **kwargs: None
        return app

    def test_saved_meaning_survives_restart_and_normalizes_only_case_spaces(self):
        self.store.save("ninna hesaru Rachit", "Your name is Rachit.", "desktop_user_approved_own")
        reopened = Store(self.store.path)
        row = reopened.corrections()[0]
        self.assertEqual(row["key"], key(" NINNA  HESARU Rachit "))
        self.assertEqual(row["english"], "Your name is Rachit.")
        self.assertNotEqual(row["key"], key("ninna hesaru Rachit?"))

    def test_uncertain_cloud_guess_is_rejected(self):
        with self.assertRaises(RuntimeError):
            parse_review(response("uncertain", "Okay.", "Need context"), "sari")
        self.assertEqual(parse_review(response("uncertain", "", "Need context"), "sari")["translation"], "")

    def test_essay_and_truncated_responses_are_rejected(self):
        with self.assertRaises(RuntimeError):
            parse_review(response("match", "word " * 150), "neeru")
        with self.assertRaises(RuntimeError):
            parse_review(response("match", "water", finish="MAX_TOKENS"), "neeru")

    def test_failed_review_cannot_overwrite_existing_correction(self):
        app = self.app()
        self.store.save("sari", "Correct.", "manual")
        self.store.put_run({"id": "a", "input": "sari", "translation": "Okay", "verification": {
            "verdict": "uncertain", "translation": "", "explanation": "Context missing"}})
        with self.assertRaises(ValueError):
            app.save({"id": "a", "choice": "verified"})
        self.assertEqual(self.store.corrections()[0]["english"], "Correct.")

    def test_saving_uses_stored_candidate_not_browser_supplied_text(self):
        app = self.app()
        self.store.put_run({"id": "a", "input": "neeru", "source_label": "synthetic_control", "translation": "water", "verification": {
            "verdict": "match", "translation": "water", "explanation": ""}})
        saved = app.save({"id": "a", "choice": "verified", "english": "Untrusted replacement"})
        self.assertEqual(saved["english"], "water")
        self.assertEqual(self.store.corrections()[0]["source_label"], "synthetic_control")

    def test_relevant_examples_ignore_unrelated_saved_names(self):
        app = self.app()
        self.store.save("ninna hesaru Rachit", "Your name is Rachit.", "manual")
        self.store.save("neeru", "water", "manual")
        self.assertEqual([r["original"] for r in app.relevant("nanage neeru beku")], ["neeru"])
        self.assertEqual(app.relevant("oota aayta"), [])

    def test_bypassed_memory_has_no_personal_examples_or_extra_bos(self):
        app = self.app()
        app.glossary = type("Glossary", (), {"matches": lambda *_: []})()
        self.store.save("neeru", "water", "manual")
        self.assertIn("User-approved translations:", app.prompt("nanage neeru beku", ""))
        prompt = app.prompt("nanage neeru beku", "", False)
        self.assertNotIn("User-approved translations:", prompt)
        self.assertEqual(prompt.count("<bos>"), 1)
        self.assertIn("<start_of_turn>model", prompt)

    def test_automated_limit_blocks_inference_before_runtime_call(self):
        app = self.app()
        app.batch_lock = threading.Lock()
        app.batch_attempts = 500
        app.started_at = 1000
        with patch("scripts.run_desktop.time.monotonic", return_value=1000), patch("scripts.run_desktop.request_json") as runtime:
            row = app.translate({"text": "neeru", "batch": True})
        self.assertIn("session limit", row["error"])
        runtime.assert_not_called()

    def test_five_hundredth_batch_case_is_allowed_but_next_case_is_blocked(self):
        app = self.app()
        app.batch_lock = threading.Lock()
        app.lock = threading.Lock()
        app.batch_attempts = 499
        app.started_at = 1000
        app.ready = True
        self.store.save("neeru", "Water.", "control", "synthetic_control")
        with patch("scripts.run_desktop.time.monotonic", return_value=1000), patch("scripts.run_desktop.request_json") as runtime:
            allowed = app.translate({"text": "neeru", "batch": True, "synthetic": True})
            blocked = app.translate({"text": "neeru", "batch": True, "synthetic": True})
        self.assertEqual(allowed["translation"], "Water.")
        self.assertEqual(app.batch_attempts, 500)
        self.assertIn("500 cases", blocked["error"])
        runtime.assert_not_called()

    def test_sixty_minute_batch_limit_still_blocks_before_inference(self):
        app = self.app()
        app.batch_lock = threading.Lock()
        app.batch_attempts = 0
        app.started_at = 1000
        with patch("scripts.run_desktop.time.monotonic", return_value=4600), patch("scripts.run_desktop.request_json") as runtime:
            row = app.translate({"text": "neeru", "batch": True, "synthetic": True})
        self.assertIn("60 minutes", row["error"])
        self.assertEqual(app.batch_attempts, 0)
        runtime.assert_not_called()

    def sentence(self):
        row = {"id": "sentence", "input": "ninna hesaru Rachit", "translation": "What is your name?", "source_label": "synthetic_control"}
        self.store.put_run(row)
        self.app().save({"id": row["id"], "choice": "own", "english": "Your name is Rachit."})
        return row

    def test_word_breakdown_preserves_sentence_and_exports_both_kinds(self):
        row = self.sentence()
        self.app().save_glossary({"id": row["id"], "terms": [
            {"original": "ninna", "english": "your"}, {"original": "hesaru", "english": "name"}, {"original": "Rachit", "english": "Rachit"}]})
        reopened = Store(self.store.path)
        exported = reopened.export()
        self.assertEqual(len(exported), 4)
        sentence = next(r for r in exported if r["kind"] == "sentence")
        self.assertEqual(sentence["english"], "Your name is Rachit.")
        word = next(r for r in exported if r["original"] == "hesaru")
        self.assertEqual(word["kind"], "glossary")
        self.assertEqual(word["parent_original"], row["input"])
        self.assertEqual(word["source_label"], "synthetic_control")
        self.assertEqual(word["review_status"], "user_approved")
        self.assertEqual(len(reopened.glossary_for("NINNA HESARU Rachit")), 3)

    def test_invalid_word_batch_leaves_existing_memory_unchanged(self):
        row = self.sentence()
        before = self.store.export()
        with self.assertRaises(ValueError):
            self.app().save_glossary({"id": row["id"], "terms": [
                {"original": "hesaru", "english": "name"}, {"original": "unrelated", "english": "guess"}]})
        self.assertEqual(self.store.export(), before)

    def test_stale_sentence_screen_cannot_save_words_after_new_correction(self):
        row = self.sentence()
        self.store.save(row["input"], "NEWER_CORRECTION", "manual")
        with self.assertRaises(ValueError):
            self.app().save_glossary({"id": row["id"], "terms": [{"original": "hesaru", "english": "name"}]})
        self.assertEqual(len(self.store.corrections()), 1)

    def test_conflicting_duplicate_words_do_not_partially_save(self):
        row = self.sentence()
        with self.assertRaises(ValueError):
            self.app().save_glossary({"id": row["id"], "terms": [
                {"original": "hesaru", "english": "name"}, {"original": "HESARU", "english": "wrong"}]})
        self.assertEqual(len(self.store.corrections()), 1)

    def test_approved_words_enter_new_sentence_hints_and_can_be_bypassed(self):
        row = self.sentence()
        app = self.app()
        app.save_glossary({"id": row["id"], "terms": [{"original": "hesaru", "english": "name"}]})
        app.glossary = type("Glossary", (), {"matches": lambda *_: []})()
        prompt = app.prompt("avara hesaru", "")
        self.assertIn("Word meanings:\nhesaru = name\n", prompt)
        self.assertNotIn("hesaru = name", app.prompt("avara hesaru", "", False))

    def test_word_edits_keep_glossary_type_and_parent_relationship(self):
        row = self.sentence()
        self.app().save_glossary({"id": row["id"], "terms": [{"original": "hesaru", "english": "name"}]})
        self.store.save("hesaru", "a name", "desktop_user_dictionary")
        word = next(r for r in self.store.export() if r["original"] == "hesaru")
        self.assertEqual(word["kind"], "glossary")
        self.assertEqual(word["parent_original"], row["input"])

    def test_bulk_mappings_accept_arrows_and_preserve_commas_in_meanings(self):
        parsed = parse_word_mappings("maadu->do, make, hotel-alli->in the restaurant", "hotel-alli maadu")
        self.assertEqual([(r["original"], r["english"]) for r in parsed["terms"]], [("maadu", "do, make"), ("hotel-alli", "in the restaurant")])
        self.assertTrue(parsed["requires_review"])

    def test_bulk_hyphen_spelling_aligns_to_input_and_outside_words_are_ignored(self):
        parsed = parse_word_mappings("hotel-alli -> in the restaurant\nmaadu => do\nunknown -> guess", "hotelalli maadu")
        self.assertEqual(parsed["terms"][0]["original"], "hotelalli")
        self.assertEqual(parsed["ignored"], ["unknown"])
        self.assertTrue(parsed["notes"])

    def test_bulk_bullets_markdown_and_unicode_arrow(self):
        parsed = parse_word_mappings("Word meanings:\n```\n- **ninna** → your\n2. `hesaru` -> name\n```", "ninna hesaru Rachit")
        self.assertEqual([r["english"] for r in parsed["terms"]], ["your", "name"])

    def test_whatsapp_suffix_mapping_matches_hyphenated_and_spaced_input(self):
        for original in ("WhatsApp-alli", "WhatsApp alli", "WhatsAppalli"):
            with self.subTest(original=original):
                parsed = parse_word_mappings("WhatsApp-alli -> on WhatsApp", original + " maadu")
                self.assertEqual(parsed["terms"], [{"original": original, "english": "on WhatsApp", "origin": "pasted_mapping"}])

    def test_bulk_conflicts_and_missing_meanings_are_rejected_without_writes(self):
        self.sentence()
        before = self.store.export()
        for text in ("ninna -> your, NINNA -> my", "ninna ->", "This is an explanation, not explicit mappings"):
            with self.assertRaises(ValueError):
                parse_word_mappings(text, "ninna hesaru Rachit")
        self.assertEqual(self.store.export(), before)

    def test_pasted_word_origin_is_retained_after_explicit_saving(self):
        row = self.sentence()
        terms = parse_word_mappings("hesaru->name", row["input"])["terms"]
        self.app().save_glossary({"id": row["id"], "terms": terms})
        word = next(r for r in self.store.export() if r["original"] == "hesaru")
        self.assertEqual(word["source"], "desktop_user_glossary_from_paste")
        self.assertEqual(word["review_status"], "user_approved")


if __name__ == "__main__":
    unittest.main()
