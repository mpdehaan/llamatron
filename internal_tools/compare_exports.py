"""Capture everything the example sets export, or compare a fresh export with a capture, to prove a change alters nothing.

Before a refactoring, or any change that shouldn't change the music, capture the exports of
every set in examples/. Afterwards, compare: it exports them again and lists every file that
differs, is missing or is new, byte for byte. A change that should alter one song, like a fix to
play directions, shows up as differences only in that song's files, which is how to check that
nothing else moved.

For each set it keeps saved.yml, the set after the tracker loads and saves it, and for each of
its songs, in a folder named after the song:

- clips/: the MIDI file of every clip, as `llamatron set.yml --to cliptree` writes them
- arrangement/: the whole song as one MIDI file and as stems, as `--to midi` and `--to stems` write them
- live.xml: the Live set, unzipped, so that it compares as text
- estimate.txt: how long the tracker estimates the song and each scene lasts

saved.yml is compared without its version line, since saving records the version. Every song
is exported with the same seed, since a song without one would play differently every time.

Run it from the top folder of the project:

    .venv/bin/python internal_tools/compare_exports.py capture /some/folder
    .venv/bin/python internal_tools/compare_exports.py compare /some/folder

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
from concurrent.futures import ProcessPoolExecutor

from llamatron.composition.file_format import SetlistSetting
from llamatron.composition.setlist import Setlist
from llamatron.playback.song_renderer import SongRenderer
from llamatron.exporters.ableton_project import AbletonProject
from llamatron.exporters.clip_tree import ClipTree
from llamatron.exporters.midi_arrangement import MidiSong, MidiStems
from llamatron.tui.document import Document
from llamatron.composition.setlist import file_stem
from llamatron.exporters.exports import export_name

EXAMPLES = 'examples/**/*.yml'
CAPTURE = 'capture'
COMPARE = 'compare'
# A file in every capture, so that capture knows a folder it may replace.
MARKER = '.llamatron_renders'
# The seed every song is rendered with, whatever its file says, so that renders can be compared.
COMPARISON_SEED = 1
LIVE_XML_SUFFIX = '.xml'
SAVED_SONG = 'saved.yml'
VERSION_LINE_START = SetlistSetting.VERSION + ':'
FILE_ENCODING = 'utf-8'
ESTIMATE = '{name}_estimate.txt'
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
    """Export every example set into its own folder inside folder, as many at once as the computer has cores."""
    paths = sorted(glob.glob(EXAMPLES, recursive=True))
    with ProcessPoolExecutor() as pool:
        # list() waits for every song, and raises the first error any of them hit.
        list(pool.map(render_example_job, [(path, folder) for path in paths]))
    open(os.path.join(folder, MARKER), 'w').close()


def plain_estimates(song):
    """Return a song's scene estimates as plain tuples, which is how the estimate file has always been written."""
    return [tuple(estimate) for estimate in SongRenderer(song, seed=COMPARISON_SEED).estimate()]


def render_example_job(job):
    """Render one example from a (path, folder) pair, which is how a process pool hands work out."""
    path, folder = job
    render_example(path=path, folder=folder)


def render_example(*, path, folder):
    """Export one set into a folder named after it inside folder, every song every way, with the files named as the program names them."""
    name = file_stem(path)
    out = os.path.join(folder, name)
    os.makedirs(out)
    setlist = Setlist.read_file(path)
    for song_name in setlist.get_song_names():
        export_song(song=setlist.get_song(song_name), out=out, name=export_name(setlist=name, song=song_name))
    Document.load(path).save(path=os.path.join(out, SAVED_SONG))


def export_song(*, song, out, name):
    """Export one song every way into a folder, as files named after name, and note how long the tracker estimates it lasts."""
    grid = SongRenderer(song, seed=COMPARISON_SEED).render()
    # The exporters print what they write, which isn't needed here.
    with contextlib.redirect_stdout(io.StringIO()):
        ClipTree(directory=out, grid=grid, name=name).export()
        MidiSong(directory=out, grid=grid, name=name).export()
        MidiStems(directory=out, grid=grid, name=name).export()
        live_set = AbletonProject(directory=out, grid=grid, name=name)
        live_set.export()
    keep_live_set_as_xml(live_set.path())
    with open(os.path.join(out, ESTIMATE.format(name=name)), 'w') as file:
        file.write(repr(plain_estimates(song)) + '\n')


def keep_live_set_as_xml(live_set):
    """Replace the gzipped Live set with its XML, which compares the same but can be read when it differs."""
    with open(live_set, 'rb') as file:
        xml = gzip.decompress(file.read())
    with open(os.path.splitext(live_set)[0] + LIVE_XML_SUFFIX, 'wb') as file:
        file.write(xml)
    os.remove(live_set)


def files_in(folder):
    """Return every file in a folder and its subfolders, as paths relative to it."""
    return {
        os.path.relpath(os.path.join(root, name), folder)
        for root, _, names in os.walk(folder) for name in names
    }


def same_file(*, captured, fresh, path):
    """Return whether a captured file and its fresh counterpart match, ignoring the version line of a re-saved set."""
    if os.path.basename(path) == SAVED_SONG:
        return without_version_line(os.path.join(captured, path)) == without_version_line(os.path.join(fresh, path))
    return filecmp.cmp(os.path.join(captured, path), os.path.join(fresh, path), shallow=False)


def without_version_line(path):
    """Return a saved set's text without the line that records the version that saved it."""
    with open(path, encoding=FILE_ENCODING) as file:
        return [line for line in file if not line.startswith(VERSION_LINE_START)]


def differences(*, captured, fresh):
    """Return a line for each file that's missing, different or new in fresh compared with captured."""
    before = files_in(captured)
    after = files_in(fresh)
    problems = [MSG_MISSING.format(path=path) for path in sorted(before - after)]
    problems += [MSG_DIFFERS.format(path=path) for path in sorted(before & after) if not same_file(captured=captured, fresh=fresh, path=path)]
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
        problems = differences(captured=folder, fresh=fresh)
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
