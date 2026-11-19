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

"""The instrument editor: one instrument's name, MIDI device or FluidSynth, channel and General MIDI sound."""

from llamatron.composition.file_format import FLUIDSYNTH_DEVICE, Section
from llamatron.music import midi
from llamatron.realtime.fluidsynth import FLUIDSYNTH_PORT_PREFIX
from llamatron.realtime.outputs import output_port_names
from llamatron.composition import defaults, limits
from llamatron.strings import help as help_text, labels, legends, marks, messages
from llamatron.tui.dialogs.sound_dialog import SoundDialog
from llamatron.tui.screens.shared.sound_trial import SoundTrial, run_in_sound
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.keyswitch_map_dialog import KeyswitchMapDialog
from llamatron.tui.screens.shared.field import Button, Field, NameField, NumberField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.text import sorted_names
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.tui import keybindings

# The place of (none) in the device picker, before FluidSynth and the ports, and in the sound picker, before the sounds.
NO_DEVICE_PLACE = 0
NO_SOUND_PLACE = 0


def sound_families(*, numbered=False):
    """Return General MIDI's families for the sound picker, each its name with its sounds as (label, General MIDI number), a label the sound's name,
    after its number where numbered."""
    def label(sound):
        name = labels.MSG_GM_SOUNDS[sound - limits.MIN_GM_SOUND]
        return labels.MSG_GM_SOUND_SHOWN.format(number=sound, name=name) if numbered else name
    return [(family, [(label(sound), sound) for sound in range(place * limits.GM_FAMILY_SIZE + limits.MIN_GM_SOUND, (place + 1) * limits.GM_FAMILY_SIZE + limits.MIN_GM_SOUND)])
            for place, family in enumerate(labels.MSG_GM_FAMILIES)]


def sound_text(sound):
    """Return how a General MIDI sound is shown: its number and name, or (none)."""
    return marks.MSG_NONE_SHOWN if sound is None else labels.MSG_GM_SOUND_SHOWN.format(number=sound, name=labels.MSG_GM_SOUNDS[sound - limits.MIN_GM_SOUND])


class InstrumentEditor(ShowsNamedItem, FieldPage):
    """One instrument: its name, the MIDI output port it plays through and its channel."""

    KEYS = keybindings.InstrumentEditor

    HELP = help_text.HELP_INSTRUMENT_EDITOR
    SECTION = Section.INSTRUMENTS
    CRUMBS_BEFORE = (labels.Crumb.INSTRUMENTS,)
    RENAME_PROMPT = messages.MSG_RENAME_INSTRUMENT_PROMPT

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def instrument(self):
        return self.document().setlist().get_instrument(self.item)

    def devices(self):
        """Return FluidSynth, then the ports this computer has now, sorted, and the instrument's own device among them even when it has gone, so that it can be seen and kept. A tracker's own FluidSynth port isn't offered, since FluidSynth is chosen as itself."""
        names = {name for name in output_port_names() if not name.startswith(FLUIDSYNTH_PORT_PREFIX)}
        if self.instrument().has_device() and not self.instrument().uses_fluidsynth():
            names.add(self.instrument().get_device())
        names.discard(FLUIDSYNTH_DEVICE)
        return [FLUIDSYNTH_DEVICE, *sorted_names(names)]

    def pick_device(self):
        devices = self.devices()
        options = [marks.MSG_NO_DEVICE_SHOWN, *devices]
        current = self.instrument().get_device()

        def chosen(place):
            self.set_device(None if place == NO_DEVICE_PLACE else devices[place - 1])
        self.ask(dialog=ChoiceDialog(title=messages.MSG_DEVICE_TITLE, options=options, current=options.index(current) if current in options else NO_DEVICE_PLACE), then=chosen)

    def pick_gm_sound(self):
        """Choose the instrument's General MIDI sound from its families, each a row that opens its sounds, with (none) above them; a sound can be tried."""
        dialog = SoundDialog(title=messages.MSG_GM_SOUND_TITLE, top=[(marks.MSG_NONE_SHOWN, NO_SOUND_PLACE)], groups=sound_families(numbered=True), current=self.instrument().get_gm_sound() or NO_SOUND_PLACE,
                             trial=SoundTrial(page=self, played=lambda sound: run_in_sound(sound or None)))
        self.ask(dialog=dialog, then=lambda place: self.set_gm_sound(None if place == NO_SOUND_PLACE else place))

    def step_gm_sound(self, offset):
        """Step to the next or previous sound, (none) below the first and the last staying put."""
        sound = (self.instrument().get_gm_sound() or NO_SOUND_PLACE) + offset
        self.set_gm_sound(None if sound <= NO_SOUND_PLACE else min(sound, limits.MAX_GM_SOUND))

    def set_gm_sound(self, sound):
        self.document().set_instrument_gm_sound(name=self.item, sound=sound)

    def set_device(self, device):
        self.document().set_instrument_device(name=self.item, device=device)

    def page_keys(self):
        return [self.bind(self.KEYS.KEYSWITCH_MAP, action=self.open_keyswitch_map)]

    def open_keyswitch_map(self):
        """Open the Keyswitch Map, whose ten slots go into the instrument together on OK, as one undo step."""
        dialog = KeyswitchMapDialog(title=messages.MSG_KEYSWITCH_MAP_TITLE.format(instrument=self.item), keyswitches=self.instrument().get_keyswitches(), setlist=self.document().setlist())
        self.ask(dialog=dialog, then=lambda keyswitches: self.document().set_instrument_keyswitches(name=self.item, keyswitches=keyswitches))

    def default_velocity_field(self):
        """Return the Default velocity field: what a step with no velocity typed plays at on the instrument's tracks, the loudest until set."""
        velocity = self.instrument().get_default_velocity()
        return NumberField(
            page=self, label=labels.MSG_DEFAULT_VELOCITY_LABEL, number=velocity, start=defaults.DEFAULT_VELOCITY, lowest=midi.MIN_VELOCITY, highest=midi.MAX_VELOCITY,
            set=lambda number: self.document().set_instrument_default_velocity(name=self.item, velocity=number),
            clear=lambda: self.document().set_instrument_default_velocity(name=self.item, velocity=None), clear_what=legends.MSG_NO_DEFAULT_VELOCITY_WHAT,
        )

    def accent_field(self):
        """Return the Accent field: what a step with its Accent on adds to its velocity on the instrument's tracks, before each track's own accent."""
        accent = self.instrument().get_accent()
        return NumberField(
            page=self, label=labels.MSG_ACCENT_LABEL, number=accent, shown=marks.MSG_ACCENT_SHOWN.format(accent=accent), lowest=limits.MIN_STEP_ACCENT, highest=limits.MAX_STEP_ACCENT,
            set=lambda number: self.document().set_instrument_accent(name=self.item, accent=number),
            clear=lambda: self.document().set_instrument_accent(name=self.item, accent=None), clear_what=legends.MSG_NO_DEFAULT_VELOCITY_WHAT,
        )

    def lead_field(self):
        """Return the Keyswitch lead field: how many milliseconds before its note a keyswitch is sent, for a plugin that needs it early, nothing unless set."""
        instrument = self.instrument()
        return NumberField(
            page=self, label=labels.MSG_KEYSWITCH_LEAD_LABEL, number=instrument.get_keyswitch_lead(), lowest=limits.MIN_KEYSWITCH_LEAD, highest=limits.MAX_KEYSWITCH_LEAD,
            shown=marks.MSG_KEYSWITCH_LEAD_SHOWN.format(milliseconds=instrument.get_keyswitch_lead()),
            title=messages.MSG_KEYSWITCH_LEAD_PROMPT.format(lowest=limits.MIN_KEYSWITCH_LEAD, highest=limits.MAX_KEYSWITCH_LEAD),
            set=lambda milliseconds: self.document().set_instrument_keyswitch_lead(name=self.item, milliseconds=milliseconds or None),
        )

    def channel_field(self):
        """Return the Channel field: a number from 1 to 16, or (auto) with nothing to change while the instrument plays through FluidSynth, which gives each track a channel."""
        instrument = self.instrument()
        if instrument.uses_fluidsynth():
            return Field(label=labels.MSG_CHANNEL_LABEL, value=lambda: marks.MSG_AUTO_CHANNEL_SHOWN)
        return NumberField(
            page=self, label=labels.MSG_CHANNEL_LABEL, number=instrument.get_channel(), lowest=midi.MIN_CHANNEL, highest=midi.MAX_CHANNEL,
            title=messages.MSG_CHANNEL_PROMPT.format(lowest=midi.MIN_CHANNEL, highest=midi.MAX_CHANNEL),
            set=lambda channel: self.document().set_instrument_channel(name=self.item, channel=channel),
        )

    def fields(self):
        instrument = self.instrument()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            Field(label=labels.MSG_DEVICE_LABEL, value=lambda: instrument.get_device() or marks.MSG_NO_DEVICE_SHOWN, adjust=None, enter=self.pick_device, enter_what=legends.What.CHOOSE,
                  clear=lambda: self.set_device(None), clear_what=legends.MSG_NO_DEVICE_WHAT),
            self.channel_field(),
            Field(label=labels.MSG_GM_SOUND_LABEL, value=lambda: sound_text(instrument.get_gm_sound()), adjust=self.step_gm_sound, enter=self.pick_gm_sound, enter_what=legends.What.CHOOSE,
                  clear=lambda: self.set_gm_sound(None), clear_what=legends.MSG_NO_GM_SOUND_WHAT),
            self.default_velocity_field(),
            self.accent_field(),
            self.lead_field(),
            Button(label=labels.MSG_KEYSWITCH_MAP_LABEL, key_name=self.KEYS.KEYSWITCH_MAP[1], enter=self.open_keyswitch_map, enter_what=self.KEYS.KEYSWITCH_MAP[2]),
        ]
