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
"""How each class shows itself to a developer: the text of every __repr__, which a debugger and a failed test print.

Each constant starts with REPR_ and is named after its class. None of this text is shown by the tracker.
"""

# music/time_signature.py
# How a time signature prints, as the expression that would build it.
REPR_TIME_SIGNATURE = 'TimeSignature(beats={beats!r}, unit={unit!r})'

# music/held.py
# How a held sound prints, as the expression that would build it.
REPR_HELD = 'Held(sound={sound!r}, length={length!r})'

# music/chord.py
# How a chord prints, as the expression that would build it.
REPR_CHORD = 'Chord(notes={notes!r})'

# music/scale.py
# How a scale prints, as the expression that would build it.
REPR_SCALE = 'Scale(root={root!r}, typ={typ!r})'

# music/note.py
# How a rest, a degree and a note print, as the expressions that would build them.
REPR_REST = 'Rest(length={length!r})'
REPR_DEGREE = 'Degree(number={number!r}, length={length!r}, octave={octave!r}, scale_notes={scale_notes!r}, half_steps={half_steps!r})'
REPR_NOTE = 'Note(name={name!r}, octave_number={octave_number!r}, length={length!r}, velocity={velocity!r}, glide={glide!r})'

# grid/control.py
# How a control prints, as the expression that would build it.
REPR_CONTROL = 'Control(time={time!r}, number={number!r}, value={value!r}, slide={slide!r})'

# grid/clip_column.py
# How a column prints, as the expression that would build it.
REPR_CLIP_COLUMN = 'ClipColumn(name={name!r}, mute={mute!r}, drum={drum!r}, gm_sound={gm_sound!r}, id={id!r})'

# grid/clip_row.py
# How a row prints, as the expression that would build it.
REPR_CLIP_ROW = 'ClipRow(name={name!r}, tempo={tempo!r}, scale={scale!r}, id={id!r})'

# grid/clip.py
# How a clip prints, as the expression that would build it.
REPR_CLIP = 'Clip(name={name!r}, notes={notes!r}, scale={scale!r}, length={length!r}, note_length={note_length!r}, id={id!r})'

# support/rational.py
# How a Rational prints, as the expression that would build it.
REPR_RATIONAL = 'Rational({numerator}, {denominator})'
