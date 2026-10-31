"""Scheduling and timing for viva preparation: SM-2 reviews, mock vivas, readiness, answer checks and talk pacing."""
import datetime
import math
import random
import re

CATEGORIES = ["Opening", "Contribution", "Literature", "Methods", "Results", "Discussion", "Limitations", "Future"]
GRADES = {"Again": 1, "Hard": 3, "Good": 4, "Easy": 5}
MOCK_GRADE = {"Strong": "Good", "Partly": "Hard", "Struggled": "Again"}
FULL_DAYS = 21
WPM = 130
HEDGES = ["i think maybe", "sort of", "kind of", "i guess", "basically", "hopefully", "i'm not sure", "i suppose", "probably just"]

BANK = [
    ("Opening", "Tell us about your thesis in five minutes.", "Practise a spoken summary: the problem, what you did, what you found, why it matters."),
    ("Opening", "Why did you choose this topic?", "Give an intellectual reason as well as a personal one."),
    ("Opening", "How did your research question change along the way?", "Change shows learning. Say what prompted it."),
    ("Opening", "What are you most proud of in this work?", "Pick one specific result or idea."),
    ("Opening", "Which chapter was the hardest to write, and why?", "Be candid, then say how you resolved it."),
    ("Contribution", "What is your original contribution to knowledge?", "State it in one or two sentences, without notes."),
    ("Contribution", "Who will care about this work, and why?", "Name a community and what they can now do."),
    ("Contribution", "What do we know now that we did not know before?", "Give a claim, not a description of your work."),
    ("Contribution", "If you had one sentence to summarise your thesis, what would it be?", "Write it down and learn it."),
    ("Contribution", "Which parts of the thesis could become papers?", "Link chapters to venues, and mention anything already published."),
    ("Literature", "Which three works most shaped your thinking?", "Know their arguments, and where you differ from them."),
    ("Literature", "Where is the gap you address, and how do you know it is a gap?", "Show how you searched, and name the nearest work."),
    ("Literature", "Who would disagree with you, and what would they say?", "Give the strongest opposing case fairly."),
    ("Literature", "How does your work extend or challenge the main theory in the field?", "Be specific about what changes."),
    ("Literature", "How did you decide what to leave out of the review?", "Describe scope and criteria."),
    ("Literature", "What has been published since you finished your review?", "Check the recent literature shortly before the viva."),
    ("Methods", "Why this method rather than the obvious alternative?", "Name the alternative and what you would have lost."),
    ("Methods", "What assumptions does your approach depend on?", "List them, and how you tested each."),
    ("Methods", "How did you choose your sample or data?", "Justify size and selection, and admit any bias."),
    ("Methods", "How did you ensure validity and reliability?", "Use terms that fit your paradigm."),
    ("Methods", "What ethical issues arose, and how did you handle them?", "Mention approval, consent and data handling."),
    ("Methods", "Talk us through how you analysed the data, step by step.", "Be able to justify each decision."),
    ("Methods", "If you ran the study again, what would you change?", "Have two or three real answers ready."),
    ("Methods", "How could someone else reproduce your work?", "Mention data, code and protocols."),
    ("Results", "What is your single most important finding?", "State it plainly, then the evidence."),
    ("Results", "Which result surprised you most?", "Say what you expected, and what you did next."),
    ("Results", "Is there another explanation for this result?", "Offer rivals yourself, then say how you ruled them out."),
    ("Results", "How confident are you in this figure or table?", "Know every figure in the thesis, and what its axes mean."),
    ("Results", "How big is the effect, and does it matter in practice?", "Separate statistical from practical significance."),
    ("Results", "Did any results contradict each other?", "Explain the tension instead of hiding it."),
    ("Discussion", "How do your findings relate to previous work?", "Say where you agree and differ, and why."),
    ("Discussion", "How far can your conclusions be generalised?", "State the boundaries of your claims."),
    ("Discussion", "What are the practical or policy implications?", "Suggest what someone should do differently."),
    ("Discussion", "Do your conclusions really follow from your evidence?", "Trace one conclusion back to its data."),
    ("Discussion", "What does this mean for the theory you started with?", "Say what you would revise."),
    ("Limitations", "What are the main weaknesses of this thesis?", "Name them first, and say why they do not undo your claims."),
    ("Limitations", "Which of your claims is the most vulnerable?", "Show that you know where the pressure falls."),
    ("Limitations", "What did you not do that you wish you had?", "Give a real answer, and explain the constraint."),
    ("Limitations", "How might bias have affected your work?", "Think about your own position, and your data."),
    ("Limitations", "What would prove you wrong?", "Say what evidence would change your mind."),
    ("Future", "What would you do next with another three years?", "Have a concrete first study in mind."),
    ("Future", "What are the most important open questions now?", "Name two and say why they matter."),
    ("Future", "How does this fit into your plans after the PhD?", "A short and honest answer is enough."),
    ("Future", "What have you learned about research from doing this?", "Reflect on process, not only on results."),
    ("Future", "Is there anything you would like to add before we finish?", "Prepare one thing you would like to say."),
]


def to_date(day):
    return day if isinstance(day, datetime.date) else datetime.date.fromisoformat(day)


def days_left(viva_date, day):
    if not viva_date:
        return None
    try:
        return (to_date(viva_date) - to_date(day)).days
    except ValueError:
        return None


def schedule(card, rating, day, limit=None):
    """Apply the SM-2 algorithm. limit keeps every question due again before the viva."""
    q = GRADES[rating]
    ease = max(1.3, (card["ease"] or 2.5) + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    reps = card["reps"] or 0
    if q < 3:
        reps, interval = 0, 1
    else:
        reps += 1
        interval = 1 if reps == 1 else 6 if reps == 2 else round((card["interval"] or 1) * ease)
    if limit is not None:
        interval = max(1, min(interval, limit))
    return {"ease": round(ease, 3), "reps": reps, "interval": interval, "due": (to_date(day) + datetime.timedelta(days=interval)).isoformat(), "last": str(day)}


def preview(card, day, limit=None):
    return {r: schedule(card, r, day, limit)["interval"] for r in GRADES}


def due(cards, day):
    """Questions to practise: overdue first, then ones never seen."""
    day = str(day)
    old = sorted((c for c in cards if c["reps"] or c["last"]), key=lambda c: c["due"] or "")
    return [c for c in old if not c["due"] or c["due"] <= day] + [c for c in cards if not c["reps"] and not c["last"]]


def strength(card):
    """0 to 1: how long you can hold this answer, where three weeks counts as secure."""
    return 0.0 if not card["reps"] else min(1.0, (card["interval"] or 0) / FULL_DAYS)


def readiness(card):
    """Practice carries most of the weight; having written an answer down carries the rest."""
    return 0.7 * strength(card) + 0.3 * (1 if (card["answer"] or "").strip() else 0)


def average(cards):
    return sum(readiness(c) for c in cards) / len(cards) if cards else 0.0


def by_group(cards, key):
    groups = {}
    for c in cards:
        groups.setdefault(key(c), []).append(c)
    return groups


def daily_target(cards, day, viva_date):
    """Reviews per day needed to reach every question at least once more before the viva."""
    left = days_left(viva_date, day)
    if left is None or left <= 0:
        return len(cards)
    return math.ceil(len(cards) / left)


def plan_mock(cards, n, seed=None):
    """n questions spread across chapters, the weakest first in each, then put in the usual order of a viva."""
    rng = random.Random(seed)
    groups = by_group(list(cards), lambda c: c.get("chapter_id"))
    for items in groups.values():
        rng.shuffle(items)
        items.sort(key=strength)
    order = list(groups)
    rng.shuffle(order)
    out = []
    while len(out) < n and any(groups.values()):
        for g in order:
            if groups[g] and len(out) < n:
                out.append(groups[g].pop(0))
    rank = {name: i for i, name in enumerate(CATEGORIES)}
    return sorted(out, key=lambda c: rank.get(c.get("category"), 99))


def mock_summary(results, limit):
    """results: [{question, seconds, rating}]."""
    if not results:
        return {"count": 0, "mean": 0, "over": 0, "strong": 0, "weak": [], "minutes": 0}
    total = sum(r["seconds"] for r in results)
    return {"count": len(results), "mean": total / len(results), "over": sum(1 for r in results if r["seconds"] > limit), "strong": sum(1 for r in results if r["rating"] == "Strong"),
            "weak": [r for r in results if r["rating"] != "Strong"], "minutes": total / 60}


def clock(seconds):
    seconds = int(round(seconds))
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    return "%s%d:%02d" % (sign, seconds // 60, seconds % 60)


def spoken_seconds(text, wpm=WPM):
    return len((text or "").split()) * 60 / wpm


def answer_check(text):
    """Word count, speaking time and habits worth noticing in a written answer."""
    words = len((text or "").split())
    low = (text or "").lower().replace("’", "'")
    found = [h for h in HEDGES if re.search(r"\b%s\b" % re.escape(h), low)]
    notes = []
    if not words:
        notes.append("No answer written yet.")
    elif words < 25:
        notes.append("Very short: add one piece of evidence.")
    elif words > 260:
        notes.append("Over two minutes aloud: find the headline, and let the examiners ask for the detail.")
    if found:
        notes.append("Hedging phrases: %s. Say what you know plainly." % ", ".join(found))
    return {"words": words, "seconds": spoken_seconds(text), "notes": notes}


def share_time(slides, minutes):
    """Split a talk across slides, in proportion to their weight, adding up exactly."""
    if not slides:
        return []
    total = int(minutes * 60)
    weights = [max(1, s["seconds"] or 60) for s in slides]
    out = [int(total * w / sum(weights)) for w in weights]
    for i in range(total - sum(out)):
        out[i % len(out)] += 1
    return out


def pace(planned, actual):
    """Rows of (planned, actual, difference) and a verdict for the whole talk."""
    rows = [(p, a, a - p) for p, a in zip(planned, actual)]
    diff = sum(a for a in actual) - sum(planned[:len(actual)])
    if abs(diff) <= 10:
        verdict = "On time."
    else:
        verdict = "%s by %s." % ("Over" if diff > 0 else "Under", clock(abs(diff)))
    worst = max(rows, key=lambda r: r[2], default=None)
    return {"rows": rows, "diff": diff, "verdict": verdict, "worst": rows.index(worst) if worst and worst[2] > 15 else None}
