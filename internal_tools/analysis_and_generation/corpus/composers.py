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

"""The composers of the classical MIDI sources (Mutopia, MAESTRO), by surname: the library genre each one's period is labelled as,
and the library person each is, where the library has a style for them. A composer with no period genre (the Renaissance has no
style yet) or no person style is a gap the coverage report names, not an error."""

import re

from llamatron.strings.genres import StyleName

N = StyleName
SURNAME_OF_CODE = re.compile(r'([A-Z][a-z]+)')
# The genre each composer's period is labelled as.
PERIODS = {
    'bach': N.BAROQUE, 'handel': N.BAROQUE, 'buxtehude': N.BAROQUE, 'corelli': N.BAROQUE, 'couperin': N.BAROQUE, 'charpentier': N.BAROQUE,
    'froberger': N.BAROQUE, 'scarlatti': N.BAROQUE, 'vivaldi': N.BAROQUE, 'purcell': N.BAROQUE, 'telemann': N.BAROQUE, 'rameau': N.BAROQUE,
    'haydn': N.CLASSICAL_ERA, 'mozart': N.CLASSICAL_ERA, 'clementi': N.CLASSICAL_ERA, 'diabelli': N.CLASSICAL_ERA, 'beethoven': N.CLASSICAL_ERA,
    'carulli': N.CLASSICAL_ERA, 'giuliani': N.CLASSICAL_ERA,
    'chopin': N.ROMANTIC, 'schubert': N.ROMANTIC, 'schumann': N.ROMANTIC, 'brahms': N.ROMANTIC, 'liszt': N.ROMANTIC, 'grieg': N.ROMANTIC,
    'dvorak': N.ROMANTIC, 'faure': N.ROMANTIC, 'franck': N.ROMANTIC, 'bruckner': N.ROMANTIC, 'tchaikovsky': N.ROMANTIC, 'mendelssohn': N.ROMANTIC,
    'rachmaninoff': N.ROMANTIC, 'scriabin': N.ROMANTIC, 'mussorgsky': N.ROMANTIC, 'balakirev': N.ROMANTIC, 'alkan': N.ROMANTIC, 'gottschalk': N.ROMANTIC,
    'holst': N.ROMANTIC, 'schumann-wieck': N.ROMANTIC,
    'debussy': N.IMPRESSIONISM, 'ravel': N.IMPRESSIONISM, 'satie': N.IMPRESSIONISM,
    'bartok': N.MODERNISM, 'berg': N.MODERNISM, 'schoenberg': N.MODERNISM, 'stravinsky': N.MODERNISM, 'prokofiev': N.MODERNISM,
    'joplin': N.RAGTIME, 'sousa': N.MARCH,
}
# The library person each composer is, where the library has a style for them.
PEOPLE = {'bach': N.JS_BACH, 'handel': N.HANDEL, 'haydn': N.HAYDN, 'mozart': N.MOZART, 'chopin': N.CHOPIN, 'vivaldi': N.VIVALDI, 'telemann': N.TELEMANN}
# A code or a name for which the surname alone is ambiguous: C. P. E. Bach is not J. S. Bach.
NOT_THE_SAME = {'BachCPE': 'bach-cpe', 'Carl Philipp Emanuel Bach': 'bach-cpe'}


def surname_of(creator):
    """Return a composer's surname in lower case, from a Mutopia code such as BachJS or a name such as Johann Sebastian Bach."""
    if not creator:
        return None
    if creator in NOT_THE_SAME:
        return NOT_THE_SAME[creator]
    first = creator.split('/')[0].strip()
    if ' ' in first:
        return first.split()[-1].lower().replace('é', 'e').replace('á', 'a').replace('ř', 'r').replace('ö', 'o')
    match = SURNAME_OF_CODE.match(first)
    return match.group(1).lower() if match else first.lower()


def period_of(creator):
    return PERIODS.get(surname_of(creator))


def person_of_composer(creator):
    return PEOPLE.get(surname_of(creator))
