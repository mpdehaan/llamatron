# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""The help text for every page of the tracker, which the second panel of the F1 dialog shows.

Each constant is one page's help, written as plain lines: a line here is a line on the screen, which
the dialog wraps if the console is narrow, and a blank line is a blank line. The text is here, away
from the pages' code, so that it can be edited by hand without touching anything that runs. The
tests check that every page's help still fits an 80 by 24 console.
"""

# A line of help ends here, and an empty text means a page has no help.
HELP_LINE_BREAK = '\n'
# What a page without help of its own shows: nothing.
HELP_NONE = ''


def help_lines(text):
    """Return the lines of a help text, as the dialog shows them."""
    text = text.strip(HELP_LINE_BREAK)
    return text.split(HELP_LINE_BREAK) if text else []


# ArrangePage
HELP_ARRANGE_PAGE = """
Scenes are rows, tracks columns, a box marks the cursor. Bars: a scene against the longest, a clip against its scene.
On an empty cell, Enter chooses a pattern and adds a clip. On a clip, Enter edits it, P opens its pattern, C copies it, V pastes it, Bksp deletes it.
On a scene's row, I inserts a scene above, C copies it below; on a track name, I inserts one before, C copies it right. M picks up a scene, track or clip to carry with the arrows.
Enter on a scene or track name opens its settings, P on a scene's shows Scene View, Bksp deletes it, never the last. A adds a scene, or a track on the top row. ×3 repeats, ∞ loops, ~ morphs, d own direction, g grabs. D shows or hides details; Tab opens a cell's, ↑↓ pick, Enter opens, Tab leaves.

With Real Time on, Space plays what the cursor is on, the song from the corner, a scene or one clip, and stops it. Z shows the visualizer.
"""

# ScenePage
HELP_SCENE_PAGE = """
A scene starts all of its clips together, and lasts as long as its longest clip that does not loop.
Scale: used by its clips, instead of the song's. Tempo: instead of the song's.
Groove: for its clips, instead of the song's. off plays them straight whatever the song or a track chooses.
Tempo ramps to: moves from Tempo to this across the scene's repeats.
Repeat: plays the whole scene that many times.
Reset AX to DX: sets that register back to its default as the scene starts, but not on its repeats.
Launch together: in real-time playback only, a start reaching any clip of the scene launches them all. Off, each clip waits for the clip above it to send one, and Arrange marks the scene.

Up and down select a setting. Left and right change it, and Enter types or chooses. Bksp goes back to the song's value.
"""

# ClipPage
HELP_CLIP_PAGE = """
Name: what the grid and the exports call it, or its pattern's name if it has none. Pattern: what it plays. Chain: generators to run on it.
Repeat: how many times it plays, then silence while other clips finish. Loop: plays until the other clips are done. One clip in each scene must not loop, or exporting stops.
Direction: overrides its pattern's play direction. With Repeat above 1, Morph to chooses a second pattern to change into across the repeats, and Morph direction is where the change starts.
Grab track: Grab steps play the note that track last started, with their chord.
Advance: real-time playback only, never an export. With Scene starts the clip below when the whole scene is done, Next when this clip ends, Off never. Blank, it shows the Set File page's default.

Up and down select. Left and right change. Enter chooses. P opens the pattern in its editor. L plays the clip as its scene would, again and again, and stops it; Play and Stop below do the same.
"""

# MainPage
HELP_MAIN_PAGE = """
This is the way into every page. Press a letter to open one, or move the box with the arrows and press Enter.
The number in a cell says how many of its things the set has: songs, patterns, chains, generators, scales and grooves of its own.

A file is a set of songs. Patterns, scales, generators, chains and grooves belong to the set, and every song shares them. Each song has its own tracks, registers and scenes, and one song is current: Songs picks it, and Registers and Arrange work on it.

Ctrl+S saves, Ctrl+O opens a file, Ctrl+X exports the current song, Ctrl+Z undoes the last change and Ctrl+Y redoes it, F1 lists every key and F3 is about llamatron, on every page. Here O opens and X exports too, and Q quits, from this screen only, asking first only when there are unsaved changes. Esc goes back, and cancels a dialog.
Nothing is saved or exported until you ask.
"""

# FilePage
HELP_FILE_PAGE = """
The set's own settings, and its file. Up and down select one. Left and right change it, and Enter types or chooses.
Title, Author, Description and Notes: only for people reading or sharing the file. Description is one line saying what the
set is; Bksp clears the first three. Enter on Notes opens them for editing, as long as you like; Tab reaches Save and Cancel. Step size: how long each step of a pattern is, unless the pattern sets its own. Default octaves: what a new note or drum hit gets.
Octave labels: as Live numbers octaves on screen (middle C is C3) or from 0 (middle C is C5).
Default follow action: a clip's Advance unless it sets its own.
Visualizer: Arrange shows it first. Hide Visualizers: not shown.
Protected: the file is never saved over, like the demos; Ctrl+S offers to save a copy instead.
N starts a new set, and W saves under a new name. The Save and Open buttons do what Ctrl+S and Ctrl+O do.
Ctrl+X exports the current song beside the set's file as <set>_<song> files, asking before it replaces a Live set.
"""

# SongsPage
HELP_SONGS_PAGE = """
The songs in the set, like the songs of one concert. Each has its own tempo, scale, seed, tracks, registers and scenes, and they all share the set's patterns, scales, generators and chains.

The marked song is current: Tracks, Registers and Arrange edit it, and Ctrl+X exports it, beside the set's file as <set>_<song>. Space makes the selected song current, and Enter does too, then opens its settings.

A adds one, C copies it, N renames it, M moves it, and S sorts them by name. Bksp deletes it, but the set keeps at least one song.
/ searches the list as you type: Tab completes, Enter keeps your place, Esc goes back to the whole list.
"""

# SongPage
HELP_SONG_PAGE = """
One song's settings. Up and down select one. Left and right change it, and Enter types or chooses.

Name: Enter renames the song, which N on the Songs page does too.
Tempo: in quarter notes a minute, unless a scene sets its own. Time signature: only changes what's drawn, the beats in the pattern editor and the bars in Live.
Scale: the set's scale its degrees play in, unless a scene sets its own; Bksp leaves it with none.
Seed: with none, every export is a new take. Set one to export the same take every time.
Groove: the swing or other timing feel every clip plays with, unless its scene or track chooses another. none is straight.
Live response: when an edit made while the song plays is heard: at the next bar, at each clip's next pass, or ASAP.
Visualizer: Arrange shows it first, over the Set File page's.
The Export row does the same as Ctrl+X, which works on every page: it writes this song as a Live set or MIDI files.
"""

# NotesPage
HELP_NOTES_PAGE = """
Notes about the set, for anyone reading or sharing its file. They don't change how it plays.

It opens editing from the Set File page. Typing adds text where the cursor is, Enter starts a new
line, Bksp erases, and the arrows move the cursor. Tab reaches the Save and Cancel buttons under
the text, and Tab again comes back; Esc cancels, throwing the typing away. While reading, up and
down scroll, E starts editing again, Bksp clears it all, after asking, and Esc goes back.
A protected set's notes can only be read, so they open reading, with no E or Bksp.
"""

# OpenPage
HELP_OPEN_PAGE = """
Choose a set file. Enter opens a file, or goes into a folder. ../ goes up a folder.
/ searches the list as you type: Tab completes, Enter keeps your place, Esc goes back to the whole list.
"""

# PatternsPage
HELP_PATTERNS_PAGE = """
Every pattern in the set, which all of its songs share. Enter edits the selected one.

A adds one, C copies it, N renames it, and renames update every clip.
M moves it, and S sorts them by name.
Bksp deletes it, but only once nothing uses it.

TIME is one play at the current song's tempo. USED counts the clips, in every song, and chains that use it.
/ searches the list as you type: Tab completes, Enter keeps your place, Esc goes back to the whole list.
"""

# TrackEditor
HELP_TRACK_EDITOR = """
Name: Enter renames the track, which updates every scene.
Drum: a drum track is never transposed. Drum patterns never are either, on any track.
Mute: the track starts switched off in Live. Its clips are still written, and other tracks can still grab from it.
Groove: for its clips, instead of the scene's or the song's. off plays them straight whatever the scene or song chooses.
Transpose: moves every note on the track along the scale when exporting, without changing its patterns.
Lowest and Highest octave: the octaves its instrument plays, the whole MIDI range to start, which the piano roll marks.
CC 1 to CC 4: the CC number that each of a pattern's CC rows sends on this track. A row with no number sends nothing here.
Instrument: where the track plays in real time, one of the Instruments page's, or none to leave it out.

Up and down select a setting. Left and right change it, Enter types, and Space or Enter toggles. Bksp clears.
"""

# OffsetsEditor
HELP_OFFSETS_EDITOR = """
The arpeggiator plays one note of the chord each step, moved this many notes along the scale.
A blank step is silent, and the next step plays the note it would have played.
The steps start again with each chord, so a length that doesn't match the chord makes a new rhythm.

Each offset is a bar from the zero line, up or down, with its number beneath: one the gauge can't reach fills its column and is marked, like +7▲.
Digits type an offset, Up and Down change it, and Space or Enter makes the step silent or plays it again.
I inserts a step, D removes one, and there can be 1 to 16.
"""

# ScalesPage
HELP_SCALES_PAGE = """
Named scales for the set's songs and their scenes to choose from. A clip uses its scene's scale, or else its song's.

A name can be anything, like main, so you can change what main is later, and everything using it follows.

A adds a C major scale and opens it. Enter opens one: its name, root and kind are on its page. N renames it, and C copies it.
M moves it, and S sorts them by name. Bksp deletes it, but only once nothing uses it.
To delete a song's scale, clear it on that song's page first.

Patterns that use degrees need a scale to export.
/ searches the list as you type: Tab completes, Enter keeps your place, Esc goes back to the whole list.
"""

# ScalePage
HELP_SCALE_PAGE = """
Name: Enter renames the scale, and every song and scene using it follows.
Root: the note the scale starts on. Left and right step through the roots, and Enter picks one on a keyboard.
Kind: major, minor, a mode or a world scale. Left and right step through them, and Enter picks from two pages.

A scale still named after its root and kind, like C Major, is renamed as they change, so the name keeps saying what it is. A name of your own, like main, stays.
The notes the root and kind make are shown underneath, and how many songs and scenes use the scale, then a keyboard with the scale's keys filled and the root bracketed.
"""

# ChainsPage
HELP_CHAINS_PAGE = """
A chain is a list of generators that run on a clip when exporting. A clip chooses one chain on its own page.

Enter edits the selected chain. A adds one, C copies it, N renames it, M moves it, and S sorts them by name.
Bksp deletes it, but only once no clip uses it.
/ searches the list as you type: Tab completes, Enter keeps your place, Esc goes back to the whole list.
"""

# ChainEditor
HELP_CHAIN_EDITOR = """
The steps run from top to bottom, each working on what the last one made.

A adds an arpeggiator or AutoRatchet, which you make on the Generators page. Enter changes one, C copies it, and Bksp removes it. M picks up a step, Up and Down carry it, and Enter drops it.
N renames the chain, and every clip using it follows.
/ searches the list as you type: Tab completes, Enter keeps your place, Esc goes back to the whole list.
"""

# GeneratorsPage
HELP_GENERATORS_PAGE = """
Every generator of the set, of every kind, its kind beside its name. Chains run them on clips, scenes and tracks, in the order each chain lists them.

Enter edits the selected one. A adds one, asking which kind, and opens it. N renames it, C copies it, M moves it up or down the list, and Bksp deletes it once nothing uses it.
/ searches the list as you type: Tab completes, Enter keeps your place, Esc goes back to the whole list.
"""

# ChainListPage
HELP_CHAIN_LIST_PAGE = """
The chains this clip, scene or track runs, in the order they run.

A clip runs its own chains first, then its scene's, then its track's. A chain listed in two places runs twice.

A adds a chain, picked from the set's. M picks one up to carry with Up and Down, Enter dropping it, and Bksp takes it out of the list. Esc goes back.
"""

# ProgressionEditor
HELP_PROGRESSION_EDITOR = """
Every: how long each chord lasts, a bar unless set, counted from the clip's start. The progression loops while the clip plays.
Chords: Enter opens the chord editor. A new progression has one chord, on the first degree, which changes nothing.
"""

# ChordsEditor
HELP_CHORDS_EDITOR = """
Each column is a chord: its bar rises to its degree, with its numeral and its name in the song's scale beneath.
A plain degree moves the clip along the scale, so the scale decides major or minor. A sharp or flat moves it by exact half steps, keeping its sound.
Up and Down move between the Chord, #/b, Scale, Quality, Tens. and Inv. rows. [ and ] change the value, digits type a degree, Space or Enter cycles #/b and Inv.
Scale borrows the chord from another scale type on the same root, Quality names the chord outright, and Tens. adds notes on top: Enter on those rows opens the Chord dialog.
I inserts a chord and D removes one. H fills the chords with a named progression, matched to the song's scale.
"""

# VoiceLeadingEditor
HELP_VOICE_LEADING_EDITOR = """
Lowest octave and Highest octave: the chords stay within them, so they don't drift up or down over a long piece.
Keep the root in the bass: the chord's lowest written note stays where it is and only the notes above it move, as when a bass track plays the roots.
"""

# HocketEditor
HELP_HOCKET_EDITOR = """
Source track: the track of the current song whose notes the hocketing tracks take turns at. Renaming that track renames
it here too. A track the song lacks hands out nothing.
Restart: every clip starts the turns again with the first track at each clip the source plays; on new scene and whole
song carry them on.
Each track still plays its own pattern's notes besides those it is handed.
"""

# StrumEditor
HELP_STRUM_EDITOR = """
Direction: by the beat strums down on the beats and up between them; down is low to high, up high to low; down up alternates; off strums nothing.
Spread: how far apart the strings sound, in milliseconds whatever the tempo, from tight to a harp's roll.
Fade: how much quieter the last string is. Loose timing: how much each gap varies. Upstroke strings: what an upstroke catches.
"""

# EuclidEditor
HELP_EUCLID_EDITOR = """
Hits over Steps make the rhythm, drawn under the fields. Rotate moves it later by that many steps.
Step: how long each step is, the clip's pattern's step size unless set.
H on Hits picks a named rhythm, like the tresillo, three hits over eight steps.
"""

# GlideEditor
HELP_GLIDE_EDITOR = """
Step: how long each step of the row is, the pattern's step size unless set.
Glide amount: how far a gliding note runs into the next.
Steps: Enter opens the row of steps, each on or off.
"""

# ShortenEditor
HELP_SHORTEN_EDITOR = """
Step: how long each step of the row is, the pattern's step size unless set.
Shorten amount: how much of itself a shortened note plays.
Steps: Enter opens the row of steps, each on or off.
"""

# RushEditor
HELP_RUSH_EDITOR = """
Step: how long each step of the row is, the pattern's step size unless set.
Rush amount: how far a note moves early, as a share of a step, up to half.
Steps: Enter opens the row of steps, each on or off.
"""

# DragEditor
HELP_DRAG_EDITOR = """
Step: how long each step of the row is, the pattern's step size unless set.
Drag amount: how far a note moves late, as a share of a step, up to half.
Steps: Enter opens the row of steps, each on or off.
"""

# StepRowEditor
HELP_STEP_ROW_EDITOR = """
A row of steps, each on or off, running from each clip's start at the generator's own step.
Left and Right move. Space or Enter turns the step under the cursor on or off, the line above saying what a step that's on does.
I inserts a step and D removes one, from 1 to 16.
"""

# DensityEditor
HELP_DENSITY_EDITOR = """
Start and end: the share of notes that play, from 0 to 100, ramping from one to the other. Blank plays as 100.
Over: how long one ramp lasts, the whole clip unless set. Then: after a ramp, hold stays at the end, repeat starts again, bounce ramps back.
"""

# SwellEditor
HELP_SWELL_EDITOR = """
Start and end: each note's velocity as a percentage, from 0 to 200, ramping from one to the other. Blank plays as 100.
Over: how long one ramp lasts, the whole clip unless set. Then: after a ramp, hold stays at the end, repeat starts again, bounce ramps back.
Accent: how much louder the beats are, up to 50 percent.
"""

# ArticulateEditor
HELP_ARTICULATE_EDITOR = """
Start and end: how long each note sounds, as a percentage of what's written, from 10 to 200, never past the next note. Blank plays as 100.
Over: how long one ramp lasts, the whole clip unless set. Then: after a ramp, hold stays at the end, repeat starts again, bounce ramps back.
"""

# DriftEditor
HELP_DRIFT_EDITOR = """
Every: how often it triggers and picks new amounts. Steps to the second version: how many triggers it takes.
Direction: forward stays at the second, loop starts again at the first, pendulum goes back and forth, brownian wanders.

Below, each setting has two versions side by side. Left and Right pick one, [ and ] change it, Enter types or picks, Bksp clears.
Vel+= and Prob are added to every note's; Degree + moves notes along the scale, and Degree random by a random amount.
Scale and Root take over the clip's scale with their prob. AX+= to DX+= add to the registers at each trigger.
"""

# AutoRatchetEditor
HELP_AUTO_RATCHET_EDITOR = """
Name: Enter renames it, and every chain using it follows.
Counts: how many equal repeats to chop each note or chord into, using the next number each time and starting again at the end.

Press Enter and type whole numbers with spaces between them, like 1 1 4.
"""

# ArpEditor
HELP_ARP_EDITOR = """
Name: Enter renames it, and every chain using it follows.
Step: how long each note of the chord plays.
Order: which way it goes through the chord. Random uses the seed.
Octave range: plays the chord again in up to 4 octaves. Octave jump: up after the whole chord, or after each note.
Offsets: the arp's own steps, like the Monomachine's. Each moves its note along the scale, and a blank step is silent. Bksp removes them.
Seed: leave it to use the song seed, or set one for just this arpeggiator.

Up and down select a setting. Left and right change it, and Enter types or chooses.
"""

# PatternEditor
HELP_PATTERN_EDITOR = """
Each column is a step, as long as the step size. Tab switches between the piano roll and the rows. Home/End jump to the ends.
Piano roll: Space or Enter draws a note of the entry size, which E picks; [ and ] drag its end, K splits it, . sharpens or flattens it, G grabs, Space, Enter or Bksp erases it, H picks its chord.
Rows: Degree is a gauge: digits set it, [ and ] nudge it, as they adjust every number, Bksp empties the step. The rows under Octave come in sections headed by a row marked + (closed) or - (open): Space or Enter opens or closes it, PgUp/PgDn jump between them.
Basics: #/b, Velocity. Chord: Chord, Scale, Tension (Enter picks), Inv. Timing: Tie (Space on empty steps after a note holds it), Gate ([ and ], or Enter to type one), Dot (d, t), Glide. Advanced: Probability, Ratchet, Ratchet Offset, Grab. CCs and Slide work on rests too. Reg. Apply uses the registers; Reg. Mod adds to them.
S sizes the pattern, and on the rows I inserts a step and D removes one. R reconfigures it: munge, load over, step size, time signature, drum on or off, direction, rename. L plays it through a track, and stops it.
"""

# RegistersPage
HELP_REGISTERS_PAGE = """
The four registers, AX to DX, are numbers the whole current song shares. Pattern steps change them with AX+= and use them with AX+Note and AX+Vel, on the pattern editor's register rows.

Each starts at its default when the song starts, and again whenever a scene resets it. Adding never takes one past its minimum or maximum: it stops there, or, if it wraps, jumps to the other end.

Up and down select. Left and right change a number, Enter types one, and Bksp goes back to its default. Enter switches wraps on and off.
"""

# GroovesPage
HELP_GROOVES_PAGE = """
A groove moves notes off the grid, like swing on a drum machine. It's a row of cells, one bar of 16ths to start with, each
saying how late (+) or early (-) a note in that cell plays, as a percentage of the cell. Grooves follow time, not steps.

The song chooses a groove, none by default, and a scene or a track can choose another, or off to play straight.
The track's choice wins, then the scene's, then the song's, but off anywhere plays straight.

The factory grooves are always there: four swings on 16ths, two on 8ths and a push. Enter looks at one and C copies it,
but they can't be changed, renamed or deleted. A adds a straight groove of your own and opens it. On your own grooves,
Enter edits, N renames, C copies, M moves, S sorts yours by name, and Bksp deletes one that nothing uses.
/ searches the list as you type: Tab completes, Enter keeps your place, Esc goes back to the whole list.
"""

# InstrumentsPage
HELP_INSTRUMENTS_PAGE = """
An instrument is a MIDI device of this computer and a channel on it, 1 to 16, for playing in real time as you work.
Each track chooses one on its track editor, or none, and a track with none is left out of real-time playback.
Two instruments may share a device and a channel. No export reads them: a Live set has its own instruments.

Adding the first instrument turns the main screen's Real Time switch on, and deleting the last turns it off.

A adds one and opens it. Enter edits, N renames, C copies, M moves, S sorts them by name, and Bksp deletes one
that no track uses.
/ searches the list as you type: Tab completes, Enter keeps your place, Esc goes back to the whole list.
"""

# InstrumentEditor
HELP_INSTRUMENT_EDITOR = """
Name: Enter renames the instrument, and every track that chose it follows.
Device: the MIDI output port, chosen from the ports this computer has now, or *FluidSynth, the software
synthesizer the tracker starts itself. (none) until one is chosen, and a track on an instrument with no device
cannot play. A port that has gone is still shown, so that the set opens without it.
Channel: 1 to 16, as the device numbers them, or (auto) with FluidSynth, which gives each track its own.
GM sound: one of General MIDI's 128 sounds, which the MIDI (General MIDI) export gives this instrument's tracks and
FluidSynth plays. Enter chooses it from the families, two to a page, which the picker turns.

Up and down select a setting. Left and right change it, and Enter types or chooses. Bksp clears the device or sound.
"""

# GrooveEditor
HELP_GROOVE_EDITOR = """
One groove's cells. Left and right move along them. Digits type an amount, Up and Down change it by one,
and a minus sign is kept while you type. I inserts a straight cell, D removes one, and there can be 1 to 32.
S changes how long a cell is: a 32nd, 16th, 8th or quarter note. N renames the groove, and every song, scene and track
that chose it follows.
A groove with more cells than fit across the screen scrolls sideways as you move.

A factory groove can only be looked at: copy it on the Grooves page to get one you can edit.
"""
