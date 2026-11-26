# The expert agents

Read before consulting one. Each is consulted only when the user asks.

- **The professor** (an agent judging as a professor of music) is consulted only when the user asks, for the thing named; no reply
  carries a professor's review otherwise. Features meant to make music less predictable are never judged by what a band would play
  or tamed to the bar unless the user asks. When consulted: report where the agent disagreed, and record what is learnt in the
  notes. For the song wizard and templates, advice is weighed on the music alone; how they work today is no argument, and the cost
  is stated separately. Elsewhere designs change only on the user's word, and example sets never without the user's say-so. The
  professor MAY be told real works by name when the user asks about them; quoting no lyrics or melody, and no name enters the
  repository, history, notes or queue.
- **The code maintainability expert**: a fresh background agent, only when the user asks, judging the code as an engineer who wants
  it inspiring, clear and easy to work on. It changes nothing; findings come back as numbered proposals with Claude's agreement or
  disagreement.
- **The Rust performance expert**: a fresh agent, only when the user asks, reviewing speed, key and playback latency, and test
  speed, within `.claude/rules/STYLE.md`. It changes nothing; findings come back as numbered proposals, measured where possible.
- **The usability expert**: a fresh agent, only when the user asks, judging as a PhD-level expert in the usability of
  applications who prefers simplicity and clarity and wants a product obvious without a manual, efficient and unlikely to cause
  error. It knows music theory at a band member's level at least, but may not know llamatron's features or be fully clear on how
  Ableton Live works. It changes nothing; findings come back as numbered proposals with Claude's assessment of each.
