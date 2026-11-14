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
"""What the visualizers are called on screen.

Each constant starts with MSG_.
"""

# visualizers/lava_lamp.py
MSG_LAVA_LAMP = 'Lava lamp'

# visualizers/milkdrop.py
MSG_MILKDROP = 'MilkDrop'

# visualizers/spectrum.py
MSG_SPECTRUM = 'Spectrum'

# visualizers/piano_roll.py: its name, the mark before each track's name in its legend, the label of each octave's C, and its drum lanes' labels, bottom first.
MSG_PIANO_ROLL = 'Piano roll'
MSG_PIANO_ROLL_LEGEND_MARK = '■ '
MSG_PIANO_ROLL_LEGEND_GAP = '  '
MSG_PIANO_ROLL_OCTAVE_LABEL = 'C{octave}'
MSG_PIANO_ROLL_DRUM_LANES = ('kick', 'snare', 'hats', 'toms', 'cymbal', 'perc')

# visualizers/llamas.py: the llamas, Claude's own drawings, facing left, their heads at the left, in three sizes; each line is padded to the drawing's width when drawn.
MSG_LLAMAS = 'Llamas'
MSG_LLAMA_SMALL = (
    ' ^^',
    '(oo)',
    ' | \\___',
    ' ||  ||',
)
MSG_LLAMA_MEDIUM = (
    '  ^ ^',
    ' (o o)',
    '  | |',
    '  | |______',
    '  |        )',
    '  || ||  ||',
)
MSG_LLAMA_LARGE = (
    '   ^  ^',
    '  (o  o)',
    '   \\  /',
    '    ||',
    '    ||_________',
    '    |          \\',
    '    |  ______   |',
    '    || ||    || ||',
)

# visualizers/hypercube.py
MSG_HYPERCUBE = 'Hypercube'

# visualizers/cycle.py
MSG_CYCLE = 'Cycle'

# visualizers/fireworks.py
MSG_FIREWORKS = 'Fireworks'

# visualizers/warpzone.py
MSG_WARPZONE = 'WarpZone'

# visualizers/pipes.py
MSG_PIPES = 'Pipes'

# visualizers/plasma.py
MSG_PLASMA = 'Plasma'

# visualizers/maze.py
MSG_MAZE = 'Maze'

# visualizers/mystify.py
MSG_MYSTIFY = 'Mystify'

# visualizers/laser_llama.py: the synthwave mode after the user's own channel's backgrounds, and its llama, Claude's drawing, a laser cannon on its back, facing right.
MSG_LASER_LLAMA = 'Laser Llama'
MSG_LASER_LLAMA_DRAWING = (
    '       ▄▄▄==',
    '  ^^  /▀▀▀',
    ' (oo)/',
    '  ||\\_____',
    '  ||      )',
    '   || ||',
)

# visualizers/mandelbrot.py
MSG_MANDELBROT = 'Mandelbrot'

# visualizers/life.py
MSG_LIFE = 'Life'

# visualizers/digital_rain.py: its name, and the characters that fall.
MSG_DIGITAL_RAIN = 'Digital rain'
MSG_RAIN_DIGITS = '01'
