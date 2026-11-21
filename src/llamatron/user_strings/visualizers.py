# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What the visualizers are called on screen.

Each constant starts with MSG_.
"""

# interface/visualizers/lava_lamp.py
MSG_LAVA_LAMP = 'Lava lamp'

# interface/visualizers/milkdrop.py
MSG_MILKDROP = 'MilkDrop'

# interface/visualizers/spectrum.py
MSG_SPECTRUM = 'Spectrum'

# interface/visualizers/piano_roll.py: its name, the mark before each track's name in its legend, the label of each octave's C, and its drum lanes' labels, bottom first.
MSG_PIANO_ROLL = 'Piano roll'
MSG_PIANO_ROLL_LEGEND_MARK = '■ '
MSG_PIANO_ROLL_LEGEND_GAP = '  '
MSG_PIANO_ROLL_OCTAVE_LABEL = 'C{octave}'
MSG_PIANO_ROLL_DRUM_LANES = ('kick', 'snare', 'hats', 'toms', 'cymbal', 'perc')

# interface/visualizers/llamas.py: the llamas, Claude's own drawings, facing left, their heads at the left, in three sizes; each line is padded to the drawing's width when drawn.
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

# interface/visualizers/hypercube.py
MSG_HYPERCUBE = 'Hypercube'

# interface/visualizers/cycle.py
MSG_CYCLE = 'Cycle'

# interface/visualizers/fireworks.py
MSG_FIREWORKS = 'Fireworks'

# interface/visualizers/warpzone.py
MSG_WARPZONE = 'WarpZone'

# interface/visualizers/pipes.py
MSG_PIPES = 'Pipes'

# interface/visualizers/plasma.py
MSG_PLASMA = 'Plasma'

# interface/visualizers/maze.py
MSG_MAZE = 'Maze'

# interface/visualizers/mystify.py
MSG_MYSTIFY = 'Mystify'

# interface/visualizers/laser_llama.py: the synthwave mode after a video channel's backgrounds, and its llama, Claude's drawing, a laser cannon on its back, facing right.
MSG_LASER_LLAMA = 'Laser Llama'
MSG_LASER_LLAMA_DRAWING = (
    '       ▄▄▄==',
    '  ^^  /▀▀▀',
    ' (oo)/',
    '  ||\\_____',
    '  ||      )',
    '   || ||',
)

# interface/visualizers/mandelbrot.py
MSG_MANDELBROT = 'Mandelbrot'

# interface/visualizers/life.py
MSG_LIFE = 'Life'

# interface/visualizers/digital_rain.py: its name, and the characters that fall.
MSG_DIGITAL_RAIN = 'Digital rain'
MSG_RAIN_DIGITS = '01'
