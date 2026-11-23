# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The instrument editor: one instrument's name, MIDI device or FluidSynth, channel and General MIDI sound."""
from llamatron.interface.forms.nodes import Button
from llamatron.interface.forms.text import sorted_names
from llamatron.interface.pages import instrument as instrument_values
from llamatron.interface.pages.instrument import InstrumentPresenter
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.keyswitch_map_dialog import KeyswitchMapDialog
from llamatron.interface.tracker.dialogs.sound_dialog import SoundDialog
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.interface.tracker.screens.shared.sound_trial import run_in_sound, SoundTrial
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels, marks, messages



def sound_families(*, numbered=False):
    """Return General MIDI's families for the sound picker, each its name with its sounds as (label, General MIDI number), a label the sound's name,
    after its number where numbered."""
    def label(sound):
        name = labels.MSG_GM_SOUNDS[sound - limits.MIN_GM_SOUND]
        return labels.MSG_GM_SOUND_SHOWN.format(number=sound, name=name) if numbered else name
    def family_sounds(place):
        return [(label(sound), sound) for sound in sounds_of_family(place)]
    return [(family, family_sounds(place)) for place, family in enumerate(labels.MSG_GM_FAMILIES)]


class InstrumentEditor(ShowsNamedItem, FieldPage):
    """One instrument: the Instrument presenter's form (interface/pages/instrument.py), with the pickers of ports and sounds and
    the Keyswitch Map, which only the tracker has."""

    KEYS = keybindings.InstrumentEditor

    HELP = help_text.HELP_INSTRUMENT_EDITOR
    SECTION = Section.INSTRUMENTS
    CRUMBS_BEFORE = (labels.Crumb.INSTRUMENTS,)
    RENAME_PROMPT = messages.MSG_RENAME_INSTRUMENT_PROMPT

    def instrument(self):
        return self.document().get_setlist().get_instrument(self.item)

    def devices(self):
        """Return FluidSynth, then the ports this computer has now, sorted, and the instrument's own device among them even when it has gone, so that it can be seen and kept. A tracker's own FluidSynth port isn't offered, since FluidSynth is chosen as itself."""
        names = set(self.app.transport.device_port_names())
        if self.instrument().has_device() and not self.instrument().uses_fluidsynth():
            names.add(self.instrument().get_device())
        names.discard(file_format.FLUIDSYNTH_DEVICE)
        return [file_format.FLUIDSYNTH_DEVICE, *sorted_names(names)]

    def pick_device(self):
        devices = self.devices()
        self.pick(title=messages.MSG_DEVICE_TITLE, values=[None, *devices], shown=[marks.MSG_NO_DEVICE_SHOWN, *devices], current=self.instrument().get_device(), then=self.set_device)

    def pick_gm_sound(self):
        """Choose the instrument's General MIDI sound from its families, each a row that opens its sounds, with (none) above them; a sound can be tried."""
        dialog = SoundDialog(title=messages.MSG_GM_SOUND_TITLE, top=[(marks.MSG_NONE_SHOWN, instrument_values.NO_SOUND_PLACE)], groups=sound_families(numbered=True), current=self.instrument().get_gm_sound() or instrument_values.NO_SOUND_PLACE,
                             trial=SoundTrial(page=self, played=lambda sound: run_in_sound(sound or None)))
        self.ask(dialog=dialog, then=lambda place: self.set_gm_sound(None if place == instrument_values.NO_SOUND_PLACE else place))

    def presenter(self):
        """Return what the page shows, for the instrument as it is now."""
        return InstrumentPresenter(page=self, document=self.document(), name=self.item)

    def fields(self):
        return self.presenter().form()

    def keyswitch_map_button(self):
        """Return the Keyswitch Map button, showing its key."""
        return Button(label=labels.MSG_KEYSWITCH_MAP_LABEL, key_name=self.KEYS.KEYSWITCH_MAP.name, enter=self.open_keyswitch_map, enter_what=self.KEYS.KEYSWITCH_MAP[2])

    def set_gm_sound(self, sound):
        self.presenter().set_gm_sound(sound)

    def set_device(self, device):
        self.presenter().set_device(device)

    def page_keys(self):
        return [self.bind(self.KEYS.KEYSWITCH_MAP, action=self.open_keyswitch_map)]

    def open_keyswitch_map(self):
        """Open the Keyswitch Map, whose ten slots go into the instrument together on OK, as one undo step."""
        dialog = KeyswitchMapDialog(title=messages.MSG_KEYSWITCH_MAP_TITLE.format(instrument=self.item), keyswitches=self.instrument().get_keyswitches(), setlist=self.document().get_setlist())
        self.ask(dialog=dialog, then=lambda keyswitches: self.document().change_set(self.document().get_setlist().get_instrument(self.item).set_keyswitches, keyswitches))


def sounds_of_family(place):
    """Return the General MIDI numbers of the sounds of a family, by the family's place."""
    return range(place * limits.GM_FAMILY_SIZE + limits.MIN_GM_SOUND, (place + 1) * limits.GM_FAMILY_SIZE + limits.MIN_GM_SOUND)
