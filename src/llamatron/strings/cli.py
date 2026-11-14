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
"""What the command line says: the help for each argument, and what an export reports.

Each constant starts with MSG_.
"""

# cli.py
MSG_CLI_WROTE = 'wrote {target} output for song ({song}) to {path}'
MSG_HELP_DESCRIPTION = 'Open the tracker, or with --to, turn the songs of a set file into Ableton Live sets or MIDI files.'
MSG_HELP_SET = 'the set file to open, or to read with --to'
MSG_HELP_TO = (
    'write the songs instead of opening the tracker, each as an Ableton Live set (ableton, the default), '
    'one MIDI file of every track (midi), a MIDI file per track (stems), a MIDI file per clip (cliptree) '
    'or one General MIDI file, each track on its own channel with its instrument\'s sound (gm)'
)
MSG_HELP_SONG = 'write only this song of the set (default: every song)'
MSG_HELP_OUT = 'the directory to write to, as files named <set>_<song> (default: beside the set)'
MSG_HELP_TEMPLATE = 'the Live set to build from (default: the one installed with llamatron)'
MSG_HELP_REPLACE = "replace each song's earlier output, so you can regenerate and listen"
MSG_HELP_SEED = "the seed for every random choice, in place of each song's, so that an export can be repeated exactly"
MSG_HELP_FORCE = 'export a set that holds values that cannot be used, with each one changed to the nearest allowed value; the set file is not changed'
MSG_HELP_AUTOPLAY = 'open on Arrange and play the song from the top, as Space on the corner does; the set needs instruments on its tracks'
MSG_HELP_AUTOPLAY_QUIT = 'as --autoplay, and quit once the song has ended'
MSG_HELP_FOR_RECORDING = 'open on the splash, leave the save mark off the header, and refuse a song that would wait on a looping clip forever, for the demo recorder (internal_tools/record_demo.py)'
MSG_HELP_MAX_SECONDS = 'quit after this many seconds whatever is playing, which the demo recorder passes as its time limit'
MSG_HELP_BATCH_VIDEO = 'record a batch video: the title on black, Arrange with READY, then the clips and the visualizer --visualizer names by turns, every ten seconds, filling a frame whose pulse changes at each scene, fading to black at the end; needs --visualizer'
MSG_HELP_NO_ALTERNATE = 'with --batch-video, show the visualizer alone in the frame rather than alternating it with the clips'
MSG_HELP_VISUALIZER = 'open Arrange playing the song with this visualizer mode over the clips, as the demo recorder and internal_tools/preview_visualizer.sh do'
# A set file that holds values that cannot be used: one line for each, saying what --force would change, or what it changed.
MSG_CLI_WOULD_CHANGE = 'would change {change}'
MSG_CLI_CHANGED = 'changed {change}'
