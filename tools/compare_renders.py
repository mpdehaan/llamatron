#!/usr/bin/env python3
# llamatron: a Python language and framework for producing MIDI clips.
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

"""Capture everything the example songs produce, or compare a fresh render with a capture, to prove a change alters nothing.

Before a refactoring, or any change that shouldn't change the music, capture the renders of
every song in examples/. Afterwards, compare: it renders them again and lists every file that
differs, is missing or is new, byte for byte. A change that should alter one song, like a fix to
play directions, shows up as differences only in that song's files, which is how to check that
nothing else moved.

For each song it keeps:
- clips/: the MIDI file of every clip, as `llamatron song.yml --to cliptree` writes them
- live.xml: the Live set, unzipped, so that it compares as text
- saved.yml: the song after the tracker loads and saves it
- estimate.txt: how long the tracker estimates the song and each scene lasts

saved.yml always differs after a version bump, because saving records the version.

Run it from the top folder of the project:

    .venv/bin/python tools/compare_renders.py capture /some/folder
    .venv/bin/python tools/compare_renders.py compare /some/folder

capture replaces a folder only if it's empty or holds an earlier capture, so that it can't wipe
anything else by mistake. compare exits with 1 if anything differs.
"""

import argparse
import contextlib
import filecmp
import glob
import gzip
import io
import os
import shutil
import sys
import tempfile

from llamatron.composition.song import Song
from llamatron.playback.song_renderer import SongRenderer
from llamatron.renderers.ableton_project import AbletonProject
from llamatron.renderers.clip_tree import ClipTree
from llamatron.tui.document import Document

EXAMPLES = 'examples/*.yml'
CAPTURE = 'capture'
COMPARE = 'compare'
# A file in every capture, so that capture knows a folder it may replace.
MARKER = '.llamatron_renders'
CLIPS_FOLDER = 'clips'
LIVE_FOLDER = 'live'
LIVE_SET = 'live.als'
LIVE_XML = 'live.xml'
SAVED_SONG = 'saved.yml'
ESTIMATE = 'estimate.txt'
FRESH_FOLDER = 'now'
MSG_CAPTURED = 'Captured {count} files in {folder}.'
MSG_NOT_A_CAPTURE = "{folder} isn't empty and doesn't hold an earlier capture, so it was left alone."
MSG_NO_CAPTURE = "{folder} doesn't hold a capture. Capture one first."
MSG_IDENTICAL = 'Identical: every file matches.'
MSG_MISSING = 'missing: {path}'
MSG_DIFFERS = 'differs: {path}'
MSG_EXTRA = 'new: {path}'
SUCCESS = 0
FAILURE = 1


def render_examples(folder):
    """Render every example song into its own folder inside folder."""
    for path in sorted(glob.glob(EXAMPLES)):
        name = os.path.splitext(os.path.basename(path))[0]
        out = os.path.join(folder, name)
        os.makedirs(out)
        song = SongRenderer(Song.read_file(path)).render()
        # The renderers print what they write, which isn't needed here.
        with contextlib.redirect_stdout(io.StringIO()):
            ClipTree(os.path.join(out, CLIPS_FOLDER), song).render()
            AbletonProject(os.path.join(out, LIVE_FOLDER), song).render()
        keep_live_set_as_xml(out)
        Document.load(path).save(os.path.join(out, SAVED_SONG))
        with open(os.path.join(out, ESTIMATE), 'w') as file:
            file.write(repr(SongRenderer(Song.read_file(path)).estimate()) + '\n')
    open(os.path.join(folder, MARKER), 'w').close()


def keep_live_set_as_xml(out):
    """Replace the gzipped Live set with its XML, which compares the same but can be read when it differs."""
    live_set = os.path.join(out, LIVE_FOLDER, LIVE_SET)
    with open(live_set, 'rb') as file:
        xml = gzip.decompress(file.read())
    with open(os.path.join(out, LIVE_XML), 'wb') as file:
        file.write(xml)
    shutil.rmtree(os.path.join(out, LIVE_FOLDER))


def files_in(folder):
    """Return every file in a folder and its subfolders, as paths relative to it."""
    return {
        os.path.relpath(os.path.join(root, name), folder)
        for root, _, names in os.walk(folder) for name in names
    }


def differences(captured, fresh):
    """Return a line for each file that's missing, different or new in fresh compared with captured."""
    before, after = files_in(captured), files_in(fresh)
    problems = [MSG_MISSING.format(path=path) for path in sorted(before - after)]
    problems += [
        MSG_DIFFERS.format(path=path) for path in sorted(before & after)
        if not filecmp.cmp(os.path.join(captured, path), os.path.join(fresh, path), shallow=False)
    ]
    problems += [MSG_EXTRA.format(path=path) for path in sorted(after - before)]
    return problems


def is_replaceable(folder):
    """Return whether capture may replace a folder: it doesn't exist, is empty, or holds an earlier capture."""
    return not os.path.exists(folder) or not os.listdir(folder) or os.path.exists(os.path.join(folder, MARKER))


def capture(folder):
    if not is_replaceable(folder):
        print(MSG_NOT_A_CAPTURE.format(folder=folder))
        return FAILURE
    shutil.rmtree(folder, ignore_errors=True)
    render_examples(folder)
    print(MSG_CAPTURED.format(count=len(files_in(folder)), folder=folder))
    return SUCCESS


def compare(folder):
    if not os.path.exists(os.path.join(folder, MARKER)):
        print(MSG_NO_CAPTURE.format(folder=folder))
        return FAILURE
    with tempfile.TemporaryDirectory() as temporary:
        fresh = os.path.join(temporary, FRESH_FOLDER)
        render_examples(fresh)
        problems = differences(folder, fresh)
    print('\n'.join(problems) if problems else MSG_IDENTICAL)
    return FAILURE if problems else SUCCESS


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('action', choices=[CAPTURE, COMPARE])
    parser.add_argument('folder', help='where the capture is kept')
    arguments = parser.parse_args()
    if arguments.action == CAPTURE:
        return capture(arguments.folder)
    return compare(arguments.folder)


if __name__ == '__main__':
    sys.exit(main())
