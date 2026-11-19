"""Technical mapping patterns reproduced as labelled synthetic parser controls.

These check formatting and storage, not the accuracy of supplied translations.
"""
from pathlib import Path
import tempfile
import unittest

from scripts.run_desktop import App, Store, match_sentence_spelling, parse_sentence_batch


CASES = """Git commit maadi repo ge push maadidheeya?|Git commit maadi -> Making a git commit, repo ge -> to the repo, push maadidheeya -> did you push
Ee code compile aagthilla, syntax error thoristhide.|Ee code -> This code, compile aagthilla -> is not compiling, syntax error -> syntax error, thoristhide -> is showing
Naale project demo ge presentation slide ready maadi.|Naale -> Tomorrow, project demo ge -> for project demo, presentation slide -> presentation slides, ready maadi -> make ready
Panambur beach ge sanje sunset nodoke hogona.|Panambur beach ge -> To Panambur beach, sanje -> evening, sunset nodoke -> to watch sunset, hogona -> let us go
Nanna laptop fan speed jaasthi aagi heat aagthide.|Nanna laptop -> My laptop, fan speed jaasthi aagi -> fan speed having increased, heat aagthide -> is heating up
Ullal bridge mele thumba thampu gaali beesuththe.|Ullal bridge mele -> Over Ullal bridge, thumba -> very, thampu gaali -> cool breeze, beesuththe -> blows
Hostel laundry wash cycle mugiyoke innu ardhagante beku.|Hostel laundry wash cycle -> Hostel laundry wash cycle, mugiyoke -> to finish, innu -> still / another, ardhagante -> half an hour, beku -> needed
Terminal alli docker container run aagthideya nodu.|Terminal alli -> In the terminal, docker container -> docker container, run aagthideya -> is it running, nodu -> look / check
Swalpa local bakery indha bisi bun butter thago.|Swalpa -> Some, local bakery indha -> from local bakery, bisi bun butter -> hot bun butter, thago -> buy / take
coastal Karnataka dali monsoon rain thumba violent iruththe.|coastal Karnataka dali -> In coastal Karnataka, monsoon rain -> monsoon rain, thumba -> very, violent iruththe -> is violent
Database migration script run maadidha mele check maadi.|Database migration script -> Database migration script, run maadidha mele -> after running, check maadi -> check
Nanna roommate mess food beda antha hotel ge hodha.|Nanna roommate -> My roommate, mess food -> mess food, beda antha -> saying no, hotel ge -> to a restaurant / hotel, hodha -> went
Kadri temple ground alli fair nadithide.|Kadri temple ground alli -> At Kadri temple ground, fair -> fair / exhibition, nadithide -> is taking place
API endpoint response slow aagi timeout aayithu.|API endpoint response -> API endpoint response, slow aagi -> being slow, timeout aayithu -> timed out
Neenu hostel electricity bill split share kottiya?|Neenu -> You, hostel electricity bill -> hostel electricity bill, split share -> split share, kottiya -> did you give / pay
Ee tea stall alli goli baje bisi bisiyagi siguththe.|Ee tea stall alli -> At this tea stall, goli baje -> goli baje, bisi bisiyagi -> piping hot / fresh, siguththe -> is available
Backend server log file alli null pointer exception banthu.|Backend server log file alli -> In backend server log file, null pointer exception -> null pointer exception, banthu -> came / appeared
State Bank bus stop alli city bus waiting maadi.|State Bank bus stop alli -> At State Bank bus stop, city bus -> city bus, waiting maadi -> wait
Room heater wire short circuit aagadhe safe aagi idiri.|Room heater wire -> Room heater wire, short circuit aagadhe -> without short-circuiting, safe aagi idiri -> keep safely
Git rebase maado modhalu backup branch create maadi.|Git rebase maado modhalu -> Before doing git rebase, backup branch -> backup branch, create maadi -> create
Tannirbhavi tree park ge cycling plan maadona.|Tannirbhavi tree park ge -> To Tannirbhavi tree park, cycling plan -> cycling plan, maadona -> let us make
Nanna laptop trackpad tap gesture work aagthilla.|Nanna laptop trackpad -> My laptop trackpad, tap gesture -> tap gesture, work aagthilla -> is not working
Canteen alli neer dosa coconut chutney jothe serve maadthare.|Canteen alli -> In the canteen, neer dosa -> neer dosa, coconut chutney jothe -> with coconut chutney, serve maadthare -> they serve
Unit tests ella pass aagidheya verify maadi.|Unit tests ella -> All unit tests, pass aagidheya -> have they passed, verify maadi -> verify
Hostel terrace mele batte dry aagoke haakidhdhini.|Hostel terrace mele -> On the hostel terrace, batte -> clothes, dry aagoke -> to dry, haakidhdhini -> have put
Cloud backup sync automatically complete aagide.|Cloud backup sync -> Cloud backup sync, automatically -> automatically, complete aagide -> has completed
Bejai market alli fresh vegetables purchase maadbeku.|Bejai market alli -> At Bejai market, fresh vegetables -> fresh vegetables, purchase maadbeku -> need to buy
Code review comments GitHub pull request alli post maadidhdhaare.|Code review comments -> Code review comments, GitHub pull request alli -> on GitHub pull request, post maadidhdhaare -> have posted
KSRTC bus online ticket reservation SMS banthu.|KSRTC bus -> KSRTC bus, online ticket reservation SMS -> online ticket reservation SMS, banthu -> arrived
Neenu debug mode on maadi break point set maadiya?|Neenu -> You, debug mode on maadi -> turning on debug mode, break point set maadiya -> did you set breakpoint
Urwa store circle hatthira traffic slow ide.|Urwa store circle hatthira -> Near Urwa store circle, traffic -> traffic, slow ide -> is slow
Nanna room water mug plastic smell barthide.|Nanna room -> My room, water mug -> water mug, plastic smell -> plastic smell, barthide -> is coming
Python virtual environment activate maadoke command heli.|Python virtual environment -> Python virtual environment, activate maadoke -> to activate, command -> command, heli -> tell
Car Street alli evening chat shop thumba crowd iruththe.|Car Street alli -> On Car Street, evening chat shop -> evening chaat shop, thumba -> very, crowd iruththe -> is crowded
SSD read write speed test run maadi nodi.|SSD read write speed test -> SSD read-write speed test, run maadi -> running, nodi -> check / look
Hostel room table lamp bulb yellow light barthide.|Hostel room table lamp bulb -> Hostel room table lamp bulb, yellow light -> yellow light, barthide -> is coming
Dependency package update npm install indha maadi.|Dependency package update -> Dependency package update, npm install indha -> using npm install, maadi -> do
Someshwar beach sunset rocks mele photo super baruththe.|Someshwar beach sunset -> Someshwar beach sunset, rocks mele -> on the rocks, photo -> photo, super baruththe -> turns out super
Nanna mouse scroll wheel jump aagthide.|Nanna -> My, mouse scroll wheel -> mouse scroll wheel, jump aagthide -> is jumping
Linux kernel update reboot maadidha mele apply aaguththe.|Linux kernel update -> Linux kernel update, reboot maadidha mele -> after rebooting, apply aaguththe -> applies
Central railway station locker room alli bag secure idiri.|Central railway station -> Central railway station, locker room alli -> in the locker room, bag -> bag, secure idiri -> keep securely
Ee fish fry rava coat crunchy aagide.|Ee fish fry -> This fish fry, rava coat -> semolina coating, crunchy aagide -> is crunchy
Local storage cache clear maadidre page load fast aaguththe.|Local storage cache -> Local storage cache, clear maadidre -> if cleared, page load -> page load, fast aaguththe -> becomes fast
Hostel corridor exhaust fan sound nillisoke heli.|Hostel corridor exhaust fan sound -> Hostel corridor exhaust fan sound, nillisoke heli -> tell to stop
PVS circle bus stop alli shelter roof leak aagthide.|PVS circle bus stop alli -> At PVS circle bus stop, shelter roof -> shelter roof, leak aagthide -> is leaking
SSH private key permission chmod 600 set maadi.|SSH private key permission -> SSH private key permissions, chmod 600 -> chmod 600, set maadi -> set
Nanna room curtain hook plastic clip murithu.|Nanna room curtain hook -> My room curtain hook, plastic clip -> plastic clip, murithu -> snapped / broke
Jyothi circle corner bakery alli fresh egg puffs ide.|Jyothi circle corner bakery alli -> In corner bakery at Jyothi circle, fresh egg puffs -> fresh egg puffs, ide -> is there
Database indexing query performance double maadidhe.|Database indexing -> Database indexing, query performance -> query performance, double maadidhe -> has doubled
Kadri park morning jogging track mud dry aagide.|Kadri park morning jogging track -> Kadri park morning jogging track, mud -> mud, dry aagide -> has dried
Git merge conflict resolve maadoke VS Code use maadi.|Git merge conflict resolve maadoke -> To resolve git merge conflict, VS Code -> VS Code, use maadi -> use
Hostel warden evening round inspection ge banthiddare.|Hostel warden -> Hostel warden, evening round inspection ge -> for evening round inspection, banthiddare -> has arrived
Surathkal beach lighthouse view platform windy ide.|Surathkal beach lighthouse view platform -> Surathkal beach lighthouse viewing platform, windy ide -> is windy
REST API JSON payload validation pass aagide.|REST API JSON payload validation -> REST API JSON payload validation, pass aagide -> has passed
Ee cycle bell thumb hammer metal ring clear ide.|Ee cycle bell thumb hammer -> This cycle bell thumb hammer, metal ring -> metal ring, clear ide -> is clear
Kankanady market flower garland fragrance hall thumba ide.|Kankanady market flower garland fragrance -> Kankanady market flower garland fragrance, hall thumba -> throughout the hall, ide -> is there
CSS flexbox layout mobile screen ge responsive ide.|CSS flexbox layout -> CSS flexbox layout, mobile screen ge -> for mobile screen, responsive ide -> is responsive
Nanna hostel bed mattress spring support soft ide.|Nanna hostel bed mattress -> My hostel bed mattress, spring support -> spring support, soft ide -> is soft
Mangaladevi temple car festival day traffic divert aaguththe.|Mangaladevi temple car festival day -> Mangaladevi temple car festival day, traffic -> traffic, divert aaguththe -> gets diverted
Environment variables file .env gitignore ge add maadi.|Environment variables file .env -> Environment variables .env file, gitignore ge -> to gitignore, add maadi -> add
Hampankatta main road shopping time parking difficult ide.|Hampankatta main road -> Hampankatta main road, shopping time -> shopping time, parking -> parking, difficult ide -> is difficult
C++ pointer memory leak valgrind tool indha trace maadi.|C++ pointer memory leak -> C++ pointer memory leak, valgrind tool indha -> using valgrind tool, trace maadi -> trace
Hostel mess night rasam cumin black pepper blend rich ide.|Hostel mess night rasam -> Hostel mess night rasam, cumin black pepper blend -> cumin black pepper blend, rich ide -> is rich
Ferry wharf indha Tannirbhavi boat ride five minutes aaguththe.|Ferry wharf indha -> From Ferry wharf, Tannirbhavi boat ride -> Tannirbhavi boat ride, five minutes -> five minutes, aaguththe -> takes / becomes
React state variable update re-render trigger maaduththe.|React state variable update -> React state variable update, re-render -> re-render, trigger maaduththe -> triggers
Nanna umbrella metal ribs strong wind withstand maaduththe.|Nanna umbrella metal ribs -> My umbrella metal ribs, strong wind -> strong wind, withstand maaduththe -> withstands
Ladyhill circle ice cream parlour night eleven pm ge close aaguththe.|Ladyhill circle ice cream parlour -> Ladyhill circle ice cream parlour, night eleven pm ge -> at 11 PM at night, close aaguththe -> closes
Webpack bundle size minify maadoke build config check maadi.|Webpack bundle size minify maadoke -> To minify webpack bundle size, build config -> build config, check maadi -> check
Hostel room cupboard wooden latch lock smooth slip aaguththe.|Hostel room cupboard wooden latch lock -> Hostel room cupboard wooden latch lock, smooth slip aaguththe -> slides smoothly
Sultan Battery watch tower stone steps narrow ive.|Sultan Battery watch tower stone steps -> Sultan Battery watchtower stone steps, narrow ive -> are narrow
Async await function try catch block alli wrap maadi.|Async await function -> Async await function, try catch block alli -> in try-catch block, wrap maadi -> wrap
Nanna room window screen mesh dust vacuum clean maadi.|Nanna room window screen mesh dust -> My room window mesh dust, vacuum clean maadi -> vacuum clean
City Centre mall escalator maintenance work finish aagide.|City Centre mall escalator -> City Centre mall escalator, maintenance work -> maintenance work, finish aagide -> has finished
Redis caching session token retrieval time minimize maadidhe.|Redis caching -> Redis caching, session token retrieval time -> session token retrieval time, minimize maadidhe -> has minimized
Hostel corridor dustbin bag daily night replacement maadi.|Hostel corridor dustbin bag -> Hostel corridor trash bag, daily night -> daily night, replacement maadi -> replace
Mannagudda sweet stall milk peda texture soft ide.|Mannagudda sweet stall milk peda -> Mannagudda sweet stall milk peda, texture -> texture, soft ide -> is soft
Postgres connection pool idle client count limit maadi.|Postgres connection pool -> Postgres connection pool, idle client count -> idle client count, limit maadi -> limit
Nanna cycle seat cover waterproof foam intact ide.|Nanna cycle seat cover waterproof foam -> My bicycle seat cover waterproof foam, intact ide -> is intact
Milagres church bell chime distance ge clear kelisuththe.|Milagres church bell chime -> Milagres church bell chime, distance ge -> from a distance, clear kelisuththe -> is heard clearly
Nginx reverse proxy SSL certificate expiry date note maadi.|Nginx reverse proxy SSL certificate -> Nginx reverse proxy SSL certificate, expiry date -> expiry date, note maadi -> note down
Hostel mess Sunday special chicken biryani aromatic ide.|Hostel mess Sunday special chicken biryani -> Hostel mess Sunday special chicken biryani, aromatic ide -> is aromatic
Bunder fishing port early morning boat auction crowd jaasthi.|Bunder fishing port -> Bunder fishing port, early morning boat auction crowd -> early morning boat auction crowd, jaasthi -> heavy / more
TypeScript interface declaration strict type checking allow maaduththe.|TypeScript interface declaration -> TypeScript interface declaration, strict type checking -> strict type checking, allow maaduththe -> allows
Nanna laptop rubber feet table surface ge firm grip koduththe.|Nanna laptop rubber feet -> My laptop rubber feet, table surface ge -> to table surface, firm grip koduththe -> gives firm grip
Valencia junction coffee house cold brew citrus notes ide.|Valencia junction coffee house cold brew -> Valencia junction coffee house cold brew, citrus notes -> citrus notes, ide -> has
GraphQL query overhead field request prevent maaduththe.|GraphQL query -> GraphQL query, overhead field request -> overhead field request, prevent maaduththe -> prevents
Hostel common room TV remote battery change maadi.|Hostel common room TV remote -> Hostel common room TV remote, battery -> battery, change maadi -> change
Pumpwell flyover road gradient smooth driving allow maaduththe.|Pumpwell flyover road gradient -> Pumpwell flyover road gradient, smooth driving -> smooth driving, allow maaduththe -> allows
Kafka consumer group offset commit lag zero aagide.|Kafka consumer group offset commit lag -> Kafka consumer group offset commit lag, zero aagide -> has become zero
Nanna raincoat hood drawstring clamp tight hold maaduththe.|Nanna raincoat hood drawstring clamp -> My raincoat hood drawstring clamp, tight hold maaduththe -> holds tightly
Kuloor bridge river backwaters high tide view picturesque ide.|Kuloor bridge river backwaters -> Kuloor bridge river backwaters, high tide view -> high tide view, picturesque ide -> is picturesque
Bash shell script executable permission chmod plus x kodi.|Bash shell script -> Bash shell script, executable permission -> executable permission, chmod plus x kodi -> give chmod +x
Hostel study hall air conditioner thermostat 24 degree fix maadi.|Hostel study hall air conditioner thermostat -> Hostel study hall air conditioner thermostat, 24 degree -> 24 degrees, fix maadi -> fix
Kodialbail bakery fresh coconut puffs warm crunch koduththe.|Kodialbail bakery fresh coconut puffs -> Kodialbail bakery fresh coconut puffs, warm crunch -> warm crunch, koduththe -> gives
Cron job schedule midnight database backup run maaduththe.|Cron job schedule -> Cron job schedule, midnight database backup -> midnight database backup, run maaduththe -> runs
Nanna cycle handlebar bell brass dome resonance sustain aaguththe.|Nanna cycle handlebar bell brass dome -> My cycle handlebar bell brass dome, resonance -> resonance, sustain aaguththe -> sustains
Falnir lane street trees shade walking ge comfort koduththe.|Falnir lane street trees shade -> Falnir lane street trees shade, walking ge -> for walking, comfort koduththe -> gives comfort
CI CD pipeline automated deployment lint check verify maadidhe.|CI CD pipeline automated deployment -> CI/CD pipeline automated deployment, lint check -> lint check, verify maadidhe -> has verified
Hostel balcony clothes rope galvanized steel core rust resistant ide.|Hostel balcony clothes rope -> Hostel balcony clothesline, galvanized steel core -> galvanized steel core, rust resistant ide -> is rust-resistant
Ella engineering build steps pass aagi system stability deliver maadi.|Ella engineering build steps pass aagi -> All engineering build steps having passed, system stability -> system stability, deliver maadi -> deliver"""


def technical_mapping_batch():
    return "\n\n".join(f"{index}.\nKanglish: {source}\nEnglish: Synthetic technical parser control.\nWord Mapping: {mappings}"
        for index, line in enumerate(CASES.splitlines(), 1) for source, mappings in [line.split("|", 1)])


class TechnicalMappingTests(unittest.TestCase):
    def test_hundred_reported_technical_mapping_patterns_parse(self):
        parsed = parse_sentence_batch(technical_mapping_batch())
        self.assertEqual(parsed["sentences"], 100)
        self.assertEqual(parsed["items"][59]["terms"][0]["original"], "Environment variables file .env")
        self.assertEqual(parsed["items"][61]["terms"][0]["original"], "C++ pointer memory leak")

    def test_technical_symbols_and_numbers_are_retained(self):
        for term in (".env", ".env.local", "C++", "C#", "config.json", "foo_bar", "src/main.py", "24 degree", "chmod 600"):
            with self.subTest(term=term):
                self.assertEqual(match_sentence_spelling(term, term + " check maadi."), term)

    def test_technical_tokens_are_not_reinterpreted_as_plain_words(self):
        for term, sentence in (("env", ".env add maadi"), (".env", "env add maadi"), ("C", "C++ pointer"),
                               ("C++", "C pointer"), ("C#", "C++ pointer"), ("config", "config.json add maadi"),
                               ("file.env", "file .env add maadi"), ("foo bar", "foo_bar add maadi"),
                               ("srcmain.py", "src/main.py add maadi"), ("24 degree", "240 degree fix maadi"),
                               (".env", "..env add maadi"), ("C++", "C+++ pointer")):
            with self.subTest(term=term):
                self.assertIsNone(match_sentence_spelling(term, sentence))

    def test_import_export_and_word_editor_keep_env_and_cpp(self):
        temp_root = Path(__file__).resolve().parents[1] / "tmp"
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(temp_root.resolve()))
            store = Store(Path(directory) / "memory.sqlite3")
            store.import_sentence_batch(parse_sentence_batch(technical_mapping_batch()), source_label="synthetic_control")
            rows = store.export()
            env = next(row for row in rows if row["original"] == "Environment variables file .env")
            self.assertEqual(env["english"], "Environment variables .env file")
            self.assertIn("Environment variables file .env gitignore ge add maadi.", env["parent_originals"])
            self.assertTrue(any(row["original"] == "C++ pointer memory leak" for row in rows))
            parent = ".env check maadi"
            store.save(parent, "Synthetic technical parser control.", "control", "synthetic_control")
            store.put_run({"id": "control", "input": parent, "saved_english": "Synthetic technical parser control.", "source_label": "synthetic_control"})
            app = object.__new__(App); app.store = store; app.record = lambda *args, **kwargs: None
            app.save_glossary({"id": "control", "terms": [{"original": ".env", "english": "environment file", "origin": "pasted_mapping"}]})
            self.assertEqual(store.glossary_for(parent)[0]["original"], ".env")


if __name__ == "__main__":
    unittest.main()
