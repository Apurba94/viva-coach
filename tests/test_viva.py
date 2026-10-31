import datetime
import os
import shutil
import tempfile
import tkinter as tk
import unittest
from unittest import mock

from viva_coach import app as A
from viva_coach import appkit as ak
from viva_coach import viva as vv

DAY = "2026-11-01"


def card(**kw):
    c = {"id": 1, "ease": 2.5, "reps": 0, "interval": 0, "due": None, "last": None, "answer": "", "chapter_id": None, "category": "Methods", "text": "Q"}
    c.update(kw)
    return c


class TestSchedule(unittest.TestCase):
    def test_sm2_intervals(self):
        c = card()
        c.update(vv.schedule(c, "Good", DAY))
        self.assertEqual((c["reps"], c["interval"], c["due"]), (1, 1, "2026-11-02"))
        c.update(vv.schedule(c, "Good", DAY))
        self.assertEqual((c["reps"], c["interval"]), (2, 6))
        c.update(vv.schedule(c, "Good", DAY))
        self.assertEqual((c["reps"], c["interval"]), (3, 15))                 # 6 * 2.5, ease unchanged by a 4

    def test_ease_changes(self):
        self.assertEqual(vv.schedule(card(), "Good", DAY)["ease"], 2.5)
        self.assertEqual(vv.schedule(card(), "Easy", DAY)["ease"], 2.6)
        self.assertEqual(vv.schedule(card(), "Hard", DAY)["ease"], 2.36)      # 2.5 + .1 - 2 * (.08 + 2 * .02)
        self.assertEqual(vv.schedule(card(ease=1.3), "Again", DAY)["ease"], 1.3)

    def test_again_starts_over(self):
        r = vv.schedule(card(reps=5, interval=40), "Again", DAY)
        self.assertEqual((r["reps"], r["interval"]), (0, 1))

    def test_nothing_is_scheduled_past_the_viva(self):
        r = vv.schedule(card(reps=5, interval=40), "Easy", DAY, limit=9)
        self.assertEqual(r["interval"], 9)
        self.assertEqual(vv.schedule(card(), "Good", DAY, limit=0)["interval"], 1)

    def test_preview(self):
        self.assertEqual(vv.preview(card(reps=1, interval=1), DAY), {"Again": 1, "Hard": 6, "Good": 6, "Easy": 6})

    def test_due_order(self):
        a = card(id=1, reps=2, interval=6, due="2026-11-05", last="2026-10-30")
        b = card(id=2, reps=1, interval=1, due="2026-10-20", last="2026-10-19")
        c = card(id=3, reps=1, interval=1, due=DAY, last="2026-10-31")
        d = card(id=4)
        self.assertEqual([x["id"] for x in vv.due([a, b, c, d], DAY)], [2, 3, 4])

    def test_failed_card_with_no_reps_is_not_treated_as_new(self):
        c = card(reps=0, last=DAY, due="2026-11-02", interval=1)
        self.assertEqual(vv.due([c], DAY), [])
        self.assertEqual(vv.due([c], "2026-11-02"), [c])


class TestReadiness(unittest.TestCase):
    def test_strength_scale(self):
        self.assertEqual(vv.strength(card()), 0)
        self.assertEqual(vv.strength(card(reps=2, interval=21)), 1)
        self.assertEqual(vv.strength(card(reps=9, interval=90)), 1)

    def test_notes_alone_are_not_enough(self):
        self.assertAlmostEqual(vv.readiness(card(answer="Notes")), 0.3)
        self.assertAlmostEqual(vv.readiness(card(answer="  ")), 0)
        self.assertAlmostEqual(vv.readiness(card(answer="Notes", reps=3, interval=30)), 1)
        self.assertEqual(vv.average([]), 0)

    def test_days_and_target(self):
        self.assertEqual(vv.days_left("2026-11-11", DAY), 10)
        self.assertIsNone(vv.days_left("", DAY))
        self.assertIsNone(vv.days_left("soon", DAY))
        self.assertEqual(vv.daily_target([card()] * 45, DAY, "2026-11-11"), 5)
        self.assertEqual(vv.daily_target([card()] * 45, DAY, ""), 45)


class TestMock(unittest.TestCase):
    def test_spreads_across_chapters(self):
        cards = [card(id=i, chapter_id=i % 3) for i in range(30)]
        got = vv.plan_mock(cards, 9, seed=1)
        self.assertEqual(sorted(sum(1 for c in got if c["chapter_id"] == k) for k in range(3)), [3, 3, 3])
        self.assertEqual(len({c["id"] for c in got}), 9)

    def test_weakest_come_first_in_a_chapter(self):
        cards = [card(id=1, reps=5, interval=30), card(id=2)]
        self.assertEqual(vv.plan_mock(cards, 1, seed=3)[0]["id"], 2)

    def test_runs_in_viva_order(self):
        cards = [card(id=i, category=c) for i, c in enumerate(reversed(vv.CATEGORIES))]
        self.assertEqual([c["category"] for c in vv.plan_mock(cards, 8, seed=2)], vv.CATEGORIES)

    def test_asks_for_more_than_exist(self):
        self.assertEqual(len(vv.plan_mock([card()], 10)), 1)
        self.assertEqual(vv.plan_mock([], 10), [])

    def test_summary(self):
        s = vv.mock_summary([{"seconds": 60, "rating": "Strong"}, {"seconds": 180, "rating": "Struggled"}], 120)
        self.assertEqual((s["count"], s["mean"], s["over"], s["strong"], s["minutes"], len(s["weak"])), (2, 120, 1, 1, 4, 1))
        self.assertEqual(vv.mock_summary([], 120)["count"], 0)


class TestTiming(unittest.TestCase):
    def test_clock(self):
        self.assertEqual([vv.clock(x) for x in (0, 59.6, 61, 3600, -75)], ["0:00", "1:00", "1:01", "60:00", "-1:15"])

    def test_answer_check(self):
        self.assertIn("No answer", vv.answer_check("")["notes"][0])
        self.assertIn("short", vv.answer_check("Too few words")["notes"][0])
        self.assertIn("two minutes", vv.answer_check("word " * 300)["notes"][0])
        self.assertEqual(vv.answer_check("word " * 130)["seconds"], 60)
        self.assertIn("sort of", vv.answer_check("It was sort of good, I guess, " + "word " * 40)["notes"][0])
        self.assertEqual(vv.answer_check("word " * 50)["notes"], [])

    def test_share_time(self):
        slides = [{"seconds": 60}, {"seconds": 120}, {"seconds": 60}]
        self.assertEqual(vv.share_time(slides, 8), [120, 240, 120])
        self.assertEqual(sum(vv.share_time([{"seconds": 7}, {"seconds": 11}, {"seconds": 13}], 10)), 600)
        self.assertEqual(vv.share_time([], 10), [])

    def test_pace(self):
        p = vv.pace([60, 60, 60], [60, 120, 60])
        self.assertEqual((p["diff"], p["verdict"], p["worst"]), (60, "Over by 1:00.", 1))
        self.assertEqual(vv.pace([60, 60], [62, 55])["verdict"], "On time.")
        self.assertEqual(vv.pace([60, 60], [30, 30])["verdict"], "Under by 1:00.")
        self.assertEqual(vv.pace([60, 60], [60])["verdict"], "On time.")      # stopped early: only the slides given count
        self.assertIsNone(vv.pace([60], [65])["worst"])

    def test_bank(self):
        self.assertGreaterEqual(len(vv.BANK), 45)
        self.assertEqual(len({t for _, t, _ in vv.BANK}), len(vv.BANK))
        self.assertEqual({c for c, _, _ in vv.BANK}, set(vv.CATEGORIES))
        self.assertTrue(all(h for _, _, h in vv.BANK))


class TestGui(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = ak.Store(A.SCHEMA, os.path.join(self.dir, "t.sqlite3"), A.APP.APP_NAME)
        A.sample(self.store)
        try:
            self.app = A.APP(self.store)
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.errors = []
        self.app.report_callback_exception = lambda e, v, t: self.errors.append(repr(v))
        self.app.update()

    def tearDown(self):
        self.store.close()
        self.app.destroy()
        shutil.rmtree(self.dir, ignore_errors=True)
        self.assertEqual(self.errors, [])

    def test_every_screen_in_both_themes(self):
        for theme in ("Dark", "Light"):
            self.app.set_theme(theme)
            for t in self.app.titles():
                self.app.navigate(t)
                self.app.update()

    def test_notes_stay_hidden_until_revealed(self):
        self.app.navigate("Practice")
        p = self.app.views["Practice"]
        self.app.update()
        self.assertFalse(p.reveal_area.winfo_ismapped())
        p.reveal()
        self.app.update()
        self.assertTrue(p.reveal_area.winfo_ismapped())
        self.assertTrue(p.rate_btns["Good"].winfo_ismapped())

    def test_rating_saves_and_moves_on(self):
        self.app.navigate("Practice")
        p = self.app.views["Practice"]
        first, n = p.card["id"], len(p.queue)
        p.reveal()
        ak.set_text(p.notes, "My new notes")
        p.rate("Good")
        row = self.store.get("question", first)
        self.assertEqual(row["answer"], "My new notes")
        self.assertEqual(row["last"], ak.today())
        self.assertEqual(len(p.queue), n - 1)
        self.assertNotEqual(p.card["id"], first)

    def test_again_comes_back_in_the_same_sitting(self):
        self.app.navigate("Practice")
        p = self.app.views["Practice"]
        first, n = p.card["id"], len(p.queue)
        p.reveal()
        p.rate("Again")
        self.assertEqual((p.queue[-1], len(p.queue)), (first, n))

    def test_practice_is_logged_once_a_day(self):
        self.app.navigate("Practice")
        p = self.app.views["Practice"]
        for _ in range(3):
            p.reveal()
            p.rate("Good")
        rows = self.store.list("session", "kind='Practice'")
        self.assertEqual((len(rows), rows[0]["questions"]), (1, 3))

    def test_leaving_keeps_edited_notes(self):
        self.app.navigate("Practice")
        p = self.app.views["Practice"]
        self.app.update()
        rid = p.card["id"]
        p.reveal()
        self.app.update()
        ak.set_text(p.notes, "Keep me")
        self.app.navigate("Today")
        self.assertEqual(self.store.get("question", rid)["answer"], "Keep me")

    def test_mock_viva(self):
        self.app.navigate("Mock viva")
        m = self.app.views["Mock viva"]
        t = [100.0]
        m.now = lambda: t[0]
        m.number.set("5")
        m.limit.set("60")
        m.start()
        self.assertEqual(len(m.items), 5)
        before = self.store.count("session")
        for rating in ("Strong", "Partly", "Struggled", "Strong", "Strong"):
            t[0] += 90 if rating == "Partly" else 30
            m.answered(rating)
        self.assertFalse(m.running)
        self.assertIn("3 of 5 strong", m.outcome.cget("text"))
        self.assertIn("1 over time", m.outcome.cget("text"))
        self.assertEqual(self.store.count("session"), before + 1)
        weak = self.store.get("question", m.results[2]["id"])
        self.assertEqual((weak["reps"], weak["interval"]), (0, 1))

    def test_stopping_a_mock_early_with_no_answers_logs_nothing(self):
        self.app.navigate("Mock viva")
        m = self.app.views["Mock viva"]
        before = self.store.count("session")
        m.start()
        m.finish()
        self.assertFalse(m.running)
        self.assertEqual(self.store.count("session"), before)

    def test_rehearsal(self):
        self.app.navigate("Talk rehearsal")
        r = self.app.views["Talk rehearsal"]
        t = [0.0]
        r.now = lambda: t[0]
        r.minutes.set("10")
        r.share()
        self.assertEqual(sum(s["seconds"] for s in self.store.list("slide")), 600)
        r.start()
        for s in list(r.slides):
            t[0] += (s["seconds"] or 0) + (120 if s["title"] == "Design" else 0)
            r.advance()
        self.assertFalse(r.running)
        self.assertIn("Over by 2:00", r.verdict.cget("text"))
        self.assertIn('"Design"', r.verdict.cget("text"))
        self.assertEqual(self.store.count("session", "kind='Talk'"), 1)

    def test_stopping_a_talk_midway(self):
        self.app.navigate("Talk rehearsal")
        r = self.app.views["Talk rehearsal"]
        t = [0.0]
        r.now = lambda: t[0]
        r.start()
        t[0] = 20
        r.advance()
        r.stop()
        self.assertIn("1 of 9 slides", r.verdict.cget("text"))

    def test_viva_date_is_checked(self):
        v = self.app.views.get("Today") or self.app.view("Today")
        v.date.set("next week")
        with mock.patch("tkinter.messagebox.showerror") as err:
            self.assertFalse(v.save_date())
        err.assert_called_once()
        v.date.set("2030-01-02")
        self.assertTrue(v.save_date())
        self.assertEqual(self.store.get_setting("viva_date"), "2030-01-02")

    def test_intervals_stop_at_the_viva(self):
        self.store.set_setting("viva_date", (datetime.date.today() + datetime.timedelta(days=3)).isoformat())
        self.assertEqual(A.limit_for(self.store), 3)
        self.store.set_setting("viva_date", "")
        self.assertIsNone(A.limit_for(self.store))

    def test_standard_questions_are_not_added_twice(self):
        self.assertEqual(A.add_bank(self.store), 0)

    def test_empty_database(self):
        self.store.close()
        self.app.destroy()
        self.store = ak.Store(A.SCHEMA, os.path.join(self.dir, "e.sqlite3"), A.APP.APP_NAME)
        self.app = A.APP(self.store)
        for t in self.app.titles():
            self.app.navigate(t)
            self.app.update()
        self.app.views["Mock viva"].start()
        self.app.views["Talk rehearsal"].start()


if __name__ == "__main__":
    unittest.main()
