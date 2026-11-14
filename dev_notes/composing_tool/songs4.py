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


def fang_removal():
    p = {**beat('game', prefix='kit'),
         'bass': mel("1 1' 1 1' 1 1' 1 1'", octave=2),
         'a': mel("1' 5 1' 3' 2' 1' 7 5 6 1' 3' 1' 6 3 6 1' 4 6 1' 4' 3' 1' 6 4 5 7 2' 4' 2' 7 5 7"),
         'b': mel("4' - 3' - 1' - 6 - 3' - 1' - 5 - 3 - 2' - 7 - 5 - 7 - 1' - - - . . . ."),
         }
    s = band(drums={'main': kit_clips('game', prefix='kit')}, harmony=('bass',))
    return song(
        stem='fang_removal', folder='by_genre', title='Fang removal', genre='Video game', tempo=150, root='D', kind='harmonic_minor',
        description="a gothic eight-bit stage theme in the manner of Castlevania's Vampire Killer, with a melody of its own",
        about="""Fang removal: a gothic stage theme at 150 beats a minute in D harmonic minor, in the manner of the
        eight-bit castle games: a square-wave lead, a second square a third below it, a driving octave
        bass and a busy kit. The melody is its own.

        The harmonic minor scale makes the fifth chord major, with its sharp seventh, which gives the
        style its gothic pull. The bass is one bar over chord i, moved by Progression: the A part goes
        i VI iv V and the B part iv i V i. The harmony track plays the lead's pattern transposed two
        scale steps down.""",
        keep=['Keep the harmonic minor scale.', 'Keep the harmony track a transposed copy of the lead.', 'Keep the melody original.'],
        instruments={'synth bass': 39, 'square lead': 81, 'square harmony': 81},
        tracks={**kit_tracks('game'), 'bass': ('synth bass', {}), 'lead': ('square lead', {}), 'harmony': ('square harmony', {'transpose': -2})},
        patterns=p, progressions={'a': {'chords': [1, 6, 4, 5]}, 'b': {'chords': [4, 1, 5, 1]}},
        scenes=[
            s('intro', 8, 'a', 'the bass and the drums.'),
            s('A', 16, 'a', 'the lead.', lead='a'),
            s('B', 8, 'b', 'the second part.', lead='b'),
            s('A harmony', 16, 'a', 'the lead with its harmony.', lead={'lead': 'a', 'harmony': 'a'}),
            s('bridge', 8, 'b', 'the harmony alone.', lead={'harmony': 'b'}),
            s('A 2', 16, 'a', 'the lead again.', lead='a'),
            s('B 2', 8, 'b', 'the second part with harmony.', lead={'lead': 'b', 'harmony': 'b'}),
            s('A 3', 16, 'a', 'the lead with harmony.', lead={'lead': 'a', 'harmony': 'a'}),
            s('last A', 16, 'a', 'the lead to the end.', lead={'lead': 'a', 'harmony': 'a'}),
        ])


def not_werewolves():
    p = {**beat('ballad', prefix='kit'),
         'stride': mel("1 . 1:3 . 5, . 1:3 .", octave=3),
         'stride_tune': mel("5 6 5 3 1' - 5 . 6 1' 6 3 1' - 6 . 2' 1' 6 4 2' - 6 . 5 7 2' 5' 4' - 2' ."),
         'piano': mel("1 5 1' 3' 5' 3' 1' 5", octave=3),
         'bass': mel("1 - - - 5, - - -", octave=3),
         'strings': mel("1:3 - - - - - - -", octave=4),
         'verse': mel("3 - 3 2 1 - 5, - 4 - 6 - 1' - - - 5 - 3 - 1 - 3 - 2 - - - . . . . "
                      "3 - 3 5 1' - 5 - 6 - 4 - 1' - 6 - 5 - 7 - 2' - 7 - 1' - - - . . . ."),
         'chorus': mel("1' - - 6 4 - 6 - 1' - - 5 3 - 5 - 2' - - 7 5 - 7 - 3' - - 1' 6 - - - "
                       "4' - - 1' 6 - 1' - 5' - - 3' 1' - 3' - 2' - 7 - 5 - 7 - 2' - - - . . . ."),
         }
    s = band(drums={'main': kit_clips('ballad', prefix='kit')}, harmony=('piano', 'bass'))
    return song(
        stem='not_werewolves', folder='by_genre', title='Not werewolves', genre='Rock', tempo=80, root='G', kind='major',
        description="a piano ballad of outlaws in the manner of Warren Zevon's Frank and Jesse James, opening with stride piano",
        about="""Not werewolves: a piano ballad in G major in the manner of Warren Zevon's Frank and Jesse James,
        opening with a stride piano at 150 beats a minute, its left hand leaping from bass note to chord,
        before the ballad settles at 80: a rolling piano, a bass, soft drums, strings in the choruses and
        a fiddle with the tune. Every note of the melody is its own.

        The stride scene has a tempo of its own. The stride left hand, the rolling piano and the bass
        are one bar each over chord I, moved by Progression: the stride goes I vi ii V, the verse
        I IV I V I IV V I and the chorus IV I V vi IV I V V.""",
        keep=['Keep the stride intro at its own faster tempo.', 'Keep the melody original.'],
        instruments={'piano': 1, 'stride piano': 1, 'acoustic bass': 33, 'strings': 49, 'fiddle': 41},
        tracks={**kit_tracks('ballad'), 'stride': ('stride piano', {}), 'piano': ('piano', {}), 'bass': ('acoustic bass', {}),
                'strings': ('strings', {}), 'lead': ('fiddle', {})},
        patterns=p, progressions={'stride': {'chords': [1, 6, 2, 5]}, 'verse': {'chords': [1, 4, 1, 5, 1, 4, 5, 1]},
                                  'chorus': {'chords': [4, 1, 5, 6, 4, 1, 5, 5]}},
        scenes=[
            s('stride', 8, None, 'the stride piano alone, at 150.', kit=None, without=('piano', 'bass'),
              extra={'stride': ('stride', ['stride']), 'lead': 'stride_tune'}, settings={'tempo': 150}),
            s('verse', 16, 'verse', 'the ballad, the fiddle with the tune.', lead='verse'),
            s('chorus', 8, 'chorus', 'the chorus with strings.', lead='chorus', extra={'strings': ('strings', ['chorus'])}),
            s('verse 2', 16, 'verse', 'the second verse.', lead='verse'),
            s('chorus 2', 8, 'chorus', 'the chorus again.', lead='chorus', extra={'strings': ('strings', ['chorus'])}),
            s('outro', 8, 'chorus', 'the piano and strings alone.', kit=None, extra={'strings': ('strings', ['chorus'])}),
        ])


def annandale():
    p = {**beat('rock', prefix='kit'),
         'keys': mel("1:7 . . 1:7 . 1:7 . .", octave=4),
         'bass': mel("1 . 1 5, 1 . 3 5", octave=3),
         'horns': mel("5 . 3 5 6 . 5 3 1' . 6 4 6 . 1' .", octave=4),
         'verse': mel("5 5 5 3 5 - - . 6 6 6 4 6 - - . 5 5 5 3 1 - 3 . 4 - - - . . . . "
                      "2 2 4 6 1' - 6 . 2' - 7 5 2' - - . 3' - 1' - 5 - 3 - 1 - - - . . . ."),
         'chorus': mel("1' - 6 - 4 - 6 - 2' - 7 - 5 - 7 - 3' - 7 - 5 - 3 - 1' - 6 - 3 - 6 - "
                       "4' - 2' - 6 - 4 - 5' - 2' - 7 - 5 - 3' - - - 1' - - - . . . . . . . ."),
         }
    s = band(drums={'main': kit_clips('rock', prefix='kit')}, harmony=('keys', 'bass'))
    horns = {'horns': 'horns', 'horns 2': 'horns'}
    return song(
        stem='annandale', folder='by_genre', title='Annandale', genre='Rock', tempo=128, root='G', kind='major',
        description="a seventies jazz-rock song in the manner of Steely Dan's My Old School, with a horn line of its own",
        about="""Annandale: a jazz-rock song at 128 beats a minute in G major, lightly swung by the factory groove
        8th swing 58, in the manner of Steely Dan's My Old School: an electric piano comping in seventh
        chords, a bass, a rock beat, a horn section answering in thirds and a tenor saxophone with the
        tune. The horn line and the melody are its own.

        The electric piano plays the scale chord 7, a seventh chord built of the scale's own notes,
        which the Progression moves to a major seventh, a minor seventh or a dominant one as the scale
        says. The keys and the bass are one bar each over chord I: the verse goes I IV I IV ii V I I and
        the chorus IV V iii vi ii V I I. The second horn track plays the horn line two scale steps down.""",
        keep=['Keep the keys on the scale chord 7.', 'Keep the second horn a transposed copy of the first.', 'Keep the melody original.'],
        instruments={'electric piano': 5, 'finger bass': 34, 'brass': 62, 'trombone': 58, 'tenor sax': 67},
        tracks={**kit_tracks('rock'), 'keys': ('electric piano', {}), 'bass': ('finger bass', {}), 'horns': ('brass', {}),
                'horns 2': ('trombone', {'transpose': -2}), 'lead': ('tenor sax', {})},
        patterns=p, groove='8th swing 58',
        progressions={'verse': {'chords': [1, 4, 1, 4, 2, 5, 1, 1]}, 'chorus': {'chords': [4, 5, 3, 6, 2, 5, 1, 1]}},
        scenes=[
            s('horns', 8, 'verse', 'the horn line.', extra=horns),
            s('verse', 16, 'verse', 'the verse.', lead='verse'),
            s('chorus', 16, 'chorus', 'the chorus.', lead='chorus'),
            s('horns 2', 8, 'verse', 'the horn line again.', extra=horns),
            s('verse 2', 16, 'verse', 'the second verse.', lead='verse'),
            s('chorus 2', 16, 'chorus', 'the chorus again.', lead='chorus'),
            s('horns 3', 8, 'verse', 'the horn line.', extra=horns),
            s('last chorus', 8, 'chorus', 'the last chorus with the horns.', lead='chorus', extra=horns),
        ])


def volcano():
    up = "1 3 4 5 7 1' 3' 4' 5' 7' 1'' 7' 5' 4' 3' 1' 7 5 4 3 1 3 4 5 7 1' 3' 5' 1'' - - -"
    p = {'kick': drum('x...............', 'kick'), 'crash': drum('x...............', 'crash'),
         'snare': drum('x.x.x.x.xxxxxxxx', 'snare'),
         'hits': mel("1:pow - - - - - - -", octave=3),
         'bass': mel("1 - - - - - - -", octave=2),
         'runs': mel(up, octave=4, step='1/32'),
         'tap': mel("1:3 - - - - - - -", octave=4),
         'trill': mel("1' 2' " * 16, octave=4, step='1/32'),
         }
    hits = {'kick': 'kick', 'crash': 'crash'}
    return song(
        stem='volcano', folder='by_genre', title='Volcano', genre='Rock', tempo=120, root='E', kind='minor',
        description="a solo guitar showpiece in the manner of Van Halen's Eruption: runs, trills and tapped arpeggios",
        about="""Volcano: a solo guitar showpiece at 120 beats a minute in E minor, in the manner of Van Halen's
        Eruption: the band hits a chord and leaves the guitar alone for runs in thirty-second notes,
        trills, and tapped arpeggios in sextuplets, before the band comes back to end it.

        The runs are one bar, moved by a Progression through i i VI VII. The tapping is a held chord broken
        up by an arpeggiator called tapping, in sixteenth-note triplets over two octaves, up and down,
        while a Progression moves the chord through i VI iv v.""",
        keep=['Keep the tapping a held chord broken up by the arpeggiator.', 'Keep the guitar alone between the band\'s hits.'],
        instruments={'distortion guitar': 31, 'rhythm guitar': 31, 'pick bass': 35},
        tracks={'kick': ('drum kit', {}), 'crash': ('drum kit', {}), 'snare': ('drum kit', {}), 'rhythm': ('rhythm guitar', {}),
                'bass': ('pick bass', {}), 'guitar': ('distortion guitar', {})},
        patterns=p, progressions={'runs': {'chords': [1, 1, 6, 7]}, 'tapping': {'chords': [1, 6, 4, 5]}},
        arps={'tapping': {'step': '1/24', 'order': 'up_down', 'octave_range': 2}},
        chains={'tap': [{'progression': 'tapping'}, {'arp': 'tapping'}]},
        scenes=[
            ('hits', 8, {**hits, 'rhythm': ('hits', ['runs']), 'bass': ('bass', ['runs'])}, 'the band hits a chord a bar.'),
            ('runs', 16, {'guitar': ('runs', ['runs'])}, 'the guitar alone, running.'),
            ('tapping', 32, {'guitar': ('tap', ['tap'])}, 'the tapped arpeggios.'),
            ('trill', 8, {'guitar': 'trill'}, 'a trill.'),
            ('tapping 2', 16, {'guitar': ('tap', ['tap']), 'bass': ('bass', ['tapping'])}, 'the tapping with the bass.'),
            ('ending', 8, {**hits, 'snare': 'snare', 'rhythm': ('hits', ['runs']), 'bass': ('bass', ['runs']), 'guitar': ('runs', ['runs'])},
             'the band back, the guitar running over it.'),
        ])


def incoming_message():
    patterns, progressions, scenes, scales = {}, {}, [], {}
    lead_tracks = {'square': 'lead', 'guitar': 'guitar', 'saw': 'saw'}
    for number, (root, kind, prog, lead, bass, style, instrument) in enumerate(STAGES):
        stage = f'stage_{number}'
        scale_name = f'{root} {kind.replace("_", " ").title()}'
        scales[scale_name] = {'root': root, 'type': kind}
        progressions[stage] = {'chords': prog}
        patterns[f'{stage}_lead'] = mel(lead, octave=5 if instrument == 'square' else 4)
        patterns[f'{stage}_bass'] = mel(BASSES[bass], octave=2)
        patterns[f'{stage}_chords'] = mel("1:3 - - - - - - -", octave=4)
        drums = {}
        for voice, line in BEATS[style].items():
            patterns[f'{stage}_{voice}'] = drum(line, voice)
            drums[voice] = f'{stage}_{voice}'
        harmony = {'bass': (f'{stage}_bass', [stage]), 'chip': (f'{stage}_chords', [stage, 'chip'])}
        melody = lead_tracks[instrument]
        if number:
            patterns[f'{stage}_transition_snare'] = drum('x.x.x.x.xxxxxxxx', 'snare')
            patterns[f'{stage}_transition_crash'] = drum('x...............', 'crash')
            patterns[f'{stage}_transition_rise'] = mel("1 3 5 1' 3' 5' 1'' 3'' 5'' 1''' - - - - - -", octave=3, step='1/16')
            scenes.append((f'to {stage}', 1, {'snare': f'{stage}_transition_snare', 'crash': f'{stage}_transition_crash',
                                              'chip': f'{stage}_transition_rise'}, f'a one-bar fill into {stage}.', {'scale': scale_name}))
        scenes.append((f'{stage}, {STAGE_NAMES[number]}', 16, {**drums, **harmony, melody: f'{stage}_lead'},
                       f'{STAGE_NAMES[number]}, in {root} {kind.replace("_", " ")}, on the {instrument}.', {'scale': scale_name}))
        scenes.append((f'{stage}, doubled', 16, {**drums, **harmony, melody: f'{stage}_lead', 'harmony': f'{stage}_lead'},
                       'the tune again with a harmony two steps below.', {'scale': scale_name}))
    voices = sorted({v for style in ('game', 'rock', 'four', 'punk', 'eurodance') for v in BEATS[style]} | {'crash'})
    return song(
        stem='incoming_message', folder='by_genre', title='Incoming message', genre='Video game', tempo=150, root='E', kind='minor',
        extra_scales=scales,
        description="nine minutes after Mega Man 2's intro and boss themes: ten stages, each a theme of its own, ending on the intro",
        about="""Incoming message: nine minutes of stage themes at 150 beats a minute, after Mega Man 2's intro and boss
        themes and the great Japanese game composers: ten stages, each in a key of its own, changing theme
        exactly nine times, with a one-bar fill and a rising chip arpeggio between each, and the last a
        reprise of the first. Every theme is its own.

        Each stage's patterns are named after it, stage_0 to stage_9. Each stage is two scenes, the tune
        and the tune doubled by a harmony two scale steps below, and every scene sets its stage's scale.
        The chip track plays a held chord broken into thirty-second notes by the arpeggiator called chip,
        the way the old sound chips played chords, and a Progression for each stage moves it and the bass.
        The tune passes between instruments fit for the composers and the bands that play their music: a
        square wave, a distortion guitar and a saw lead.""",
        keep=['Keep the patterns named after their stage.', 'Keep exactly nine changes of theme, with a one-bar fill between each.',
              'Keep the last stage a reprise of the first.', 'Keep the themes original.'],
        instruments={'synth bass': 39, 'chip': 81, 'square lead': 81, 'distortion guitar': 31, 'saw lead': 82, 'harmony': 82},
        tracks={**{v: ('drum kit', {}) for v in voices}, 'bass': ('synth bass', {}), 'chip': ('chip', {}), 'lead': ('square lead', {}),
                'guitar': ('distortion guitar', {}), 'saw': ('saw lead', {}), 'harmony': ('harmony', {'transpose': -2})},
        patterns=patterns, progressions=progressions,
        arps={'chip': {'step': '1/32', 'order': 'up'}},
        chains={**{name: [{'progression': name}] for name in progressions}, 'chip': [{'arp': 'chip'}]},
        scenes=scenes)


SONGS = [fang_removal, not_werewolves, annandale, volcano, incoming_message]
