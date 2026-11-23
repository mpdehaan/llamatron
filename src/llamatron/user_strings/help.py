# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

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
On an empty cell, ENTER chooses a pattern and adds a clip. On a clip, ENTER edits it, J jumps to its pattern, C copies it, V pastes it, Bksp deletes it.
On a scene's row, I inserts a scene above, C copies it below; on a track name, I inserts one before, C copies it right. M picks up a scene, track or clip to carry with the arrows.
ENTER on a scene or track name opens its settings, P on a scene's shows Scene View, Bksp deletes it, never the last. A adds a scene, or a track on the top row. ×3 repeats, ∞ loops, ~ morphs, d own direction, g grabs. D shows or hides details; Tab opens a cell's, ↑↓ pick, ENTER opens, Tab leaves.

With Real Time on, Space plays what the cursor is on, the song from the corner, a scene or one clip, and stops it. Z shows the visualizer.
"""

# ScenePage
HELP_SCENE_PAGE = """
A scene starts all of its clips together, and lasts as long as its longest clip that does not loop.
Scale, Tempo, Groove: for its clips, instead of the song's; a Groove of off plays them straight. Repeat: plays it that many times.
Reset Draws: starts a draw over from its first slot as the scene starts, but not on its repeats.
Launch together: in real-time playback only, a start reaching any clip launches them all; off, each waits for the clip above.
Tab goes to the tabs, where Left and Right choose one. Tempo Ramps move the tempo over bars from its start and before its end.

Up, down, Left and Right select a setting. [ and ] change it, and ENTER types or chooses. Bksp takes the song's value.
"""

# ClipPage
HELP_CLIP_PAGE = """
Name: what the grid and exports call it, else its pattern's name. Patterns: what it plays; A adds, M moves, Bksp removes.
Tab goes to the tabs; Left and Right choose one. Settings: Repeat, Loop, the orders, Morph to, Follow action, Scale, Velocity, Grab.
Chords to Phrasing: its own generators, off until Enabled; each tab's Conditions button opens when a pass bypasses it.
More Generators: the set's generators it runs, after its own. PgUp and PgDn choose the tab before or after.
One clip in each scene must not loop, or exporting stops. Follow action is for real-time playback only.

Up, down, Left and Right select. [ and ] change. ENTER chooses. J jumps to the pattern. L plays the clip and stops it.
"""

# MainPage
HELP_MAIN_PAGE = """
This is the way into every page. Press a letter to open one, or move the box with the arrows and press ENTER.
The number on a button says how many of its things the set has: songs, patterns, chains, generators, scales and grooves of its own.

A file is a set of songs. Patterns, scales, generators, chains and grooves belong to the set, and every song shares them. Each song has its own tracks, draws and scenes, and one song is current: Songs picks it, and Draws and Arrange work on it.

Ctrl+S saves, Ctrl+O opens a file, Ctrl+X exports the current song, Ctrl+Z undoes the last change and Ctrl+Y redoes it, F1 lists every key and F3 is about llamatron, on every page. Here O opens and X exports too, and Q quits, from this screen only, asking first only when there are unsaved changes. ESC goes back, and cancels a dialog.
Nothing is saved or exported until you ask.
"""

# FilePage
HELP_FILE_PAGE = """
The set's own settings, and its file. Tab goes to the tabs; Left and Right choose one.
Title, Author, Description and Notes are for people reading the file; Bksp clears the first three. ENTER on Notes opens them; Tab reaches Save and CANCEL.
Step size: each step's length, unless a pattern sets its own. Default octaves: what a new note or drum hit gets. Octave labels: middle C as C3, as Live has it, or as C5.
Default follow action: a clip's Follow action unless it sets its own.
Visualizer: Arrange shows it first. Hide Visualizers: not shown.
Protected: the file is never saved over, like the demos.
New starts a new set; Save As (W) saves under a new name.
Ctrl+X exports the current song beside the set's file as <set>_<song> files.
"""

# SongsPage
HELP_SONGS_PAGE = """
The songs in the set, like the songs of one concert. Each has its own tempo, scale, seed, tracks, draws and scenes, and they all share the set's patterns, scales, generators and chains.

The marked song is current: Tracks, Draws and Arrange edit it, and Ctrl+X exports it, beside the set's file as <set>_<song>. Space makes the selected song current, and ENTER does too, then opens its settings.

A adds one, C copies it, N renames it, M moves it, and S sorts them by name. Bksp deletes it, but the set keeps at least one song.
/ searches the list as you type: Tab completes, ENTER keeps your place, ESC goes back to the whole list.
"""

# SongPage
HELP_SONG_PAGE = """
One song's settings. Up and down select one. [ and ] change it, and ENTER types or chooses.

Name: ENTER renames the song, which N on the Songs page does too.
Tempo: in quarter notes a minute, unless a scene sets its own. Time signature: only changes what's drawn, the beats in the pattern editor and the bars in Live.
Scale: the set's scale its degrees play in, unless a scene sets its own; Bksp leaves it with none.
Seed: none makes each export a new take; set one to repeat it.
Groove: every clip's swing, unless a scene or track chooses.
Live response: when an edit made while the song plays is heard: at the next bar, at each clip's next pass, or ASAP.
Preview instrument: what Listen plays a pattern through.
Visualizer: Arrange shows it first, over the File/Global page's.
The Export row does the same as Ctrl+X, which works on every page: it writes this song as a Live set or MIDI files.
"""

# NotesPage
HELP_NOTES_PAGE = """
Notes about the set, for anyone reading or sharing its file. They don't change how it plays.

It opens editing from the File/Global page. Typing adds text where the cursor is, ENTER starts a new
line, Bksp erases, and the arrows move the cursor. Tab reaches the Save and CANCEL buttons under
the text, and Tab again comes back; ESC cancels, throwing the typing away. While reading, up and
down scroll, E starts editing again, Bksp clears it all, after asking, and ESC goes back.
A protected set's notes can only be read, so they open reading, with no E or Bksp.
"""

# OpenPage
HELP_OPEN_PAGE = """
Choose a set file. ENTER opens a file, or goes into a folder. ../ goes up a folder.
The page comes back to the folder it last showed, until llamatron is closed.
/ searches the list as you type: Tab completes, ENTER keeps your place, ESC goes back to the whole list.
"""

# PatternsPage
HELP_PATTERNS_PAGE = """
Every pattern in the set, which all of its songs share, in a tab for each group, always sorted.
Tab goes to the row of tabs and back; Left and Right choose a tab there; PgUp and PgDn choose one from anywhere.
ENTER edits the selected pattern; + (New) makes one in the group.

A adds a pattern to the group, C copies, N renames, and renames update every clip.
G moves the pattern to another group. Bksp deletes it, once nothing uses it.
On the row of tabs: N renames the group, C copies all of it, Bksp ungroups its patterns.
L plays the pattern at once, again and again, and stops it.

TIME is one play at the current song's tempo. USED counts the clips, in every song, and chains that use it.
/ searches the list as you type: Tab completes, ENTER keeps your place, ESC goes back to the whole list.
"""

# TrackEditor
HELP_TRACK_EDITOR = """
Name: ENTER renames the track, which updates every scene and its pattern group. Drum: a drum track is never transposed.
Mute: starts switched off in Live; its clips can still be grabbed. Groove: for its clips, instead of the scene's or song's.
Transpose: moves its notes along the scale. Lowest and Highest octave: what its instrument plays, which the piano roll marks.
Default velocity: a step with none typed. Accent: what an accent adds. Instrument: where it plays in real time, or none.
MIDI CCs: the CC number each of a pattern's CC rows sends here.
Tab goes to the tabs; Left and Right choose one. Chords, Arp, Guitarify, Timing, Phrasing: its own generators, off until Enabled;
each tab's Conditions button opens when a pass bypasses it. More Generators: the set's generators it runs, after the built-ins.

Up, down, Left and Right select a setting. [ and ] change it, ENTER types, and Space or ENTER toggles. Bksp clears.
"""

# OffsetsEditor
HELP_OFFSETS_EDITOR = """
The arpeggiator plays one note of the chord each step, moved this many notes along the scale.
A blank step is silent, and the next step plays the note it would have played.
The steps start again with each chord, so a length that doesn't match the chord makes a new rhythm.

Each offset is a bar from the zero line, up or down, with its number beneath: one the gauge can't reach fills its column and is marked, like +7▲.
Digits type an offset, Up and Down change it, and Space or ENTER makes the step silent or plays it again.
I inserts a step, D removes one, and there can be 1 to 16.
"""

# ScalesPage
HELP_SCALES_PAGE = """
Named scales for the set's songs and their scenes to choose from. A clip uses its scene's scale, or else its song's.

A name can be anything, like main, so you can change what main is later, and everything using it follows.

A adds a C major scale and opens it. ENTER opens one: its name, root and kind are on its page. N renames it, and C copies it.
M moves it, and S sorts them by name. Bksp deletes it, but only once nothing uses it.
To delete a song's scale, clear it on that song's page first.

Patterns that use degrees need a scale to export.
/ searches the list as you type: Tab completes, ENTER keeps your place, ESC goes back to the whole list.
"""

# ScalePage
HELP_SCALE_PAGE = """
Name: ENTER renames the scale, and every song and scene using it follows.
Root: the note the scale starts on. [ and ] step through the roots, and ENTER picks one on a keyboard.
Kind: major, minor, a mode or a world scale. [ and ] step through them, and ENTER picks from two pages.

A scale still named after its root and kind, like C Major, is renamed as they change, so the name keeps saying what it is. A name of your own, like main, stays.
The notes the root and kind make are shown underneath, and how many songs and scenes use the scale, then a keyboard with the scale's keys filled and the root bracketed.
"""

# ChainEditor
HELP_CHAIN_EDITOR = """
The steps run from top to bottom, each working on what the last one made.

A adds a generator, which you make on the Generators page. ENTER changes one, C copies it, and Bksp removes it. M picks up a step, Up and Down carry it, and ENTER drops it.
N renames the chain, and every clip using it follows. W opens the chain's statements about the draws, which say when a pass goes by the whole chain.
/ searches the list as you type: Tab completes, ENTER keeps your place, ESC goes back to the whole list.
"""

# ChainStatementsPage
HELP_CHAIN_STATEMENTS_PAGE = """
Conditional Execution for a whole chain. Each line is a statement about a draw, such as AD odd. Each time a clip's pattern starts over, the statements are read, and when any is true the clip's notes go by this chain untouched for that pass.

Left and Right move between a line's parts and ENTER changes the part: the draw, the operator, and a number or another draw. A line set to ignored does nothing. Bksp sets a line back to ignored.
"""

# GeneratorStatementsPage
HELP_GENERATOR_STATEMENTS_PAGE = """
Conditional Execution for one built-in generator. Each line is a statement about a draw, such as AD odd. Each time a clip's pattern starts over, the statements are read, and when any is true the clip's notes go by this generator untouched for that pass.

Left and Right move between a line's parts and ENTER changes the part: the draw, the operator, and a number or another draw. A line set to ignored does nothing. Bksp sets a line back to ignored.
"""

# GeneratorsPage
HELP_GENERATORS_PAGE = """
Every generator of the set, under a heading for its type, the types and the generators under each sorted by name. Chains run them on clips, scenes and tracks, in the order each chain lists them.

Every type is closed until opened. Space or ENTER on a heading opens and closes its type, and PgUp and PgDn jump between the headings.
ENTER edits the selected generator. A adds one, asking which type under headings that Space opens, and opens it. N renames it, C copies it, and Bksp deletes it once nothing uses it.
/ searches the list as you type: Tab completes, ENTER keeps your place, ESC goes back to the whole list.
"""

# GeneratorListPage
HELP_GENERATOR_LIST_PAGE = """
The generators this clip, scene or track runs, in the order they run: a chain runs its own generators in its place.

A clip runs its own generators first, then its scene's, then its track's. A generator listed in two places runs twice.

A adds a generator, picked from the set's. M picks one up to carry with Up and Down, ENTER dropping it, and Bksp takes it out of the list. ESC goes back.
"""

# ChordsEditor
HELP_CHORDS_EDITOR = """
Each column is a chord: its bar rises to its degree, with its numeral and its name in the song's scale beneath.
A plain degree moves the clip along the scale, so the scale decides major or minor. A sharp or flat moves it by exact half steps, keeping its sound.
Up and Down move between the Chord, #/b, Quality, Tens., Scale and Inv. rows. [ and ] change the value, digits type a degree, Space or ENTER cycles #/b and Inv.
Scale borrows the chord from another scale type on the same root, Quality names the chord outright, and Tens. adds notes on top: ENTER on those rows opens the Chord dialog.
I inserts a chord and D removes one. H fills the chords with a named progression, matched to the song's scale.
"""

# PluginEditor: the help every generator page drawn from its plugin's view shares, which each page replaces with its plugin's own.
HELP_PLUGIN_EDITOR = """
A generator's settings, as its kind describes them.
"""

# GuitarBarEditor
HELP_GUITAR_BAR_EDITOR = """
A bar of strokes, one a cell, following the song's bars. Left and Right move; [ and ] change the cursor's stroke.
Strokes: nothing, down, up (the top strings), mute (short and quiet), bass, alt bass (the fifth), and string 1 to 4 from the highest.
Space or ENTER accents a cell. I inserts a cell and D removes one. S steps the cell length. R picks a ready-made bar.
"""

# StepRowEditor
HELP_STEP_ROW_EDITOR = """
A row of steps, each on or off, running from each clip's start at the generator's own step.
Left and Right move. Space or ENTER turns the step under the cursor on or off, the line above saying what a step that's on does.
I inserts a step and D removes one, from 1 to 16.
"""

# PatternEditor
HELP_PATTERN_EDITOR = """
Each column is a step, as long as the step size. Tab switches between the piano roll and the rows. Home/End jump to the ends.
Roll: Space or ENTER draws a note of the entry size (E picks); [ and ] drag its end, X splits it, . sharpens or flattens it, G grabs, Bksp erases it, H picks its chord, K its keyswitches.
Rows: Degree is a gauge: digits set it, [ and ] nudge it, as they adjust every number, Bksp empties the step. The rows under Octave come in sections headed by a row marked + (closed) or - (open): Space or ENTER opens or closes it, PgUp/PgDn jump between them.
Basics: #/b, Velocity, Keyswitch. Chord: Chord, Tension, Scale (ENTER picks), Inv. Timing: Tie (Space after a note holds it), Gate (ENTER types one), Dot (d, t), Glide. Advanced: Probability, Ratchet, Ratchet Offset, Grab. CCs and Slide work on rests too. Use Draws adds the draws to notes and velocities.
S sizes the pattern, and on the rows I inserts a step and D removes one. M munges it. R reconfigures it: load over, step size, time signature, drum on or off, direction, rename. L plays it at once, again and again, and stops it.
"""

# DrawsPage
HELP_DRAWS_PAGE = """
The eight draws, AD to HD, are short lists of numbers the whole current song shares. A pattern's step uses one with Note+=
or Vel+= in the Use Draws section, and takes the next number of its strip each time, added to its note or velocity.

Direction says which slot comes next: a pattern's directions, serial (every slot once a round, in a random order) or any
(a slot at random every time). A blank slot is passed over. Slots is how many the strip holds, and Value Min and Value Max
keep every slot within them. Conditions redraw makes a condition that reads the draw take a number from it too.

Up and down select, and Space or ENTER opens a draw. On the strip, Left and Right move between slots, [ and ] change one,
a digit puts that number in one, ENTER types any number and Bksp makes it blank. While the song plays, each draw's last slot is lit.
"""

# GroovesPage
HELP_GROOVES_PAGE = """
A groove moves notes off the grid, like swing on a drum machine. It's a row of cells, one bar of 16ths to start with, each
saying how late (+) or early (-) a note in that cell plays, as a percentage of the cell. Grooves follow time, not steps.

The song chooses a groove, none by default, and a scene or a track can choose another, or off to play straight.
The track's choice wins, then the scene's, then the song's, but off anywhere plays straight.

The factory grooves are always there: four swings on 16ths, two on 8ths and a push. ENTER looks at one and C copies it,
but they can't be changed, renamed or deleted. A adds a straight groove of your own and opens it. On your own grooves,
ENTER edits, N renames, C copies, M moves, S sorts yours by name, and Bksp deletes one that nothing uses.
/ searches the list as you type: Tab completes, ENTER keeps your place, ESC goes back to the whole list.
"""

# InstrumentsPage
HELP_INSTRUMENTS_PAGE = """
An instrument is a MIDI device of this computer and a channel on it, 1 to 16, for playing in real time as you work.
Each track chooses one on its track editor, or none, and a track with none is left out of real-time playback.
Two instruments may share a device and a channel. No export reads them: a Live set has its own instruments.

Adding the first instrument turns the main screen's Real Time switch on, and deleting the last turns it off.

A adds one and opens it. ENTER edits, N renames, C copies, M moves, S sorts them by name, and Bksp deletes one
that no track uses.
/ searches the list as you type: Tab completes, ENTER keeps your place, ESC goes back to the whole list.
"""

# InstrumentEditor
HELP_INSTRUMENT_EDITOR = """
Name: ENTER renames the instrument, and every track that chose it follows.
Device: the MIDI output port, chosen from the ports this computer has now, or *FluidSynth, the software
synthesizer the tracker starts itself. A track on an instrument with no device cannot play. A port that
has gone is still shown.
Channel: 1 to 16, as the device numbers them, or (auto) with FluidSynth, which gives each track its own.
GM sound: one of General MIDI's 128 sounds, which the MIDI (General MIDI) export gives this instrument's tracks and
FluidSynth plays. ENTER chooses it from the families, each opening its sounds, where a sound can be heard.
Default velocity: a step with none typed. Accent: an accent adds.

Up and down select a setting. [ and ] change it, and ENTER types or chooses. Bksp clears the device or sound.
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

HELP_WIZARD_PAGE = """
The song wizard makes a whole song from a few choices. Nothing in the set changes until Apply.

The tree at the left lists the wizard's parts. Up and down move through the tree, left and right close and open a part, and the settings of the part under the cursor show at the right.
ENTER or Tab moves into the settings, and ESC or Tab moves back to the tree.
Genre, then Subgenre: choose both first. A dim part of the tree is locked until then. The key, the scale, the tempo and the form take what the subgenre usually has, and each can be changed.
Composition: Chords, the chord progression; Melody, the melody style of the tunes; Hooks, whether the song has a hook.
Tunes: the tune of each kind of section. ENTER edits its notes in the pattern editor; edited notes are yours, and no choice changes them.
A new take, in the legend on a tune, writes that tune again and leaves the rest of the song.
Form: the sections the song plays, in order, listed under Form in the tree. On a section, I inserts a section before it, A adds one at the end, C copies it, Bksp removes it
and M moves it, and its settings choose its kind, how many bars it lasts and who plays in it.
Apply: ENTER on the Apply button makes the song and shows Arrange. Undo then takes the whole song away again.
L listens to a hook, a tune or a section, and stops it. ESC in the tree closes the wizard, and asks first.
"""
