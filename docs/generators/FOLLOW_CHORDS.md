# FollowChords

FollowChords moves a clip's notes to the chords another track plays, so that a song's chords are written once, in one place, and everything else follows them. Its Chords From names the track followed.

## Chords Track

Put the song's chords on a track of their own, called Chords here, and turn that track's Mute on in the track editor so that the chords are a guide and make no sound. In each scene, the Chords track's clip says what the chords are, in either of two ways. The chords can be written by hand, a step a chord, with the step's Degree as the chord's root and its Chord row as the chord. Or the pattern can hold one chord and a [Progression](PROGRESSION.md) in that clip's chain can make the progression from it. FollowChords reads the chords as they come out of the Chords track, after that track's own chain, so the two ways are followed alike.

## Following

Write a figure over chord I, a bar of bass, an arpeggio or a held chord, and add FollowChords to a chain on its clip. As each note starts, FollowChords finds the chord most lately started on the track followed, in the same scene, and moves the note up the clip's scale by as many notes as that chord's root is above the scale's root. The scale decides whether a chord is major or minor, as with a Progression: a figure written on A in A minor plays F, A and C over a chord on F. Where the track followed plays a chord from outside the scale, such as E major in A minor, a note of the figure that is a third, a fifth or a seventh above the figure's root takes the chord's own note, so the figure plays G sharp. Rests, rhythm, velocity and gates stay as written.

A chord goes on through the rests after it, until the next chord starts. Before the first chord of a scene, with no track chosen, or in a scene where the track followed has no clip, nothing moves. A drum pattern is left alone. Tracks cannot follow each other in a circle.

Change a chord on the Chords track and every clip that follows it changes with it.

## Settings

| Setting | What it does |
| --- | --- |
| Name | `ENTER` renames it, and every chain using it follows. |
| Chords from | The track whose chords are followed, a track of the current song. Renaming the track renames this too, and a track the song doesn't have moves nothing. |

## Applying the Generator

`examples/learning/24_follow_chords.yml` shows three tracks following one muted track, SILENT Chords, with the chords written by hand and then made by a Progression.
