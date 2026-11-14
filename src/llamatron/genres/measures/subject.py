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

"""Subjects and evidence. A subject is anything the library can ask a measure of: a style, a variant, a person's style, a song's
sketch, a song heard from its notes, a stretch of one, a creator or a piece measured in the corpus. Each answers the same
questions, its value for a measure and the evidence the value rests on, so that any subject compares with any other and a new
kind of subject works with everything that already asks. Evidence says what a value stands on: written in the catalog by hand,
measured from the corpus (from how many pieces, of which sources, at what weight), or heard from a song's own notes; it is how
the library knows what it knows."""

from dataclasses import dataclass

from llamatron.genres.measures.registry import MEASURES, measure

# The weight of a value that rests on everything it could.
FULL_WEIGHT = 1.0


class Basis:
    """What a value rests on."""

    WRITTEN = 'written'
    MEASURED = 'measured'
    HEARD = 'heard'


class SubjectKind:
    """The kinds of subject."""

    FAMILY = 'family'
    STYLE = 'style'
    VARIANT = 'variant'
    PERSON = 'person'
    SONG_SKETCH = 'song sketch'
    STUDIED_SONG = 'studied song'
    PHASE = 'phase'
    SONG = 'song'
    STRETCH = 'stretch'
    CORPUS_CREATOR = 'corpus creator'
    CORPUS_PIECE = 'corpus piece'


# The kinds that are one piece of music, a point; every other kind is a region many pieces lie in, which a point fits by
# falling within its spreads.
POINTS = (SubjectKind.SONG, SubjectKind.STRETCH, SubjectKind.CORPUS_PIECE)


@dataclass(slots=True, kw_only=True, frozen=True)
class Evidence:
    """What one value rests on: its basis; its origin, the name of what set it (the style up the lineage that wrote it, the
    variant, the song heard); for a measured value the pieces it was measured from and their sources; and its weight, from 0 to
    1, how far the sources are trusted."""

    basis: str
    origin: str
    pieces: int = 0
    sources: tuple = ()
    weight: float = FULL_WEIGHT


@dataclass(slots=True, kw_only=True, frozen=True)
class Reading:
    """One subject's answer for one measure: the measure, the value and the evidence."""

    measure: object
    value: object
    evidence: object


class Subject:
    """What every subject answers. A subject has a name, a kind and trait(name); the rest follows."""

    __slots__ = ()

    def value(self, name):
        """Return the subject's value for a measure by its name, such as vocal.singable, or None where it is unknown."""
        return measure(name).of(self)

    def evidence_of(self, name):
        """Return the evidence the subject's value for a measure rests on, or None where nothing is recorded."""
        return None

    def reading(self, name):
        """Return the subject's value for a measure with its evidence, or None where the value is unknown."""
        value = self.value(name)
        return Reading(measure=measure(name), value=value, evidence=self.evidence_of(name)) if value is not None else None

    def readings(self):
        """Return every measure the subject knows, each with its value and evidence."""
        found = [self.reading(each.name()) for each in MEASURES]
        return [each for each in found if each is not None]

    def is_region(self):
        """Return whether the subject is a region many pieces lie in, not one piece."""
        return self.kind not in POINTS

    def fixed(self):
        """Return the traits the subject never changes, which count for more when something is fitted to it."""
        return ()

    def families_known(self):
        """Return the families of the library the subject belongs to, as far as anything says: none for a song."""
        return ()

    def pieces_known(self):
        """Return how many pieces the subject's summary rests on, or None where it rests on no count of pieces."""
        return None
