# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the video tutorial says as it builds a set: a sentence at each point worth a word, and what a key does the first time it matters.

The tutorial (tutorial/plan.py) says each of these as it reaches that part of the build, and the
caption strip shows them at the foot of the screen (tui/caption_strip.py).
"""

# tutorial/plan.py
MSG_NARRATE_START = 'This is llamatron. We start from a new set and build {title} from nothing.'
MSG_NARRATE_SONG = 'First the song itself: its name and its settings.'
# Said as each thing is made, or as one the new set already has is renamed to what the target calls it,
# Each with the word for the thing that follows.
MSG_NARRATE_MAKING = 'And now we are making {kind} called ({name}).'
MSG_NARRATE_RENAMING = 'There is already {kind}, so we are going to rename it.'
MSG_A_SONG = 'a song'
MSG_A_SCALE = 'a scale'
MSG_A_TRACK = 'a track'
MSG_A_SCENE = 'a scene'
MSG_A_PATTERN = 'a pattern'
MSG_A_DRUM_PATTERN = 'a drum pattern'
MSG_AN_INSTRUMENT = 'an instrument'
MSG_NARRATE_PATTERN_ROWS = 'Now the finer settings of ({name}), row by row.'
MSG_NARRATE_CLIP = 'Putting ({pattern}) on track ({track}) in scene ({scene}).'
# The ending: the finished song shown on Arrange, then, with a MIDI
# port to play through, the instruments and the play, and without one, the tutorial ends there.
MSG_NARRATE_COMPLETE = 'Now the song is complete, we can export it now.'
MSG_NARRATE_PLAY_LIVE = 'However, for this demo, lets play it live into a DAW instead.'
MSG_NARRATE_EXPORT_KEY = "If we wanted to export, it's Ctrl+X."
MSG_NARRATE_REAL_TIME = 'Now we are going to set up the Realtime MIDI details to map into our DAW.'
MSG_NARRATE_GUIDE = 'Read the online guide docs for more information.'
MSG_NARRATE_PLAY = "And now it's time to play the song."
MSG_NARRATE_DONE = 'That is {title}.'
MSG_NARRATE_WOULD_EXPORT = 'To export it now we would press Ctrl+X.'
MSG_NARRATE_TUTORIAL_COMPLETE = 'The tutorial is now complete.'
MSG_NARRATE_QUITTING = 'In exiting the app, we will be asked if we want to save any changes.'
# What a key does, said the first time it is pressed where it matters:
# the arrows anywhere and again on the piano roll and in the rows view, ENTER and ESC anywhere, and
# Space once on each kind of page.
MSG_EXPLAIN_ARROWS = 'Arrow keys navigate around the app.'
MSG_EXPLAIN_ESCAPE = 'ESC always goes back to the previous screen.'
MSG_EXPLAIN_ARROWS_ON_ROLL = 'We move around with arrow keys.'
MSG_EXPLAIN_ARROWS_IN_ROWS = 'In the extra details on the pattern, the arrow keys are also used to navigate.'
MSG_EXPLAIN_ENTER = 'ENTER is always available.'
MSG_EXPLAIN_SPACE_ON_ROLL = 'Space is used to enter notes.'
MSG_EXPLAIN_BACKSPACE_ON_ROLL = 'If we need to, notes can be removed with Bksp.'
MSG_EXPLAIN_SPACE_ON_ARRANGE = 'Space starts and stops songs, scenes, and tracks.'
MSG_EXPLAIN_SPACE_TOGGLES = 'Pressing space toggles many types of cells.'

# tutorial/plan.py: what the plan found in the target and cannot set yet, in the report.
MSG_LEFT_OUT_SONG_SETTING = 'the song setting {setting}'
MSG_LEFT_OUT_SCALE = 'deleting the scale ({name}), which the song still uses'
MSG_LEFT_OUT_TRACK_SETTING = 'the track setting {setting} of ({name})'
MSG_LEFT_OUT_SCENE_SETTING = 'the scene setting {setting} of ({name})'
MSG_LEFT_OUT_CLIP_SETTING = 'the clip setting {setting} of track ({track}) in scene ({scene})'
MSG_LEFT_OUT_PATTERN_SETTING = 'the pattern setting {setting} of ({name})'
MSG_LEFT_OUT_ROW = 'the {row} row of ({name})'

# tutorial/runner.py: the lines of the tutorial's report after it ran.
MSG_TUTORIAL_SAID = '{seconds:7.1f}  {text}'
MSG_TUTORIAL_LEFT_OUT = 'left out, since the tutorial cannot set it yet: {what}'
MSG_TUTORIAL_KEYS = '{count} keys pressed in {seconds:.1f} seconds'

# tutorial/plan.py: what is said on the main screen once the cursor's box is on the cell the tutorial
# is about to open, or the Real Time switch it is about to turn on.
MSG_NARRATE_OPENING = 'Opening {cell}'
MSG_NARRATE_TURNING_ON = 'Turning on {cell}'
# tutorial/plan.py: the call-out of a letter key the first time it is pressed on a kind of page, with
# the words its legend gives it.
MSG_CALL_LETTER = 'Press {key} for {what}'

# tutorial/subtitles.py: a cue of the SubRip file written beside the video, and a moment as SubRip writes it.
MSG_SUBTITLE_CUE = '{number}\n{start} --> {end}\n{text}\n\n'
MSG_SUBTITLE_TIME = '{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}'
