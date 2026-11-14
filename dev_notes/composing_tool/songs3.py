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


def strange_woodworking():
    p = {'kick': drum('x...x...x...x...', 'kick'), 'hat': drum('xxxxxxxxxxxxxxxx', 'hat'),
         'sequence': mel("1:3 - - - - - - -", octave=3),
         'bass': mel("1 - - - - - - -", octave=2),
         'pad': mel("1:3 - - - - - - -", octave=4),
         'a': mel("5 - - - 3 - - - 1' - - - 7 - - - 6 - - - 1' - - - 5 - - - - - - -", step='1/4'),
         'b': mel("4 - 6 - 1' - - - 3' - 1' - 7 - - - 2' - 7 - 5 - - - 7 - - - - - - -", step='1/4'),
         }
    kit = {'kick': 'kick', 'hat': 'hat'}
    s = band(drums={'main': kit}, harmony=('sequence', 'bass', 'pad'))
    seq = ['sequence']
    return song(
        stem='strange_woodworking', folder='showcase', title='Strange woodworking', genre='Soundtrack', tempo=100, root='E', kind='minor',
        description='a dark analog-synth score in the manner of Survive and John Carpenter, built on an arpeggiated sequence',
        about="""Strange woodworking: a dark synth score at 100 beats a minute in E minor, in the manner of Survive's
        music for Stranger Things and John Carpenter's films: a sequencer pulsing in sixteenths, a deep
        bass, a cold halo pad, a slow square-wave lead and a machine kick, with a hat that only plays
        where a Euclidean rhythm says.

        The sequence is a held chord broken into sixteenths over two octaves by an arpeggiator called
        sequence. The sequence, the bass and the pad are one bar each over chord i, moved by
        Progression: the main part goes i VI i VI and the rise iv VI VII v. The hat track's own
        Euclidean mask keeps 7 of every 16 sixteenths.""",
        keep=['Keep the sequence a held chord broken up by the arpeggiator.', "Keep the hat's Euclidean mask on its track.",
              'Keep the melody original.'],
        instruments={'synth bass': 39, 'halo pad': 95, 'square lead': 81, 'sequencer': 82},
        tracks={'kick': ('drum kit', {}), 'hat': ('drum kit', {'euclid_hits': 7, 'euclid_steps': 16}), 'sequence': ('sequencer', {}),
                'bass': ('synth bass', {}), 'pad': ('halo pad', {}), 'lead': ('square lead', {})},
        patterns=p, progressions={'dark': {'chords': [1, 6, 1, 6]}, 'rise': {'chords': [4, 6, 7, 5]}},
        arps={'sequence': {'step': '1/16', 'order': 'up', 'octave_range': 2}},
        chains={'sequence': [{'arp': 'sequence'}]},
        scenes=[
            s('sequence', 8, 'dark', 'the sequence alone.', kit=None, without=('bass', 'pad'), chains=seq),
            s('gathering', 8, 'dark', 'the bass and the pad join.', kit=None, chains=seq),
            s('theme', 16, 'dark', 'the kick, the hat and the lead.', lead='a', chains=seq),
            s('rise', 16, 'rise', 'the second part.', lead='b', chains=seq),
            s('alone', 8, 'rise', 'the sequence alone again.', kit=None, without=('bass', 'pad'), chains=seq),
            s('theme 2', 16, 'dark', 'the theme again.', lead='a', chains=seq),
            s('ending', 4, 'dark', 'the pad fades with the sequence.', kit=None, without=('bass',), chains=seq),
        ])


def get_the_traps_egon():
    p = {**beat('funk', prefix='kit'),
         'bass': mel("1 . 1 3 4 . 5 7, 1' . 7 5 4 . 3 .", octave=2),
         'stabs': mel(". 1:3 . . 1:3 . . . . 4:3 . . 1:3 . . .", octave=4),
         'hook': mel("5 5 5 . 7 . 5 . 4 . 3 . 1 . . . 5 5 5 . 1' . 7 . 5 . 4 . 3 - - ."),
         'b': mel("4' - 3' 1' 6 - . . 4' - 3' 1' 6 - . . 1' - 7 5 3 - . . 1' - - - . . . ."),
         'wail': mel("1' - - - - - - - 7 - - - - - - -", octave=5),
         }
    s = band(drums={'main': kit_clips('funk', prefix='kit')}, harmony=('bass', 'stabs'))
    return song(
        stem='get_the_traps_egon', folder='by_genre', title='Get the traps, Egon', genre='Soundtrack', tempo=116, root='G', kind='mixolydian',
        description='a mid-eighties spooky funk-pop film theme in the manner of Ghostbusters, with a riff of its own',
        about="""Get the traps, Egon: a funk-pop film theme at 116 beats a minute in G mixolydian, in the manner of
        the mid-eighties comedy hits: a two-bar synth bass riff, chord stabs, a funk beat, a synth brass
        hook and a sci-fi wail for the ghosts. The riff and the hook are its own.

        The mixolydian scale gives the bass its flat seventh. The riff and the stabs are two bars long
        and play as written, and in the middle part a Progression moves them to IV IV I I.""",
        keep=['Keep the riff and the stabs two bars long.', 'Keep the riff and the hook original.'],
        instruments={'synth bass': 39, 'polysynth': 91, 'synth brass': 63, 'sci-fi': 104},
        tracks={**kit_tracks('funk'), 'bass': ('synth bass', {}), 'stabs': ('polysynth', {}), 'lead': ('synth brass', {}), 'ghost': ('sci-fi', {})},
        patterns=p, progressions={'middle': {'chords': [4, 4, 1, 1]}},
        scenes=[
            s('intro', 8, None, 'the bass riff and the drums.', without=('stabs',)),
            s('riff', 16, None, 'the stabs join.'),
            s('hook', 16, None, 'the brass hook.', lead='hook'),
            s('middle', 8, 'middle', 'the middle part, moved to IV and I.', lead='b'),
            s('hook 2', 16, None, 'the hook again.', lead='hook'),
            s('ghosts', 8, None, 'the drums and the ghostly wail.', without=('bass', 'stabs'), extra={'ghost': 'wail'}),
            s('last hook', 16, None, 'the hook with the wail.', lead='hook', extra={'ghost': 'wail'}),
        ])


def sandworm():
    p = {**beat('trance', prefix='kit'),
         'stab': mel("1 1 1 1 1 . 1 1 1 1 1 1 1 . 1 .", octave=5, step='1/16'),
         'bass': mel(". . 1 . . . 1 . . . 1 . . . 1 .", octave=2, step='1/16'),
         'pad': mel("1:3 - - - - - - -", octave=4),
         }
    trance = kit_clips('trance', prefix='kit')
    s = band(drums={'main': trance, 'thin': {'kick': 'kit_kick', 'hat': 'kit_hat'}}, harmony=('bass',))
    build = {'density_start': 25, 'density_end': 100}
    return song(
        stem='sandworm', folder='by_genre', title='Sandworm', genre='Electronic', tempo=136, root='B', kind='minor',
        description='a late nineties trance anthem in the manner of Sandstorm, its builds made by Density',
        about="""Sandworm: a trance anthem at 136 beats a minute in B minor, in the manner of the late nineties: a
        saw lead hammering a stuttering sixteenth-note rhythm, an off-beat bass, a pad for the
        breakdown and a four-on-the-floor kick. The rhythm is its own.

        The lead and the bass are one bar each over chord i, moved by Progression through i VI VII i.
        The two builds are made by the scenes' Density, from 25% to 100%, which thins every clip to its
        strongest beats and fills it back in, and in the last drop a second lead track, transposed up
        seven scale steps, doubles the first an octave up.""",
        keep=['Keep the builds made by the scenes\' Density.', 'Keep the lead and the bass one bar long over chord i.'],
        instruments={'saw lead': 82, 'synth bass': 39, 'halo pad': 95},
        tracks={**kit_tracks('trance'), 'bass': ('synth bass', {}), 'lead': ('saw lead', {}), 'lead high': ('saw lead', {'transpose': 7}),
                'pad': ('halo pad', {})},
        patterns=p, progressions={'turn': {'chords': [1, 6, 7, 1]}},
        scenes=[
            s('intro', 16, 'turn', 'the kick and the hats.', kit='thin', without=('bass',)),
            s('build', 8, 'turn', 'the bass and the full kit, Density rising from 25% to 100%.', settings=build),
            s('drop', 16, 'turn', 'the lead.', lead={'lead': ('stab', ['turn'])}),
            s('breakdown', 16, 'turn', 'the pad and the bass, no drums.', kit=None, extra={'pad': ('pad', ['turn'])}),
            s('build 2', 8, 'turn', 'the lead returns, Density rising again.', lead={'lead': ('stab', ['turn'])}, settings=build),
            s('drop 2', 16, 'turn', 'the lead and the full kit.', lead={'lead': ('stab', ['turn'])}),
            s('last drop', 16, 'turn', 'the lead doubled an octave up.', lead={'lead': ('stab', ['turn']), 'lead high': ('stab', ['turn'])}),
            s('outro', 8, 'turn', 'the kick and the hats.', kit='thin', without=('bass',)),
        ])


def aliens_counting():
    p = {**beat('rock', prefix='kit'),
         'crash': drum('x...............', 'crash'),
         'guitar': mel("1:5 - 1:5 - 1:5 - 1:5 -", octave=3),
         'bass': mel("1 1 1 1 1 1 1 1", octave=2),
         'pad': mel("1:3 - - - - - - -", octave=4),
         'riff': mel("1' 7 1' . 5 . . . 3' 2' 3' . 1' . . . 6 5 6 . 3 . . . 1' 7 1' . 6 . . . "
                     "4 3 4 . 1 . . . 6 5 6 . 4 . . . 5 4 5 . 2 . . . 7 6 7 . 2' - - -", step='1/16'),
         'verse': mel("5 5 5 3 5 . 1' . 5 5 5 3 5 . 3 . 6 6 6 1' 3' . 1' . 7 - 5 - 2' - - ."),
         }
    kit = kit_clips('rock', prefix='kit')
    s = band(drums={'main': kit, 'big': {**kit, 'crash': 'crash'}}, harmony=('guitar', 'bass', 'pad'))
    return song(
        stem='aliens_counting', folder='by_genre', title='Aliens counting', genre='Rock', tempo=118, root='F#', kind='minor',
        description='a mid-eighties synth-rock anthem in the manner of The Final Countdown, with a fanfare of its own',
        about="""Aliens counting: a synth-rock anthem at 118 beats a minute in F sharp minor, in the manner of the mid
        eighties: a synth brass fanfare in sixteenths, power chords, a pick bass, a pad and a rock beat
        with crashes. The fanfare and the verse are its own.

        The guitar, the bass and the pad are one bar each over chord i, moved by Progression: the
        fanfare goes i VI iv v and the verse i i VI VII.""",
        keep=['Keep the guitar, bass and pad one bar long over chord i.', 'Keep the fanfare original.'],
        instruments={'distortion guitar': 31, 'pick bass': 35, 'polysynth': 91, 'synth brass': 63, 'voice': 54},
        tracks={**kit_tracks('rock'), 'crash': ('drum kit', {}), 'guitar': ('distortion guitar', {}), 'bass': ('pick bass', {}),
                'pad': ('polysynth', {}), 'brass': ('synth brass', {}), 'lead': ('voice', {})},
        patterns=p, progressions={'fanfare': {'chords': [1, 6, 4, 5]}, 'verse': {'chords': [1, 1, 6, 7]}},
        scenes=[
            s('intro', 8, 'fanfare', 'the pad alone.', kit=None, without=('guitar', 'bass')),
            s('fanfare', 8, 'fanfare', 'the brass fanfare.', lead={'brass': 'riff'}, kit='big'),
            s('verse', 16, 'verse', 'the verse.', lead='verse'),
            s('fanfare 2', 8, 'fanfare', 'the fanfare again.', lead={'brass': 'riff'}, kit='big'),
            s('verse 2', 16, 'verse', 'the second verse.', lead='verse'),
            s('fanfare 3', 8, 'fanfare', 'the fanfare.', lead={'brass': 'riff'}, kit='big'),
            s('solo', 8, 'fanfare', 'the fanfare an octave down on the voice.', lead={'lead': 'riff'}),
            s('last fanfare', 16, 'fanfare', 'the fanfare to the end.', lead={'brass': 'riff'}, kit='big'),
        ])


def angry_shark():
    p = {'lurk': mel("1 - - - b2 - - -", octave=2),
         'approach': mel("1 b2 1 b2 1 b2 1 b2", octave=2),
         'attack': mel("1 b2 1 b2 1 b2 1 b2 1 b2 1 b2 1 b2 1 b2", octave=2, step='1/16'),
         'cellos': mel("1 b2 1 b2 1 b2 1 b2", octave=3),
         'timpani': mel("1 . . . . . . . 1 . . . 1 . 1 .", octave=2, step='1/16'),
         'horns': mel("1' - - 7 6 - 5 - 1' - - 7 6 - 3' - 2' - - 1' 7 - 6 - 5 - - - - - - -"),
         'tuba': mel("1 - - - - - - - b2 - - - - - - -", octave=2),
         'hits': drum('x.......x...x.x.', 'tom_lo'),
         }
    return song(
        stem='angry_shark', folder='by_genre', title='Angry shark', genre='Soundtrack', tempo=140, root='E', kind='minor',
        description='a menacing orchestral film score in the manner of Jaws, two low notes speeding up as the shark comes',
        about="""Angry shark: an orchestral score in E minor, in the manner of the mid-seventies thrillers: two low
        notes a half step apart in the double basses, slow at first and faster as the danger comes,
        cellos, a tuba, timpani, low toms and horns with a call of their own.

        The scenes ramp the tempo: the approach speeds up from 70 to 140 beats a minute across its
        bars, the attack and the chase stay at 150, the retreat slows from 150 back to 70, and the last
        scene lurks at 70 again.""",
        keep=['Keep the tempo ramps on the approach and the retreat.', 'Keep the horn call original.'],
        instruments={'contrabass': 44, 'cello': 43, 'tuba': 59, 'timpani': 48, 'horns': 61},
        tracks={'basses': ('contrabass', {}), 'cellos': ('cello', {}), 'tuba': ('tuba', {}), 'timpani': ('timpani', {}),
                'hits': ('drum kit', {}), 'horns': ('horns', {})},
        patterns=p,
        scenes=[
            ('lurking', 8, {'basses': 'lurk'}, 'the basses alone, slowly.', {'tempo': 70}),
            ('approach', 16, {'basses': 'approach', 'cellos': 'cellos'}, 'the cellos join, speeding up from 70 to 140.', {'tempo_start': 70, 'tempo_end': 140}),
            ('attack', 16, {'basses': 'attack', 'cellos': 'cellos', 'tuba': 'tuba', 'timpani': 'timpani', 'hits': 'hits'},
             'the basses in sixteenths, the tuba, timpani and toms.', {'tempo': 150}),
            ('chase', 16, {'basses': 'attack', 'cellos': 'cellos', 'tuba': 'tuba', 'timpani': 'timpani', 'hits': 'hits', 'horns': 'horns'},
             'the horns call.', {'tempo': 150}),
            ('chase 2', 8, {'basses': 'attack', 'cellos': 'cellos', 'tuba': 'tuba', 'timpani': 'timpani', 'hits': 'hits', 'horns': 'horns'},
             'the call again.', {'tempo': 150}),
            ('retreat', 8, {'basses': 'approach', 'cellos': 'cellos'}, 'slowing from 150 to 70.', {'tempo_start': 150, 'tempo_end': 70}),
            ('lurking again', 8, {'basses': 'lurk'}, 'the basses alone.', {'tempo': 70}),
        ])


def very_large_mammals():
    p = {**beat('shuffle', prefix='kit'),
         'bass': mel("1 3 5 6 b7 6 5 3", octave=3),
         'organ': mel(". 1:3 . 1:3 . 1:3 . 1:3", octave=4),
         'horns': mel(". . . . 1:dom7 . . .", octave=4),
         'tune': mel("1' . 1' 2' 3' . 1' . 6 . 6 1' 4' . 1' . 5 . 5 6 1' . 3' . 5 - - - . . . . "
                     "6 . 6 1' 4' . 1' . 6 . 6 1' 4' . 6 . 5 . 5 6 1' . 3' . 1' - - - . . . . "
                     "7 . 7 2' 5' . 2' . 6 . 6 1' 4' . 1' . 5 . 3' . 1' . 5 . 7 - - - 2' - - ."),
         }
    blues = [1, 4, 1, 1, 4, 4, 1, 1, 5, 4, 1, 5]
    s = band(drums={'main': kit_clips('shuffle', prefix='kit')}, harmony=('bass', 'organ'))
    return song(
        stem='very_large_mammals', folder='by_genre', title='Very large mammals', genre='Soundtrack', tempo=112, root='F', kind='major',
        description='a lumbering boogie-woogie film tune in the manner of Baby Elephant Walk, with a tune of its own',
        about="""Very large mammals: a boogie-woogie tune at 112 beats a minute in F major, shuffled by the factory
        groove 8th swing 66, in the manner of the early sixties film scores: a walking boogie bass, an
        organ on the off-beats, horn stabs and a calliope with a playful tune of its own.

        The boogie bass, the organ and the horns are one bar each over chord I, moved through the
        twelve-bar blues, I IV I I IV IV I I V IV I V, by a Progression, so every scene is a chorus of
        twelve bars. The horns play a dom7, which stays a dominant seventh on every chord.""",
        keep=['Keep every scene a twelve-bar chorus.', 'Keep the horns\' chord a dom7.', 'Keep the tune original.'],
        instruments={'acoustic bass': 33, 'organ': 17, 'brass': 62, 'calliope': 83},
        tracks={**kit_tracks('shuffle'), 'bass': ('acoustic bass', {}), 'organ': ('organ', {}), 'horns': ('brass', {}), 'lead': ('calliope', {})},
        patterns=p, progressions={'blues': {'chords': blues}}, groove='8th swing 66',
        scenes=[
            s('boogie', 12, 'blues', 'the bass, the organ and the drums.'),
            s('tune', 12, 'blues', 'the calliope tune.', lead='tune'),
            s('horns', 12, 'blues', 'the tune with the horns.', lead='tune', extra={'horns': ('horns', ['blues'])}),
            s('walk', 12, 'blues', 'the horns and the band, no tune.', extra={'horns': ('horns', ['blues'])}),
            s('tune 2', 12, 'blues', 'the tune again.', lead='tune'),
            s('stomp', 12, 'blues', 'the bass and the drums alone.', without=('organ',)),
            s('last tune', 12, 'blues', 'the tune with everything.', lead='tune', extra={'horns': ('horns', ['blues'])}),
        ])


def four_wheels_g():
    p = {**beat('funk', prefix='kit'),
         'clap': drum('....x.......x...', 'clap'),
         'bass': mel("1 1' 1 1' . 1 1' 1 1 1' 1 1' . 1 1' 1", octave=2, step='1/16'),
         'pad': mel(". 1:3 . . 1:3 . . .", octave=4),
         'hook': mel("1 . 1' . 7 5 . 4 5 . 3 . 1 . 5, . 6, . 6 . 1 3 . 6 7, . 2 . 5 - - ."),
         'b': mel("1' - 6 - 3' - 1' . 2' - 7 - 4' - 2' . 3' - 1' - 5 - 3 . 1' - - - . . . ."),
         'bells': mel("1' 5 3 5 1' 5 3 5", octave=5),
         }
    kit = {**kit_clips('funk', prefix='kit'), 'clap': 'clap'}
    s = band(drums={'main': kit}, harmony=('bass', 'pad'))
    return song(
        stem='four_wheels_g', folder='by_genre', title='Four wheels G', genre='Soundtrack', tempo=118, root='F', kind='minor',
        description='a mid-eighties synth film theme in the manner of Axel F, with a hook of its own',
        about="""Four wheels G: a synth theme at 118 beats a minute in F minor, in the manner of the mid-eighties
        action comedies: a staccato saw lead leaping octaves, a bouncing octave bass in sixteenths, chord
        stabs, bells and a drum machine with a clap. The hook is its own.

        The bass and the stabs are one bar each over chord i, moved by Progression: the hook goes
        i i iv v and the second part VI VII i i.""",
        keep=['Keep the bass and the stabs one bar long over chord i.', 'Keep the hook original.'],
        instruments={'synth bass': 40, 'polysynth': 91, 'saw lead': 82, 'crystal': 99},
        tracks={**kit_tracks('funk'), 'clap': ('drum kit', {}), 'bass': ('synth bass', {}), 'pad': ('polysynth', {}),
                'lead': ('saw lead', {}), 'bells': ('crystal', {})},
        patterns=p, progressions={'hook': {'chords': [1, 1, 4, 5]}, 'b': {'chords': [6, 7, 1, 1]}},
        scenes=[
            s('intro', 8, 'hook', 'the bass and the drums.', without=('pad',)),
            s('hook', 16, 'hook', 'the hook.', lead='hook'),
            s('second part', 8, 'b', 'the second part.', lead='b'),
            s('hook 2', 16, 'hook', 'the hook again.', lead='hook'),
            s('bells', 8, 'hook', 'the drums and the bells.', without=('bass', 'pad'), extra={'bells': ('bells', ['hook'])}),
            s('hook 3', 16, 'hook', 'the hook with the bells.', lead='hook', extra={'bells': ('bells', ['hook'])}),
            s('second part 2', 8, 'b', 'the second part again.', lead='b'),
            s('last hook', 8, 'hook', 'the hook to the end.', lead='hook'),
        ])


def microwave_snacks():
    p = {**beat('disco', prefix='kit'),
         'bass': mel("1 . 1 . 1 . 1 .", octave=2),
         'a': mel("1' 5 1' 3 1' 5 . . 1' 5 1' 3 1' 5 . . 1' 6 1' 4 1' 6 . . 7 5 7 3 7 5 . .", step='1/16'),
         'b': mel("3' 1' 3' 6 3' 1' . . 3' 1' 3' 6 3' 1' . . 2' 7 2' 5 2' 7 . . 2' 7 2' 5 2' 7 . .", step='1/16'),
         'blips': drum('x.x.x.x.x.x.x.x.', 'claves'),
         }
    s = band(drums={'main': kit_clips('disco', prefix='kit')}, harmony=('bass',))
    return song(
        stem='microwave_snacks', folder='by_genre', title='Microwave snacks', genre='Electronic', tempo=130, root='A', kind='minor',
        description='an early-seventies Moog novelty tune in the manner of Popcorn, with a tune of its own',
        about="""Microwave snacks: a synthesizer novelty tune at 130 beats a minute in A minor, in the manner of the
        early seventies: a staccato square lead whose tune bounces off a high repeated note, a synth bass
        on the eighths, a disco beat and claves blipping where a Euclidean rhythm says. The tune is its own.

        The lead plays every other sixteenth on its high note, the trick of the style, and the tune in
        between. The bass is one bar over chord i, moved by Progression: the A part goes i iv and the B
        part VI v. The claves' track keeps 5 of every 8 steps by its Euclidean mask.""",
        keep=['Keep the high repeated note between the tune\'s notes.', 'Keep the tune original.'],
        instruments={'synth bass': 39, 'square lead': 81},
        tracks={**kit_tracks('disco'), 'blips': ('drum kit', {'euclid_hits': 5, 'euclid_steps': 8}), 'bass': ('synth bass', {}),
                'lead': ('square lead', {})},
        patterns=p, progressions={'a': {'chords': [1, 4]}, 'b': {'chords': [6, 5]}},
        scenes=[
            s('intro', 8, 'a', 'the bass and the drums.'),
            s('A', 16, 'a', 'the bouncing tune.', lead='a'),
            s('B', 8, 'b', 'the second tune.', lead='b'),
            s('A 2', 16, 'a', 'the tune with the claves.', lead='a', extra={'blips': 'blips'}),
            s('alone', 8, 'a', 'the lead alone.', kit=None, without=('bass',), lead='a'),
            s('A 3', 16, 'a', 'the tune again.', lead='a', extra={'blips': 'blips'}),
            s('B 2', 8, 'b', 'the second tune again.', lead='b', extra={'blips': 'blips'}),
            s('last A', 16, 'a', 'the tune to the end.', lead='a'),
        ])


def nomore_nomore():
    p = {**beat('eurodance', prefix='kit'),
         'bass': mel(". . 1 . . . 1 . . . 1 . . . 1 .", octave=2, step='1/16'),
         'piano': mel("1:3 . . 1:3 . . 1:3 . . . 1:3 . . . . .", octave=4, step='1/16'),
         'pad': mel("1:3 - - - - - - -", octave=4),
         'verse': mel("5 . 5 . 3 5 . 1 6 . 6 . 1' 6 . 3 5 . 5 . 7 5 . 3 7 . 7 . 2' - - ."),
         'chorus': mel("1' - 1' 3' 5' - 3' . 1' - 1' 3' 6 - 3 . 7 - 7 1' 3' - 5 . 2' - 7 - 4' - - ."),
         }
    s = band(drums={'main': kit_clips('eurodance', prefix='kit')}, harmony=('bass', 'piano', 'pad'))
    return song(
        stem='nomore_nomore', folder='by_genre', title='No more, no more', genre='Electronic', tempo=124, root='D', kind='minor',
        description='an early-nineties eurodance song in the manner of What Is Love, with a melody of its own',
        about="""No more, no more: a eurodance song at 124 beats a minute in D minor, in the manner of the early
        nineties: an off-beat synth bass, a piano stabbing a syncopated rhythm, a pad, a driving kit with
        sixteenth hats and a singing synth voice. The melody is its own.

        The bass, the piano and the pad are one bar each over chord i, moved through i VI III VII by a
        Progression.""",
        keep=['Keep the bass, piano and pad one bar long over chord i.', 'Keep the melody original.'],
        instruments={'synth bass': 39, 'piano': 1, 'new age pad': 89, 'synth voice': 55},
        tracks={**kit_tracks('eurodance'), 'bass': ('synth bass', {}), 'piano': ('piano', {}), 'pad': ('new age pad', {}),
                'lead': ('synth voice', {})},
        patterns=p, progressions={'turn': {'chords': [1, 6, 3, 7]}},
        scenes=[
            s('intro', 8, 'turn', 'the piano and the drums.', without=('bass', 'pad')),
            s('verse', 16, 'turn', 'the verse.', lead='verse'),
            s('chorus', 16, 'turn', 'the chorus.', lead='chorus'),
            s('break', 8, 'turn', 'the pad and the chorus, no drums.', kit=None, lead='chorus', without=('piano',)),
            s('verse 2', 16, 'turn', 'the second verse.', lead='verse'),
            s('chorus 2', 16, 'turn', 'the chorus again.', lead='chorus'),
            s('last chorus', 8, 'turn', 'the chorus once more.', lead='chorus'),
            s('outro', 4, 'turn', 'the piano and the drums.', without=('bass', 'pad')),
        ])


SONGS = [strange_woodworking, get_the_traps_egon, sandworm, aliens_counting, angry_shark, very_large_mammals, four_wheels_g,
         microwave_snacks, nomore_nomore]
