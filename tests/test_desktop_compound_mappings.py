"""User-reported mapping patterns reproduced as synthetic parser controls.

The fixture checks matching and persistence, not Kannada translation accuracy.
"""
from pathlib import Path
import tempfile
import unittest

from scripts.run_desktop import App, Store, match_sentence_spelling, parse_sentence_batch, parse_word_mappings


CASES = """Yaake ashtu kopisikolluthiddiri?|Yaake -> Why, ashtu -> that much / so, kopisikolluthiddiri -> are you getting angry
Manege hosa curtains tharbeku.|Manege -> For the house, hosa -> new, curtains -> curtains, tharbeku -> need to bring
Nanna purse table mele ide.|Nanna -> My, purse -> purse, table mele -> on the table, ide -> is
Neenu yaava cinema nodoke hogthiya?|Neenu -> You, yaava -> which, cinema -> movie, nodoke -> to watch, hogthiya -> are you going
Ee apple thumba sihi aagide.|Ee -> This, apple -> apple, thumba -> very, sihi aagide -> is sweet
Thumba dina aayithu ninnannu nodi.|Thumba dina -> Many days, aayithu -> became / has been, ninnannu -> you, nodi -> seeing
Nimage yaradru phone maadidhra?|Nimage -> To you, yaradru -> anyone, phone maadidhra -> did they call
Ee kelsa mugiyoke innu time beku.|Ee -> This, kelsa -> work, mugiyoke -> to finish, innu -> more / still, time beku -> time is needed
Avanige heloke naanu yaaru?|Avanige -> To him, heloke -> to tell, naanu -> I, yaaru -> who
Swalpa baagilu thagiyiri.|Swalpa -> A little, baagilu -> door, thagiyiri -> open
Illi thumba sound barthide.|Illi -> Here, thumba -> a lot of / much, sound -> noise / sound, barthide -> is coming
Ninna address share maadu.|Ninna -> Your, address -> address, share maadu -> share
Nanu ondu hosa car thagobeku.|Nanu -> I, ondu -> a / one, hosa -> new, car -> car, thagobeku -> want to buy
Ee shirt nange sariyaagi aagthilla.|Ee -> This, shirt -> shirt, nange -> to me, sariyaagi -> properly, aagthilla -> is not fitting
Magu thumba aluthide.|Magu -> Baby / Child, thumba -> a lot, aluthide -> is crying
Ivathina news nodidheera?|Ivathina -> Today's, news -> news, nodidheera -> did you see
Nanna bag thumba heavy ide.|Nanna -> My, bag -> bag, thumba -> very, heavy ide -> is heavy
Naale match yelli nadeyuththe?|Naale -> Tomorrow, match -> match, yelli -> where, nadeyuththe -> happens / takes place
Neenu bega baroke aagalwa?|Neenu -> You, bega -> early / quickly, baroke -> to come, aagalwa -> is it not possible
Nanage halu kudiyaoke ishta illa.|Nanage -> To me / I, halu -> milk, kudiyaoke -> to drink, ishta illa -> don't like
Nimma room number eshtu?|Nimma -> Your, room number -> room number, eshtu -> what / how much
Nanu certificate print haakbeku.|Nanu -> I, certificate -> certificate, print haakbeku -> need to print
Ee road alli speed breaker jaasthi ide.|Ee road alli -> On this road, speed breaker -> speed breaker, jaasthi -> more / many, ide -> are
Avanu thumba husharagi drive maadthane.|Avanu -> He, thumba -> very, husharagi -> carefully, drive maadthane -> drives
Swalpa side bidi.|Swalpa -> A little, side -> side way, bidi -> leave / give
Nange online shopping thumba ishta.|Nange -> To me / I, online shopping -> online shopping, thumba -> very much, ishta -> like
Ee room thumba clean aagide.|Ee -> This, room -> room, thumba -> very, clean aagide -> is clean
Naanu dentist hatthira hogbeku.|Naanu -> I, dentist -> dentist, hatthira -> near / to, hogbeku -> have to go
Hotte thumba thumbythu.|Hotte -> Stomach, thumba -> completely / full, thumbythu -> got filled
Neenu yava branch thegedhukonde?|Neenu -> You, yava -> which, branch -> branch, thegedhukonde -> took / chose
Ee colour nimage thumba suit aaguththe.|Ee colour -> This colour, nimage -> to you, thumba -> very, suit aaguththe -> suits
Bega luggage pack maadi.|Bega -> Quickly, luggage -> luggage, pack maadi -> pack
Nanna shoe lace bichikonthide.|Nanna -> My, shoe lace -> shoe lace, bichikonthide -> is untying / coming loose
Ee tablet daily thagobeku.|Ee -> This, tablet -> tablet, daily -> daily, thagobeku -> must take
Neenu assignment submit maadidheeya?|Neenu -> You, assignment -> assignment, submit maadidheeya -> did you submit
Window open maadi, fresh air barli.|Window -> Window, open maadi -> open, fresh air -> fresh air, barli -> let it come
Nange thumba tired ansthide.|Nange -> To me / I, thumba -> very, tired ansthide -> feeling tired
Nimmannu illi nodi thumba kushi aayithu.|Nimmannu -> You, illi -> here, nodi -> seeing, thumba -> very, kushi aayithu -> became happy
Ee plant ge neeru haaki.|Ee plant ge -> To this plant, neeru -> water, haaki -> pour / put
Nanu market alli onion thagonde.|Nanu -> I, market alli -> in the market, onion -> onions, thagonde -> bought
Avanige Kannada baralla.|Avanige -> To him, Kannada -> Kannada, baralla -> does not know / come
Nanna bike tyre puncture aagide.|Nanna -> My, bike -> bike, tyre -> tyre, puncture aagide -> is punctured
Swalpa salt kami ide curry alli.|Swalpa -> A little, salt -> salt, kami ide -> is less, curry alli -> in the curry
Eega weather thumba pleasant aagide.|Eega -> Now, weather -> weather, thumba -> very, pleasant aagide -> is pleasant
Door bell yaaro ring maadthiddare.|Door bell -> Doorbell, yaaro -> someone, ring maadthiddare -> is ringing
Nanu hostel mess food thinde.|Nanu -> I, hostel mess food -> hostel mess food, thinde -> ate
Neenu yaake idhanna thalidhe?|Neenu -> You, yaake -> why, idhanna -> this, thalidhe -> pushed
Naale holiday antha notice banthu.|Naale -> Tomorrow, holiday -> holiday, antha -> that / stating, notice -> notice, banthu -> came
Nanna laptop charger maratbitthe.|Nanna -> My, laptop charger -> laptop charger, maratbitthe -> completely forgot
Ee coffee thumba kadu aagide.|Ee -> This, coffee -> coffee, thumba -> very, kadu aagide -> is bitter
Bus stop yelli antha thilisi.|Bus stop -> Bus stop, yelli -> where, antha -> that, thilisi -> inform / let me know
Nanu exam ge revision maadbeku.|Nanu -> I, exam ge -> for the exam, revision -> revision, maadbeku -> need to do
Neenu idhanna clean maadiya?|Neenu -> You, idhanna -> this, clean maadiya -> will you clean
Ee app thumba fast aagi run aaguththe.|Ee app -> This app, thumba -> very, fast aagi -> quickly / fast, run aaguththe -> runs
Swalpa sugar parcel kodi.|Swalpa -> Some, sugar -> sugar, parcel kodi -> pack and give
Avanu nanna classmate.|Avanu -> He, nanna -> my, classmate -> classmate
Battery percentage thumba low ide.|Battery percentage -> Battery percentage, thumba -> very, low ide -> is low
Neenu cinema thumba enjoy maadiya?|Neenu -> You, cinema -> movie, thumba -> a lot, enjoy maadiya -> did you enjoy
Nanna file delete aagide.|Nanna -> My, file -> file, delete aagide -> got deleted
Illi thumba mosquitoes ive.|Illi -> Here, thumba -> many, mosquitoes -> mosquitoes, ive -> are there
Ee medicine water jothe thagoli.|Ee medicine -> This medicine, water jothe -> with water, thagoli -> take
Train delay aaguththe antha helidru.|Train -> Train, delay aaguththe -> will be delayed, antha -> that, helidru -> they told
Nanu ice cream shop ge hogbeku.|Nanu -> I, ice cream shop ge -> to ice cream shop, hogbeku -> need to go
Ivathina lunch alli curd rice ithu.|Ivathina -> Today's, lunch alli -> in lunch, curd rice -> curd rice, ithu -> was there
Neenu yelli settle aagoke plan maadthiya?|Neenu -> You, yelli -> where, settle aagoke -> to settle, plan maadthiya -> do you plan
Nange swalpa biscuits beku.|Nange -> To me / I, swalpa -> some, biscuits -> biscuits, beku -> want
Ee shirt colour fade aagide.|Ee shirt -> This shirt, colour -> colour, fade aagide -> has faded
Road clear aagide, bega hogona.|Road -> Road, clear aagide -> is clear, bega -> quickly, hogona -> let's go
Neenu match live nodthiddiya?|Neenu -> You, match -> match, live -> live, nodthiddiya -> are you watching
Avanu thumba humble vyakthi.|Avanu -> He, thumba -> very, humble -> humble, vyakthi -> person
Ee watch water resistant ideya?|Ee watch -> This watch, water resistant -> water resistant, ideya -> is it
Nange drawing maado abhyasa ide.|Nange -> To me / I, drawing maado -> drawing, abhyasa -> habit, ide -> have / is
Neenu daily news paper odhthiya?|Neenu -> You, daily -> daily, news paper -> newspaper, odhthiya -> do you read
Bega dinner ready maadi.|Bega -> Quickly, dinner -> dinner, ready maadi -> make ready
Nanna shoes leather du.|Nanna -> My, shoes -> shoes, leather du -> of leather
Signal drop aagide, voice kelisthilla.|Signal -> Signal, drop aagide -> is dropped, voice -> voice, kelisthilla -> is not hearing / audible
Illi bench mele koodi.|Illi -> Here, bench mele -> on the bench, koodi -> sit
Ee plant flowers kooda koduththe.|Ee plant -> This plant, flowers -> flowers, kooda -> also, koduththe -> gives
Nanu hotel indha parcel thande.|Nanu -> I, hotel indha -> from hotel, parcel -> parcel, thande -> brought
Ee building thumba old aagide.|Ee building -> This building, thumba -> very, old aagide -> is old
Swalpa fan turn off maadi.|Swalpa -> Please / A little, fan -> fan, turn off maadi -> turn off
Neenu interview attend aagidhdheya?|Neenu -> You, interview -> interview, attend aagidhdheya -> did you attend
Nanna bag chain muridu hogide.|Nanna -> My, bag chain -> bag zipper / chain, muridu hogide -> is broken
Naale morning walking hogona.|Naale morning -> Tomorrow morning, walking -> walking, hogona -> let's go
Ee cake thumba soft aagide.|Ee cake -> This cake, thumba -> very, soft aagide -> is soft
Nange fresh vegetables tharoke heli.|Nange -> For me, fresh vegetables -> fresh vegetables, tharoke -> to bring, heli -> tell
Neenu Bangalore ge yavaga move aagthiya?|Neenu -> You, Bangalore ge -> to Bangalore, yavaga -> when, move aagthiya -> are you moving
Nanna water bottle empty aagide.|Nanna -> My, water bottle -> water bottle, empty aagide -> is empty
Weather forecast alli heavy rain helidhdhaare.|Weather forecast alli -> In weather forecast, heavy rain -> heavy rain, helidhdhaare -> they have said
Illi traffic rules follow maadbeku.|Illi -> Here, traffic rules -> traffic rules, follow maadbeku -> must follow
Neenu hosa phone purchase maadiya?|Neenu -> You, hosa phone -> new phone, purchase maadiya -> did you purchase
Ee pen thumba smooth aagi barithey.|Ee pen -> This pen, thumba -> very, smooth aagi -> smoothly, barithey -> writes
Nanu daily gym session miss maadolla.|Nanu -> I, daily -> daily, gym session -> gym session, miss maadolla -> do not miss
Illi tea thumba famous.|Illi -> Here, tea -> tea, thumba -> very, famous -> famous
Nanna cycle break loose aagide.|Nanna -> My, cycle break -> cycle brake, loose aagide -> has become loose
Swalpa sound kammi maadi, nanu study maadbeku.|Swalpa -> A bit, sound kammi maadi -> lower the volume, nanu -> I, study maadbeku -> have to study
Neenu weekend alli free irthiya?|Neenu -> You, weekend alli -> on weekend, free -> free, irthiya -> will you be
Ee milk shake thumba chill aagide.|Ee milkshake -> This milkshake, thumba -> very, chill aagide -> is chilled
Avanu cricket thumba chennagi aadthane.|Avanu -> He, cricket -> cricket, thumba -> very, chennagi -> well, aadthane -> plays
Naale sanje cinema theater alli meet aagona.|Naale sanje -> Tomorrow evening, cinema theater alli -> at the cinema theater, meet aagona -> let us meet"""


def reported_mapping_batch():
    return "\n\n".join(f"{index}.\nKanglish: {source}\nEnglish: Synthetic parser control.\nWord Mapping: {mappings}"
        for index, line in enumerate(CASES.splitlines(), 1) for source, mappings in [line.split("|", 1)])


class CompoundMappingTests(unittest.TestCase):
    def test_all_hundred_reported_mapping_patterns_parse(self):
        parsed = parse_sentence_batch(reported_mapping_batch())
        self.assertEqual(parsed["sentences"], 100)
        self.assertEqual(len(parsed["items"]), 100)
        self.assertEqual(parsed["items"][97]["terms"][0]["original"], "Ee milk shake")
        self.assertEqual(parsed["items"][97]["terms"][0]["english"], "This milkshake")
        self.assertTrue(any("Ee milkshake" in note for note in parsed["items"][97]["notes"]))

    def test_joined_spaced_and_hyphenated_compounds_align_in_both_directions(self):
        for source, sentence, expected in (("Ee milkshake", "Ee milk shake thumba chill aagide.", "Ee milk shake"),
                                           ("ice cream shop ge", "icecream shopge hogbeku", "icecream shopge"),
                                           ("phone-number", "phone number kodi", "phone number"),
                                           ("news paper", "newspaper odhthiya", "newspaper"),
                                           ("hotel-alli", "hotel alli maadu", "hotel alli")):
            with self.subTest(source=source):
                self.assertEqual(match_sentence_spelling(source, sentence), expected)

    def test_substrings_typos_nonadjacent_words_and_punctuation_do_not_match(self):
        for source, sentence in (("milkshake", "milkshaker thumba chill"), ("milkshake", "milk and shake beku"),
                                 ("milkshake", "milk, shake beku"), ("milk shake", "milk, shake beku"),
                                 ("milkshake", "milk. Shake beku"), ("milkshake", "milksheke beku"),
                                 ("phone number", "phone nanna number kodi"), ("ram", "Ramesh bandaru")):
            with self.subTest(source=source):
                self.assertIsNone(match_sentence_spelling(source, sentence))

    def test_exact_word_boundaries_are_preferred_over_compound_fallback(self):
        self.assertEqual(match_sentence_spelling("milkshake", "milk shake mattu milkshake beku"), "milkshake")
        self.assertEqual(match_sentence_spelling("milk shake", "milkshake mattu milk shake beku"), "milk shake")

    def test_aligned_mapping_saves_and_exports_the_actual_sentence_spelling(self):
        temp_root = Path(__file__).resolve().parents[1] / "tmp"
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(temp_root.resolve()))
            store = Store(Path(directory) / "memory.sqlite3")
            parsed = parse_sentence_batch(reported_mapping_batch())
            result = store.import_sentence_batch(parsed, source_label="synthetic_control")
            self.assertEqual(result["sentences"], 100)
            row = next(row for row in store.export() if row["original"] == "Ee milk shake")
            self.assertEqual(row["english"], "This milkshake")
            self.assertEqual(row["parent_meanings"], [{"parent_original": "Ee milk shake thumba chill aagide.", "english": "This milkshake"}])
            # The own-correction word editor uses the same matching rule.
            app = object.__new__(App); app.store = store; app.record = lambda *args, **kwargs: None
            parent = "ice cream shop ge hogbeku"
            store.save(parent, "Synthetic parser control.", "control", "synthetic_control")
            store.put_run({"id": "control", "input": parent, "saved_english": "Synthetic parser control.", "source_label": "synthetic_control"})
            app.save_glossary({"id": "control", "terms": [{"original": "icecream", "english": "ice cream", "origin": "pasted_mapping"}]})
            self.assertEqual(store.glossary_for(parent)[0]["original"], "ice cream")


if __name__ == "__main__":
    unittest.main()
