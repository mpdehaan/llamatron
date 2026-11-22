# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The drum kit's fields of the song wizard's drummer: the break, the fills, the quiet notes and what each piece of the kit plays."""

import functools

from llamatron.interface.tracker.note_names import note_shown
from llamatron.interface.tracker.screens.shared.field import Cells, ChoiceField, Field, NumberField, Toggle
from llamatron.model.schema import limits
from llamatron.user_strings import labels, legends, marks
from llamatron.wizards.create_song import wizard_limits, wizard_names

# A field is worth showing once there is more than one way to choose.
A_CHOICE = 2


class KitFields:
    """The fields of the drummer's kit on the wizard's player panel, made around the player's own: the break first, since it
    takes the place of the kick's, the snare's and the cymbal's own ways, then the fills, the quiet notes and a row for each
    piece of the kit the song plays."""

    __slots__ = ('_choices', '_page')

    def __init__(self, *, choices, page):
        self._choices = choices
        self._page = page

    def around(self, fields):
        """Return the drummer's fields with the kit's around them: the break first, since it takes the place of the kick's, the
        snare's and the cymbal's own ways, then the fills, the quiet notes and a row for each piece of the kit the song plays."""
        choices = self._choices
        kit = choices.get_kit()
        fields = [*self.break_fields(), *fields, *self.fill_pattern_fields(), self.fills_field()]
        if kit.has_quiet_notes() or not kit.plays_quiet_notes():
            page = self._page
            fields.append(Toggle(label=labels.MSG_WIZARD_QUIET_NOTES_LABEL, on=kit.plays_quiet_notes(), set=page.choosing(kit.set_quiet_notes)))
        fields += [self.piece_row(piece) for piece in kit.pieces()]
        return fields

    def break_fields(self):
        """Return the Break field where the song may play a break, and under it, while one is chosen, how far it is cut up: a
        number stepped or typed, drawn as a horizontal gauge that is empty for the break as written."""
        choices = self._choices
        page = self._page
        kit = choices.get_kit()
        breaks = kit.breaks()
        if not breaks:
            return []
        current = kit.get_break() or labels.MSG_WIZARD_NO_BREAK
        fields = [ChoiceField(page=page, label=labels.MSG_WIZARD_BREAK_LABEL, choices=[labels.MSG_WIZARD_NO_BREAK, *breaks], current=current,
                              set=page.choosing(functools.partial(self._set_break, kit=kit)))]
        if kit.get_break() is not None:
            cut = kit.get_break_cut()
            gauge = marks.MSG_WIZARD_GAUGE_FULL * (cut - wizard_names.LEAST_CUT) + marks.MSG_WIZARD_GAUGE_EMPTY * (wizard_names.MOST_CUT - cut)
            shown = marks.MSG_WIZARD_BUSY_SHOWN.format(gauge=gauge, level=cut, most=wizard_names.MOST_CUT)
            fields.append(NumberField(page=page, label=labels.MSG_WIZARD_BREAK_CUT_LABEL, number=cut, shown=shown, lowest=wizard_names.LEAST_CUT,
                                      highest=wizard_names.MOST_CUT, set=page.choosing(kit.set_break_cut)))
        return fields

    @staticmethod
    def _set_break(name, *, kit):
        """Have the song play a break by its name, or none."""
        if name == labels.MSG_WIZARD_NO_BREAK:
            name = None
        kit.set_break(name)

    def fill_pattern_fields(self):
        """Return the field for what the drums' fill is, where the genre has more than one, since one is nothing to choose."""
        choices = self._choices
        page = self._page
        band = choices.get_band()
        trait = band.song_trait(wizard_limits.FILLS_TRAITS)
        if trait is None:
            return []
        ways = band.song_ways(trait)
        if len(ways) < A_CHOICE:
            return []
        choose = page.choosing(functools.partial(self._set_way, band=band, trait=trait))
        return [ChoiceField(page=page, label=labels.MSG_WIZARD_FILLS_LABEL, choices=ways, current=band.get_way(trait), set=choose)]

    def fills_field(self):
        """Return the field for how often a fill comes: a number stepped or typed, drawn as a horizontal gauge that is empty at
        never, beside the words for the position."""
        choices = self._choices
        page = self._page
        kit = choices.get_kit()
        position = kit.get_fills()
        gauge = marks.MSG_WIZARD_GAUGE_FULL * (position - wizard_limits.FEWEST_FILLS) + marks.MSG_WIZARD_GAUGE_EMPTY * (wizard_limits.MOST_FILLS - position)
        often = labels.MSG_WIZARD_FILLS_COME[position - wizard_limits.FEWEST_FILLS]
        shown = marks.MSG_WIZARD_FILLS_SHOWN.format(gauge=gauge, often=often)
        return NumberField(page=page, label=labels.MSG_WIZARD_DRUM_FILLS_LABEL, number=position, shown=shown, lowest=wizard_limits.FEWEST_FILLS,
                           highest=wizard_limits.MOST_FILLS, set=page.choosing(kit.set_fills))

    def piece_row(self, piece):
        """Return the row of a piece of the kit, two cells side by side: whether the piece plays, switched with Space, and what
        the piece sounds as, chosen from a list: its own drum, another drum of the kit, or a General MIDI sound on a note."""
        choices = self._choices
        page = self._page
        kit = choices.get_kit()
        label = labels.MSG_WIZARD_KIT_PIECE.format(piece=piece)
        clear = None
        if kit.piece_sound(piece) is not None:
            to_own_drum = page.choosing(functools.partial(self._set_piece_sound, kit=kit, piece=piece))
            clear = functools.partial(to_own_drum, None)
        switch = Toggle(label=label, on=kit.piece_is_on(piece), set=self.piece_setter(piece))
        sound = Field(label=label, value=functools.partial(self._piece_shown, piece), enter=functools.partial(page.pick_piece_sound, piece),
                      enter_what=legends.What.CHOOSE, clear=clear, clear_what=legends.MSG_OWN_DRUM_WHAT)
        return Cells(label=label, cells=[switch, sound])

    def _piece_shown(self, piece):
        """Return what a piece of the kit sounds as: its own drum, another drum of the kit, or a General MIDI sound on a note."""
        choices = self._choices
        kit = choices.get_kit()
        sound = kit.piece_sound(piece)
        if sound is None:
            return marks.MSG_WIZARD_OWN_DRUM_SHOWN.format(piece=piece)
        if isinstance(sound, str):
            return marks.MSG_WIZARD_KIT_DRUM_SHOWN.format(drum=sound)
        general_midi = labels.MSG_GM_SOUNDS[sound - limits.MIN_GM_SOUND]
        return marks.MSG_WIZARD_SOUND_ON_NOTE.format(sound=general_midi, note=note_shown(kit.piece_note(piece)))

    @staticmethod
    def _set_piece_sound(sound, *, kit, piece):
        """Have a piece of the kit sound as a sound, or its own drum with None."""
        kit.set_piece_sound(piece=piece, sound=sound)

    def piece_setter(self, piece):
        """Return what switches a piece of the kit on or off, refusing to switch off the last."""
        choices = self._choices
        kit = choices.get_kit()
        page = self._page
        return page.refusing(functools.partial(self._set_piece_on, kit=kit, piece=piece))

    @staticmethod
    def _set_piece_on(on, *, kit, piece):
        """Switch a piece of the kit on or off."""
        kit.set_piece_on(piece=piece, on=on)

    @staticmethod
    def _set_way(value, *, band, trait):
        """Have the band play a trait a way."""
        band.set_way(trait=trait, value=value)

