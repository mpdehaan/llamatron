#!/usr/bin/env python3
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

"""Print one line per example set: how long it plays, its scenes and tracks, and which of a few features it uses.

    .venv/bin/python internal_tools/demo_summary.py                          # every set in examples/, as a plain table
    .venv/bin/python internal_tools/demo_summary.py --format ascii           # the same with ruled rows and borders
    .venv/bin/python internal_tools/demo_summary.py --format markdown        # the same as a Markdown table
    .venv/bin/python internal_tools/demo_summary.py examples/learning/19_hocket_shanty.yml   # only the sets named
    .venv/bin/python internal_tools/demo_summary.py --write-docs             # put the Markdown table into docs/DEMOS.md
    .venv/bin/python internal_tools/demo_summary.py --check                  # fail if the table in docs/DEMOS.md is out of date
    .venv/bin/python internal_tools/demo_summary.py --csv                    # comma-separated values (sh user_scripts/demo_report.sh)
    internal_tools/demo_summary.sh

A table with a row per set and a column each for what it plays (the set's description), the length when
played (every song of the set added up), the scenes, the tracks, and then one column per feature in FEATURE_COLUMNS, with a
check mark where the set uses it and nothing where it doesn't. The features come from
internal_tools/demo_features.py, which knows how to tell each one from a set's data, so a column here is a
heading and the names of one or more of that tool's features; add a column by adding a line to
FEATURE_COLUMNS. internal_tools/demo_features.py is the long form, every feature by every set. The Markdown
table sits between a pair of marker comments in docs/DEMOS.md, where --write-docs replaces it
and test/test_demo_summary.py checks it is current, so that readers see what each demo shows.
"""

import argparse
import csv
import io
import re
import importlib.util
import pathlib
import sys

from llamatron.tui.document import Document
from llamatron.tui.text import clock
from llamatron.support.example_sets import example_sets
from llamatron.support.safe_yaml import load_safely
from llamatron.composition.setlist import file_stem

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMOS_DOCUMENT = ROOT / 'docs' / 'DEMOS.md'
FEATURES_SCRIPT = ROOT / 'internal_tools' / 'demo_features.py'
FEATURES_MODULE = 'demo_features'
# Each feature column: its heading, and the features of demo_features.FEATURES any one of which marks it.
# They are the features a song doesn't always use, the user's choice of 2026-11-11, so that the table says what is special about each set.
# The examples' videos on YouTube, and the column of the list that links them.
VIDEOS = ROOT / 'internal_tools' / 'demo_videos.yml'
NOTHING = ''
APOSTROPHE = "'"
STAR = '*'
FEATURE_COLUMNS = [
    ('chords', ['chords']),
    ('arps', ['arps']),
    ('ratchets', ['ratchets', 'ratchet offsets', 'AutoRatchets']),
    ('chains', ['chains']),
    ('grabs', ['grab steps', 'grab track']),
    ('hocket', ['hockets']),
    ('morphs', ['morphs']),
    ('directions', ['pattern direction', 'clip direction']),
    ('ties', ['ties']),
    ('probability', ['probability']),
    ('grooves', ['song groove', 'scene groove', 'track groove', 'own grooves']),
    ('key changes', ['scene scale', 'clip scale']),
    ('tempo changes', ['scene tempo', 'tempo ramps']),
    ('CCs', ['CC rows', 'slides', 'track CC numbers']),
    ('registers', ['register note rows', 'register velocity rows', 'register adds', 'register sets', 'register resets', 'registers section']),
    ('conditions', ['conditions']),
    ('binding', ['register binding']),
    ('shapes', ['clip shapes', 'scene shapes', 'Densities', 'Swells', 'Articulates']),
    ('progressions', ['progressions', 'voice leadings', 'inversions']),
    ('strum', ['strums']),
    ('euclid', ['euclids']),
    ('feel', ['glides', 'shortens', 'rushes', 'drags']),
]
SET_HEADING = 'set'
DESCRIPTION_HEADING = 'plays'
GENRE_HEADING = 'genre'
# The table of the pages of demos on docs/DEMOS.md: each page and how many demos it describes.
PAGE_HEADING = 'page'
DEMOS_HEADING = 'demos'
TUTORIAL_TITLE = 'Tutorial Demos'
# Between a set's songs' genres, when they differ.
GENRE_JOIN = ', '
LENGTH_HEADING = 'length'
SCENES_HEADING = 'scenes'
TRACKS_HEADING = 'tracks'
# The columns before the features: the set's name and what it plays at the left of their columns, the numbers at the right. A feature's mark is centered.
LEFT_HEADINGS = [SET_HEADING, GENRE_HEADING, DESCRIPTION_HEADING]
NUMBER_HEADINGS = [LENGTH_HEADING, SCENES_HEADING, TRACKS_HEADING]
USED = '✓'
UNUSED = ''
SET_WIDTH = 16

FORMAT_PLAIN = 'plain'
FORMAT_ASCII = 'ascii'
FORMAT_MARKDOWN = 'markdown'
FORMATS = [FORMAT_PLAIN, FORMAT_ASCII, FORMAT_MARKDOWN]
CSV_LINE_END = '\n'
COLUMN_GAP = '  '
RULE = '-'
# The bordered table's corners and edges, and how a Markdown table is ruled and aligned.
CORNER = '+'
EDGE = '|'
MARKDOWN_RULE = '---'
MARKDOWN_RIGHT = '---:'
MARKDOWN_CENTER = ':---:'
MARKDOWN_CELL = ' {cell} '
LINE_BREAK = '\n'
FILE_ENCODING = 'utf-8'
# The marker comments each table sits between in docs/DEMOS.md, the list of the examples and the table of what each uses, and only the text between them is replaced.
MARKER_START = '<!-- generated by internal_tools/demo_summary.py -->'
MARKER_END = '<!-- end of the generated table -->'
# The pages of demos, one for each genre, the user's design, and the marker comments around each demo's summary on its page.
DEMO_PAGES = ROOT / 'docs' / 'demos'
DEMO_PAGE_LINK = 'demos/{page}'
SUMMARY_START = '<!-- generated by internal_tools/demo_summary.py: about {stem} -->'
SUMMARY_END = '<!-- end of the generated summary of {stem} -->'
PAGE_SUFFIX = '.md'
NOT_A_NAME_CHARACTER = r'[^A-Za-z0-9]+'
NAME_JOIN = '_'
NO_GENRE = 'Other'
# Each demo's file links to the file on GitHub, so that people can read how the set file says it, then its starting key
# and tempo, the first scene's or else the song's, and its length, the user's design.
FACTS_LINE = '[`{path}`]({link}) · {key} · {tempo} BPM · {length} · {scenes} scenes · {tracks} tracks'
GITHUB_FILE = 'https://github.com/mpdehaan/llamatron/blob/main/{path}'
KEY_TEXT = '{root} {kind}'
NO_KEY = 'no key'
KIND_WORD_JOIN = '_'
KIND_WORD_SPACE = ' '
FACTS_VIDEO = ' · [▶ watch the video]({url})'
NO_FEATURES = 'It uses no feature beyond patterns, tracks and scenes.'
SET_LINK = '[{name}]({link})'
MSG_NO_SECTION = 'no section for {stem} in docs/demos/{page}: add one, with a heading, a description and the markers {start} and {end}'
# Each page of demos keeps its sections sorted by the demo's name without its learning number, with a linked index of
# them at the top, and the Tutorial Demos page holds the learning demos' sections again in their numbered order, the
# user's design. A section is a heading naming the demo's file, its description, and its generated summary.
SECTION_HEADING = re.compile(r'^## (?P<title>.+): `(?P<file>[^`]+\.yml)`$', re.MULTILINE)
LEARNING_NUMBER = re.compile(r'^\d+_')
SET_SUFFIX = '.yml'
ANCHOR = '<a id="{name}"></a>'
ANCHOR_LINE = re.compile(r'^<a id="[^"]+"></a>\n', re.MULTILINE)
INDEX_START = '<!-- generated by internal_tools/demo_summary.py: the index of this page -->'
INDEX_END = '<!-- end of the generated index -->'
INDEX_LINE = '- [{title}](#{name}): `{file}`'
SUMMARY_MARKER_LINE = re.compile(r'^<!-- (generated by internal_tools/demo_summary.py: about|end of the generated summary of) .* -->\n', re.MULTILINE)
TUTORIAL_PAGE = 'TUTORIAL.md'
TUTORIAL_INTRO = """# Tutorial Demos

The demos in `examples/learning/`, in the order to learn them, each teaching one feature a scene at a time. Each is described again on its genre's page; [About Demos](../DEMOS.md) lists every page of demos.
"""
LEARNING = 'learning'
# The pages made of one folder's demos, the user's design: examples/other's, listed last among the pages of demos; the
# Tutorial Demos page is the learning folder's, in its numbered order.
OTHER = 'other'
OTHER_PAGE = 'OTHER.md'
OTHER_TITLE = 'Other'
OTHER_INTRO = """# Other

The demos in `examples/other/`, which fit no other folder. Each is described again on its genre's page; [About Demos](../DEMOS.md) lists every page of demos.
"""
FOLDER_PAGES = (TUTORIAL_PAGE, OTHER_PAGE)
PARAGRAPH = '\n\n'
LINE = '\n'
OPTION_FORMAT = '--format'
OPTION_CSV = '--csv'
OPTION_WRITE_DOCS = '--write-docs'
OPTION_CHECK = '--check'
MSG_NO_MARKER = 'no marker ({marker}) in {path}'
MSG_UP_TO_DATE = 'the table in {path} is current'
MSG_OUT_OF_DATE = 'the table in {path} is out of date: run internal_tools/demo_summary.py --write-docs'
MSG_WRITTEN = 'wrote the table in {path}'
SUCCESS = 0
FAILURE = 1


def load_features():
    """Load internal_tools/demo_features.py as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(FEATURES_MODULE, FEATURES_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unknown_features(features):
    """Return the names FEATURE_COLUMNS use that demo_features doesn't define, so that a renamed feature can't fall silent."""
    known = {name for name, _ in features.FEATURES}
    return [name for _, names in FEATURE_COLUMNS for name in names if name not in known]


def played_seconds(document):
    """Return how long every song of the set plays, added up, or None if any can't be worked out."""
    total = 0
    for name in document.setlist().get_song_names():
        document.select_song(name)
        seconds = document.lengths().song_seconds()
        if seconds is None:
            return None
        total += seconds
    return total


def summary_row(*, path, features):
    """Return one set's cells, as text, in the order of the headings."""
    document = Document.load(path)
    setlist = document.setlist()
    used = features.features_used(path)
    cells = [
        features.short_name(path),
        GENRE_JOIN.join(setlist.get_genres()),
        setlist.get_description(),
        clock(played_seconds(document)),
        str(sum(len(setlist.get_song(name).get_scenes()) for name in setlist.get_song_names())),
        str(sum(len(setlist.get_song(name).get_track_names()) for name in setlist.get_song_names())),
    ]
    cells.extend(USED if any(name in used for name in names) else UNUSED for _, names in FEATURE_COLUMNS)
    return cells


def headings():
    return LEFT_HEADINGS + NUMBER_HEADINGS + [heading for heading, _ in FEATURE_COLUMNS]


def widths(rows):
    """Return each column's width: its widest cell or heading, and at least SET_WIDTH for the set's name."""
    return [max(len(head), *(len(row[place]) for row in rows), SET_WIDTH if place == 0 else 0) for place, head in enumerate(headings())]


def aligned(*, cells, widths):
    """Return the cells padded to their columns: the set's name and what it plays at the left, the numbers at the right and the marks centered."""
    padded = []
    for place, (cell, width) in enumerate(zip(cells, widths)):
        if headings()[place] in LEFT_HEADINGS:
            padded.append(cell.ljust(width))
        elif headings()[place] in NUMBER_HEADINGS:
            padded.append(cell.rjust(width))
        else:
            padded.append(cell.center(width))
    return padded


def plain_table(rows):
    """Return the lines of the plain table: the headings, a rule, and a row per set."""
    sizes = widths(rows)
    lines = [COLUMN_GAP.join(aligned(cells=headings(), widths=sizes)), COLUMN_GAP.join(RULE * width for width in sizes)]
    lines.extend(COLUMN_GAP.join(aligned(cells=row, widths=sizes)) for row in rows)
    return [line.rstrip() for line in lines]


def ascii_table(rows):
    """Return the lines of the bordered table: a rule of corners and dashes above, between and below the rows, and edges between the cells."""
    sizes = widths(rows)
    rule = CORNER + CORNER.join(RULE * (width + 2) for width in sizes) + CORNER
    lines = [rule, bordered(cells=headings(), widths=sizes), rule]
    for row in rows:
        lines.append(bordered(cells=row, widths=sizes))
        lines.append(rule)
    return lines


def bordered(*, cells, widths):
    return EDGE + EDGE.join(MARKDOWN_CELL.format(cell=cell) for cell in aligned(cells=cells, widths=widths)) + EDGE


def markdown_table(rows):
    """Return the lines of the Markdown table, aligned as the plain one is through its rule of colons."""
    alignments = [MARKDOWN_RULE if heading in LEFT_HEADINGS else MARKDOWN_RIGHT if heading in NUMBER_HEADINGS else MARKDOWN_CENTER for heading in headings()]
    lines = [markdown_line(headings()), markdown_line(alignments)]
    lines.extend(markdown_line(row) for row in rows)
    return lines


def markdown_line(cells):
    return EDGE + EDGE.join(MARKDOWN_CELL.format(cell=cell) for cell in cells) + EDGE


def csv_lines(*, headings, rows):
    """Return a table as lines of comma-separated values, the headings first, for a spreadsheet or another program."""
    held = io.StringIO()
    writer = csv.writer(held, lineterminator=CSV_LINE_END)
    writer.writerow(headings)
    writer.writerows(rows)
    return held.getvalue().splitlines()


TABLES = {FORMAT_PLAIN: plain_table, FORMAT_ASCII: ascii_table, FORMAT_MARKDOWN: markdown_table}


def rows_for(*, paths, features):
    return [summary_row(path=path, features=features) for path in paths]


def with_table(*, text, table, start=MARKER_START, end=MARKER_END):
    """Return the document's text with the table between a pair of markers replaced."""
    if start not in text or end not in text[text.index(start):]:
        raise SystemExit(MSG_NO_MARKER.format(marker=start, path=DEMOS_DOCUMENT.relative_to(ROOT)))
    head = text[:text.index(start) + len(start)]
    tail = text[text.index(end, len(head)):]
    return head + LINE_BREAK + LINE_BREAK.join(table) + LINE_BREAK + tail


def videos(*, path=None):
    """Return the YouTube link of each example that has a video, by its file stem, from internal_tools/demo_videos.yml."""
    with open(VIDEOS if path is None else path, encoding=FILE_ENCODING) as file:
        return load_safely(file) or {}


def genre_of(path):
    """Return the genre a set's page of demos is named after: its first song's genre, or NO_GENRE."""
    genres = Document.load(path).setlist().get_genres()
    return genres[0] if genres else NO_GENRE


def genre_page(genre):
    """Return the file name of a genre's page of demos, such as HIP_HOP.md for Hip hop."""
    return re.sub(NOT_A_NAME_CHARACTER, NAME_JOIN, genre.replace(APOSTROPHE, NOTHING)).strip(NAME_JOIN).upper() + PAGE_SUFFIX


def feature_table(cells):
    """Return a one-row Markdown table of the features a set's cells mark as used, or a sentence when it uses none."""
    used = [heading for (heading, _), cell in zip(FEATURE_COLUMNS, cells[len(LEFT_HEADINGS) + len(NUMBER_HEADINGS):]) if cell == USED]
    if not used:
        return [NO_FEATURES]
    return [markdown_line(used), markdown_line([MARKDOWN_CENTER] * len(used)), markdown_line([USED] * len(used))]


def starting_key_and_tempo(path):
    """Return the key a set's first song starts in, as its root and scale type, and its tempo there: the first scene's own, or else the song's."""
    song = Document.load(path).song()
    scenes = song.get_scenes()
    first = scenes[0] if scenes else None
    scale_name = (first.get_scale_name() if first else None) or song.get_scale_name()
    tempo = (first.get_tempo(0) if first else None) or song.get_tempo()
    if scale_name is None:
        return NO_KEY, tempo
    scale = song.get_named_scale(scale_name)
    return KEY_TEXT.format(root=scale.get_root(), kind=scale.get_kind().replace(KIND_WORD_JOIN, KIND_WORD_SPACE)), tempo


def demo_summary(*, path, cells, links):
    """Return the lines of one demo's summary on its genre's page: its file, starting key and tempo, length, scenes, tracks and video, then the features it uses."""
    _, _, _, length, scenes, tracks = cells[:len(LEFT_HEADINGS) + len(NUMBER_HEADINGS)]
    shown = pathlib.Path(path).as_posix()
    key, tempo = starting_key_and_tempo(path)
    facts = FACTS_LINE.format(path=shown, link=GITHUB_FILE.format(path=shown), key=key, tempo=tempo, length=length, scenes=scenes, tracks=tracks)
    if file_stem(path) in links:
        facts += FACTS_VIDEO.format(url=links[file_stem(path)])
    return [facts, NOTHING, *feature_table(cells)]


def index_lines(*, paths):
    """Return the table of the pages that describe the demos, the user's design: the Tutorial Demos page first, then each genre's page with how many demos it describes, each linked; no demo is listed here, since each page lists its own."""
    genres = {}
    for path in paths:
        genres.setdefault(genre_of(path), []).append(path)
    lines = [markdown_line([PAGE_HEADING, DEMOS_HEADING]), markdown_line([MARKDOWN_RULE, MARKDOWN_RIGHT]),
             folder_line(title=TUTORIAL_TITLE, page=TUTORIAL_PAGE, paths=in_folder(paths=paths, folder=LEARNING))]
    for genre in sorted(genres, key=str.lower):
        link = DEMO_PAGE_LINK.format(page=genre_page(genre))
        lines.append(markdown_line([SET_LINK.format(name=genre, link=link), str(len(genres[genre]))]))
    lines.append(folder_line(title=OTHER_TITLE, page=OTHER_PAGE, paths=in_folder(paths=paths, folder=OTHER)))
    return lines


def in_folder(*, paths, folder):
    """Return the examples in one folder of examples/, in the order given."""
    return [path for path in paths if pathlib.Path(path).parent.name == folder]


def folder_line(*, title, page, paths):
    """Return the row of the table of pages for a page made of one folder's demos, with how many it holds."""
    return markdown_line([SET_LINK.format(name=title, link=DEMO_PAGE_LINK.format(page=page)), str(len(paths))])


def with_summaries(*, texts, paths, rows, links):
    """Return each genre page's text with every demo's summary written between its markers, and the problems: each demo whose page lacks its section."""
    problems = []
    for path, row in zip(paths, rows):
        page = genre_page(genre_of(path))
        start = SUMMARY_START.format(stem=file_stem(path))
        end = SUMMARY_END.format(stem=file_stem(path))
        text = texts.get(page, NOTHING)
        if start not in text or end not in text[text.index(start):]:
            problems.append(MSG_NO_SECTION.format(stem=file_stem(path), page=page, start=start, end=end))
            continue
        texts[page] = with_table(text=text, table=demo_summary(path=path, cells=row, links=links), start=start, end=end)
    return texts, problems


def bare_name(file_name):
    """Return a demo's name without its learning number or suffix, such as blues_chords for 08_blues_chords.yml, which sorts the genre pages and names each section's anchor."""
    return LEARNING_NUMBER.sub(NOTHING, file_name.removesuffix(SET_SUFFIX))


def page_parts(text):
    """Return a page of demos as its introduction, without its generated index, and its sections, each from its heading to the next, without their anchors."""
    text = ANCHOR_LINE.sub(NOTHING, text)
    if INDEX_START in text:
        before, _, after = text.partition(INDEX_START)
        text = before + after.partition(INDEX_END)[2]
    starts = [found.start() for found in SECTION_HEADING.finditer(text)]
    if not starts:
        return text.rstrip(), []
    ends = starts[1:] + [len(text)]
    return text[:starts[0]].rstrip(), [text[start:end].strip() for start, end in zip(starts, ends)]


def section_file(section):
    """Return the file a section's heading names."""
    return SECTION_HEADING.match(section).group('file')


def page_index(sections):
    """Return the linked index of a page's sections, one line each, between its markers."""
    lines = [INDEX_LINE.format(title=found.group('title'), name=bare_name(found.group('file')), file=found.group('file'))
             for found in (SECTION_HEADING.match(section) for section in sections)]
    return LINE.join([INDEX_START, *lines, INDEX_END])


def page_text(*, intro, sections):
    """Return a page of demos from its introduction and its sections in order, with the index after the introduction and an anchor before each section."""
    anchored = [ANCHOR.format(name=bare_name(section_file(section))) + LINE + section for section in sections]
    return PARAGRAPH.join([intro, page_index(sections), *anchored]) + LINE


def sorted_page(text):
    """Return a genre page with its sections sorted by each demo's name without its learning number, and its index made again."""
    intro, sections = page_parts(text)
    if not sections:
        return text
    return page_text(intro=intro, sections=sorted(sections, key=lambda section: bare_name(section_file(section))))


def folder_page(*, texts, paths, folder, intro, in_order=False):
    """Return a page made of one folder's demos: each one's section, copied from its genre page without the summary's markers,
    in the order given (the Tutorial Demos page's numbered order) or else by the demo's name."""
    sections = {}
    for page, text in texts.items():
        if page not in FOLDER_PAGES:
            for section in page_parts(text)[1]:
                sections[section_file(section)] = SUMMARY_MARKER_LINE.sub(NOTHING, section)
    names = [pathlib.Path(path).name for path in in_folder(paths=paths, folder=folder)]
    if not in_order:
        names = sorted(names, key=bare_name)
    ordered = [sections[name] for name in names if name in sections]
    return page_text(intro=intro.rstrip(), sections=ordered)


def tutorial_page(*, texts, paths):
    """Return the Tutorial Demos page: the learning demos, in the numbered order."""
    return folder_page(texts=texts, paths=paths, folder=LEARNING, intro=TUTORIAL_INTRO, in_order=True)


def write_docs(*, features, check_only):
    """Put the index of every example into docs/DEMOS.md and each demo's summary onto its genre's page in docs/demos/, or with check_only say whether they are current. Return the exit code."""
    paths = example_sets()
    rows = rows_for(paths=paths, features=features)
    links = videos()
    text = DEMOS_DOCUMENT.read_text(encoding=FILE_ENCODING)
    updated = with_table(text=text, table=index_lines(paths=paths))
    pages = {path.name: path.read_text(encoding=FILE_ENCODING) for path in DEMO_PAGES.glob(STAR + PAGE_SUFFIX)}
    written, problems = with_summaries(texts=dict(pages), paths=paths, rows=rows, links=links)
    written = {name: page if name in FOLDER_PAGES else sorted_page(page) for name, page in written.items()}
    written[TUTORIAL_PAGE] = tutorial_page(texts=written, paths=paths)
    written[OTHER_PAGE] = folder_page(texts=written, paths=paths, folder=OTHER, intro=OTHER_INTRO)
    for problem in problems:
        print(problem, file=sys.stderr)
    shown = DEMOS_DOCUMENT.relative_to(ROOT)
    changed = updated != text or written != pages
    if problems:
        return FAILURE
    if not changed:
        print(MSG_UP_TO_DATE.format(path=shown))
        return SUCCESS
    if check_only:
        print(MSG_OUT_OF_DATE.format(path=shown))
        return FAILURE
    DEMOS_DOCUMENT.write_text(updated, encoding=FILE_ENCODING)
    for name, page_text in written.items():
        if page_text != pages.get(name):
            (DEMO_PAGES / name).write_text(page_text, encoding=FILE_ENCODING)
    print(MSG_WRITTEN.format(path=shown))
    return SUCCESS


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('paths', nargs='*', help='the sets to summarize; with none, every set in examples/')
    parser.add_argument(OPTION_FORMAT, choices=FORMATS, default=FORMAT_PLAIN, help='how the table is drawn')
    parser.add_argument(OPTION_CSV, action='store_true', help='print comma-separated values, for a spreadsheet or another program')
    parser.add_argument(OPTION_WRITE_DOCS, action='store_true', help='write the Markdown table of every example into docs/DEMOS.md instead of printing')
    parser.add_argument(OPTION_CHECK, action='store_true', help='fail if the table in docs/DEMOS.md is out of date, without writing')
    arguments = parser.parse_args(argv)
    features = load_features()
    unknown = unknown_features(features)
    if unknown:
        raise ValueError(unknown)
    if arguments.write_docs or arguments.check:
        return write_docs(features=features, check_only=arguments.check)
    paths = arguments.paths or example_sets()
    rows = rows_for(paths=paths, features=features)
    for line in csv_lines(headings=headings(), rows=rows) if arguments.csv else TABLES[arguments.format](rows):
        print(line)
    return SUCCESS


if __name__ == '__main__':
    sys.exit(main(argv=sys.argv[1:]))
