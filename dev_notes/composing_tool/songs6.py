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

from lib import *


def not_star_trek():
    p = {'snare': drum('x..ox.o.x..ox.oo', 'snare'), 'crash': drum('x...............', 'crash'),
         'strings': mel("1 5 1' 5 1 5 1' 5 1 5 1' 5", octave=3, step='1/12'),
         'basses': mel("1 - - - 5, - - -", octave=3),
         'brass': mel("1:3 - - - 1:3 - 1:3 -", octave=4),
         'timpani': mel("1 . . . 1 . 1 1", octave=2),
         'fanfare': mel("5 - - 1' - - 3' - 2' - 1' - 6 - 4 - 5 - 3 - 1' - 5 - 7 - - - 2' - - -"),
         'b': mel("3' - - 1' 6 - 3' - 1' - - 6 4 - 1' - 5' - - 3' 1' - 5 - 2' - 4' - 5' - - -"),
         'bridge': mel("6 - - - 1' - - - 7 - - - 5 - - - 1' - - - 6 - - - 2' - - - 7 - - -"),
         }
    march = {'snare': 'snare', 'timpani': 'timpani'}
    s = band(drums={'main': march, 'big': {**march, 'crash': 'crash'}, 'roll': {'timpani': 'timpani'}}, harmony=('strings', 'basses', 'brass'))
    return song(
        stem='not_star_trek', folder='by_genre', title='Not Star Trek', genre='Soundtrack', tempo=106, root='D', kind='major',
        description='a majestic symphonic space-opera theme in the manner of the original Battlestar Galactica, with a fanfare of its own',
        about="""Not Star Trek: a symphonic theme at 106 beats a minute in D major, in the manner of the original
        Battlestar Galactica's late-seventies television theme: horns with a heroic fanfare, trumpets
        taking it up, strings driving in triplets, a brass section's chords, low strings, timpani and a
        march on the snare. The fanfare and the melodies are its own.

        The strings' triplets, the low strings and the brass chords are one bar each over chord I, moved
        by Progression: the fanfare goes I IV I V, the second theme vi IV I V and the bridge vi iii IV V.
        The opening and the bridge rise from quiet to full by the scenes' Swell.""",
        keep=['Keep the strings, low strings and brass one bar long over chord I.', "Keep the opening's and the bridge's swells.",
              'Keep the fanfare original.'],
        instruments={'strings': 49, 'contrabass': 44, 'brass': 62, 'timpani': 48, 'horns': 61, 'trumpet': 57},
        tracks={'snare': ('drum kit', {}), 'crash': ('drum kit', {}), 'timpani': ('timpani', {}), 'strings': ('strings', {}),
                'basses': ('contrabass', {}), 'brass': ('brass', {}), 'horns': ('horns', {}), 'trumpet': ('trumpet', {})},
        patterns=p, progressions={'fanfare': {'chords': [1, 4, 1, 5]}, 'second': {'chords': [6, 4, 1, 5]}, 'bridge': {'chords': [6, 3, 4, 5]}},
        scenes=[
            s('opening', 8, 'fanfare', 'the strings and the timpani, swelling from quiet.', kit='roll', without=('brass',),
              settings={'swell_start': 30, 'swell_end': 100}),
            s('fanfare', 16, 'fanfare', 'the horns with the fanfare.', lead={'horns': 'fanfare'}),
            s('second theme', 16, 'second', 'the trumpet with the second theme.', lead={'trumpet': 'b'}),
            s('fanfare 2', 16, 'fanfare', 'the fanfare on horns and trumpet together.', lead={'horns': 'fanfare', 'trumpet': 'fanfare'}, kit='big'),
            s('bridge', 8, 'bridge', 'a quieter bridge on the horns, swelling back.', lead={'horns': 'bridge'}, kit='roll',
              settings={'swell_start': 40, 'swell_end': 100}),
            s('finale', 16, 'fanfare', 'the fanfare to the end, everything playing.', lead={'horns': 'fanfare', 'trumpet': 'fanfare'}, kit='big'),
        ])


SONGS = [not_star_trek]
