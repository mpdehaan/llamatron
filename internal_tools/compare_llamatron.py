# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Hold llamatron to the Python program's last answers, frozen in py_legacy/frozen_test_data/ before the Python program was
retired: every example set and test set is put through a step by llamatron, and what it makes is compared with what the
Python made of the same file. The Rust side is src/target/release/llamatron-compare.

    .venv/bin/python internal_tools/compare_llamatron.py load      # every example's and test set's data, as both load it
    .venv/bin/python internal_tools/compare_llamatron.py render    # every song rendered from one seed, each clip's notes
    .venv/bin/python internal_tools/compare_llamatron.py screens   # the key tour's screens at 80x24 and 160x50
    .venv/bin/python internal_tools/compare_llamatron.py load --only tie

A set changed since its answers were frozen has none to be held to, and is counted apart. It prints each set that differs
with the first place it differs, and a count, and exits 1 when anything differs, so that the commit check can run it.
"""

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
import pathlib
import queue
import shutil
import subprocess
import sys

TOP = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOP / 'python' / 'src'))
from llamatron_tools.safe_yaml import load_safely  # noqa: E402

RUST = TOP / 'src' / 'target' / 'release' / 'llamatron-compare'
EXAMPLES = TOP / 'examples'
FROZEN = TOP / 'py_legacy' / 'frozen_test_data'
# The test sets, which the frozen answers name test_data/...
TEST_SETS = FROZEN / 'test_data'
ANSWERS = FROZEN / 'answers'
SHOWN = 120
# The steps whose answers are frozen.
STEPS = ('load', 'layout', 'migrate', 'save', 'edits', 'pattern_edits', 'render', 'timeline', 'player', 'midi', 'live', 'import')
# Where the screen tour's baseline is kept, git-ignored, first copied from the frozen one.
KEPT = TOP / '.cache' / 'compare_llamatron'
# What a set changed since the answers were frozen is answered with, so that it is counted apart.
CHANGED = 'changed since frozen'


def kept_python(step, path):
    """Return the Python's frozen answer for a step on a set or MIDI file, None where the step does not apply to it, or
    CHANGED where the file is not the one the answer was frozen for."""
    key = key_of(path)
    index = json.loads((ANSWERS / step / 'index.json').read_text(encoding='utf-8'))
    if index.get(key) != hashlib.sha256(path.read_bytes()).hexdigest():
        return CHANGED
    return json.loads(gzip.decompress((ANSWERS / step / (key + '.json.gz')).read_bytes()))


def key_of(path):
    """Return a set's place as the frozen answers name it: examples/... or test_data/..."""
    if path.is_relative_to(TEST_SETS):
        return 'test_data/' + str(path.relative_to(TEST_SETS))
    return str(path.relative_to(TOP))


class Server:
    """One llamatron-compare that answers step after step on its pipes, so that a set starts no program of its own."""

    def __init__(self):
        self.process = subprocess.Popen([str(RUST), 'serve'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def ask(self, command, path):
        """Return the code a step ends with on a set, what it printed and what went wrong."""
        self.process.stdin.write('{}\t{}\n'.format(command, path).encode('utf-8'))
        self.process.stdin.flush()
        code, printed, wrong = (int(part) for part in self.process.stdout.readline().decode('utf-8').split('\t'))
        return code, self.process.stdout.read(printed).decode('utf-8'), self.process.stdout.read(wrong).decode('utf-8')

    def close(self):
        self.process.stdin.close()
        self.process.wait()


def answer_of(code, printed, wrong):
    """Return what llamatron made of a set: its output, or that the set waits on a part not ported, or what went wrong."""
    if code == NOT_PORTED:
        return NotPorted(wrong.strip())
    if code != 0:
        return 'FAILED: ' + wrong.strip()
    return printed.rstrip('\n')


def rust_answers(command, paths):
    """Return llamatron's answer for a step on each set, in order, from a server for each core working side by side."""
    servers = queue.Queue()
    made = []
    for _ in range(max(1, min(os.cpu_count() or 1, len(paths)))):
        server = Server()
        made.append(server)
        servers.put(server)

    def asked(path):
        server = servers.get()
        try:
            return answer_of(*server.ask(command, path))
        finally:
            servers.put(server)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(made)) as pool:
        answers = list(pool.map(asked, paths))
    for server in made:
        server.close()
    return answers


def rust(command, path):
    """Return what llamatron makes of one set for a step."""
    return rust_answers(command, [path])[0]


# What llamatron-compare exits with for a set using a part of the program not ported yet.
NOT_PORTED = 3


class NotPorted(str):
    """What llamatron-compare says of a set that uses a part of the program not ported yet, which is counted apart."""


def first_difference(first, second):
    """Return where two texts first differ, with a little of each from there."""
    for place, (one, other) in enumerate(zip(first, second)):
        if one != other:
            return 'at {}: python {!r} rust {!r}'.format(place, first[max(0, place - 20):place + SHOWN], second[max(0, place - 20):place + SHOWN])
    return 'lengths {} and {}'.format(len(first), len(second))


def same_in_order(python, port):
    """Return whether two JSON texts hold the same data with every mapping's order counted, as a set's order of items is."""
    if port.startswith('FAILED'):
        return False
    return json.loads(python, object_pairs_hook=list) == json.loads(port, object_pairs_hook=list)


def same_as_data(python, port):
    """Return whether two saved sets hold the same data: mappings in any order, lists in order (the user's rule)."""
    if port.startswith('FAILED'):
        return False
    # The same text is the same data; only texts that differ are read, which is slow without libyaml.
    if python == port:
        return True
    return load_safely(python) == load_safely(port)


# How each step's two outputs are compared: as text unless named here.
COMPARED = {'save': same_as_data, 'import': same_as_data, 'edits': same_in_order, 'pattern_edits': same_in_order}


# The screen tour: the Python's capture, made once, since the Python program is frozen, and where the Rust's replay of its
# keys is written. The tour starts by exporting a PDF, which stays in the Python program, so the Rust starts after it.
SCREENS = pathlib.Path('/tmp/claude/llamatron/screens')
SCREEN_SIZES = ((80, 24), (160, 50))
NOT_PORTED_PAGE = '(not ported)'
# What the capture writes for the folder its tour ran in, and the folder the Rust's tour runs in.
FOLDER = 'FOLDER'
TOUR_FOLDER = 'tour_folder'
# The home folder the tour's MIDI import picker starts in, the same as the Python tour's.
# The home folder the Rust's tour runs with: a copy of the frozen one at a short path, so that no screen cuts its name.
FROZEN_HOME = TEST_SETS / 'tour_home'
TOUR_HOME = SCREENS / 'tour_home'
# Where the home folder was when the Python's tour was captured, and what both tours' screens name it.
CAPTURED_HOME = TOP / 'tests' / 'data' / 'tour_home'
HOME = 'HOME'
PDF_PAGE = 'PdfExportPage'
LEAVE = 'escape'


def python_screens():
    """Return the Python's screen tour at each size, from its frozen capture, copied out first where it has not been."""
    files = [SCREENS / 'screens_{}x{}.json'.format(*size) for size in SCREEN_SIZES]
    if not all(path.exists() for path in files) or not (SCREENS / 'tour.yml').exists():
        shutil.copytree(FROZEN / 'screens' / 'capture', SCREENS, dirs_exist_ok=True)
    shutil.rmtree(TOUR_HOME, ignore_errors=True)
    shutil.copytree(FROZEN_HOME, TOUR_HOME)
    return [(size, json.loads(home_named(path.read_text(encoding='utf-8'), CAPTURED_HOME))) for size, path in zip(SCREEN_SIZES, files)]


def home_named(text, home):
    """Return screens with the tour's home folder, wherever it was, written as HOME, as both tours show it."""
    return text.replace(json.dumps(str(home))[1:-1], HOME)


def with_folder_named(text, folder):
    """Return the Rust's screens with the folder its tour ran in written as FOLDER, by every name the folder goes by."""
    text = home_named(text, TOUR_HOME)
    for name in sorted({str(folder), str(folder.resolve())}, key=len, reverse=True):
        text = text.replace(json.dumps(name)[1:-1], FOLDER)
    return text


def pieces(line):
    """Return a screen line's pieces as one comparable list: empty pieces left out, and neighbours of one style joined. A line
    naming the tour's folder ends without its blanks, which hang on how long the folder's real path was."""
    joined = []
    for text, style in line:
        if not text:
            continue
        if joined and joined[-1][1] == style:
            joined[-1][0] += text
        else:
            joined.append([text, style])
    if any(FOLDER in text or HOME in text for text, _ in joined):
        while joined and not joined[-1][0].strip():
            joined.pop()
    return joined


def held_set(name):
    """Return the whole path of a set the capture wrote, which it names inside its folder, for the Rust's tour to read from
    the folder of its own it runs in."""
    return str(SCREENS / name)


def keys_with_stacks(stop):
    """Return a stop's keys, each with the pages and dialogs open as it was pressed and, where the key before changed the
    set, the file the set was then written to, whether it held unsaved changes and its current song, joined by a unit
    separator."""
    keys = []
    for key, stack, (written, dirty, song) in zip(stop['keys'], stop['stacks_before'], stop['sets_before']):
        parts = [key, ','.join(stack)]
        if written:
            parts += [held_set(written), str(dirty), song]
        keys.append('\x1f'.join(parts))
    return keys


def after_the_pdf(stops):
    """Return the tour's stops from the first with the PDF export page closed, its help among them, that stop's keys from
    where ESC left the PDF page."""
    first = next(place for place, stop in enumerate(stops) if PDF_PAGE not in stop['stack'])
    # Each stop carries the types of generator the Generators page showed open before its keys, as the stop before left them.
    before = [stops[place - 1].get('open_types', []) if place > 0 else [] for place in range(first, len(stops))]
    stops = [dict(stop, open_before=opened) for stop, opened in zip(stops[first:], before)]
    keys = stops[0]['keys']
    stops[0]['keys'] = keys[keys.index(LEAVE) + 1:]
    stops[0]['stacks_before'] = stops[0]['stacks_before'][keys.index(LEAVE) + 1:]
    stops[0]['sets_before'] = stops[0]['sets_before'][keys.index(LEAVE) + 1:]
    return stops


def baseline_path(size):
    """Return where the stops that differed when the baseline was taken are kept for a size."""
    path = KEPT / SCREENS_BASELINE.format(*size)
    frozen = FROZEN / 'screens' / SCREENS_BASELINE.format(*size)
    if not path.exists() and frozen.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(frozen.read_bytes())
    return path


def capture_digest(size):
    """Return a digest of the Python's capture at a size, which a baseline belongs to."""
    return hashlib.sha256((SCREENS / 'screens_{}x{}.json'.format(*size)).read_bytes()).hexdigest()


def read_baseline(size):
    """Return the stops kept as still differing at a size, or None where no baseline belongs to this capture."""
    path = baseline_path(size)
    if not path.exists():
        return None
    held = json.loads(path.read_text(encoding='utf-8'))
    return set(held['differing']) if held['capture'] == capture_digest(size) else None


def write_baseline(size, differing):
    """Keep the stops that differ at a size, for the capture they belong to."""
    path = baseline_path(size)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'capture': capture_digest(size), 'differing': sorted(differing)}), encoding='utf-8')


def compare_screens(shown_most=None, baseline=False):
    """Replay the screen tour's keys in the Rust tracker at each size and compare every stop's screen; return the exit code.

    While pages are being ported, the stops that differ are kept as a baseline (with baseline), and a run fails only where a
    stop outside it differs, the baseline shrinking as stops come to match, so that nothing that matches can break."""
    differing = 0
    for size, stops in python_screens():
        stops = after_the_pdf(stops)
        keys_file = SCREENS / 'keys_{}x{}.txt'.format(*size)
        keys_file.write_text(''.join('\t'.join([','.join(stop['stack']), held_set(stop['set']) if stop['set'] else '', str(stop['dirty']), stop['song'], ','.join(stop['open_before']), *keys_with_stacks(stop)]) + '\n' for stop in stops), encoding='utf-8')
        # The Rust's tour runs in a folder of its own holding the set alone, as the Python's ran, so that the Open page lists
        # the same files; the set is opened as the Python's tour held its path, in that folder or by its name from inside it.
        folder = SCREENS / TOUR_FOLDER
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir()
        shutil.copy(SCREENS / 'tour.yml', folder / 'tour.yml')
        held = stops[0]['path']
        opened = str(folder / 'tour.yml') if held.startswith(FOLDER) else held
        # The MIDI import's picker starts in the home folder, which is the tour's own, as the Python's tour patched it.
        done = subprocess.run([str(RUST), 'screens', opened, str(keys_file), str(size[0]), str(size[1])], capture_output=True, text=True, cwd=folder, env={**os.environ, 'HOME': str(TOUR_HOME)})
        if done.returncode != 0:
            print('{}x{}: the Rust tour failed: {}'.format(*size, done.stderr.strip()[:SHOWN]))
            return 1
        port = json.loads(with_folder_named(done.stdout, folder))
        differing_stops = set()
        pages = {}
        shown = 0
        # The pages the Rust has ported, which it shows as themselves somewhere on the tour; a stop on any other waits.
        ported = {rust_stop['page'] for rust_stop in port}
        for number, (python, rust_stop) in enumerate(zip(stops, port)):
            counts = pages.setdefault(python['page'], [0, 0, 0])
            if rust_stop['page'] == NOT_PORTED_PAGE or python['page'] not in ported:
                counts[2] += 1
                continue
            same = rust_stop['page'] == python['page'] and [pieces(line) for line in python['screen']] == [pieces(line) for line in rust_stop['screen']]
            counts[0 if same else 1] += 1
            if not same:
                differing_stops.add(number)
            if not same and shown < (shown_most or MOST_SCREEN_DIFFERENCES):
                shown += 1
                print(screen_difference(size=size, number=number, python=python, port=rust_stop))
        ported_differ = sum(counts[1] for counts in pages.values())
        waiting = sum(counts[2] for counts in pages.values())
        print('{}x{}: {} of {} stops differ, {} wait on pages not ported yet'.format(*size, ported_differ, len(stops) - waiting, waiting))
        if baseline:
            write_baseline(size, differing_stops)
            print('{}x{}: the {} differing stops kept as the baseline'.format(*size, len(differing_stops)))
            continue
        kept = read_baseline(size)
        if kept is None:
            differing += ported_differ
            continue
        new = sorted(differing_stops - kept)
        write_baseline(size, differing_stops & kept)
        print('{}x{}: {} of the baseline\'s {} still differ, {} newly'.format(*size, len(differing_stops & kept), len(kept), len(new)))
        if new:
            print('  newly differing stops: {}'.format(', '.join(str(number) for number in new[:SHOWN_NEW])))
        differing += len(new)
        for page, (same, different, unported) in pages.items():
            if different:
                print('  {}: {} of {} differ'.format(page, different, same + different))
    return 1 if differing else 0


MOST_SCREEN_DIFFERENCES = 3
# Where the baseline of differing stops is kept, by size, and how many newly differing stops are named.
SCREENS_BASELINE = 'screens_baseline_{}x{}.json'
SHOWN_NEW = 20


def screen_difference(*, size, number, python, port):
    """Return where a stop's screens first differ, the line's text and pieces on each side."""
    if port['page'] != python['page']:
        return '{}x{} stop {}: the Rust shows {}, the Python {}'.format(*size, number, port['page'], python['page'])
    for line, (first, second) in enumerate(zip(python['screen'], port['screen'])):
        if pieces(first) != pieces(second):
            return '{}x{} stop {} ({}, {}) line {}:\n  python: {}\n  rust:   {}'.format(*size, number, python['page'], python['place'], line, pieces(first), pieces(second))
    return '{}x{} stop {}: the screens have {} and {} lines'.format(*size, number, len(python['screen']), len(port['screen']))


def main():
    made = argparse.ArgumentParser(prog='compare_llamatron.py', description='Hold llamatron2 to the Python program.')
    made.add_argument('step', choices=sorted([*STEPS, 'screens']))
    made.add_argument('--only', help='only the sets whose path holds this text')
    made.add_argument('--differences', type=int, help='for screens, how many differing stops to show, three unless given')
    made.add_argument('--baseline', action='store_true', help='for screens, keep the stops that differ now, so that only others fail')
    options = made.parse_args()
    if options.step == 'screens':
        return compare_screens(shown_most=options.differences, baseline=options.baseline)
    found = [*EXAMPLES.rglob('*.yml'), *TEST_SETS.rglob('*.yml')]
    if options.step == 'import':
        found += EXAMPLES.rglob('*.mid')
    sets = sorted(path for path in found if options.only is None or options.only in str(path))
    differing = 0
    skipped = 0
    changed = 0
    waiting = {}
    held = {path: kept_python(options.step, path) for path in sets}
    asked = [path for path in sets if held[path] is not None and held[path] != CHANGED]
    ports = dict(zip(asked, rust_answers(options.step, asked)))
    for path in sets:
        python = held[path]
        if python is None:
            skipped += 1
            continue
        if python == CHANGED:
            changed += 1
            continue
        port = ports[path]
        if isinstance(port, NotPorted):
            waiting[port] = waiting.get(port, 0) + 1
            continue
        same = COMPARED.get(options.step, str.__eq__)(python, port)
        if not same:
            differing += 1
            print('{}: {}'.format(path.relative_to(TOP), first_difference(python, port)))
    ported = len(sets) - skipped - changed - sum(waiting.values())
    if changed:
        print('{} sets changed since the answers were frozen, so have none to be held to'.format(changed))
    print('{} of {} sets differ{}'.format(differing, ported, ', {} skipped as the step does not apply'.format(skipped) if skipped else ''))
    if waiting:
        print('{} sets wait on parts not ported yet:'.format(sum(waiting.values())))
        for what, count in sorted(waiting.items(), key=lambda item: -item[1]):
            print('  {} {}'.format(count, what))
    return 1 if differing else 0


if __name__ == '__main__':
    sys.exit(main())
