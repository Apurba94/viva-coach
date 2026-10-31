# Viva Coach

Prepare for a PhD viva or thesis defence. Answer aloud, get the timing right, and let spaced practice bring back what is fading.

* **Today:** days to go, questions waiting, overall readiness and your history of practice and rehearsal.
* **Practice:** spaced repetition with the SM-2 algorithm. Each question stays hidden until you have answered it aloud. Set a viva date and
  intervals are kept short enough that everything comes back before the day.
* **Mock viva:** timed questions drawn from every chapter, weakest first, in the order a viva usually runs. Weak answers return to practice.
* **Question bank:** 45 standard viva questions with advice, plus your own, each with answer notes that report their speaking time and
  flag hedging phrases.
* **Readiness:** by chapter and by kind of question, so you can see what to do next.
* **Slides and Talk rehearsal:** share a talk's length across its slides, time each slide as you speak, and see where you run over.
* **Examiners:** notes on your examiners' work, and on what they may ask.

`--demo` opens a temporary database with a fictional thesis. All data stays on your computer.

## From source

```bash
python -m viva_coach
python -m unittest discover -s tests -t .
python build_exe.py
```

## Limits

Readiness is a rough guide built from review intervals and written notes, and it does not predict how a viva will go. Practice ratings
are your own judgement, so they are only as honest as you are. The standard questions are general: your supervisor and your examiners'
own work are better guides to what will be asked in your field. Nothing here listens to you, so time aloud with a friend as well.

## License

MIT
