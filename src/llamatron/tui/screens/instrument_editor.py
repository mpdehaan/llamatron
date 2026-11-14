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
from llamatron.music.midi import MAX_CHANNEL, MIN_CHANNEL
from llamatron.realtime.fluidsynth import FLUIDSYNTH_PORT_PREFIX
from llamatron.realtime.outputs import output_port_names
from llamatron.strings.help import HELP_INSTRUMENT_EDITOR
from llamatron.composition.limits import GM_FAMILY_SIZE, MAX_GM_SOUND, MIN_GM_SOUND
from llamatron.strings.labels import Crumb, MSG_CHANNEL_LABEL, MSG_DEVICE_LABEL, MSG_GM_FAMILIES, MSG_GM_PAGE_NAME, MSG_GM_SOUND_LABEL, MSG_GM_SOUND_SHOWN, MSG_GM_SOUNDS
from llamatron.strings.legends import MSG_NO_DEVICE_WHAT, MSG_NO_GM_SOUND_WHAT, What
from llamatron.strings.marks import MSG_AUTO_CHANNEL_SHOWN, MSG_NO_DEVICE_SHOWN, MSG_NONE_SHOWN
from llamatron.strings.messages import MSG_CHANNEL_PROMPT, MSG_DEVICE_TITLE, MSG_GM_SOUND_TITLE, MSG_RENAME_INSTRUMENT_PROMPT
from llamatron.tui.dialogs.grid_choice_dialog import GridChoiceDialog, grouped_grid
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.screens.field import Field, NameField, NumberField
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.text import sorted_names
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.tui import keybindings

# The place of (none) in the device picker, before FluidSynth and the ports, and in the sound picker, before the sounds.
NO_DEVICE_PLACE = 0
NO_SOUND_PLACE = 0
# How many of General MIDI's families the sound picker shows on a page, side by side, so that the longest names fit an 80 by 24 console.
FAMILIES_A_PAGE = 2


def sound_pages():
    """Return the sound picker's pages, each two families side by side under their headings, as places in the options, (none) being place 0 and sound n place n."""
    families = [(family, list(range(place * GM_FAMILY_SIZE + MIN_GM_SOUND, (place + 1) * GM_FAMILY_SIZE + MIN_GM_SOUND))) for place, family in enumerate(MSG_GM_FAMILIES)]
    return [
        (MSG_GM_PAGE_NAME.format(number=page + 1), grouped_grid([[family] for family in families[page * FAMILIES_A_PAGE:(page + 1) * FAMILIES_A_PAGE]]))
        for page in range(len(families) // FAMILIES_A_PAGE)
    ]


def sound_text(sound):
    """Return how a General MIDI sound is shown: its number and name, or (none)."""
    return MSG_NONE_SHOWN if sound is None else MSG_GM_SOUND_SHOWN.format(number=sound, name=MSG_GM_SOUNDS[sound - MIN_GM_SOUND])


class InstrumentEditor(ShowsNamedItem, FieldPage):
    """One instrument: its name, the MIDI output port it plays through and its channel."""

    KEYS = keybindings.InstrumentEditor

    HELP = HELP_INSTRUMENT_EDITOR
    SECTION = Section.INSTRUMENTS
    CRUMBS_BEFORE = (Crumb.INSTRUMENTS,)
    RENAME_PROMPT = MSG_RENAME_INSTRUMENT_PROMPT

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
        options = [MSG_NO_DEVICE_SHOWN, *devices]
        current = self.instrument().get_device()

        def chosen(place):
            self.set_device(None if place == NO_DEVICE_PLACE else devices[place - 1])
        self.ask(dialog=ChoiceDialog(title=MSG_DEVICE_TITLE, options=options, current=options.index(current) if current in options else NO_DEVICE_PLACE), then=chosen)

    def pick_gm_sound(self):
        """Choose the instrument's General MIDI sound from its families, a page of two at a time, with (none) above them."""
        options = [MSG_NONE_SHOWN, *MSG_GM_SOUNDS]
        current = self.instrument().get_gm_sound() or NO_SOUND_PLACE
        dialog = GridChoiceDialog(title=MSG_GM_SOUND_TITLE, options=options, grid=None, current=current, top=[NO_SOUND_PLACE], pages=sound_pages())
        self.ask(dialog=dialog, then=lambda place: self.set_gm_sound(None if place == NO_SOUND_PLACE else place))

    def step_gm_sound(self, offset):
        """Step to the next or previous sound, (none) below the first and the last staying put."""
        sound = (self.instrument().get_gm_sound() or NO_SOUND_PLACE) + offset
        self.set_gm_sound(None if sound <= NO_SOUND_PLACE else min(sound, MAX_GM_SOUND))

    def set_gm_sound(self, sound):
        self.document().set_instrument_gm_sound(name=self.item, sound=sound)

    def set_device(self, device):
        self.document().set_instrument_device(name=self.item, device=device)

    def channel_field(self):
        """Return the Channel field: a number from 1 to 16, or (auto) with nothing to change while the instrument plays through FluidSynth, which gives each track a channel."""
        instrument = self.instrument()
        if instrument.uses_fluidsynth():
            return Field(label=MSG_CHANNEL_LABEL, value=lambda: MSG_AUTO_CHANNEL_SHOWN)
        return NumberField(
            page=self, label=MSG_CHANNEL_LABEL, number=instrument.get_channel(), lowest=MIN_CHANNEL, highest=MAX_CHANNEL,
            title=MSG_CHANNEL_PROMPT.format(lowest=MIN_CHANNEL, highest=MAX_CHANNEL),
            set=lambda channel: self.document().set_instrument_channel(name=self.item, channel=channel),
        )

    def fields(self):
        instrument = self.instrument()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            Field(label=MSG_DEVICE_LABEL, value=lambda: instrument.get_device() or MSG_NO_DEVICE_SHOWN, adjust=None, enter=self.pick_device, enter_what=What.CHOOSE,
                  clear=lambda: self.set_device(None), clear_what=MSG_NO_DEVICE_WHAT),
            self.channel_field(),
            Field(label=MSG_GM_SOUND_LABEL, value=lambda: sound_text(instrument.get_gm_sound()), adjust=self.step_gm_sound, enter=self.pick_gm_sound, enter_what=What.CHOOSE,
                  clear=lambda: self.set_gm_sound(None), clear_what=MSG_NO_GM_SOUND_WHAT),
        ]
