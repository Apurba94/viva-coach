"""Viva Coach desktop program."""
import datetime
import time
import tkinter as tk
from tkinter import messagebox, ttk

from . import appkit as ak
from . import viva as vv
from .appkit import Entity, Field, entities

SCHEMA = entities(
    Entity("chapter", "Chapter", "Chapters", "title", [
        Field("number", "Number", "int", default=1, list_col=True, width=8),
        Field("title", "Title", required=True, list_col=True, width=36),
        Field("claim", "Main claim", "long", list_col=True, width=44),
        Field("notes", "Things to reread", "long"),
    ], "number"),
    Entity("question", "Question", "Questions", "text", [
        Field("text", "Question", "long", required=True, list_col=True, width=52),
        Field("chapter_id", "Chapter", "ref", ref="chapter", list_col=True, width=20),
        Field("category", "Category", "choice", vv.CATEGORIES, default="Contribution", list_col=True, width=12),
        Field("hint", "Advice", "long"),
        Field("answer", "My answer notes", "long"),
        Field("ease", "Ease", "number", default=2.5),
        Field("interval", "Interval", "int", default=0, list_col=True, width=8),
        Field("reps", "Reviews", "int", default=0),
        Field("due", "Due", "date", list_col=True, width=11),
        Field("last", "Last practised", "date"),
    ], "id"),
    Entity("examiner", "Examiner", "Examiners", "name", [
        Field("name", "Name", required=True, list_col=True, width=24),
        Field("role", "Role", "choice", ["Internal", "External", "Chair", "Supervisor"], default="External", list_col=True, width=10),
        Field("field", "Field", list_col=True, width=26),
        Field("works", "Their relevant work", "long"),
        Field("likely", "Questions they may ask", "long", list_col=True, width=40),
    ]),
    Entity("slide", "Slide", "Slides", "title", [
        Field("position", "Order", "int", default=1, list_col=True, width=8),
        Field("title", "Slide", required=True, list_col=True, width=36),
        Field("seconds", "Planned seconds", "int", default=60, list_col=True, width=14),
        Field("notes", "Speaker notes", "long"),
    ], "position"),
    Entity("session", "Session", "Sessions", "kind", [
        Field("day", "Date", "date", required=True, list_col=True, width=11),
        Field("kind", "Kind", list_col=True, width=12),
        Field("questions", "Items", "int", list_col=True, width=7),
        Field("minutes", "Minutes", "number", list_col=True, width=9),
        Field("summary", "Summary", "long", list_col=True, width=50),
    ], "day DESC, id DESC"),
)


def add_bank(store, chapter=None):
    """Add the standard questions that are not in the database yet, and report how many were new."""
    have = {q["text"] for q in store.list("question")}
    n = 0
    for category, text, hint in vv.BANK:
        if text not in have:
            store.insert("question", text=text, category=category, hint=hint, chapter_id=chapter)
            n += 1
    return n


def sample(store):
    c = [store.insert("chapter", number=n, title=t, claim=k) for n, t, k in (
        (1, "Introduction", "Sleep timing shapes memory more than sleep length."), (2, "Literature review", "Earlier studies did not separate timing from length."),
        (3, "Method", "A within-subject design isolates timing."), (4, "Results", "Later sleep lowered recall by a medium effect."), (5, "Discussion", "Schedules matter for students' learning."))]
    add_bank(store)
    cats = {"Opening": c[0], "Contribution": c[0], "Literature": c[1], "Methods": c[2], "Results": c[3], "Discussion": c[4], "Limitations": c[4], "Future": c[4]}
    start = datetime.date.fromisoformat(ak.today())
    for i, q in enumerate(store.list("question")):
        extra = {}
        if i % 3 == 0:
            iv = (1, 6, 15, 24)[i % 4]
            extra = dict(reps=1 + i % 4, interval=iv, last=ak.today(), due=(start + datetime.timedelta(days=(i % 5) - 2)).isoformat())
        if i % 4 == 0:
            extra["answer"] = "A fictional outline answer, with one piece of evidence from the chapter that supports it."
        store.update("question", q["id"], chapter_id=cats[q["category"]], **extra)
    store.insert("examiner", name="Dr A. External (fictional)", role="External", field="Cognitive psychology", works="Wrote the main review of sleep and recall.", likely="Why not a larger sample?\nHow does this fit her 2019 model?")
    for i, (t, s) in enumerate((("Title and thanks", 20), ("The problem", 90), ("What was missing", 90), ("Research questions", 60), ("Design", 120), ("Main result", 150), ("What it means", 120), ("Limits and next steps", 60), ("Take-home message", 30)), 1):
        store.insert("slide", position=i, title=t, seconds=s, notes="A short fictional speaker note for this slide, for rehearsal.")
    store.set_setting("viva_date", (start + datetime.timedelta(days=30)).isoformat())
    store.insert("session", day=ak.today(), kind="Mock viva", questions=5, minutes=9.5, summary="3 strong, 2 to revisit (sample)")


def limit_for(store):
    left = vv.days_left(store.get_setting("viva_date"), ak.today())
    return left if left and left > 0 else None


class Today(ttk.Frame):
    title = "Today"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        self.date = tk.StringVar()
        ak.labeled_entry(row, "Viva date (YYYY-MM-DD)", self.date, 16).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Save date", command=self.save_date).pack(side="left", anchor="s")
        ttk.Button(row, text="Start practice", style="Accent.TButton", command=lambda: app.navigate("Practice")).pack(side="left", anchor="s", padx=(8, 0))
        self.head = ttk.Frame(self)
        self.head.pack(fill="x", pady=(0, 8))
        self.advice = ttk.Label(self, wraplength=int(950 * app.scale), justify="left")
        self.advice.pack(anchor="w", pady=(0, 8))
        self.table = ak.Table(self, app, [("d", "Date", 12), ("k", "Kind", 14), ("q", "Items", 8), ("m", "Minutes", 9), ("s", "Summary", 60)])
        self.table.pack(fill="both", expand=True)

    def save_date(self):
        text = self.date.get().strip()
        if text and not ak.parse_date(text):
            messagebox.showerror("Viva date", "Please enter the date as YYYY-MM-DD.", parent=self)
            return False
        self.app.store.set_setting("viva_date", text)
        self.refresh()
        return True

    def refresh(self):
        s = self.app.store
        date = s.get_setting("viva_date")
        self.date.set(date or "")
        cards = s.list("question")
        day = ak.today()
        left = vv.days_left(date, day)
        waiting = vv.due(cards, day)
        for w in self.head.winfo_children():
            w.destroy()
        ak.tiles(self.head, [("Days to the viva", "-" if left is None else str(left), date or "set the date above"), ("Waiting today", str(len(waiting)), "questions"),
                             ("Readiness", "%.0f%%" % (100 * vv.average(cards)), "practice and written notes"), ("Sessions", str(s.count("session")), "practice and rehearsal")]).pack(fill="x")
        if left is None:
            text = "Set your viva date, and intervals will be kept short enough that every question comes back before the day."
        elif left < 0:
            text = "The date has passed. Congratulations if it went well: update the date if it has moved."
        elif left == 0:
            text = "It is today. Read your main claim once, eat something, and trust your preparation. You know this work better than anyone in the room."
        else:
            text = "About %d reviews a day will cover every question before the viva. Rehearse your talk at least twice a week in the final fortnight." % vv.daily_target(cards, day, date)
        self.advice.configure(text=text)
        self.table.fill([[r["day"], r["kind"] or "", r["questions"] or "", "%g" % r["minutes"] if r["minutes"] else "", ak.short(r["summary"] or "", 90)] for r in s.list("session")[:30]])


class Practice(ttk.Frame):
    title = "Practice"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.queue, self.card, self.done = [], None, 0
        self.count = ttk.Label(self, style="Muted.TLabel")
        self.count.pack(anchor="w", pady=(0, 6))
        box = ak.panel(self, padding=18)
        box.pack(fill="both", expand=True)
        self.where = ttk.Label(box, style="PanelMuted.TLabel")
        self.where.pack(anchor="w")
        self.question = ttk.Label(box, style="Head.TLabel", wraplength=int(880 * app.scale), justify="left", font=(ak.FONT, 15, "bold"))
        self.question.pack(anchor="w", pady=(6, 10))
        self.prompt = ttk.Label(box, style="PanelMuted.TLabel", text="Answer aloud first, as you would in the room. Then compare.")
        self.prompt.pack(anchor="w")
        self.reveal_area = ttk.Frame(box, style="Panel.TFrame")
        self.reveal_area.pack(fill="both", expand=True, pady=(10, 0))
        self.hint = ttk.Label(self.reveal_area, style="PanelMuted.TLabel", wraplength=int(880 * app.scale), justify="left")
        self.hint.pack(anchor="w", pady=(0, 6))
        frame, self.notes = ak.make_text(self.reveal_area, app.colors, height=7)
        frame.pack(fill="both", expand=True)
        self.controls = ttk.Frame(self)
        self.controls.pack(fill="x", pady=(8, 0))
        self.show_btn = ttk.Button(self.controls, text="Show advice and my notes", style="Accent.TButton", command=self.reveal)
        self.more_btn = ttk.Button(self.controls, text="Practise the five weakest anyway", command=self.extra)
        self.rate_btns = {}
        for name in vv.GRADES:
            self.rate_btns[name] = ttk.Button(self.controls, command=lambda n=name: self.rate(n))

    def refresh(self):
        self.commit()
        cards = self.app.store.list("question")
        self.queue = [c["id"] for c in vv.due(cards, ak.today())]
        self.next_card()

    def extra(self):
        cards = sorted(self.app.store.list("question"), key=vv.readiness)
        self.queue = [c["id"] for c in cards[:5]]
        self.next_card()

    def clear_controls(self):
        for w in self.controls.winfo_children():
            w.pack_forget()

    def next_card(self):
        self.clear_controls()
        self.reveal_area.pack_forget()
        self.card = self.app.store.get("question", self.queue[0]) if self.queue else None
        self.count.configure(text="%d waiting, %d reviewed in this sitting" % (len(self.queue), self.done))
        if not self.card:
            self.where.configure(text="")
            self.question.configure(text="All done for today.")
            self.prompt.configure(text="Come back tomorrow: the spacing is what makes it stick.")
            if self.app.store.count("question"):
                self.more_btn.pack(side="left")
            return
        c = self.card
        self.where.configure(text=" · ".join(x for x in (c["category"], self.app.store.label("chapter", c["chapter_id"]) if c["chapter_id"] else "") if x))
        self.question.configure(text=c["text"])
        self.prompt.configure(text="Answer aloud first, as you would in the room. Then compare.")
        self.show_btn.pack(side="left")

    def reveal(self):
        c = self.card
        self.prompt.configure(text="How did that go? You can improve your notes here.")
        self.hint.configure(text=c["hint"] or "")
        ak.set_text(self.notes, c["answer"] or "")
        self.reveal_area.pack(fill="both", expand=True, pady=(10, 0))
        self.clear_controls()
        day = ak.today()
        days = vv.preview(c, day, limit_for(self.app.store))
        for name, b in self.rate_btns.items():
            b.configure(text="%s (%s)" % (name, "%d day%s" % (days[name], "" if days[name] == 1 else "s")))
            b.pack(side="left", padx=(0, 6))

    def commit(self):
        """Keep edits to the notes of the card on screen."""
        if self.card and self.rate_btns["Good"].winfo_ismapped():
            self.app.store.update("question", self.card["id"], answer=ak.get_text(self.notes).strip())
        return True

    def rate(self, name):
        c = self.card
        self.app.store.update("question", c["id"], answer=ak.get_text(self.notes).strip(), **vv.schedule(c, name, ak.today(), limit_for(self.app.store)))
        self.queue.pop(0)
        if name == "Again":
            self.queue.append(c["id"])
        self.done += 1
        log(self.app.store, "Practice", 1)
        self.next_card()


def log(store, kind, items, minutes=None, summary=""):
    """One practice row per day; rehearsals get a row each."""
    day = ak.today()
    if kind == "Practice":
        rows = store.list("session", "day=? AND kind=?", (day, kind))
        if rows:
            n = (rows[0]["questions"] or 0) + items
            store.update("session", rows[0]["id"], questions=n, summary="%d reviews" % n)
            return
        summary = "%d reviews" % items
    store.insert("session", day=day, kind=kind, questions=items, minutes=minutes, summary=summary)


class Timed(ttk.Frame):
    """A clock that follows the current item of a timed run."""
    now = staticmethod(time.monotonic)

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.running, self.started, self.job = False, 0.0, None

    def seconds(self):
        return self.now() - self.started

    def begin_item(self):
        self.started = self.now()
        self.running = True
        self.tick()

    def tick(self):
        if self.job:
            self.after_cancel(self.job)
            self.job = None
        if self.running:
            self.paint(self.seconds())
            self.job = self.after(250, self.tick)

    def halt(self):
        self.running = False
        self.tick()


class Mock(Timed):
    title = "Mock viva"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.items, self.results, self.index = [], [], 0
        self.setup = ttk.Frame(self)
        self.setup.pack(fill="x", pady=(0, 8))
        self.number, self.limit = tk.StringVar(value="10"), tk.StringVar(value="120")
        ak.labeled_combo(self.setup, "Questions", self.number, ["5", "10", "15", "20", "30"], 6).pack(side="left", padx=(0, 8))
        ak.labeled_combo(self.setup, "Seconds for each", self.limit, ["60", "90", "120", "180", "240"], 8).pack(side="left", padx=(0, 8))
        self.start_btn = ttk.Button(self.setup, text="Start mock viva", style="Accent.TButton", command=self.start)
        self.start_btn.pack(side="left", anchor="s")
        ttk.Button(self.setup, text="Stop", command=self.finish).pack(side="left", anchor="s", padx=(6, 0))
        box = ak.panel(self, padding=18)
        box.pack(fill="x")
        self.progress = ttk.Label(box, style="PanelMuted.TLabel", text="Questions come from every chapter, weakest first, in the usual order of a viva.")
        self.progress.pack(anchor="w")
        self.clock_lbl = ttk.Label(box, style="Kpi.TLabel", text="0:00")
        self.clock_lbl.pack(anchor="w")
        self.question = ttk.Label(box, style="Head.TLabel", wraplength=int(880 * app.scale), justify="left", font=(ak.FONT, 15, "bold"))
        self.question.pack(anchor="w", pady=(6, 10))
        self.rating = ttk.Frame(box, style="Panel.TFrame")
        self.rating.pack(anchor="w")
        for name in vv.MOCK_GRADE:
            ttk.Button(self.rating, text=name, command=lambda n=name: self.answered(n)).pack(side="left", padx=(0, 6))
        self.outcome = ttk.Label(self, wraplength=int(950 * app.scale), justify="left")
        self.outcome.pack(anchor="w", pady=(8, 4))
        self.table = ak.Table(self, app, [("q", "Question", 66), ("t", "Time", 8), ("r", "How it went", 12)])
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        pass

    def paint(self, s):
        limit = int(self.limit.get())
        self.clock_lbl.configure(text=vv.clock(s), foreground=self.app.colors["danger"] if s > limit else self.app.colors["ink"])

    def start(self):
        self.items = vv.plan_mock(self.app.store.list("question"), int(self.number.get()))
        self.results, self.index = [], 0
        self.table.fill([])
        self.outcome.configure(text="")
        if self.items:
            self.show_question()

    def show_question(self):
        q = self.items[self.index]
        self.progress.configure(text="Question %d of %d · %s" % (self.index + 1, len(self.items), q["category"] or ""))
        self.question.configure(text=q["text"])
        self.begin_item()

    def answered(self, rating):
        if not self.running:
            return
        q = self.items[self.index]
        self.results.append({"id": q["id"], "text": q["text"], "seconds": self.seconds(), "rating": rating})
        self.app.store.update("question", q["id"], **vv.schedule(q, vv.MOCK_GRADE[rating], ak.today(), limit_for(self.app.store)))
        self.index += 1
        if self.index < len(self.items):
            self.show_question()
        else:
            self.finish()

    def finish(self):
        if not self.running:
            return
        self.halt()
        limit = int(self.limit.get())
        r = vv.mock_summary(self.results, limit)
        self.question.configure(text="Mock viva finished")
        self.progress.configure(text="")
        text = "%d of %d strong, average %s per question, %d over time." % (r["strong"], r["count"], vv.clock(r["mean"]), r["over"])
        self.outcome.configure(text=text + " Questions that did not go well will return in practice soon.")
        self.table.fill([("%d" % i, (ak.short(x["text"], 90), vv.clock(x["seconds"]), x["rating"]), "ok" if x["rating"] == "Strong" else "warning") for i, x in enumerate(self.results)])
        if self.results:
            log(self.app.store, "Mock viva", r["count"], round(r["minutes"], 1), text)


class Bank(ttk.Frame):
    title = "Question bank"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.view = ak.EntityView(self, app, "question", skip=("ease", "interval", "reps", "due", "last"), buttons=[("Add standard questions", self.add)], on_select=self.check, split=0.58)
        self.view.pack(fill="both", expand=True)
        self.note = ttk.Label(self, style="Muted.TLabel", wraplength=int(950 * app.scale), justify="left")
        self.note.pack(anchor="w", pady=(6, 0))
        self.refresh, self.commit = self.view.refresh, self.view.commit

    def add(self):
        n = add_bank(self.app.store)
        self.view.refresh()
        self.app.status("Added %d standard questions" % n)

    def check(self, row):
        if not row:
            self.note.configure(text="")
            return
        c = vv.answer_check(row["answer"])
        self.note.configure(text="Notes: %d words, about %s aloud. %s" % (c["words"], vv.clock(c["seconds"]), " ".join(c["notes"])))


class Chapters(ttk.Frame):
    title = "Chapters"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.view = ak.EntityView(self, app, "chapter")
        self.view.pack(fill="both", expand=True)
        self.refresh, self.commit = self.view.refresh, self.view.commit


class Readiness(ttk.Frame):
    title = "Readiness"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Readiness counts how long you can hold each answer (three weeks counts as secure) and whether you have written notes. It is a guide, not a prediction.",
                  style="Muted.TLabel", wraplength=int(950 * app.scale), justify="left").pack(anchor="w", pady=(0, 6))
        cols = [("n", "Group", 30), ("q", "Questions", 10), ("s", "Practised", 10), ("w", "With notes", 11), ("r", "Readiness", 10)]
        ttk.Label(self, text="By chapter", style="Muted.TLabel").pack(anchor="w")
        self.chapters = ak.Table(self, app, cols, height=6)
        self.chapters.pack(fill="both", expand=True, pady=(0, 8))
        ttk.Label(self, text="By kind of question", style="Muted.TLabel").pack(anchor="w")
        self.kinds = ak.Table(self, app, cols, height=8)
        self.kinds.pack(fill="both", expand=True)

    @staticmethod
    def row(name, cards):
        r = vv.average(cards)
        return (name, ([name, len(cards), sum(1 for c in cards if c["reps"]), sum(1 for c in cards if (c["answer"] or "").strip()), "%.0f%%" % (100 * r)]), "ok" if r >= 0.7 else "danger" if r < 0.3 else "warning")

    def refresh(self):
        cards = self.app.store.list("question")
        names = {c["id"]: c["title"] for c in self.app.store.list("chapter")}
        g = vv.by_group(cards, lambda c: names.get(c["chapter_id"], "No chapter"))
        self.chapters.fill([self.row(n, g[n]) for n in sorted(g, key=lambda k: vv.average(g[k]))])
        g2 = vv.by_group(cards, lambda c: c["category"] or "Other")
        self.kinds.fill([self.row(n, g2[n]) for n in vv.CATEGORIES + ["Other"] if n in g2])


class Slides(ttk.Frame):
    title = "Slides"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.view = ak.EntityView(self, app, "slide")
        self.view.pack(fill="both", expand=True)
        self.refresh, self.commit = self.view.refresh, self.view.commit


class Rehearsal(Timed):
    title = "Talk rehearsal"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.slides, self.times, self.index = [], [], 0
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        self.minutes = tk.StringVar(value="15")
        ak.labeled_entry(top, "Talk length (minutes)", self.minutes, 10).pack(side="left", padx=(0, 8))
        ttk.Button(top, text="Share time across slides", command=self.share).pack(side="left", anchor="s", padx=(0, 8))
        ttk.Button(top, text="Start rehearsal", style="Accent.TButton", command=self.start).pack(side="left", anchor="s", padx=(0, 6))
        self.next_btn = ttk.Button(top, text="Next slide", command=self.advance)
        self.next_btn.pack(side="left", anchor="s", padx=(0, 6))
        ttk.Button(top, text="Stop", command=self.stop).pack(side="left", anchor="s")
        box = ak.panel(self, padding=14)
        box.pack(fill="x")
        self.now_lbl = ttk.Label(box, style="Head.TLabel", text="Ready when you are")
        self.now_lbl.pack(anchor="w")
        self.clock_lbl = ttk.Label(box, style="Kpi.TLabel", text="0:00")
        self.clock_lbl.pack(anchor="w")
        self.notes = ttk.Label(box, style="PanelMuted.TLabel", wraplength=int(880 * app.scale), justify="left")
        self.notes.pack(anchor="w")
        self.verdict = ttk.Label(self, wraplength=int(950 * app.scale), justify="left")
        self.verdict.pack(anchor="w", pady=(8, 4))
        self.table = ak.Table(self, app, [("s", "Slide", 36), ("p", "Planned", 9), ("e", "Notes aloud", 12), ("a", "Rehearsed", 11), ("d", "Difference", 11)])
        self.table.pack(fill="both", expand=True)

    def paint(self, s):
        planned = self.slides[self.index]["seconds"] or 0 if self.index < len(self.slides) else 0
        self.clock_lbl.configure(text=vv.clock(s), foreground=self.app.colors["danger"] if s > planned else self.app.colors["ink"])

    def show_table(self):
        rows = []
        for i, s in enumerate(self.slides):
            planned = s["seconds"] or 0
            done = i < len(self.times)
            late = done and self.times[i] - planned > 15
            rows.append(("%d" % s["id"], (s["title"], vv.clock(planned), vv.clock(vv.spoken_seconds(s["notes"])), vv.clock(self.times[i]) if done else "", ("%+d s" % round(self.times[i] - planned)) if done else ""), "warning" if late else ""))
        self.table.fill(rows)

    def refresh(self):
        if not self.running:
            self.slides = self.app.store.list("slide")
            self.verdict.configure(text="%d slides, %s planned." % (len(self.slides), vv.clock(sum(s["seconds"] or 0 for s in self.slides))) if not self.times else self.verdict.cget("text"))
            self.show_table()

    def share(self):
        try:
            minutes = float(self.minutes.get())
        except ValueError:
            messagebox.showerror("Talk length", "Please enter a number of minutes.", parent=self)
            return
        if minutes <= 0:
            return
        self.times = []
        for s, secs in zip(self.slides, vv.share_time(self.slides, minutes)):
            self.app.store.update("slide", s["id"], seconds=secs)
        self.refresh()

    def start(self):
        self.slides = self.app.store.list("slide")
        self.times, self.index = [], 0
        if self.slides:
            self.verdict.configure(text="")
            self.show_table()
            self.show_slide()

    def show_slide(self):
        s = self.slides[self.index]
        self.now_lbl.configure(text="%d of %d: %s" % (self.index + 1, len(self.slides), s["title"]))
        self.notes.configure(text=ak.short(s["notes"] or "", 400))
        self.begin_item()

    def advance(self):
        if not self.running:
            return
        self.times.append(self.seconds())
        self.index += 1
        if self.index < len(self.slides):
            self.show_table()
            self.show_slide()
        else:
            self.stop()

    def stop(self):
        if not self.running:
            return
        self.halt()
        self.now_lbl.configure(text="Rehearsal finished")
        self.notes.configure(text="")
        self.show_table()
        if self.times:
            planned = [s["seconds"] or 0 for s in self.slides]
            p = vv.pace(planned, self.times)
            extra = ' The longest overrun was "%s".' % self.slides[p["worst"]]["title"] if p["worst"] is not None else ""
            text = "%s Total %s across %d of %d slides.%s" % (p["verdict"], vv.clock(sum(self.times)), len(self.times), len(self.slides), extra)
            self.verdict.configure(text=text)
            log(self.app.store, "Talk", len(self.times), round(sum(self.times) / 60, 1), text)


class Examiners(ttk.Frame):
    title = "Examiners"

    def __init__(self, parent, app):
        super().__init__(parent)
        ttk.Label(self, text="Read your examiners' recent work. Note where it touches yours, and what they are likely to probe.", style="Muted.TLabel").pack(anchor="w", pady=(0, 6))
        self.view = ak.EntityView(self, app, "examiner")
        self.view.pack(fill="both", expand=True)
        self.refresh, self.commit = self.view.refresh, self.view.commit


class APP(ak.BaseApp):
    APP_NAME, ACCENT = "Viva Coach", "#6d28d9"
    SCHEMA, SAMPLE = SCHEMA, staticmethod(sample)
    VIEWS = [Today, Practice, Mock, Bank, Chapters, Readiness, Slides, Rehearsal, Examiners, ak.DataView]


def main(argv=None):
    return ak.main(APP, argv)
