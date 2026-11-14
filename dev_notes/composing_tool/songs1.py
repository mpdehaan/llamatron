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


def rick_rolling():
    p = {**beat('disco'),
         'bass': mel("1 1' 1 1' 1 1' 1 1'", octave=2),
         'stabs': mel(". 1:3 . 1:3 . 1:3 . 1:3", octave=4),
         'verse': mel("4 6 4 6 1' . 6 . 5 . 7 5 2' . 7 . 3 5 3 5 7 . 5 . 6 . 1' 6 3' 1' 6 ."),
         'pre': mel("6 6 6 5 4 . 2 . 3 3 3 5 7 . 5 . 4 4 4 6 1' . 6 . 5 7 2' 4' - - . ."),
         'chorus': mel("1' 1' 6 4 . 6 1' 6 7 . 5 2' - . 7 5 5 7 3' - 2' 7 5 3 6 - - 1' 3' - 1' ."),
         }
    d = kit_clips('disco')
    return song(
        stem='rick_rolling', folder='by_genre', title='Rick rolling', genre='Pop', tempo=114, root='Bb', kind='major',
        description='a late eighties dance-pop song in the manner of Never Gonna Give You Up, with a melody of its own',
        about="""Rick rolling: a dance-pop song at 114 beats a minute in B flat major, in the manner of the late
  eighties hit factories: an octave-bouncing synth bass, off-beat chord stabs, a four-on-the-floor
  disco beat and a singing lead. Every note of the melody is its own; only the style is borrowed.

  The bass and the stabs are one bar each, written over chord I and moved through the chords by
  Progression chains: the verse and chorus go IV V iii vi, and the build-up climbs ii iii IV V.""",
        keep=['Keep the bass and the stabs one bar long over chord I, so that the progressions move them.',
              'Keep the melody original, borrowing only the style.'],
        instruments={'synth bass': 39, 'synth brass': 63, 'synth voice': 55},
        tracks={**kit_tracks('disco'), 'bass': ('synth bass', {}), 'stabs': ('synth brass', {}), 'lead': ('synth voice', {})},
        patterns=p, progressions={'turn': {'chords': [4, 5, 3, 6]}, 'climb': {'chords': [2, 3, 4, 5]}},
        scenes=[
            ('intro', 4, {**d, 'bass': ('bass', ['turn']), 'stabs': ('stabs', ['turn'])}, 'the beat, the bass and the stabs.'),
            ('verse', 16, {**d, 'bass': ('bass', ['turn']), 'stabs': ('stabs', ['turn']), 'lead': 'verse'}, 'the verse melody.'),
            ('build', 8, {**d, 'bass': ('bass', ['climb']), 'stabs': ('stabs', ['climb']), 'lead': 'pre'}, 'the climb to the chorus.'),
            ('chorus', 16, {**d, 'bass': ('bass', ['turn']), 'stabs': ('stabs', ['turn']), 'lead': 'chorus'}, 'the chorus.'),
            ('verse 2', 16, {**d, 'bass': ('bass', ['turn']), 'stabs': ('stabs', ['turn']), 'lead': 'verse'}, 'the second verse.'),
            ('build 2', 8, {**d, 'bass': ('bass', ['climb']), 'stabs': ('stabs', ['climb']), 'lead': 'pre'}, 'the climb again.'),
            ('last chorus', 16, {**d, 'bass': ('bass', ['turn']), 'stabs': ('stabs', ['turn']), 'lead': 'chorus'}, 'the chorus to the end.'),
        ])




def peanut_buttercup():
    p = {**beat('disco', prefix='kit'),
         'tamb': drum('....x.......x...', 'tamb'),
         'bass': mel("1 . 1 5, 1 . 5, 1", octave=3),
         'piano': mel("1:3 . 1:3 1:3 . 1:3 . 1:3", octave=4),
         'horns': mel(". . . . 1:3 . 1:3 .", octave=4),
         'verse': mel("5 5 3 5 6 5 3 1 3 . 5 . 7 5 3 . 4 4 6 4 1' 6 4 . 5 . 7 . 2' - - ."),
         'chorus': mel("1' - 7 1' 3' - 1' . 7 - 5 7 2' - . . 1' - 6 1' 3' - 1' . 6 - 4 6 1' - . . "
                       "1' 3' 5' 3' 1' - 5 . 7 . 2' . 5' - 2' . 1' . 6 . 4 6 1' . 7 - - - 2' - - ."),
         'bridge': mel("3' - 1' 6 3' - . . 3' - 7 5 3' - . . 1' - 6 4 1' - . . 2' - 7 5 2' 4' 5' ."),
         }
    kit = {**kit_clips('disco', prefix='kit'), 'tamb': 'tamb'}
    s = band(drums={'main': kit}, harmony=('bass', 'piano', 'horns'))
    return song(
        stem='peanut_buttercup', folder='by_genre', title='Peanut buttercup', genre='Pop', tempo=132, root='C', kind='major',
        description='a late sixties soul-pop song in the manner of Build Me Up Buttercup, with a melody of its own',
        about="""Peanut buttercup: a bright soul-pop song at 132 beats a minute in C major, in the manner of the late
        sixties: a bouncing piano, horn stabs on the off-beats, a tambourine on two and four and a lead
        that sings over the top. The melody is its own; only the style is borrowed.

        The bass, the piano and the horns are one bar each over chord I, moved by Progression chains: the
        verse climbs I iii IV V, the chorus goes I V vi IV I V IV V, and the bridge vi iii IV V.""",
        keep=['Keep the bass, piano and horns one bar long over chord I.', 'Keep the melody original.'],
        instruments={'finger bass': 34, 'piano': 1, 'brass': 62, 'alto sax': 66},
        tracks={**kit_tracks('disco'), 'tamb': ('drum kit', {}), 'bass': ('finger bass', {}), 'piano': ('piano', {}),
                'horns': ('brass', {}), 'lead': ('alto sax', {})},
        patterns=p, progressions={'verse': {'chords': [1, 3, 4, 5]}, 'chorus': {'chords': [1, 5, 6, 4, 1, 5, 4, 5]},
                                  'bridge': {'chords': [6, 3, 4, 5]}},
        scenes=[
            s('intro', 4, 'verse', 'the band, with no melody.'),
            s('verse', 16, 'verse', 'the verse.', lead='verse'),
            s('chorus', 16, 'chorus', 'the chorus.', lead='chorus'),
            s('verse 2', 16, 'verse', 'the second verse.', lead='verse'),
            s('chorus 2', 16, 'chorus', 'the chorus again.', lead='chorus'),
            s('bridge', 8, 'bridge', 'the bridge.', lead='bridge'),
            s('last chorus', 16, 'chorus', 'the last chorus.', lead='chorus'),
            s('outro', 8, 'chorus', 'the band plays out.'),
        ])


def bless_the_rains():
    p = {**beat('latin', prefix='kit'),
         'kick': drum('x.......x.......', 'kick'),
         'marimba': mel("1 . 5 . 3' . 5 . 1' . 5 . 3' 5 1' .", octave=4, step='1/16'),
         'bass': mel("1 . . 1 . . 5, .", octave=2),
         'pad': mel("1:3 - - - - - - -", octave=4),
         'verse': mel("3 3 3 2 1 . 5, . 6, 1 3 1 6, . . . 4 4 6 4 1' . 6 . 5 . 7 . 2' 7 5 ."),
         'chorus': mel("6 - 1' 3' - 1' 6 . 4 - 6 1' - 6 4 . 1' - 3' 5' - 3' 1' . 7 - 5 2' - - . ."),
         }
    kit = {**kit_clips('latin', prefix='kit'), 'kick': 'kick'}
    s = band(drums={'main': kit}, harmony=('marimba', 'bass', 'pad'))
    return song(
        stem='bless_the_rains', folder='by_genre', title='Bless the rains', genre='Pop', tempo=96, root='A', kind='major',
        description='an early eighties soft-rock song in the manner of Africa, with a melody of its own',
        about="""Bless the rains: a soft-rock song at 96 beats a minute in A major, in the manner of the early
        eighties: a marimba riff in sixteenths, congas, a shaker and a cowbell, a warm pad and a lead
        that rises into the chorus. The melody and the riff are its own.

        The marimba, the bass and the pad are one bar each over chord I, moved by Progression: the
        verse goes I vi IV V and the chorus vi IV I V.""",
        keep=['Keep the marimba, bass and pad one bar long over chord I.', 'Keep the melody original.'],
        instruments={'marimba': 13, 'finger bass': 34, 'warm pad': 90, 'voice': 54},
        tracks={**kit_tracks('latin'), 'kick': ('drum kit', {}), 'marimba': ('marimba', {}), 'bass': ('finger bass', {}),
                'pad': ('warm pad', {}), 'lead': ('voice', {})},
        patterns=p, progressions={'verse': {'chords': [1, 6, 4, 5]}, 'chorus': {'chords': [6, 4, 1, 5]}},
        scenes=[
            s('intro', 4, 'verse', 'the marimba riff and the percussion.', without=('bass', 'pad')),
            s('verse', 16, 'verse', 'the verse.', lead='verse'),
            s('chorus', 16, 'chorus', 'the chorus.', lead='chorus'),
            s('verse 2', 16, 'verse', 'the second verse.', lead='verse'),
            s('chorus 2', 16, 'chorus', 'the chorus to the end.', lead='chorus'),
            s('outro', 4, 'verse', 'the riff alone again.', without=('bass', 'pad')),
        ])


def goodnight_world():
    p = {**beat('four', prefix='kit'),
         'bass': mel("1 1 1' 1 7, 1 5 1' 1 1 1' 1 5 1 3 1'", octave=2, step='1/16'),
         'pad': mel("1:3 - - - - - - -", octave=4),
         'a': mel("5 . 5 . 3 . 1 . 6 . 6 . 1' . 3' . 5 . 7 . 2' . 7 . 5 - - - . . . ."),
         'b': mel("1' - 3' 1' 5 . 3 . 1' - 6 1' 3' . 1' . 2' - 7 5 2' . 7 . 5 . 2' . 5' - - ."),
         }
    s = band(drums={'main': kit_clips('four', prefix='kit')}, harmony=('bass', 'pad'))
    return song(
        stem='goodnight_world', folder='by_genre', title='Goodnight world', genre='Pop', tempo=126, root='C', kind='minor',
        description='an early eighties synth-pop song in the manner of Sweet Dreams, with a melody of its own',
        about="""Goodnight world: a synth-pop song at 126 beats a minute in C minor, in the manner of the early
        eighties: a sixteenth-note synth bass that leaps an octave, a cold string pad, a drum machine
        and a saw lead. The melody and the bass line are its own.

        The bass and the pad are one bar each over chord i, moved through i VI v v by a Progression.""",
        keep=['Keep the bass and the pad one bar long over chord i.', 'Keep the melody original.'],
        instruments={'synth bass': 39, 'synth strings': 51, 'saw lead': 82},
        tracks={**kit_tracks('four'), 'bass': ('synth bass', {}), 'pad': ('synth strings', {}), 'lead': ('saw lead', {})},
        patterns=p, progressions={'turn': {'chords': [1, 6, 5, 5]}},
        scenes=[
            s('intro', 8, 'turn', 'the bass and the drums.', without=('pad',)),
            s('first line', 16, 'turn', 'the first tune.', lead='a'),
            s('second line', 16, 'turn', 'the second tune, higher.', lead='b'),
            s('first again', 16, 'turn', 'the first tune again.', lead='a'),
            s('break', 8, 'turn', 'the drums drop out.', kit=None),
            s('second again', 16, 'turn', 'the second tune again.', lead='b'),
            s('outro', 16, 'turn', 'the band plays out.'),
        ])


def spot_over_there():
    p = {**beat('rock', prefix='kit'),
         'crash': drum('x...............', 'crash'),
         'guitar': mel("1:5 1:5 1:5 1:5 1:5 1:5 1:5 1:5", octave=3),
         'bass': mel("1 1 1 1 1 1 1 1", octave=2),
         'verse': mel("1' 1' 7 1' 3' . 1' . 7 7 5 7 2' . 7 . 6 6 4 6 1' . 6 . 7 - 5 - 2' - . ."),
         'chorus': mel("4' - 3' 1' 6 . 1' . 5' - 2' 7 5 . 7 . 5' - 3' 1' 3' . 5' . 3' - 1' - 6 - . ."),
         'bridge': mel("6 . 1' . 3' - - . 4 . 6 . 1' - - . 3 . 5 . 1' - - . 5 . 7 . 2' - - ."),
         }
    kit = kit_clips('rock', prefix='kit')
    s = band(drums={'main': kit, 'big': {**kit, 'crash': 'crash'}}, harmony=('guitar', 'bass'))
    return song(
        stem='spot_over_there', folder='by_genre', title='Spot over there', genre='Rock', tempo=120, root='E', kind='major',
        description="an early 2000s power-pop song in the manner of Stacy's Mom, with a melody of its own",
        about="""Spot over there: a power-pop song at 120 beats a minute in E major, in the manner of the early
        2000s: driving eighth-note power chords, a pick bass on every eighth, a rock beat with a crash
        on every chorus bar, and a bright lead. The melody is its own.

        The guitar plays root and fifth, the scale chord 5, and the guitar and the bass are one bar each,
        moved by Progression: the verse goes I V IV V, the chorus IV V I vi and the bridge vi IV I V.""",
        keep=['Keep the guitar and the bass one bar long over chord I.', 'Keep the melody original.'],
        instruments={'overdriven guitar': 30, 'pick bass': 35, 'voice': 54},
        tracks={**kit_tracks('rock'), 'crash': ('drum kit', {}), 'guitar': ('overdriven guitar', {}), 'bass': ('pick bass', {}),
                'lead': ('voice', {})},
        patterns=p, progressions={'verse': {'chords': [1, 5, 4, 5]}, 'chorus': {'chords': [4, 5, 1, 6]}, 'bridge': {'chords': [6, 4, 1, 5]}},
        scenes=[
            s('intro', 4, 'verse', 'the guitar and the drums.', without=('bass',)),
            s('verse', 16, 'verse', 'the verse.', lead='verse'),
            s('chorus', 16, 'chorus', 'the chorus, a crash on every bar.', lead='chorus', kit='big'),
            s('verse 2', 16, 'verse', 'the second verse.', lead='verse'),
            s('chorus 2', 16, 'chorus', 'the chorus again.', lead='chorus', kit='big'),
            s('bridge', 8, 'bridge', 'the bridge.', lead='bridge'),
            s('last chorus', 16, 'chorus', 'the last chorus.', lead='chorus', kit='big'),
        ])


def know_your_slang():
    p = {**beat('rock', prefix='kit'),
         'tamb': drum('x.x.x.x.x.x.x.x.', 'tamb'),
         'soft_kick': drum('x.......x.......', 'kick'),
         'strum': mel("1:3 . 1:3 1:3 . 1:3 1:3 1:3", octave=3),
         'bass': mel("1 . . 5, 1 . 5, .", octave=2),
         'jangle': mel("1 3 5 3 1' 5 3 5 1 3 5 3 1' 5 3 5", octave=4, step='1/16'),
         'verse': mel("5 . 5 6 5 3 1 . 2 . 2 5 7 5 2 . 3 . 3 6 1' 6 3 . 4 . 4 6 1' - - ."),
         'chorus': mel("1' - 6 4 1' . 6 . 1' - 5 3 1' . 5 . 2' - 7 5 2' . 7 . 5' - 2' - 7 - - ."),
         'onion': mel("1' 3' 5' 3' 1' 3' 5' 3' 1' 4' 6' 4' 1' 4' 6' 4' 1' 3' 6' 3' 1' 3' 6' 3' 2' 5' 7' 5' 2' 5' 7' 5'", octave=4),
         }
    soft = {'tamb': 'tamb', 'kick': 'soft_kick'}
    loud = {**kit_clips('rock', prefix='kit'), 'tamb': 'tamb'}
    s = band(drums={'soft': soft, 'loud': loud}, harmony=('strum', 'bass'))
    return song(
        stem='know_your_slang', folder='by_genre', title='Know your slang', genre='Rock', tempo=116, root='G', kind='major',
        description="an indie rock song in the manner of the Shins' New Slang and Know Your Onion, with melodies of its own",
        about="""Know your slang: an indie rock song at 116 beats a minute in G major, in two moods after the Shins:
        the lilting acoustic strum and tambourine of New Slang, and the jangling electric guitar and
        full kit of Know Your Onion. The melodies are its own.

        The steel guitar strums with the track's own Strum, down and up as a hand would, and the strum,
        the bass and the jangle are one bar each over chord I, moved by Progression: the verse goes
        I V vi IV, the chorus IV I V V and the jangling part I IV vi V.""",
        keep=['Keep the strum, the bass and the jangle one bar long over chord I.', 'Keep the strum on the guitar track.',
              'Keep the melodies original.'],
        instruments={'steel guitar': 26, 'finger bass': 34, 'clean guitar': 28, 'harmonica': 23},
        tracks={**kit_tracks('rock'), 'tamb': ('drum kit', {}), 'strum': ('steel guitar', {'strum_direction': 'down_up', 'strum_spread': 'normal'}),
                'bass': ('finger bass', {}), 'jangle': ('clean guitar', {}), 'lead': ('harmonica', {})},
        patterns=p, progressions={'verse': {'chords': [1, 5, 6, 4]}, 'chorus': {'chords': [4, 1, 5, 5]}, 'onion': {'chords': [1, 4, 6, 5]}},
        scenes=[
            s('intro', 4, 'verse', 'the strummed guitar alone.', kit=None, without=('bass',)),
            s('verse', 16, 'verse', 'the acoustic verse, tambourine and a soft kick.', lead='verse', kit='soft'),
            s('chorus', 16, 'chorus', 'the chorus.', lead='chorus', kit='soft'),
            s('jangle', 16, 'onion', 'the electric guitar and the full kit.', kit='loud', extra={'jangle': ('jangle', ['onion'])}),
            s('verse 2', 16, 'verse', 'the acoustic verse again.', lead='verse', kit='soft'),
            s('jangle 2', 16, 'onion', 'the jangling part with its tune.', kit='loud', lead='onion', extra={'jangle': ('jangle', ['onion'])}),
            s('outro', 4, 'verse', 'the strum alone.', kit=None, without=('bass',)),
        ])


def green_men():
    p = {**beat('punk', prefix='kit'),
         'crash': drum('x...............', 'crash'),
         'guitar': mel("1:5 1:5 1:5 1:5 1:5 1:5 1:5 1:5", octave=3),
         'bass': mel("1 1 1 1 1 1 1 1", octave=2),
         'verse': mel("1' 1' 1' 7 1' 3' 1' . 7 7 7 5 7 2' 7 . 1' 1' 1' 6 1' 3' 1' . 1' 1' 6 4 6 - - ."),
         'chorus': mel("4' - 4' - 3' 1' 6 . 3' - 3' - 1' 5 3 . 2' - 2' - 7 5 2' . 1' - 6 - 3' - - ."),
         }
    kit = kit_clips('punk', prefix='kit')
    s = band(drums={'main': kit, 'big': {**kit, 'crash': 'crash'}, 'half': {'kick': 'kit_kick', 'crash': 'crash'}}, harmony=('guitar', 'bass'))
    return song(
        stem='green_men', folder='by_genre', title='Green men', genre='Rock', tempo=180, root='E', kind='major',
        description='a pop-punk song in the manner of the late nineties and early 2000s, its power chords strummed',
        about="""Green men: a pop-punk song at 180 beats a minute in E major, in the manner of Green Day and Sum 41:
        eighth-note power chords, a pick bass on every eighth, a fast kick and snare, and a shouted lead.
        The melody is its own.

        The guitar's power chords are strummed: the track strums every chord down, tight, the way a
        pick rakes the strings, and in the bridge a Strum generator called rake, in the clips' chains,
        wins over the track's and strums down and up, looser. The guitar and the bass are one bar each,
        moved by Progression: the verse goes I V vi IV, the chorus IV I V vi.""",
        keep=['Keep the guitar track strummed, and the rake generator in the bridge.', 'Keep the melody original.'],
        instruments={'distortion guitar': 31, 'pick bass': 35, 'overdriven guitar': 30},
        tracks={**kit_tracks('punk'), 'crash': ('drum kit', {}), 'guitar': ('distortion guitar', {'strum_direction': 'down', 'strum_spread': 'tight'}),
                'bass': ('pick bass', {}), 'lead': ('overdriven guitar', {})},
        patterns=p, progressions={'verse': {'chords': [1, 5, 6, 4]}, 'chorus': {'chords': [4, 1, 5, 6]}, 'bridge': {'chords': [6, 4, 6, 5]}},
        strums={'rake': {'direction': 'down_up', 'spread': 'loose'}},
        chains={'rake': [{'strum': 'rake'}]},
        scenes=[
            s('intro', 8, 'verse', 'the guitar alone, then the band.', kit='half', without=('bass',)),
            s('verse', 16, 'verse', 'the verse.', lead='verse'),
            s('chorus', 16, 'chorus', 'the chorus, a crash on every bar.', lead='chorus', kit='big'),
            s('verse 2', 16, 'verse', 'the second verse.', lead='verse'),
            s('chorus 2', 16, 'chorus', 'the chorus again.', lead='chorus', kit='big'),
            s('bridge', 16, 'bridge', 'the bridge, the guitar raked down and up.', kit='half', chains=['rake']),
            s('chorus 3', 16, 'chorus', 'the chorus.', lead='chorus', kit='big'),
            s('verse 3', 16, 'verse', 'the verse once more.', lead='verse'),
            s('last chorus', 16, 'chorus', 'the last chorus.', lead='chorus', kit='big'),
        ])


def training_montage():
    p = {**beat('rock', prefix='kit'),
         'hits_kick': drum('x..x..x.x...x.x.', 'kick'),
         'crash': drum('x...............', 'crash'),
         'hits': mel("1:5 . . 1:5 . . 1:5 . 1:5 . . . 1:5 . 1:5 .", octave=3, step='1/16'),
         'bass': mel("1 . . 1 . . 1 . 1 . . . 1 . 1 .", octave=2, step='1/16'),
         'pad': mel("1:3 - - - - - - -", octave=4),
         'verse': mel("5 5 5 5 3 . 1 . 5 5 5 5 3 . 1 . 6 6 6 6 1' . 3' . 7 - 5 - 2' - - ."),
         'pre': mel("1' - 6 - 3' - 1' . 2' - 7 - 5 - 2' . 3' - 1' - 5 - 3' . 1' - - - . . . ."),
         'chorus': mel("1' . 1' . 3' - 1' . 2' . 2' . 4' - 2' . 1' . 1' . 3' 1' 6 . 7 - 2' - 5' - - ."),
         }
    hits = {'kick': 'hits_kick', 'crash': 'crash'}
    rock = kit_clips('rock', prefix='kit')
    s = band(drums={'hits': hits, 'main': rock}, harmony=('hits', 'bass', 'pad'))
    return song(
        stem='training_montage', folder='by_genre', title='Training montage', genre='Rock', tempo=108, root='C', kind='minor',
        description='an early eighties arena-rock song in the manner of Eye of the Tiger, for a training montage',
        about="""Training montage: an arena-rock song at 108 beats a minute in C minor, in the manner of the early
        eighties film anthems: muted guitar chords hit in a syncopated rhythm with the kick, then a
        driving rock beat, a synth pad, and a brass lead. The rhythm and the melody are its own.

        The guitar's hits, the bass and the pad are one bar each over chord i, moved by Progression:
        the verse goes i i VI VII, the build VI VII i i, and the chorus i VII VI VII.""",
        keep=['Keep the hits, the bass and the pad one bar long over chord i.', 'Keep the melody original.'],
        instruments={'distortion guitar': 31, 'finger bass': 34, 'polysynth': 91, 'brass': 62},
        tracks={**kit_tracks('rock'), 'crash': ('drum kit', {}), 'hits': ('distortion guitar', {}), 'bass': ('finger bass', {}),
                'pad': ('polysynth', {}), 'lead': ('brass', {})},
        patterns=p, progressions={'verse': {'chords': [1, 1, 6, 7]}, 'build': {'chords': [6, 7, 1, 1]}, 'chorus': {'chords': [1, 7, 6, 7]}},
        scenes=[
            s('intro', 8, 'verse', 'the hits and the kick together.', kit='hits', without=('pad',)),
            s('verse', 16, 'verse', 'the verse over the hits.', lead='verse', kit='hits'),
            s('build', 8, 'build', 'the build.', lead='pre'),
            s('chorus', 16, 'chorus', 'the chorus.', lead='chorus'),
            s('verse 2', 16, 'verse', 'the second verse.', lead='verse', kit='hits'),
            s('build 2', 8, 'build', 'the build again.', lead='pre'),
            s('last chorus', 8, 'chorus', 'the last chorus.', lead='chorus'),
        ])


def secret_chord():
    p = {'piano': mel("1 5 1' 3' 1' 5", octave=3),
         'bass': mel("1 - - - - -", octave=2),
         'strings': mel("1:3 - - - - -", octave=4),
         'brush': drum('x.....o.....', 'stick', step='1/8') if False else drum('x....o', 'stick', step='1/8'),
         'verse': mel("5 - 5 3 - 1 6, - 1 3 - . 5 - 5 6 - 5 3 - - . . . 4 - 4 6 - 1' 7 - 5 2 - . 3 - 5 1' - 5 7 - - 2' - . "
                      "1' - 5 3 - 5 4 - 6 1' - 6 5 - 7 2' - 7 6 - - 1' - . 6 - 4 1' - 6 7 - 5 2' - 7 7 - 5 3 - 5 6 - - - - ."),
         'chorus': mel("1' - 6 4 - . 1' - 6 3 - . 1' - 6 4 - 6 5 - - 3 - 1 2 - 5 7 - 2' 1' - - 5 - 3 2 - 5 7 - 5 1' - - - - ."),
         }
    verse = [1, 6, 1, 6, 4, 5, 1, 5, 1, 4, 5, 6, 4, 5, 3, 6]
    chorus = [4, 6, 4, 1, 5, 1, 5, 1]
    s = band(drums={'main': {'brush': 'brush'}}, harmony=('piano', 'bass'))
    return song(
        stem='secret_chord', folder='by_genre', title='Secret chord', genre='Folk', tempo=84, root='C', kind='major',
        time_signature='6/8',
        description="Leonard Cohen's chords for Hallelujah in 6/8, played through a Progression, under a melody of its own",
        about="""Secret chord: a slow ballad in 6/8 at 84 beats a minute in C major on the chords of Leonard Cohen's
        Hallelujah, with a melody of its own: a rolling piano, a bass, strings in the choruses and a
        cello singing the tune.

        The piano's broken chord, the bass and the strings are each one bar long over chord I, and the
        chords come from Progression chains, as the song goes: the verse C Am C Am F G C G, then
        C F G Am F G Em Am, and the chorus F Am F C G C G C. Where the song's turnaround has E major,
        the scale's own chord on 3 is E minor, which this set plays.""",
        keep=['Keep the piano, bass and strings one bar long over chord I, so that the progressions play the chords.',
              'Keep the melody original: only the chords are the song.'],
        instruments={'piano': 1, 'acoustic bass': 33, 'strings': 49, 'cello': 43},
        tracks={'brush': ('drum kit', {}), 'piano': ('piano', {}), 'bass': ('acoustic bass', {}), 'strings': ('strings', {}),
                'lead': ('cello', {})},
        patterns=p, progressions={'verse': {'chords': verse}, 'chorus': {'chords': chorus}},
        scenes=[
            s('intro', 4, 'chorus', 'the piano alone.', kit=None, without=('bass',)),
            s('verse', 16, 'verse', 'the first verse.', lead='verse', kit=None),
            s('chorus', 8, 'chorus', 'the chorus, with strings.', lead='chorus', extra={'strings': ('strings', ['chorus'])}),
            s('verse 2', 16, 'verse', 'the second verse, a brush on the beats.', lead='verse'),
            s('chorus 2', 8, 'chorus', 'the chorus.', lead='chorus', extra={'strings': ('strings', ['chorus'])}),
            s('verse 3', 16, 'verse', 'the third verse.', lead='verse'),
            s('chorus 3', 8, 'chorus', 'the chorus.', lead='chorus', extra={'strings': ('strings', ['chorus'])}),
            s('last chorus', 8, 'chorus', 'the last chorus, the piano and strings alone.', kit=None, extra={'strings': ('strings', ['chorus'])}),
        ])


SONGS = [rick_rolling, peanut_buttercup, bless_the_rains, goodnight_world, spot_over_there, know_your_slang, green_men,
         training_montage, secret_chord]
