# Musician

A pattern says which notes a track plays. A band does more with those notes than play them. A rhythm guitarist who hears the singer start a line plays softer, a lead guitarist waits for the singer to breathe before playing a lick, an organist holds a chord where a pianist strikes the chord and lets go, and the whole band plays a verse more gently than the chorus that follows. A song whose every track plays its pattern in full, all the time, sounds crowded and flat, however good the patterns are.

A Musician is one player of the band. The Musician is given a clip's notes and plays them as a player of its instrument would: differently in each kind of section, with room left for the tune, and with a touch of the player's own. Every note heard is a note the pattern wrote, which the Musician may move to the chord, leave out, hold, cut short, strike again or play louder or softer. The Musician writes no new part.

A musician reaches for a Musician when a song's tracks are right and the song still does not sound like a band. Make one Musician for each track, and add each to a chain on that track's clips.

## Instrument

Instrument says who is playing, and with that what the player does unasked. The backing players, "rhythm guitarist", "backing piano", "backing organ", "backing synth", "backup singers", "horn section" and "string section", play softer while the tune sounds. The lead players, "lead guitarist", "lead organ", "lead piano", "lead synth" and "answering player", play only where the tune rests. The "bassist" gives way to nobody. An organ, a synth pad, singers and strings hold each note until the next, and a horn section plays short stabs. The "drummer" and the "percussionist" play drums, whose notes no chord moves.

Each instrument also has a lowest and a highest note, which Range respects.

## Chords From and Tune From

Chords from names the track whose chords the Musician follows, in the same scene, exactly as [Follow Chords](FOLLOW_CHORDS.md) does: the part is written once over chord I, and the Musician moves the notes to whatever chord that track plays. A Musician with a track in Chords from needs no Follow Chords in its chain.

Tune from names the track that carries the tune. The Musician listens to that track and makes room, as Gives way says.

## Touch

Activity says how much of the part the player plays. With "light" the player keeps the notes that start on a beat and every note a beat long or longer, and with "sparse" the notes on the first and third beats. With "busy" each note a quarter note or longer is struck twice, and with "busiest" each note an eighth note or longer.

Loudness moves every note louder or softer, from -3 to 3. Looseness, from 0 to 3, lets each note come out a little louder or softer than the last, as a hand does; 0 is a player who never wavers.

Gives way says what the player does while the tune sounds: "not at all"; "a little", softer; "a lot", softer still and only the notes on the beats; or "plays in the gaps", silent until the tune rests.

Accents says which notes of the bar the player leans on: "downbeat", the first note of each bar; "backbeat", beats two and four; or "offbeats", the notes between the beats.

Notes says how the notes are held: "as written", "held", each until the next note starts, or "short".

Range moves the part an octave down with "low" or up with "high", and then brings any note the instrument cannot play back inside the instrument.

## Kinds of Section

A scene can say what kind of section it is, on the Scene page: a verse, a chorus, a breakdown and so on. Under the Musician's settings is a heading for each kind of section the song has, such as "In a verse", and under each heading are two settings.

Plays says whether the player plays in that kind of section at all. A player who sits out the verses and comes in at the chorus is the oldest way a band makes a chorus feel bigger.

Played says how the part is played there:

| Played | What is heard |
| --- | --- |
| "whole" | The part as the touch settings leave it |
| "softer" | Every note softer |
| "thinned" | Only the notes that start on a beat |
| "head only" | The first bar of every two |
| "muted" | Every note very short and a little softer, as a guitarist's palm mute |
| "hits" | Only the first note of each bar, a quarter note long at most |

## Settings

| Setting | Choices | A new Musician starts with |
| --- | --- | --- |
| Name | `ENTER` renames it, and every chain using it follows. | |
| Instrument | The fifteen players named above | "rhythm guitarist" |
| Chords from | A track, or "(none)" | "(none)" |
| Tune from | A track, or "(none)" | "(none)" |
| Activity | "sparse", "light", "as written", "busy", "busiest" | "as written" |
| Loudness | -3 to 3 | 0 |
| Looseness | 0 to 3 | 0 |
| Gives way | "not at all", "a little", "a lot", "plays in the gaps" | What the instrument does |
| Accents | "none", "downbeat", "backbeat", "offbeats" | "none" |
| Notes | "as written", "held", "short" | What the instrument does |
| Range | "low", "as written", "high" | "as written" |
| Plays, under a kind of section | on or off | on |
| Played, under a kind of section | "whole", "softer", "thinned", "head only", "muted", "hits" | "whole" |

A drummer and a percussionist have no Chords from and no Range.

## Applying the Generator

`examples/learning/26_musician.yml` plays a band's patterns as written and then hands the same patterns to Musicians, through a verse, a chorus and a breakdown, so that what each setting does is heard against the scene before.
