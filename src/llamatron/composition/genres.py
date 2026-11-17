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

"""The genres a song can say it is, the subgenres of each and the variants of a subgenre.

A song's Genre, Subgenre and Variant are for people to read and for whatever plays in a style, such as a
musician, to take its habits from. A genre with no subgenres listed is only a name. A mashup's
subgenre is the genre it is mashed with. Text a file holds that is none of these is read as nothing,
so no set stops opening for a genre the program doesn't know.
"""

MASHUP = 'Mashup'
# What a mashup of a genre is called where one name is wanted, as the pages of demos want.
MASHUP_NAMED = '{subgenre} Mashup'
MASHUP_SUFFIX = ' Mashup'

GENRES = [
    'Blues', "Children's", 'Classical', 'Country', 'Electronic', 'Exercise', 'Experimental', 'Folk', 'Funk', 'Gospel', MASHUP, 'Metal', 'Pop', 'Ragtime', 'Rock',
    'Soundtrack', 'TV Theme', 'Video Game', 'World',
]

# Each genre's subgenres, for the genres that have any.
SUBGENRES = {
    'Blues': ['driving shuffle', 'jump blues', 'minor blues', 'shuffle', 'slow blues', 'texas shuffle'],
    'Electronic': [
        'ambient', 'big beat', 'chiptune', 'downtempo', 'drum and bass', 'dubstep', 'electro', 'hi-nrg', 'house', 'italo', 'minimal techno', 'synth-pop', 'techno', 'trance',
    ],
    'Experimental': ['serial chords', 'serial synths', 'serial trio', 'serial winds'],
    'Funk': ['disco', 'funk', 'new orleans', 'sixties soul', 'soul ballad', 'southern soul'],
    MASHUP: ['Blues', 'Electronic', 'Funk', 'Jazz', 'Metal', 'Rock', 'World'],
    'Pop': ['baroque', 'big studio', 'bubblegum', 'folk pop', 'soul pop', 'sunshine', 'waltz ballad'],
    'Rock': ['arena rock', 'british invasion', 'folk rock', 'hard rock', 'new wave', 'punk', 'rock and roll', 'rock ballad', 'six-eight ballad'],
}

# Each subgenre's variants, by genre, for the subgenres that have any.
VARIANTS = {
    'Rock': {'hard rock': ['blues-based', 'heavy', 'boogie', 'stomp']},
}


def subgenres_of(genre):
    """Return a genre's subgenres, none for a genre that has none or for no genre."""
    return SUBGENRES.get(genre, [])


def variants_of(*, genre, subgenre):
    """Return a subgenre's variants, none for a subgenre that has none."""
    return VARIANTS.get(genre, {}).get(subgenre, [])


def known(*, text, choices):
    """Return the choice the text names, whatever its capitals, or None when it names none."""
    if not isinstance(text, str):
        return None
    wanted = text.strip().lower()
    return next((choice for choice in choices if choice.lower() == wanted), None)


def sensible_style(*, genre, subgenre, variant):
    """Return a genre, subgenre and variant made sensible: each as the program writes it, or None where the text names nothing known.

    A genre written the older way, as a mashup's genre and the word Mashup in one, is read as the
    mashup of that genre. A subgenre means something only under its genre, and a variant under its subgenre.
    """
    if isinstance(genre, str) and genre.strip().endswith(MASHUP_SUFFIX):
        subgenre = genre.strip()[:-len(MASHUP_SUFFIX)]
        genre = MASHUP
    genre = known(text=genre, choices=GENRES)
    subgenre = known(text=subgenre, choices=subgenres_of(genre))
    variant = known(text=variant, choices=variants_of(genre=genre, subgenre=subgenre))
    return genre, subgenre, variant


def style_name(*, genre, subgenre):
    """Return one name for a genre and subgenre where one is wanted: the genre, or for a mashup with a subgenre, the two as one."""
    if genre == MASHUP and subgenre is not None:
        return MASHUP_NAMED.format(subgenre=subgenre)
    return genre
