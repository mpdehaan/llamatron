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

"""Fetch the public-domain scores the genre library's corpus study reads beyond music21's own (internal_tools/analysis_and_generation/fetch_corpus.sh):
the Humdrum collections KernScores serves, from their maintainers' repositories on GitHub (the user's choice when KernScores was
down), and the research datasets the user allowed (109 A): the Weimar Jazz Database of transcribed solos, the McGill Billboard
chord annotations, de Clercq and Temperley's rock corpus and Google Magenta's Groove MIDI drums; and the popular-music and folk
sources of 113 A: Lakh MIDI's clean subset, the open part of the Enhanced Wikifonia lead sheets, the Public Domain Song
Anthology and the Session's and Nottingham's folk tunes; all into .corpus/, which git ignores, for analysis only: nothing fetched
is committed or passed on, and only measurements leave .corpus/ (the use the EU's text-and-data-mining exceptions and American
fair use cover; each source's terms are noted beside it). Only the files a collection needs are kept, sparing the connection (the user's rule): an archive comes in one download
with its other files dropped, the smaller Humdrum collections a file at a time with a pause between, a database as one file. A
file already fetched isn't fetched again, a download past the size allowed is refused, and no archive member may land outside its
folder. Nothing in the test suite runs this; development only.

    internal_tools/analysis_and_generation/fetch_corpus.sh                 asks category by category, saying each one's size and terms
    internal_tools/analysis_and_generation/fetch_corpus.sh --all           every collection and dataset, without asking
    internal_tools/analysis_and_generation/fetch_corpus.sh joplin essen    the named ones, by their folders
"""

import io
import json
import zipfile
import pathlib
import re
import ssl
import sys
import tarfile
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent / '.corpus'
SCORE_SUFFIX = '.krn'
# The most one download may come to, in bytes, within the user's allowance.
ALLOWED_BYTES = 50 * 1000 * 1000
PAUSE_SECONDS = 0.2
TIMEOUT_SECONDS = 60
# A generic name for the requests, carrying nothing about the person running it.
AGENT = 'llamatron-corpus-fetch'
ARCHIVE = 'archive'
FILES = 'files'
ZIP = 'zip'
SINGLE = 'single'
DATAVERSE = 'dataverse'
MUTOPIA = 'mutopia'
MEGABYTE = 1000 * 1000
DATAVERSE_FILES = '{server}/api/datasets/:persistentId/?persistentId={doi}'
DATAVERSE_FILE = '{server}/api/access/datafile/{id}'
TREE = 'https://api.github.com/repos/{repository}/git/trees/{branch}?recursive=1'
RAW = 'https://raw.githubusercontent.com/{repository}/{branch}/{path}'
TARBALL = 'https://codeload.github.com/{repository}/tar.gz/{branch}'
# Each Humdrum collection on GitHub: its folder under .corpus/, how it comes, its repository and branch.
COLLECTIONS = (
    ('essen', ARCHIVE, 'ccarh/essen-folksong-collection', 'main'),
    ('joplin', FILES, 'craigsapp/joplin', 'main'),
    ('chopin-mazurkas', FILES, 'craigsapp/chopin-mazurkas', 'main'),
    ('haydn-piano-sonatas', FILES, 'craigsapp/haydn-piano-sonatas', 'master'),
    ('mozart-piano-sonatas', FILES, 'craigsapp/mozart-piano-sonatas', 'main'),
    ('beethoven-string-quartets', FILES, 'craigsapp/beethoven-string-quartets', 'main'),
    ('beethoven-piano-sonatas', FILES, 'craigsapp/beethoven-piano-sonatas', 'main'),
    ('bach-chorales', FILES, 'craigsapp/bach-370-chorales', 'main'),
    ('bach-art-of-fugue', FILES, 'craigsapp/art-of-the-fugue', 'main'),
    ('vivaldi-op6', FILES, 'craigsapp/vivaldi-op6', 'main'),
)
# Each research dataset: its folder under .corpus/, how it comes, its address, the endings of the files kept, the most it may come
# to in megabytes, and its terms.
DATASETS = (
    ('weimar-jazz', SINGLE, 'https://jazzomat.hfm-weimar.de/download/downloads/wjazzd.db', ('.db',), 50, 'Open Database License, with credit'),
    ('billboard', ARCHIVE, 'https://www.dropbox.com/s/2lvny9ves8kns4o/billboard-2.0-salami_chords.tar.gz?dl=1', ('.txt',), 5, 'CC0'),
    ('billboard', SINGLE, 'https://www.dropbox.com/s/o0olz0uwl9z9stb/billboard-2.0-index.csv?dl=1', ('.csv',), 1, 'CC0'),
    ('rock-corpus', ZIP, 'https://rockcorpus.midside.com/versions/rock_corpus_v2-1.zip', ('.txt', '.har', '.mel', '.clt', '.nlt', '.csv', '.tsv'), 5, 'CC BY 4.0'),
    ('groove-midi', ZIP, 'https://storage.googleapis.com/magentadata/datasets/groove/groove-v1.0.0-midionly.zip', ('.mid', '.midi', '.csv'), 10, 'CC BY 4.0'),
    ('lakh-clean', ARCHIVE, 'http://hog.ee.columbia.edu/craffel/lmd/clean_midi.tar.gz', ('.mid', '.midi'), 250,
     'CC BY 4.0 for the collection; the songs are copyrighted transcriptions, analysed only'),
    ('openewld', ARCHIVE, 'https://codeload.github.com/00sapo/OpenEWLD/tar.gz/master', ('.mxl', '.xml', '.db', '.csv', '.json'), 10, 'public domain scores, MIT for the rest'),
    ('song-anthology', DATAVERSE, 'https://dataverse.lib.virginia.edu doi:10.18130/V3/C4RD06', ('.xml',), 30, 'CC0, waived by David Berger and Chuck Israels'),
    ('thesession', SINGLE, 'https://raw.githubusercontent.com/adactio/TheSession-data/main/json/tunes.json', ('.json',), 30, 'published openly by the Session for reuse'),
    ('nottingham', ARCHIVE, 'https://codeload.github.com/jukedeck/nottingham-dataset/tar.gz/master', ('.abc',), 5, 'GPL-3.0'),
    ('mutopia', MUTOPIA, 'https://www.mutopiaproject.org/cgibin/make-table.cgi?Composer={composer}&preview=1', ('.mid',), 30,
     'public domain or Creative Commons, piece by piece; MIDI made from the engraved scores'),
    ('maestro', ZIP, 'https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0-midi.zip', ('.mid', '.midi', '.csv', '.json'), 70,
     'CC BY-NC-SA 4.0, non-commercial; piano competition performances'),
)
# The composers sampled from the Mutopia Project, by its codes, across the periods from the Renaissance to early American music,
# and how many pieces of each (120 B): a diverse classical sample of MIDI made from engraved scores.
MUTOPIA_COMPOSERS = ('DowlandJ', 'GesualdoC', 'GibbonsO', 'JanequinC', 'BachJS', 'HandelGF', 'CorelliA', 'CouperinF', 'BuxtehudeD', 'CharpentierMA',
                     'FrobergerJJ', 'HaydnFJ', 'MozartWA', 'BeethovenLv', 'ClementiM', 'DiabelliA', 'ChopinFF', 'SchubertF', 'SchumannR', 'BrahmsJ',
                     'LisztF', 'GriegE', 'DvorakA', 'FaureG', 'FranckC', 'ElgarE', 'BrucknerA', 'MendelssohnFB', 'TchaikovskyPI', 'DebussyC',
                     'SatieE', 'BartokB', 'HolstGT', 'JoplinS', 'FosterSC', 'GottschalkLM', 'SousaJP', 'GiulianiM', 'CarulliF', 'BachCPE')
MUTOPIA_PIECES = 6
MUTOPIA_LINK = 'href="(https://www.mutopiaproject.org/ftp/[^"]+\\.mid)"'
# The most each Humdrum collection comes to, in megabytes, and the terms they share.
COLLECTION_MEGABYTES = {'essen': 35, 'joplin': 1, 'chopin-mazurkas': 1, 'haydn-piano-sonatas': 1, 'mozart-piano-sonatas': 2, 'beethoven-string-quartets': 4,
                        'beethoven-piano-sonatas': 3, 'bach-chorales': 2, 'bach-art-of-fugue': 1, 'vivaldi-op6': 1}
COLLECTION_TERMS = 'public-domain music; the encodings their editors\', for study'
# The sources by category, each with what it is, so that a person chooses what to download: the title, a line about it, and
# the sources' folders.
CATEGORIES = (
    ('Public-domain scores', 'engraved or encoded scores of music out of copyright: rags, mazurkas, sonatas, old songs',
     ('joplin', 'chopin-mazurkas', 'haydn-piano-sonatas', 'mozart-piano-sonatas', 'mutopia', 'song-anthology', 'openewld')),
    ('Public-domain chamber, choral and keyboard scores', 'string quartets, four-part chorales, fugues and concertos, so that the classical corpus is not all piano',
     ('beethoven-string-quartets', 'beethoven-piano-sonatas', 'bach-chorales', 'bach-art-of-fugue', 'vivaldi-op6')),
    ('Folk tunes', 'single-line traditional tunes, many transcribed by players', ('essen', 'thesession', 'nottingham')),
    ('Research annotations', 'experts\' transcriptions and labels: jazz solos, chart songs\' chords, rock harmony, drummers',
     ('weimar-jazz', 'billboard', 'rock-corpus', 'groove-midi')),
    ('Recorded piano performances', 'competition performances as MIDI, for non-commercial use', ('maestro',)),
    ('Popular songs', 'MIDI transcriptions of copyrighted songs, analysed only and never passed on; much the largest download',
     ('lakh-clean',)),
)
EVERYTHING = '--all'
YES = ('y', 'yes')
NO = 'n'
JOIN = ', '
HAVE = 'already here'
HAVE_NOT = 'not here yet'
INTRODUCTION = ('The genre library\'s corpus, downloaded into .corpus/ (which git ignores) for analysis on this computer only.\n'
                'Each category is asked about; a part left out is passed over when the corpus is recalculated.\n')
CATEGORY_HEADING = '{title} (up to {megabytes} MB)'
CATEGORY_ABOUT = '  {about}'
SOURCE_LINE = '  - {name}: up to {megabytes} MB; {terms}; {have}'
QUESTION = '  Fetch these? [y/N] '
NOTHING_CHOSEN = 'nothing chosen, nothing fetched'
NO_SUCH_SOURCE = 'no source called ({names}); the sources: {known}'
WHAT_NEXT = 'next: internal_tools/analysis_and_generation/corpus_tables.sh measures what is here into tables'
FETCHED = '{name}: {count} scores in {folder}'
FETCHED_WITH_TERMS = '{name}: {count} files in {folder} ({terms})'
TOO_BIG = 'refused: the collections would come to {size} bytes, past the {allowed} allowed'


def verifying_context():
    """Return an SSL context that verifies certificates against certifi's bundle when it is installed (music21 brings it), since
    a Python from python.org has no certificate store of its own until its installer's certificate step is run."""
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def opened(url):
    request = urllib.request.Request(url, headers={'User-Agent': AGENT})
    return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=verifying_context())


def is_score(path):
    return path.endswith(SCORE_SUFFIX)


def safe_member_path(name, *, keep_top=False):
    """Return where an archive member goes under its collection's folder, without the archive's top folder unless asked to keep
    it, or None for one that would land outside it, such as an absolute path or one climbing out with '..'."""
    parts = pathlib.PurePosixPath(name).parts[(0 if keep_top else 1):]
    if not parts or name.startswith('/') or '..' in parts or '\\' in name:
        return None
    return pathlib.PurePosixPath(*parts)


def downloaded(url, *, allowed=ALLOWED_BYTES):
    """Return a download's bytes, refusing one past the size allowed."""
    with opened(url) as response:
        data = response.read(allowed + 1)
    if len(data) > allowed:
        raise SystemExit(TOO_BIG.format(size=len(data), allowed=allowed))
    return data


def kept(name, *, endings):
    return name.lower().endswith(endings) and not pathlib.PurePosixPath(name).name.startswith('.')


def fetch_dataverse(*, folder, address, endings, allowed):
    """Fetch the files of a Dataverse dataset whose endings are kept, one at a time with a pause between, skipping any already
    here; address is the server and the dataset's DOI, separated by a space."""
    server, doi = address.split()
    with opened(DATAVERSE_FILES.format(server=server, doi=doi)) as response:
        files = json.load(response)['data']['latestVersion']['files']
    wanted = [entry['dataFile'] for entry in files if kept(entry['dataFile']['filename'], endings=endings)]
    if sum(entry['filesize'] for entry in wanted) > allowed:
        raise SystemExit(TOO_BIG.format(size=sum(entry['filesize'] for entry in wanted), allowed=allowed))
    for entry in wanted:
        target = folder / pathlib.PurePosixPath(entry['filename']).name
        if target.exists():
            continue
        target.write_bytes(downloaded(DATAVERSE_FILE.format(server=server, id=entry['id']), allowed=allowed))
        time.sleep(PAUSE_SECONDS)
    return len(wanted)


def fetch_mutopia(*, folder, address, allowed):
    """Fetch a sample of the Mutopia Project's MIDI files: up to MUTOPIA_PIECES of each composer named, spread through the
    composer's table, a file at a time with a pause between, skipping any already here."""
    count = 0
    total = 0
    for composer in MUTOPIA_COMPOSERS:
        with opened(address.format(composer=composer)) as response:
            page = response.read().decode(errors='replace')
        links = list(dict.fromkeys(re.findall(MUTOPIA_LINK, page)))
        step = max(1, len(links) // MUTOPIA_PIECES)
        for link in links[::step][:MUTOPIA_PIECES]:
            target = folder / composer / pathlib.PurePosixPath(link).name
            if not target.exists():
                try:
                    data = downloaded(link, allowed=allowed)
                except urllib.error.HTTPError:
                    continue
                total += len(data)
                if total > allowed:
                    raise SystemExit(TOO_BIG.format(size=total, allowed=allowed))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                time.sleep(PAUSE_SECONDS)
            count += 1
        time.sleep(PAUSE_SECONDS)
    return count


def fetch_dataset(*, folder, kind, url, endings, allowed=ALLOWED_BYTES):
    """Fetch one research dataset: a single file saved under its own name, the kept files of a Dataverse dataset, or an archive
    with only the files whose endings are kept, each member's path checked."""
    if kind == DATAVERSE:
        return fetch_dataverse(folder=folder, address=url, endings=endings, allowed=allowed)
    if kind == MUTOPIA:
        return fetch_mutopia(folder=folder, address=url, allowed=allowed)
    if kind == SINGLE:
        target = folder / pathlib.PurePosixPath(url.split('?')[0]).name
        if not target.exists():
            target.write_bytes(downloaded(url, allowed=allowed))
        return 1
    if any(folder.iterdir()):
        return sum(1 for path in folder.rglob('*') if path.is_file() and kept(path.name, endings=endings))
    data = downloaded(url, allowed=allowed)
    count = 0
    if kind == ZIP:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                place = safe_member_path(member.filename, keep_top=True)
                if place is None or member.is_dir() or not kept(member.filename, endings=endings):
                    continue
                target = folder / place
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(member))
                count += 1
        return count
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for member in archive.getmembers():
            place = safe_member_path(member.name, keep_top=True)
            if place is None or not member.isfile() or not kept(member.name, endings=endings):
                continue
            target = folder / place
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
            count += 1
    return count


def fetch_archive(*, folder, repository, branch):
    """Fetch a collection as one archive and keep only its score files, refusing any member that isn't a plain file."""
    data = downloaded(TARBALL.format(repository=repository, branch=branch))
    count = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for member in archive.getmembers():
            place = safe_member_path(member.name)
            if place is None or not member.isfile() or not is_score(member.name):
                continue
            target = folder / place
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
            count += 1
    return count


def fetch_files(*, folder, repository, branch):
    """Fetch a collection's score files one at a time, pausing between, skipping any already here."""
    with opened(TREE.format(repository=repository, branch=branch)) as response:
        tree = json.load(response)['tree']
    scores = [entry for entry in tree if entry['type'] == 'blob' and is_score(entry['path']) and safe_member_path('top/' + entry['path']) is not None]
    if sum(entry.get('size', 0) for entry in scores) > ALLOWED_BYTES:
        raise SystemExit(TOO_BIG.format(size=sum(entry.get('size', 0) for entry in scores), allowed=ALLOWED_BYTES))
    for entry in scores:
        target = folder / entry['path']
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with opened(RAW.format(repository=repository, branch=branch, path=entry['path'])) as response:
            target.write_bytes(response.read())
        time.sleep(PAUSE_SECONDS)
    return len(scores)


def megabytes_of(name):
    """Return the most a source may come to, in megabytes."""
    return COLLECTION_MEGABYTES.get(name) or sum(megabytes for dataset, _, _, _, megabytes, _ in DATASETS if dataset == name)


def terms_of(name):
    """Return a source's terms in a few words."""
    return next((terms for dataset, _, _, _, _, terms in DATASETS if dataset == name), COLLECTION_TERMS)


def every_name():
    return tuple(dict.fromkeys([name for name, _, _, _ in COLLECTIONS] + [name for name, _, _, _, _, _ in DATASETS]))


def asked(*, ask=input, say=print):
    """Return the sources a person chooses, category by category: each category is described, with its sources, their sizes
    and their terms, and fetched only on a yes; no answer at all, as when nobody is there to ask, is a no."""
    chosen = []
    for title, about, names in CATEGORIES:
        say(CATEGORY_HEADING.format(title=title, megabytes=sum(megabytes_of(name) for name in names)))
        say(CATEGORY_ABOUT.format(about=about))
        for name in names:
            say(SOURCE_LINE.format(name=name, megabytes=megabytes_of(name), terms=terms_of(name),
                                   have=HAVE if (ROOT / name).is_dir() and any((ROOT / name).iterdir()) else HAVE_NOT))
        try:
            answer = ask(QUESTION)
        except EOFError:
            answer = NO
        if answer.strip().lower() in YES:
            chosen += names
    return chosen


def fetch_named(wanted):
    """Fetch the named sources, each into its folder under .corpus/."""
    for name, kind, repository, branch in COLLECTIONS:
        if name not in wanted:
            continue
        folder = ROOT / name
        folder.mkdir(parents=True, exist_ok=True)
        fetch = fetch_archive if kind == ARCHIVE else fetch_files
        count = fetch(folder=folder, repository=repository, branch=branch)
        print(FETCHED.format(name=name, count=count, folder=folder))
    for name, kind, url, endings, megabytes, terms in DATASETS:
        if name not in wanted:
            continue
        folder = ROOT / name
        folder.mkdir(parents=True, exist_ok=True)
        count = fetch_dataset(folder=folder, kind=kind, url=url, endings=endings, allowed=megabytes * MEGABYTE)
        print(FETCHED_WITH_TERMS.format(name=name, count=count, folder=folder, terms=terms))


def main(*, argv=None):
    arguments = list(argv if argv is not None else sys.argv[1:])
    if EVERYTHING in arguments:
        wanted = every_name()
    elif arguments:
        unknown = [name for name in arguments if name not in every_name()]
        if unknown:
            raise SystemExit(NO_SUCH_SOURCE.format(names=JOIN.join(unknown), known=JOIN.join(every_name())))
        wanted = arguments
    else:
        print(INTRODUCTION)
        wanted = asked()
    if not wanted:
        print(NOTHING_CHOSEN)
        return 0
    fetch_named(set(wanted))
    print(WHAT_NEXT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
