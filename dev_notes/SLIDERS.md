# Sliders for Generating and Improving Songs

A design to mark up (110 C), not built. The user's model: a genre is a network of traits, each with parameters of many kinds,
some working together and some not; making, adjusting or improving a song is a balancing operation in the spirit of minimax,
not a maximization; the person sets sliders for what to spend the song's "fit" on, as an image generator has a slider for how
closely to follow the prompt, with no AI model inside. Each slider here says what it moves, what the library measures it by
today (so that improving a song can report where the song stands on it), and its range. Claude's proposals are marked
**Proposal**; anything can be struck out or changed.

## How the Sliders Work Together

A song, or a candidate change to one, is scored on several goals at once, each goal a measure the library can take (fit to a
style, an emotional target, surprise against the inverted U, virtuosity and so on). Each slider sets how much its goal counts,
or a target it aims at. Hard limits are kept apart from goals: the coupling rules (`rules.py`), the person's locks (keep the
melody, keep the drums), the change budget, and an originality floor that no homage may pass.

Ways of balancing the goals (**Proposal: offer all four, default to candidates**):

1. **Weighted sum.** Each goal times its slider, added up. Simple, predictable; a strong goal can drown the rest.
2. **Maximin.** Raise the weakest goal first, then the next: the closest to the user's minimax. No goal is sacrificed, but a
   song may end up merely good at everything.
3. **Priority order.** Goals in an order the person sets; a later goal only breaks ties left by an earlier one. Good for
   "fit the style first, then make it emotional".
4. **Candidates along a frontier.** Several results, each trading the goals off differently (more emotional but less
   faithful, more virtuosic but less singable), shown side by side for the person to pick, as an image generator shows four
   images. Best for exploring; costs more time to make.

## A. Adherence: How Closely to Follow What Was Asked

| Slider | What it moves | Measured today by | Range |
| --- | --- | --- | --- |
| Style fit | how tightly the song stays inside the style's region, the prompt-strength slider | `fit` and the tightness of `field_gap` | loose (the style's spirit) to strict (its typical values) |
| Recognizability | how far the song stands from neighbouring styles | `recognizability` | blends in to unmistakable |
| Source likeness | how close a homage stays to its source | `source_fit` | distant cousin to "another day" |
| Originality floor | how close a homage may never come: no melody, figure or progression copied | not yet: a melodic and rhythmic similarity check is needed | a hard limit, not a goal |
| Rule strictness | how far the coupling rules and the style's norms may bend, which is also the budget for breaking them | `broken_rules`, counted | textbook to anything goes |
| Tradition blend | how much of a tradition (Irish, klezmer, maqam, West African) is blended in | not yet: traditions as blendable traits (107 B, not chosen yet) | 0% to 100% per tradition |

## B. The Listener's Experience

| Slider | What it moves | Measured today by | Range |
| --- | --- | --- | --- |
| Emotional intensity | how strongly the song pushes its emotion | energy contrast, tension depth, the cue model's strength (`emotion.py`) | gentle to overwhelming |
| Emotional target | what emotion, as a point or as a path over the song: valence and arousal, or the nine music emotions (wonder, transcendence, tenderness, nostalgia, peacefulness, power, joyful activation, tension, sadness) | the cues for perceived emotion (`CUE_DIRECTIONS`) | a point, or a path drawn over time |
| Familiar to surprising | where the song sits on the inverted U | expectation surprise, uncertainty and familiarity | comfortable to adventurous |
| Surprise placement | where violations land: spread out, early, late, or where the listener is most sure (Cheung) | surprise against uncertainty, step by step on the path | a choice |
| Tension depth | how far the tension curve rises and falls | energy contrast; Farbood's surface features (to build) | flat to dramatic |
| Groove | syncopation towards the pleasurable middle (Witek), ghost notes, swing | groove swing and ghosts; syncopation (to build) | stiff to deep pocket |
| Singability | how easily a person could sing the lead | vocal singable, range, steps | instrumental to singalong |
| Hook strength | how strong, how often and where the hook returns | hook strength, hummable, placement | subtle to relentless |
| Repetition | how much material returns (Margulis) | melody repetition, expectation familiarity | through-composed to mantra |

## C. Craft

| Slider | What it moves | Measured today by | Range |
| --- | --- | --- | --- |
| Virtuosity | density, range, rhythmic variety, technique devices | melody density and range, phrasing rhythmic variety, devices | plain to dazzling |
| Complexity, per dimension | harmony, rhythm, melody, form and texture each on its own slider, so simple and complex are never blended into the middle (the user's rule) | harmonic rhythm and qualities; meter changes and syncopation; melody steps and range; form sections; texture parts | simple to complex, five sliders |
| Interplay | call and response, comping, trading, laying out | texture call-and-response; the interplay devices | one voice to a conversation |
| Voice independence | how independently the parts move | voice leading independence, contrary motion | parallel to contrapuntal |
| Space | how much room the arrangement leaves | texture density, phrasing space | dense to sparse |
| Polish to rawness | precise and smooth against loose and rough (Steely Dan against the White Stripes) | phrasing looseness, velocity spread, sounds | raw to immaculate |
| Human feel | timing and velocity looseness, push and drag | groove push, phrasing looseness | machine to human |

## D. Structure and Size

| Slider | What it moves | Measured today by | Range |
| --- | --- | --- | --- |
| Length | the song's length in minutes or bars | the render's length | a target |
| Patterns, per instrument or voice | how many patterns each part gets | the set's patterns | a count each |
| Scenes | how many scenes | the set's scenes | a count |
| Epic to distilled | the same flavour with many transitions and details, or few (the user's rule: both) | path steps, transitions, devices | distilled to epic |
| Transition smoothness | how prepared each change of scene is | transitions' abruptness and preparation | sawtooth to seamless |
| Arc shape | the energy path over the song | the path's energy curve and its shape | a shape chosen or drawn |
| Genres and proportions | several genres in one song and how much of each | paths aligned to several styles | a list with shares |
| Reprise | how often earlier material returns, varied in another style | path alignment with itself | none to rondo-like |
| Change budget (improving) | how much of an existing song may change, and what is locked | differences counted against the original | untouched to rewritten |

## Further Out

- **Listener expertise.** The more experienced the listener, the more complexity they accept (Berklee's reharmonization lesson);
  one slider that moves the complexity sliders' acceptable ranges together.
- **Era drift.** Move a song forward or back along the graph of styles: the same song as it might have sounded ten years
  earlier or later.
- **Weirdness.** Distance from every known style, a search for novelty in the graph's empty spaces.
- **Evolution rate.** For endless pieces: how fast the music changes and how long a motif lives before it is let go.
- **Randomness, with a seed.** How freely each choice is made within its region, reproducible by its seed.
- **Mood journey.** The emotional target as a path drawn over the song rather than a point, the path model applied to emotion.

## Presets (Proposal)

Named settings of all the sliders at once, as starting points:

- **Learn the form.** Distilled, strict style fit, simple on every dimension, high repetition, few patterns: easy to read and edit.
- **Finished epic.** Epic, seamless transitions, an arching arc, high interplay, tension deep.
- **Homage.** High source likeness under the originality floor, strict style fit.
- **Singalong.** High singability, strong hook, familiar side of the U, simple harmony, verse and chorus.
- **Adventurous.** Loose style fit, rule strictness low with surprises placed where the listener is sure, complexity high on one
  or two dimensions only.
- **Endless drift.** For hours of music: slow evolution, high repetition with gradual variation, low tension, ambient sounds.

## How It Might Look (Proposal)

On a generator's settings page, each slider a row with a horizontal bar, `[` and `]` stepping it, as every settings page does;
sections open and close as the accordion does:

```
  GENERATE SONG
  ────────────────────────────────────────────────────────────────────────────
    Name             new song
    Style            power pop ▾
    Balance          candidates (4) ▾

  - Adherence
    Style fit        ████████████░░░░░░░░  strict
    Recognizability  ██████████░░░░░░░░░░
    Rule strictness  ██████░░░░░░░░░░░░░░  bends where sure

  - Listener
    Emotion          joyful activation ▾
    Intensity        ██████████████░░░░░░
    Familiar ↔ new   ████████░░░░░░░░░░░░
    Singability      ████████████████░░░░

  + Craft (set)
  + Structure

    G generate   P preset   Esc back
```

## Questions for the User

- Which ways of balancing to offer, and which first.
- Which sliders matter most, and which to strike.
- Whether emotion is chosen as a point, a path, or both.
- Whether presets are wanted, and which.
- Where the sliders live: a generator's page in the tracker, the genre explorer app, or both.
