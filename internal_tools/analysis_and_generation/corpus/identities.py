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

"""One identity for each creator across every source (the user's direction): the same person is DebussyC in Mutopia, Claude
Debussy in MAESTRO and debussy in a composer's collection, and a band is "The Beatles" in one place and "Beatles" in another, so
every creator is resolved to a canonical key and a display name before anything is grouped, merged or compared, and conclusions
drawn across sources neither split one person in two nor count them twice."""

import re
import unicodedata

from corpus.composers import PERIODS, surname_of

# The display name of each composer the corpus knows, by surname key.
COMPOSER_NAMES = {
    'bach': 'Johann Sebastian Bach', 'bach-cpe': 'Carl Philipp Emanuel Bach', 'handel': 'George Frideric Handel', 'buxtehude': 'Dieterich Buxtehude',
    'corelli': 'Arcangelo Corelli', 'couperin': 'François Couperin', 'charpentier': 'Marc-Antoine Charpentier', 'froberger': 'Johann Jakob Froberger',
    'scarlatti': 'Domenico Scarlatti', 'vivaldi': 'Antonio Vivaldi', 'purcell': 'Henry Purcell', 'telemann': 'Georg Philipp Telemann',
    'rameau': 'Jean-Philippe Rameau', 'haydn': 'Joseph Haydn', 'mozart': 'Wolfgang Amadeus Mozart', 'clementi': 'Muzio Clementi',
    'diabelli': 'Anton Diabelli', 'beethoven': 'Ludwig van Beethoven', 'carulli': 'Ferdinando Carulli', 'giuliani': 'Mauro Giuliani',
    'chopin': 'Frédéric Chopin', 'schubert': 'Franz Schubert', 'schumann': 'Robert Schumann', 'brahms': 'Johannes Brahms', 'liszt': 'Franz Liszt',
    'grieg': 'Edvard Grieg', 'dvorak': 'Antonín Dvořák', 'faure': 'Gabriel Fauré', 'franck': 'César Franck', 'bruckner': 'Anton Bruckner',
    'tchaikovsky': 'Pyotr Ilyich Tchaikovsky', 'mendelssohn': 'Felix Mendelssohn', 'rachmaninoff': 'Sergei Rachmaninoff', 'scriabin': 'Alexander Scriabin',
    'mussorgsky': 'Modest Mussorgsky', 'balakirev': 'Mily Balakirev', 'alkan': 'Charles-Valentin Alkan', 'gottschalk': 'Louis Moreau Gottschalk',
    'holst': 'Gustav Holst', 'debussy': 'Claude Debussy', 'ravel': 'Maurice Ravel', 'satie': 'Erik Satie', 'bartok': 'Béla Bartók', 'berg': 'Alban Berg',
    'schoenberg': 'Arnold Schoenberg', 'stravinsky': 'Igor Stravinsky', 'prokofiev': 'Sergei Prokofiev', 'joplin': 'Scott Joplin',
    'sousa': 'John Philip Sousa', 'foster': 'Stephen Foster', 'dowland': 'John Dowland', 'gesualdo': 'Carlo Gesualdo', 'gibbons': 'Orlando Gibbons',
    'janequin': 'Clément Janequin',
}
LEADING_ARTICLE = re.compile(r'^(the|a)\s+')
NOT_A_LETTER = re.compile(r'[^a-z0-9]+')
COMPOSER_KEY = 'composer:{surname}'
NAME_KEY = 'name:{name}'


def plain(text):
    """Return text in plain lower-case letters and digits, accents removed, so that spellings of one name compare equal."""
    folded = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower().strip()
    return NOT_A_LETTER.sub(' ', LEADING_ARTICLE.sub('', folded)).strip()


def identity_of(creator):
    """Return a creator's canonical key and display name: a composer the corpus knows by surname, whatever the spelling or code;
    anyone else by their name in plain letters, without a leading article, so "The Beatles" and "Beatles" are one band."""
    if not creator:
        return None, None
    surname = surname_of(creator)
    if surname in COMPOSER_NAMES and (surname in PERIODS or surname in ('bach-cpe', 'foster', 'dowland', 'gesualdo', 'gibbons', 'janequin')):
        return COMPOSER_KEY.format(surname=surname), COMPOSER_NAMES[surname]
    name = plain(creator)
    return (NAME_KEY.format(name=name), creator.strip()) if name else (None, None)
