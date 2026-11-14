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
"""The fields of a Euclidean mask, which the track editor's + Euclid section and the Euclid editor share: hits, steps, rotation and step, and the picker of named rhythms that H opens on Hits."""

from llamatron.composition.euclid import NAMED_RHYTHMS, rhythm
from llamatron.composition.file_format import EuclidPart
from llamatron.composition.limits import DEFAULT_EUCLID_STEPS, MAX_EUCLID, MIN_EUCLID, NO_ROTATION
from llamatron.strings.labels import MSG_EUCLID_FIELD_LABELS, MSG_EUCLID_LABEL, MSG_EUCLID_PART_LABELS, MSG_RHYTHM_NAMES
from llamatron.strings.marks import MSG_EUCLID_HIT, MSG_EUCLID_MISS, MSG_NONE_SHOWN, MSG_PATTERN_STEP_SHOWN, MSG_RHYTHM_SHOWN
from llamatron.strings.messages import MSG_RHYTHM_PICKER_TITLE
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.screens.field import NumberField
from llamatron.tui.screens.time_field import time_field


def drawn_rhythm(*, hits, steps, rotate=NO_ROTATION):
    """Return a rhythm as the page shows it, a mark a step, like X..X..X."""
    return ''.join(MSG_EUCLID_HIT if hit else MSG_EUCLID_MISS for hit in rhythm(hits=hits, steps=steps, rotate=rotate))


def euclid_fields(*, page, value, store, prefixed=True):
    """Return a mask's four fields, each part read by value(part) and kept by store(part, value), None leaving it blank; prefixed puts Euclid in front of each label, as in a section."""
    def label(part):
        return MSG_EUCLID_FIELD_LABELS[part] if prefixed else MSG_EUCLID_PART_LABELS[part]

    def number(part, *, start, lowest, highest):
        held = value(part)
        return NumberField(
            page=page, label=label(part), number=held, start=start, shown=MSG_NONE_SHOWN if held is None else None, lowest=lowest, highest=highest,
            set=lambda chosen: store(part, chosen), clear=lambda: store(part, None),
        )
    return [
        number(EuclidPart.HITS, start=MIN_EUCLID, lowest=MIN_EUCLID, highest=MAX_EUCLID),
        number(EuclidPart.STEPS, start=DEFAULT_EUCLID_STEPS, lowest=MIN_EUCLID, highest=MAX_EUCLID),
        number(EuclidPart.ROTATE, start=NO_ROTATION, lowest=NO_ROTATION, highest=MAX_EUCLID - 1),
        time_field(page=page, label=label(EuclidPart.STEP), written=value(EuclidPart.STEP), first=MSG_PATTERN_STEP_SHOWN, store=lambda chosen: store(EuclidPart.STEP, chosen)),
    ]


def euclid_section(*, page, value, store):
    """Return a + Euclid section, closed until opened and saying when its hits are set, and its four fields."""
    heading = page.heading(label=MSG_EUCLID_LABEL, is_set=lambda: value(EuclidPart.HITS) is not None)
    return [heading, *euclid_fields(page=page, value=value, store=store)]


def pick_rhythm(*, page, store):
    """Ask which named rhythm to use, and fill the hits and steps with it, the rotation back to none."""
    names = list(NAMED_RHYTHMS)
    options = [MSG_RHYTHM_SHOWN.format(name=MSG_RHYTHM_NAMES[name], hits=hits, steps=steps, drawn=drawn_rhythm(hits=hits, steps=steps)) for name, (hits, steps) in NAMED_RHYTHMS.items()]

    def chosen(place):
        hits, steps = NAMED_RHYTHMS[names[place]]
        store(EuclidPart.HITS, hits)
        store(EuclidPart.STEPS, steps)
        store(EuclidPart.ROTATE, None)
    page.ask(dialog=ChoiceDialog(title=MSG_RHYTHM_PICKER_TITLE, options=options), then=chosen)
