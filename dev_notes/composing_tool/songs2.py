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


def sax_reindeer():
    p = {'kick': drum('x.......x.......', 'kick'), 'snare': drum('....x.......x...', 'snare'), 'hat': drum('x.x.x.x.x.x.x.x.', 'hat'),
         'bass': mel("1 . 5, . 1 . 5, .", octave=3),
         'piano': mel(". 1:3 . 1:3 . 1:3 . 1:3", octave=4),
         'a': mel("1 2 3 5 6 5 3 2 1 . 5, . 1 . . . 3 4 5 6 1' 6 5 3 5 . 1' . 5 . . . "
                  "4 5 6 1' 2' 1' 6 5 4 . 1' . 6 . . . 5 6 1' 2' 3' 2' 1' 6 5 . 3 . 1 . . .", step='1/16'),
         'b': mel("5 6 7 2' 4' 2' 7 6 5 . 2' . 7 . . . 4 5 6 1' 2' 1' 6 5 4 . 6 . 1' . . . "
                  "3 5 1' 3' 5' 3' 1' 5 3 . 1' . 5 . . . 2 4 5 7 2' . 5 . 7 . 2' . 5' . . .", step='1/16'),
         }
    kit = {'kick': 'kick', 'snare': 'snare', 'hat': 'hat'}
    s = band(drums={'main': kit}, harmony=('bass', 'piano'))
    sax = lambda part: {'sax': part}
    return song(
        stem='sax_reindeer', folder='by_genre', title='Sax reindeer', genre='TV theme', tempo=144, root='Bb', kind='major',
        description='a breakneck novelty saxophone romp in the manner of Yakety Sax, with runs of its own',
        about="""Sax reindeer: a novelty romp at 144 beats a minute in B flat major, in the manner of Yakety Sax and
        the chases it scored: a tenor saxophone running in sixteenths, a honky-tonk piano on the
        off-beats, an oom-pah bass and a two-beat kit. Every run is its own.

        The bass and the piano are one bar each over chord I, moved by Progression: the A part goes
        I I IV I and the B part V IV I V. In the middle the piano takes the tune.""",
        keep=['Keep the bass and the piano one bar long over chord I.', 'Keep the runs original.'],
        instruments={'acoustic bass': 33, 'honky-tonk piano': 4, 'tenor sax': 67, 'piano lead': 4},
        tracks={'kick': ('drum kit', {}), 'snare': ('drum kit', {}), 'hat': ('drum kit', {}), 'bass': ('acoustic bass', {}),
                'piano': ('honky-tonk piano', {}), 'sax': ('tenor sax', {}), 'piano solo': ('piano lead', {})},
        patterns=p, progressions={'a': {'chords': [1, 1, 4, 1]}, 'b': {'chords': [5, 4, 1, 5]}},
        scenes=[
            s('intro', 4, 'a', 'the band.'),
            s('A', 16, 'a', 'the saxophone runs.', lead=sax('a')),
            s('B', 8, 'b', 'the second part.', lead=sax('b')),
            s('A 2', 16, 'a', 'the runs again.', lead=sax('a')),
            s('piano', 8, 'a', 'the piano takes the tune.', lead={'piano solo': 'a'}),
            s('A 3', 16, 'a', 'the saxophone again.', lead=sax('a')),
            s('B 2', 8, 'b', 'the second part again.', lead=sax('b')),
            s('A 4', 16, 'a', 'the runs once more.', lead=sax('a')),
            s('tag', 16, 'a', 'the saxophone and the piano together.', lead={'sax': 'a', 'piano solo': 'a'}),
        ])


def spy_hunting():
    p = {**beat('surf', prefix='kit'),
         'riff': mel("1 1 3 1 4 #4 5 3", octave=3),
         'stabs': mel(". . . . . . 1:3 -", octave=4),
         'head': mel("5 - - 3 5 - 7 - 1' - - - . . . . 5 - - 3 4 #4 5 - 3 - - - . . . . "
                     "1' - - 6 1' - 3' - 4' - - - . . . . 5 - - 3 4 #4 5 - 1' - - - . . . . "
                     "2' - - 7 2' - 4' - 1' - - 6 4 - 1' - 5 - 3 - 1 - 5, - 1 - - - . . . ."),
         }
    blues = [1, 1, 1, 1, 4, 4, 1, 1, 5, 4, 1, 1]
    kit = kit_clips('surf', prefix='kit')
    s = band(drums={'main': kit}, harmony=('riff',))
    return song(
        stem='spy_hunting', folder='by_genre', title='Spy hunting', genre='TV theme', tempo=112, root='E', kind='minor',
        description='a late fifties spy-jazz theme in the manner of Peter Gunn, with a riff and a tune of its own',
        about="""Spy hunting: a spy theme at 112 beats a minute in E minor, in the manner of the late fifties
        detective shows: a low guitar riff in eighths, doubled by the bass, a surf beat on the ride,
        stabbing brass and a tenor saxophone with the tune. The riff and the tune are its own.

        The riff and the brass are one bar each over chord i, moved through a minor twelve-bar blues
        by a Progression, i i i i iv iv i i v iv i i, so every scene is one chorus of twelve bars.""",
        keep=['Keep the riff and the stabs one bar long over chord i.', 'Keep every scene a twelve-bar chorus.', 'Keep the riff and the tune original.'],
        instruments={'clean guitar': 28, 'pick bass': 35, 'brass': 62, 'tenor sax': 67},
        tracks={**kit_tracks('surf'), 'riff': ('clean guitar', {}), 'bass': ('pick bass', {}), 'stabs': ('brass', {}), 'lead': ('tenor sax', {})},
        patterns=p, progressions={'blues': {'chords': blues}},
        scenes=[
            s('riff', 12, 'blues', 'the guitar riff alone.', kit=None),
            s('drums', 12, 'blues', 'the bass doubles the riff and the drums come in.', extra={'bass': ('riff', ['blues'])}),
            s('brass', 12, 'blues', 'the brass stabs join.', extra={'bass': ('riff', ['blues']), 'stabs': ('stabs', ['blues'])}),
            s('head', 12, 'blues', 'the saxophone plays the tune.', lead='head', extra={'bass': ('riff', ['blues']), 'stabs': ('stabs', ['blues'])}),
            s('head 2', 12, 'blues', 'the tune again.', lead='head', extra={'bass': ('riff', ['blues']), 'stabs': ('stabs', ['blues'])}),
            s('break', 12, 'blues', 'the brass and the riff, no saxophone.', extra={'bass': ('riff', ['blues']), 'stabs': ('stabs', ['blues'])}),
            s('last head', 12, 'blues', 'the tune to the end.', lead='head', extra={'bass': ('riff', ['blues']), 'stabs': ('stabs', ['blues'])}),
        ])


def phoenix_foundation():
    p = {**beat('rock', prefix='kit'),
         'crash': drum('x...............', 'crash'),
         'bass': mel("1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1", octave=2, step='1/16'),
         'guitar': mel("1:5 - 1:5 - . 1:5 - .", octave=3),
         'keys': mel("1:3 - - - - - - -", octave=4),
         'a': mel("1' - 5 - 1' 2' 3' - 1' - 6 - 4' - 1' - 2' - 7 - 5' - 2' . 1' - 6 - 4 - - ."),
         'b': mel("3' - - 1' 6 - 3' . 1' - - 6 4 - 1' . 5' - - 3' 1' - 5' . 2' - 4' - 5' - - ."),
         }
    kit = kit_clips('rock', prefix='kit')
    s = band(drums={'main': kit, 'big': {**kit, 'crash': 'crash'}}, harmony=('bass', 'guitar', 'keys'))
    return song(
        stem='phoenix_foundation', folder='by_genre', title='Phoenix Foundation', genre='TV theme', tempo=130, root='G', kind='major',
        description='a mid-eighties action-show theme in the manner of MacGyver, with a melody of its own',
        about="""Phoenix Foundation: an action-show theme at 130 beats a minute in G major, in the manner of the
        mid-eighties: a synth brass melody, rock guitar chords, a pulsing synth bass in sixteenths and
        sparkling keys. The melody is its own.

        The keys play a held chord, and an arpeggiator called sparkle, in the keys' chains, breaks it
        into sixteenths over two octaves. The bass, the guitar and the keys are one bar each over
        chord I, moved by Progression: the A part goes I IV V IV and the B part vi IV I V.""",
        keep=['Keep the keys a held chord broken up by the sparkle arpeggiator.', 'Keep the bass, guitar and keys one bar long over chord I.',
              'Keep the melody original.'],
        instruments={'synth bass': 39, 'overdriven guitar': 30, 'polysynth': 91, 'synth brass': 63},
        tracks={**kit_tracks('rock'), 'crash': ('drum kit', {}), 'bass': ('synth bass', {}), 'guitar': ('overdriven guitar', {}),
                'keys': ('polysynth', {}), 'lead': ('synth brass', {})},
        patterns=p, progressions={'a': {'chords': [1, 4, 5, 4]}, 'b': {'chords': [6, 4, 1, 5]}},
        arps={'sparkle': {'step': '1/16', 'order': 'up', 'octave_range': 2}},
        chains={'sparkle': [{'arp': 'sparkle'}]},
        scenes=[
            s('intro', 8, 'a', 'the bass, the keys and the drums.', without=('guitar',), chains=['sparkle']),
            s('theme', 16, 'a', 'the theme.', lead='a', chains=['sparkle']),
            s('rise', 8, 'b', 'the second part.', lead='b', kit='big', chains=['sparkle']),
            s('theme 2', 16, 'a', 'the theme again.', lead='a', chains=['sparkle']),
            s('guitar', 16, 'a', 'the band without the melody.', chains=['sparkle']),
            s('rise 2', 8, 'b', 'the second part again.', lead='b', kit='big', chains=['sparkle']),
            s('last theme', 16, 'a', 'the theme to the end.', lead='a', kit='big', chains=['sparkle']),
            s('outro', 8, 'a', 'the band plays out.', chains=['sparkle']),
        ])


def uphill_cops():
    p = {'kick': drum('x.........x.....', 'kick'), 'stick': drum('....x.......x...', 'stick'), 'hat': drum('x...x...x...x...', 'pedal'),
         'chords': mel("1:3 - - - - - - -", octave=4),
         'bass': mel("1 - - - 5, - - -", octave=3),
         'strings': mel("1:3 - - - - - - -", octave=4),
         'melody': mel("3' - - 2' 1' - 5 - 7 - - 5 3 - - - 6 - 1' - 4' - 3' - 2' - - - - - . . "
                       "1' - - 7 6 - 3 - 4 - 6 - 1' - 6 - 2' - 1' - 6 - 4 - 5 - - - - - . ."),
         }
    kit = {'kick': 'kick', 'stick': 'stick', 'hat': 'hat'}
    s = band(drums={'main': kit}, harmony=('chords', 'bass'))
    return song(
        stem='uphill_cops', folder='by_genre', title='Uphill cops', genre='TV theme', tempo=76, root='D', kind='major',
        description='a gentle piano theme in the manner of Hill Street Blues, its chords voice-led, with a melody of its own',
        about="""Uphill cops: a gentle theme at 76 beats a minute in D major, in the manner of the early eighties
        police dramas: a solo piano with the tune, an electric piano with the chords, a fretless bass,
        strings and soft drums. The melody is its own.

        The electric piano and the strings hold one chord a bar, which a Progression moves through
        I iii IV V vi IV ii V, and a Voice leading generator called smooth, after the progression in
        the chains, voices each chord nearest the one before, between octaves 4 and 5, so the chords
        glide rather than jump.""",
        keep=['Keep the chords voice-led by smooth after the progression.', 'Keep the melody original.'],
        instruments={'electric piano': 5, 'fretless bass': 36, 'strings': 49, 'piano': 1},
        tracks={'kick': ('drum kit', {}), 'stick': ('drum kit', {}), 'hat': ('drum kit', {}), 'chords': ('electric piano', {}),
                'bass': ('fretless bass', {}), 'strings': ('strings', {}), 'lead': ('piano', {})},
        patterns=p, progressions={'theme': {'chords': [1, 3, 4, 5, 6, 4, 2, 5]}},
        voice_leadings={'smooth': {'lowest_octave': 4, 'highest_octave': 5}},
        chains={'theme': [{'progression': 'theme'}, {'voice_leading': 'smooth'}]},
        scenes=[
            s('intro', 8, 'theme', 'the chords and the bass.', kit=None),
            s('theme', 16, 'theme', 'the piano with the tune, soft drums.', lead='melody'),
            s('strings', 16, 'theme', 'the strings join.', lead='melody', extra={'strings': ('strings', ['theme'])}),
            s('quiet', 8, 'theme', 'the tune over the chords alone.', lead='melody', kit=None, without=('bass',)),
            s('outro', 8, 'theme', 'the chords and the strings.', kit=None, extra={'strings': ('strings', ['theme'])}),
        ])


def forgot_your_name():
    p = {**beat('ballad', prefix='kit'),
         'piano': mel("1:3 . 1:3 . 1:3 . 1:3 1:3", octave=4),
         'bass': mel("1 - - 5, 1 - - 5,", octave=3),
         'verse': mel("3 - 2 1 5, - 1 . 2 - 4 6 4 - 2 . 6 - 4 1' 6 - 4 . 5 - - 7 2' - . ."),
         'chorus': mel("1' - - 3' 5' - 3' . 1' - - 6 3' - 1' . 2' - - 6 4' - 2' . 7 - 5 - 2' - - ."),
         'bridge': mel("1' - 6 4 1' - . . 2' - 7 5 2' - . . 7 - 5 3 7 - . . 1' - - 6 3 - . ."),
         }
    s = band(drums={'main': kit_clips('ballad', prefix='kit')}, harmony=('piano', 'bass'))
    return song(
        stem='forgot_your_name', folder='by_genre', title='Forgot your name', genre='TV theme', tempo=108, root='Eb', kind='major',
        description='a warm piano sitcom theme in the manner of Cheers, with a melody of its own',
        about="""Forgot your name: a warm sitcom theme at 108 beats a minute in E flat major, in the manner of the
        early eighties: a piano comping on the beats, a bass, soft drums with a side stick, and a
        clarinet singing the tune. The melody is its own.

        The piano and the bass are one bar each over chord I, moved by Progression: the verse goes
        I ii IV V, the chorus goes round I vi ii V, and the bridge IV V iii vi.""",
        keep=['Keep the piano and the bass one bar long over chord I.', 'Keep the melody original.'],
        instruments={'piano': 1, 'finger bass': 34, 'clarinet': 72},
        tracks={**kit_tracks('ballad'), 'piano': ('piano', {}), 'bass': ('finger bass', {}), 'lead': ('clarinet', {})},
        patterns=p, progressions={'verse': {'chords': [1, 2, 4, 5]}, 'chorus': {'chords': [1, 6, 2, 5]}, 'bridge': {'chords': [4, 5, 3, 6]}},
        scenes=[
            s('intro', 4, 'chorus', 'the piano alone.', kit=None, without=('bass',)),
            s('verse', 16, 'verse', 'the verse.', lead='verse'),
            s('chorus', 16, 'chorus', 'the chorus.', lead='chorus'),
            s('verse 2', 16, 'verse', 'the second verse.', lead='verse'),
            s('chorus 2', 16, 'chorus', 'the chorus again.', lead='chorus'),
            s('bridge', 8, 'bridge', 'the bridge.', lead='bridge'),
            s('ending', 4, 'chorus', 'the piano alone.', kit=None, without=('bass',)),
        ])


def tropical_51():
    p = {'kick': drum('x..x..x.x..x..x.', 'kick'), 'tom_lo': drum('x...x...x...x...', 'tom_lo'), 'tom_hi': drum('..x...x...x...x.', 'tom_hi'),
         'snare': drum('....x.......x...', 'snare'), 'crash': drum('x...............', 'crash'),
         'strings': mel("1 3 5 3 1' 5 3 5 1 3 5 3 1' 5 3 5", octave=4, step='1/16'),
         'bass': mel("1 . 1 . 1 . 5, .", octave=3),
         'timpani': mel("1 . . . 1 . 1 .", octave=2),
         'a': mel("1' - - 5 1' - 3' - 5' - - - - - . . 3' - - 1' 6 - 1' - 2' - - 7 5 - . ."),
         'b': mel("4' - - 1' 6 - 1' - 4' - - - - - . . 3' - - 1' 5 - 1' - 5' - - - - - . . "
                  "3' - 1' - 6 - 1' - 2' - 7 - 5 - 2' - 1' - - - - - - - . . . . . . . ."),
         'counter': mel("1 - - - 3 - - - 1 - - - 3 - - - 6, - - - 1 - - - 7, - - - 2 - - -", octave=4),
         }
    toms = {'kick': 'kick', 'tom_lo': 'tom_lo', 'tom_hi': 'tom_hi', 'snare': 'snare'}
    s = band(drums={'main': toms, 'big': {**toms, 'crash': 'crash'}}, harmony=('strings', 'bass', 'timpani'))
    return song(
        stem='tropical_51', folder='by_genre', title='Tropical 51', genre='TV theme', tempo=150, root='C', kind='minor',
        description='a big-band police-show theme in the manner of Hawaii Five-0, with a fanfare of its own',
        about="""Tropical 51: a big-band theme at 150 beats a minute in C minor, in the manner of the late sixties
        police shows: pounding toms, timpani, strings racing in sixteenths, a brass section with the
        fanfare and trombones answering. The fanfare is its own.

        The strings, the bass and the timpani are one bar each over chord i, moved by Progression: the
        A part goes i i VI VII and the B part iv iv i i VI VII i i.""",
        keep=['Keep the strings, bass and timpani one bar long over chord i.', 'Keep the fanfare original.'],
        instruments={'strings': 49, 'acoustic bass': 33, 'timpani': 48, 'brass': 62, 'trombone': 58},
        tracks={'kick': ('drum kit', {}), 'tom_lo': ('drum kit', {}), 'tom_hi': ('drum kit', {}), 'snare': ('drum kit', {}),
                'crash': ('drum kit', {}), 'strings': ('strings', {}), 'bass': ('acoustic bass', {}), 'timpani': ('timpani', {}),
                'lead': ('brass', {}), 'trombone': ('trombone', {})},
        patterns=p, progressions={'a': {'chords': [1, 1, 6, 7]}, 'b': {'chords': [4, 4, 1, 1, 6, 7, 1, 1]}},
        scenes=[
            s('intro', 8, 'a', 'the toms and the strings.', without=('bass', 'timpani')),
            s('fanfare', 16, 'a', 'the brass fanfare.', lead='a', kit='big'),
            s('answer', 16, 'b', 'the second part, the trombones answering.', lead={'lead': 'b', 'trombone': 'counter'}),
            s('fanfare 2', 16, 'a', 'the fanfare again.', lead='a', kit='big'),
            s('answer 2', 16, 'b', 'the second part again.', lead={'lead': 'b', 'trombone': 'counter'}),
            s('drums', 8, 'a', 'the toms and the timpani alone.', without=('strings', 'bass')),
            s('fanfare 3', 16, 'a', 'the fanfare.', lead='a', kit='big'),
            s('last answer', 16, 'b', 'the last answer.', lead={'lead': 'b', 'trombone': 'counter'}, kit='big'),
        ])


def not_painless():
    p = {'stick': drum('x.......x.......', 'stick'), 'hat': drum('x.o.x.o.x.o.x.o.', 'shaker'),
         'guitar': mel("1:3 - - - - - - -", octave=3),
         'bass': mel("1 - - 5, 1 - - -", octave=3),
         'choir': mel("1:3 - - - - - - -", octave=4),
         'melody': mel("5 - - 3 1 - 5 - 6 - - 4 1' - 6 - 7 - - 5 2' - 7 - 5 - - 3 7, - 3 - "
                       "6 - - 1' 3' - 1' - 2' - - 6 4 - 2 - 5 - 7 - 2' - 7 - 1' - - - - - . ."),
         }
    kit = {'stick': 'stick', 'hat': 'hat'}
    s = band(drums={'main': kit}, harmony=('guitar', 'bass'))
    return song(
        stem='not_painless', folder='by_genre', title='Not painless', genre='TV theme', tempo=90, root='G', kind='minor',
        description='a gentle, wistful guitar theme in the manner of M*A*S*H, with a melody of its own',
        about="""Not painless: a gentle theme at 90 beats a minute in G minor, in the manner of the early seventies:
        a nylon guitar picking its chords, a bass, a side stick and a shaker, a choir in the second
        half and a flute with the tune. The melody is its own.

        The guitar holds one chord a bar, which an arpeggiator called picking, in the guitar's chains,
        plays in eighths up and down. The chords go round the circle of fifths in minor,
        i iv VII III VI ii v i, from a Progression.""",
        keep=['Keep the guitar a held chord picked by the arpeggiator.', 'Keep the melody original.'],
        instruments={'nylon guitar': 25, 'acoustic bass': 33, 'choir': 53, 'flute': 74},
        tracks={'stick': ('drum kit', {}), 'hat': ('drum kit', {}), 'guitar': ('nylon guitar', {}), 'bass': ('acoustic bass', {}),
                'choir': ('choir', {}), 'lead': ('flute', {})},
        patterns=p, progressions={'circle': {'chords': [1, 4, 7, 3, 6, 2, 5, 1]}},
        arps={'picking': {'step': '1/8', 'order': 'up_down'}},
        chains={'picking': [{'arp': 'picking'}]},
        scenes=[
            s('intro', 4, 'circle', 'the guitar alone.', kit=None, without=('bass',), extra={'guitar': ('guitar', ['circle', 'picking'])}),
            s('theme', 16, 'circle', 'the flute with the tune.', lead='melody', extra={'guitar': ('guitar', ['circle', 'picking'])}),
            s('choir', 16, 'circle', 'the choir joins.', lead='melody', extra={'guitar': ('guitar', ['circle', 'picking']), 'choir': ('choir', ['circle'])}),
            s('interlude', 8, 'circle', 'the guitar and the choir.', extra={'guitar': ('guitar', ['circle', 'picking']), 'choir': ('choir', ['circle'])}),
            s('theme 2', 16, 'circle', 'the tune again.', lead='melody', extra={'guitar': ('guitar', ['circle', 'picking'])}),
            s('outro', 8, 'circle', 'the guitar alone.', kit=None, extra={'guitar': ('guitar', ['circle', 'picking'])}),
        ])


def mysterious_spooky():
    p = {'snap': drum('....x.......x...', 'claves'), 'kick': drum('x.......x.......', 'kick'),
         'bass': mel("1 . 5, . 1 . 5, .", octave=3),
         'harpsichord': mel("1:3 . . 1:3 . . 1:3 .", octave=4),
         'theme': mel("2 #2 3 . 4 . 6 . 5 #5 6 . 7 . 2' . 1' . 5 . 3 . 1 . . . . . . . . . "
                      "3 #3 4 . 5 . 1' . 6 #6 7 . 1' . 3' . 2' . 7 . 5 . 2 . . . . . . . . ."),
         }
    s = band(drums={'main': {'snap': 'snap', 'kick': 'kick'}, 'snaps': {'snap': 'snap'}}, harmony=('bass', 'harpsichord'))
    return song(
        stem='mysterious_spooky', folder='by_genre', title='Mysterious and spooky', genre='TV theme', tempo=132, root='F', kind='major',
        description='a creepy, kooky harpsichord theme in the manner of The Addams Family, with a tune of its own',
        about="""Mysterious and spooky: a playful theme at 132 beats a minute in F major, in the manner of the mid
        sixties: a harpsichord with a chromatic, creeping tune, finger snaps (claves here) on two and
        four, a tuba-like bass and a church organ. The tune is its own.

        The bass and the harpsichord's chords are one bar each over chord I, moved by Progression
        through ii V I I and then iii vi ii V; the tune creeps up in half steps with accidentals.""",
        keep=['Keep the snaps on two and four.', 'Keep the tune original.'],
        instruments={'tuba': 59, 'harpsichord': 7, 'church organ': 20, 'harpsichord lead': 7},
        tracks={'snap': ('drum kit', {}), 'kick': ('drum kit', {}), 'bass': ('tuba', {}), 'harpsichord': ('harpsichord', {}),
                'lead': ('harpsichord lead', {}), 'organ': ('church organ', {})},
        patterns=p, progressions={'theme': {'chords': [2, 5, 1, 1, 3, 6, 2, 5]}},
        scenes=[
            s('snaps', 4, None, 'the snaps alone.', kit='snaps', without=('bass', 'harpsichord')),
            s('theme', 16, 'theme', 'the harpsichord tune.', lead='theme'),
            s('snaps and bass', 8, 'theme', 'the snaps and the bass.', kit='snaps', without=('harpsichord',)),
            s('theme 2', 16, 'theme', 'the tune again.', lead='theme'),
            s('organ', 16, 'theme', 'the church organ takes the tune.', lead={'organ': 'theme'}),
            s('theme 3', 16, 'theme', 'the harpsichord and the organ together.', lead={'lead': 'theme', 'organ': 'theme'}),
            s('snaps 2', 8, 'theme', 'the snaps and the bass again.', kit='snaps', without=('harpsichord',)),
            s('last theme', 16, 'theme', 'the tune to the end.', lead='theme'),
        ])


SONGS = [sax_reindeer, spy_hunting, phoenix_foundation, uphill_cops, forgot_your_name, tropical_51, not_painless, mysterious_spooky]
