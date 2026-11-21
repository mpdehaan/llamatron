# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The fields of a Euclidean mask, which the track editor's + Euclid section and the Euclid editor share: hits, steps, rotation and step, and the picker of named rhythms that H opens on Hits."""

from llamatron.engine.generators.euclid import strings as euclid_strings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.screens.generators.time_field import time_field
from llamatron.interface.tracker.screens.shared.field import NumberField
from llamatron.model.objects import euclid
from llamatron.model.objects.euclid import rhythm
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import EuclidPart
from llamatron.user_strings import labels, marks, messages


def drawn_rhythm(*, hits, steps, rotate=limits.NO_ROTATION):
    """Return a rhythm as the page shows it, a mark a step, like X..X..X."""
    return ''.join(marks.MSG_EUCLID_HIT if hit else marks.MSG_EUCLID_MISS for hit in rhythm(hits=hits, steps=steps, rotate=rotate))


def euclid_fields(*, page, value, store, prefixed=True):
    """Return a mask's four fields, each part read by value(part) and kept by store(part, value), None leaving it blank; prefixed puts Euclid in front of each label, as in a section."""
    def label(part):
        return labels.MSG_EUCLID_FIELD_LABELS[part] if prefixed else labels.MSG_EUCLID_PART_LABELS[part]

    def number(part, *, start, lowest, highest):
        held = value(part)
        return NumberField(
            page=page, label=label(part), number=held, start=start, shown=marks.MSG_NONE_SHOWN if held is None else None, lowest=lowest, highest=highest,
            set=lambda chosen: store(part, chosen), clear=lambda: store(part, None),
        )
    return [
        number(EuclidPart.HITS, start=limits.MIN_EUCLID, lowest=limits.MIN_EUCLID, highest=limits.MAX_EUCLID),
        number(EuclidPart.STEPS, start=limits.DEFAULT_EUCLID_STEPS, lowest=limits.MIN_EUCLID, highest=limits.MAX_EUCLID),
        number(EuclidPart.ROTATE, start=limits.NO_ROTATION, lowest=limits.NO_ROTATION, highest=limits.MAX_EUCLID - 1),
        time_field(page=page, label=label(EuclidPart.STEP), written=value(EuclidPart.STEP), first=marks.MSG_PATTERN_STEP_SHOWN, store=lambda chosen: store(EuclidPart.STEP, chosen)),
    ]


def euclid_section(*, page, value, store):
    """Return a + Euclid section, closed until opened and saying when its hits are set, and its four fields."""
    heading = page.heading(label=euclid_strings.MSG_LABEL, is_set=lambda: value(EuclidPart.HITS) is not None)
    return [heading, *euclid_fields(page=page, value=value, store=store)]


def pick_rhythm(*, page, store):
    """Ask which named rhythm to use, and fill the hits and steps with it, the rotation back to none."""
    names = list(euclid.NAMED_RHYTHMS)
    options = [marks.MSG_RHYTHM_SHOWN.format(name=labels.MSG_RHYTHM_NAMES[name], hits=hits, steps=steps, drawn=drawn_rhythm(hits=hits, steps=steps)) for name, (hits, steps) in euclid.NAMED_RHYTHMS.items()]

    def chosen(place):
        hits, steps = euclid.NAMED_RHYTHMS[names[place]]
        store(EuclidPart.HITS, hits)
        store(EuclidPart.STEPS, steps)
        store(EuclidPart.ROTATE, None)
    page.ask(dialog=ChoiceDialog(title=messages.MSG_RHYTHM_PICKER_TITLE, options=options), then=chosen)
