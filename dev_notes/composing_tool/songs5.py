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


def the_mineral():
    p = {'kick': drum('x.........x.x...', 'kick'), 'snare': drum('....x..o.x..x..o', 'snare'), 'hat': drum('xoxoxoxoxoxoxoxo', 'hat'),
         'open': drum('......x.......x.', 'open'), 'crash': drum('x...............', 'crash'),
         'bass': mel("1 . 1 . 7, . 1 3 . 1 . 4 . 3 1 .", octave=2, step='1/16'),
         'stabs': mel("1:3 . . . . . 1:3 . . . 1:3 . . . . .", octave=4, step='1/16'),
         'pad': mel("1:3 - - - - - - -", octave=4),
         'riff': mel("1' . . 1' . . 7 . 5 . . 3 . . 5 . 1' . . 1' . . 3' . 2' . . 7 . 5 - -", step='1/16'),
         'vox': mel("5 - - - - - - - 3 - - - - - - -", octave=5),
         }
    beat_clips = {'kick': 'kick', 'snare': 'snare', 'hat': 'hat', 'open': 'open'}
    s = band(drums={'main': beat_clips, 'big': {**beat_clips, 'crash': 'crash'}, 'hats': {'hat': 'hat'}}, harmony=('bass', 'stabs'))
    slur = ['slur']
    return song(
        stem='the_mineral', folder='by_genre', title='The mineral', genre='Electronic', tempo=128, root='E', kind='minor',
        description="a late-nineties big beat track in the manner of the Crystal Method's Vegas, with riffs of its own",
        about="""The mineral: a big beat track at 128 beats a minute in E minor, in the manner of the Crystal Method's
        album Vegas: a funky breakbeat, a gritty sixteenth-note synth bass that slurs between some notes,
        chord stabs, a screaming saw riff, a sci-fi pad and a wordless synth voice. The riffs are its own.

        The bass's slurs come from a Glide generator called slur, in the bass's chains, which holds a note
        into the next on the steps it marks. The bass and the stabs are one bar each over chord i, moved by
        a Progression through i i VI VII, and the build is a scene whose Density rises from 20% to 100%.""",
        keep=['Keep the bass slurred by the slur Glide generator.', "Keep the build made by the scene's Density.", 'Keep the riffs original.'],
        instruments={'synth bass': 40, 'polysynth': 91, 'saw lead': 82, 'sci-fi pad': 104, 'synth voice': 55},
        tracks={'kick': ('drum kit', {}), 'snare': ('drum kit', {}), 'hat': ('drum kit', {}), 'open': ('drum kit', {}), 'crash': ('drum kit', {}),
                'bass': ('synth bass', {}), 'stabs': ('polysynth', {}), 'lead': ('saw lead', {}), 'pad': ('sci-fi pad', {}), 'vox': ('synth voice', {})},
        patterns=p, progressions={'riff': {'chords': [1, 1, 6, 7]}},
        glides={'slur': {'steps': [False, False, True, False, False, False, True, False], 'glide_amount': '1/32'}},
        chains={'riff': [{'progression': 'riff'}], 'slur': [{'glide': 'slur'}]},
        scenes=[
            s('intro', 8, 'riff', 'the pad and the hats.', kit='hats', without=('bass', 'stabs'), extra={'pad': ('pad', ['riff'])}),
            s('break', 8, 'riff', 'the breakbeat alone.', without=('bass', 'stabs')),
            s('bass', 16, 'riff', 'the slurring bass and the stabs.', extra={'bass': ('bass', ['riff', 'slur'])}),
            s('riff', 16, 'riff', 'the saw riff.', lead='riff', kit='big', extra={'bass': ('bass', ['riff', 'slur'])}),
            s('breakdown', 8, 'riff', 'the pad and the voice, no drums.', kit=None, without=('stabs',),
              extra={'pad': ('pad', ['riff']), 'vox': 'vox', 'bass': ('bass', ['riff', 'slur'])}),
            s('build', 8, 'riff', 'everything returns, Density rising from 20% to 100%.', lead='riff', extra={'bass': ('bass', ['riff', 'slur'])},
              settings={'density_start': 20, 'density_end': 100}),
            s('drop', 16, 'riff', 'the riff, the voice and the full break.', lead='riff', kit='big',
              extra={'bass': ('bass', ['riff', 'slur']), 'vox': 'vox', 'pad': ('pad', ['riff'])}),
            s('outro', 16, 'riff', 'the break and the bass play out.', without=('stabs',), extra={'bass': ('bass', ['riff', 'slur'])}),
        ])


SONGS = [the_mineral]
