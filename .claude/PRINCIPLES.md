# What Decides a Close Call

The goals the user judges the work by, gathered from how they've answered, so that a choice the rules don't settle is made
the way the user would make it. `CLAUDE.md` imports this file, so it's in force in every session. `docs/WHY_LLAMATRON.md`
says what llamatron is for; this file says how the user weighs one way of building it against another.

- **Someone who never reads the manual still gets around.** Buttons and on-screen choices win over remembered keys; every key
  is shown where it works, on the legend, a button's face or the F1 menu; a field shows what kind of field it is (`▾` for a
  list) and what value it really has (`A Minor (from scene)`). The least surprising behaviour wins, judged musically and
  against the apps people already know, such as Esc closing the topmost thing.
- **Consistency wins over novelty.** One key means one thing across the tracker, one way of moving, choosing and confirming
  works everywhere, and a new thing looks like the existing thing it's most like. Where a feature already does what's asked,
  that's said first.
- **What people see is current.** Every visible change carries its docs, its screenshots and the website, published; GitHub's
  front page should never look stale, so `main` is pushed when the user agrees.
- **Demos are music first.** They're starting points people enjoy and learn from, each a plain workout of its feature or a
  piece that sounds good; one is rewritten only with the user's say-so, asked upfront, and new demo ideas wait at the bottom of
  the queue.
- **Bugs are understood.** A bug the user finds is reproduced, fixed at its cause, explained, and held by a test.
- **Progress with every reply.** Agreed work is built before the next questions are asked; each question offers lettered
  choices with Claude's recommendation; the queue (`dev_notes/QUEUE.md`) says what's next.
