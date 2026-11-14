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

"""Every source the corpus reads: where it lives under .corpus/, what kind of music data it holds, how far it can be trusted, and
its terms, so that a generator can use only knowledge whose sources allow what the person intends and print the credits owed."""

from dataclasses import dataclass


class Kind:
    """What a source's pieces hold."""

    SCORE = 'score'
    SOLO = 'transcribed solo'
    LEAD_SHEET = 'lead sheet'
    TUNE = 'folk tune'
    ARRANGEMENT = 'MIDI arrangement'
    CHORDS = 'chord annotation'
    DRUMS = 'performed drums'


class Quality:
    """How far a source's data can be trusted: edited by scholars, annotated by experts, or made by many hands of uneven care."""

    SCHOLARLY = 'scholarly edition'
    EXPERT = 'expert annotation'
    PERFORMED = 'recorded performance'
    CROWD = 'made by many hands'


@dataclass(slots=True, kw_only=True, frozen=True)
class Terms:
    """A source's license as it bears on what is made from it: whether commercial use is allowed, whether attribution is owed,
    whether derived data must be shared alike, the license's name, and the credit to print."""

    name: str
    commercial: bool
    attribution: bool
    share_alike: bool
    credit: str


@dataclass(slots=True, kw_only=True, frozen=True)
class Source:
    """One source: its name, its folder under .corpus/, its kind, its quality, its terms, and the library style its pieces are
    compared with when they share one."""

    name: str
    folder: str
    kind: str
    quality: str
    terms: Terms
    style: str = None


PUBLIC_DOMAIN = Terms(name='public domain or CC0', commercial=True, attribution=False, share_alike=False, credit='')
CCARH = Terms(name="CCARH's personal-use terms", commercial=False, attribution=True, share_alike=False,
              credit='Essen Folksong Collection, Center for Computer Assisted Research in the Humanities')
UNSTATED = Terms(name='no license stated; the music is public domain, the encoding its editor\'s', commercial=False, attribution=True, share_alike=False,
                 credit='Humdrum encoding by Craig Stuart Sapp')

SOURCES = (
    Source(name='essen', folder='essen', kind=Kind.TUNE, quality=Quality.SCHOLARLY, terms=CCARH),
    Source(name='joplin', folder='joplin', kind=Kind.SCORE, quality=Quality.SCHOLARLY, terms=UNSTATED),
    Source(name='chopin-mazurkas', folder='chopin-mazurkas', kind=Kind.SCORE, quality=Quality.SCHOLARLY, terms=UNSTATED),
    Source(name='haydn-piano-sonatas', folder='haydn-piano-sonatas', kind=Kind.SCORE, quality=Quality.SCHOLARLY, terms=UNSTATED),
    Source(name='mozart-piano-sonatas', folder='mozart-piano-sonatas', kind=Kind.SCORE, quality=Quality.SCHOLARLY, terms=UNSTATED),
    Source(name='beethoven-string-quartets', folder='beethoven-string-quartets', kind=Kind.SCORE, quality=Quality.SCHOLARLY, terms=UNSTATED),
    Source(name='beethoven-piano-sonatas', folder='beethoven-piano-sonatas', kind=Kind.SCORE, quality=Quality.SCHOLARLY, terms=UNSTATED),
    Source(name='bach-chorales', folder='bach-chorales', kind=Kind.SCORE, quality=Quality.SCHOLARLY,
           terms=Terms(name='CC BY-NC-SA 4.0', commercial=False, attribution=True, share_alike=True, credit='370 Chorales by J. S. Bach, edited by Craig Stuart Sapp')),
    Source(name='bach-art-of-fugue', folder='bach-art-of-fugue', kind=Kind.SCORE, quality=Quality.SCHOLARLY, terms=UNSTATED),
    Source(name='vivaldi-op6', folder='vivaldi-op6', kind=Kind.SCORE, quality=Quality.SCHOLARLY, terms=UNSTATED),
    Source(name='weimar-jazz', folder='weimar-jazz', kind=Kind.SOLO, quality=Quality.EXPERT,
           terms=Terms(name='Open Database License', commercial=True, attribution=True, share_alike=True, credit='Weimar Jazz Database, the Jazzomat Research Project')),
    Source(name='billboard', folder='billboard', kind=Kind.CHORDS, quality=Quality.EXPERT, terms=PUBLIC_DOMAIN),
    Source(name='rock-corpus', folder='rock-corpus', kind=Kind.CHORDS, quality=Quality.EXPERT,
           terms=Terms(name='CC BY 4.0', commercial=True, attribution=True, share_alike=False, credit='Rock corpus, Trevor de Clercq and David Temperley')),
    Source(name='groove-midi', folder='groove-midi', kind=Kind.DRUMS, quality=Quality.PERFORMED,
           terms=Terms(name='CC BY 4.0', commercial=True, attribution=True, share_alike=False, credit='Groove MIDI Dataset, Google Magenta')),
    Source(name='lakh-clean', folder='lakh-clean', kind=Kind.ARRANGEMENT, quality=Quality.CROWD,
           terms=Terms(name='CC BY 4.0 for the collection; the songs are copyrighted', commercial=False, attribution=True, share_alike=False,
                       credit='Lakh MIDI Dataset, Colin Raffel')),
    Source(name='openewld', folder='openewld', kind=Kind.LEAD_SHEET, quality=Quality.CROWD, terms=PUBLIC_DOMAIN),
    Source(name='song-anthology', folder='song-anthology', kind=Kind.LEAD_SHEET, quality=Quality.SCHOLARLY, terms=PUBLIC_DOMAIN),
    Source(name='nottingham', folder='nottingham', kind=Kind.TUNE, quality=Quality.CROWD,
           terms=Terms(name='GPL-3.0', commercial=True, attribution=True, share_alike=True, credit='Nottingham Music Database, cleaned by Jukedeck')),
    Source(name='mutopia', folder='mutopia', kind=Kind.SCORE, quality=Quality.SCHOLARLY,
           terms=Terms(name='public domain or Creative Commons, piece by piece', commercial=False, attribution=True, share_alike=True, credit='The Mutopia Project')),
    Source(name='maestro', folder='maestro', kind=Kind.ARRANGEMENT, quality=Quality.PERFORMED,
           terms=Terms(name='CC BY-NC-SA 4.0', commercial=False, attribution=True, share_alike=True, credit='MAESTRO, Google Magenta')),
    Source(name='thesession', folder='thesession', kind=Kind.TUNE, quality=Quality.CROWD,
           terms=Terms(name='published openly for reuse; the tunes are traditional', commercial=True, attribution=True, share_alike=False, credit='The Session')),
)

SOURCES_BY_NAME = {source.name: source for source in SOURCES}


def credits(names):
    """Return the credits owed for knowledge drawn from the named sources, each once."""
    return list(dict.fromkeys(SOURCES_BY_NAME[name].terms.credit for name in names if SOURCES_BY_NAME[name].terms.attribution))


