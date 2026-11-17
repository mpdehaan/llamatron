# Jam Music

Songs that open into improvising and come back. (practice, from writing on how these bands improvise)

- **Three kinds of improvising**: one soloist over the band holding the song's chords and groove; the whole band improvising
  together, nobody in front, each part reacting to the others; and a jam that leaves the song's key, groove and tempo and
  becomes something else, perhaps arriving at another song.
- **Modal vamps**: the jam sits on one chord or two alternating chords a step apart, so that scale and mood matter and
  progression does not. Chords are loose; the bass and the drums are free to move.
- **Segues**: one song runs into the next without stopping, by a shared chord, a groove that changes slowly, or a breakdown to
  near silence. A set is a suite.
- **Shape of a jam**: start from the song's last chord and groove, thin out, find a new idea, build it over several minutes to
  a peak, with the whole band rising together, then fall back and return to the song's theme.
- **Bands of the southern kind** add twin lead guitars in harmony and two drummers; the heavy kind is a blues-rock trio with
  funk, soul, jazz and reggae feels by turns; the funk kind locks to one groove for many minutes with small changes.
- For a wizard: a "jam" section is a vamp of one or two chords, long, with an Intensity that rises across it, the lead role
  passing between players, and an optional segue into the next section.

## The Composed-and-Improvised Quartet

A four-piece (guitar, keyboards, bass, drums) whose songs pair written-out passages with open improvising. (practice)

- **Two kinds of jam.** Inside the song: the band keeps the song's chords, key and groove and builds from quiet to a peak, the
  guitar leading. Outside the song: the band leaves the chords, key, meter or feel behind and finds a new groove together, which
  may become a second and third jam before a return or a move into another song. Length does not tell which kind a jam is.
- **Shape of a jam inside the song**: settle on one or two chords; drop the volume and thin out; trade small ideas; a slow climb
  in register, density and loudness over many phrases; a sustained peak, often one long held or trilled note over the band's
  full chords; then the written ending or the song's last chorus. Tension and release on a long scale.
- **Shape of a jam outside the song**: someone offers a new idea (a bass figure, a keyboard change of sound, a drum pattern); the
  others drop what they were playing and join it; the key moves, most often up a fourth to IV, or to the relative major or minor;
  the feel changes (rock to funk, to ambient, to a major-key "bliss" section); meter may shift or bars be added while tension
  builds. Leadership passes among all four players.
- **Modes**: a minor jam is nearly always Dorian; a major jam is Mixolydian or Lydian; Phrygian is rare. Jams move between modes
  that share the same notes by changing which note the bass treats as home, so a key change needs no new notes.
- **Roles**: the guitar is the main voice, sustaining tone, with loops and long delays for texture; the keyboard player changes
  instrument to change the jam's color (piano for bright rock, organ for swells, a funk keyboard for clipped rhythm, electric piano
  for mellow passages, synthesizer for space); the bass plays counter-melodies and rhythmic counterpoint around the guitar and often
  starts a change; the drums follow the smallest shift at once and mark each new section.
- **Sparse funk**: a later style where all four play short clipped parts with rests between them, nobody soloing, the groove made
  of the gaps; the guitar plays muted scratches and wah figures, the keys a funk keyboard, the bass the hook.
- **Composed songs**: long multi-part pieces with written counterpoint between guitar and keys, fugue-like entries, odd and
  changing meters, sudden stops, unison runs, and sections that never return, ending in one chord progression held for the jam.
  The written part earns the release of the improvised part.
- **Listening as a practice**: each player repeats and varies what a neighbor just played until all four have locked into one
  idea, then one player changes it and the round begins again. Imitation first, then answer, then lead.
- Measured for the style's tag in the chord dataset: major keys (minor in one song in five), I IV, IV I and IV I V I, bVII in
  three songs in ten, vi in four in ten, a solo labeled in a sixth (the jams are not written down).

## A Song Is a Plan, a Jam Is Players Listening

A note Claude wrote in another conversation, kept nearly whole, names and all.
(practice throughout)

A composed song is modeled from the top down, with every player reading a shared plan. A jam is modeled from the bottom up, with
every player listening to the others and no one knowing what comes next.

### Playing a Song: A Shared Plan

The standard model is a hierarchy:

- **Form**: the sections, their lengths and an energy level for each.
- **Harmony**: a chord chart per section.
- **Roles**: drums keep time and signpost the form, bass ties harmony to the kick, keys and guitar split the midrange, and the
  lead carries the melody.
- **Realization**: each role turns "chorus, G major, energy 8" into actual notes.
- **Performance**: microtiming, dynamics and articulation.

What makes it sound like a band is coupling between the parts:

- **Rhythmic lock**: the bass agrees with the kick.
- **Register allocation**: parts do not crowd the same octave.
- **A density budget**: when the vocal is busy, everyone else thins out, and when it rests, someone fills.

Because the plan is known, every player has lookahead. The drummer's fill is scheduled because the chorus is two bars away.
Rule-based tools like Band-in-a-Box work this way explicitly. Neural multitrack models such as MuseGAN learn the same coordination implicitly from
data, by modeling all the tracks jointly.

### Jamming: Agents That Listen

In a jam the plan is gone, so the model becomes a set of agents, each with three parts:

- **Listening**: it tracks what the others are doing, including density, register, loudness, rhythm and implied harmony.
- **A stance**: it supports, complements, contrasts, leads or lays out. Knowing when not to play is a decision the model must be
  able to make.
- **Memory**: motifs go into a shared pool, so one player can quote what another played eight bars ago.

Four things change in kind:

- The model is causal. It can only use the past, so there is no lookahead.
- Transitions are negotiated. A player proposes a change by repeating a new riff or raising the intensity, and the others join or
  ignore it. A fill becomes a proposal instead of an announcement, like a lead drummer's set call (`RHYTHM_AND_GROOVE.md`).
- Leadership rotates. The rhythm section follows the soloist's arc, then someone else takes over.
- Form emerges. The build, peak and release come from feedback between the players.

Timing changes too. In a real band, the tempo is a mutual adjustment, with each player correcting slightly toward the others.
Researchers model this as coupled oscillators.

Real systems worth knowing: George Lewis's Voyager listens to a human improviser and decides whether to follow or go its own
way; François Pachet's Continuator answers a player's phrases in the player's own style using Markov models; IRCAM's OMax does
something similar from a live memory of the performance; Al Biles's GenJam trades fours.

### Most Music Sits in Between

Pure plan and pure freedom are the two ends. Most improvised music fixes something, which the theorist Jeff Pressing called the referent:

| Music | What is fixed | What is free |
| --- | --- | --- |
| A jazz standard | The form and chords, cycling | The notes |
| A modal vamp | A groove and a mode | Length and direction |
| Terry Riley's In C | 53 phrases, in order | When each player moves on |
| Free improvisation | Nothing | Everything |

A good jam model picks a referent and lets the agents negotiate the rest.
