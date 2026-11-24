# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""One instrument's page as a presenter: its name, the velocity its steps play at, its accent and velocity, which apply however it
plays, then its tabs, MIDI (the port it plays through, its channel, its General MIDI sound, how early a keyswitch is sent and
its latency), Synth and Effects (interface/pages/sound_tabs.py), MIDI and Synth each switched on by its own On, which switches
the other off, and then the Keyswitch Map button."""

from llamatron.interface.forms import percentages
from llamatron.interface.forms.nodes import Field, NameField, NumberField, SettingNumberField, Toggle
from llamatron.interface.forms.tab_box import Tab, TabBox, TabColumn
from llamatron.interface.pages.sound_tabs import SoundTabs
from llamatron.model.schema import defaults, limits
from llamatron.model.schema.file_format import InstrumentKind, InstrumentSetting
from llamatron.model.values import midi
from llamatron.user_strings import labels, legends, marks, messages

# The place of (none) in the sound picker, before the sounds.
NO_SOUND_PLACE = 0


class InstrumentPresenter:
    """What an instrument's page shows and does, for one of the set's instruments by name. Its page does what only the tracker
    can: rename(), pick_device() among this computer's ports, pick_gm_sound() with sounds to try, and keyswitch_map_button()."""

    __slots__ = ('_page', '_document', '_name')

    def __init__(self, *, page, document, name):
        self._page = page
        self._document = document
        self._name = name

    def instrument(self):
        return self._document.get_setlist().get_instrument(self._name)

    def step_gm_sound(self, offset):
        """Step to the next or previous sound, (none) below the first and the last staying put."""
        sound = (self.instrument().get_gm_sound() or NO_SOUND_PLACE) + offset
        self.set_gm_sound(None if sound <= NO_SOUND_PLACE else min(sound, limits.MAX_GM_SOUND))

    def set_gm_sound(self, sound):
        self._document.change_set(self._document.get_setlist().get_instrument(self._name).set_gm_sound, sound)

    def set_device(self, device):
        self._document.change_set(self._document.get_setlist().get_instrument(self._name).set_device, device)

    def default_velocity_field(self):
        """Return the Default velocity field: what a step with no velocity typed plays at on the instrument's tracks, the loudest until set."""
        velocity = self.instrument().get_default_velocity()
        return SettingNumberField(page=self._page, document=self._document, label=labels.MSG_DEFAULT_VELOCITY_LABEL, holder=self.instrument(), name=InstrumentSetting.DEFAULT_VELOCITY, in_effect=velocity, start=defaults.DEFAULT_VELOCITY, clear_what=str(defaults.DEFAULT_VELOCITY))

    def velocity_change_field(self):
        """Return the Velocity field: the percentage of its written velocity every clip of the instrument's tracks plays, stacking with the
        track's, the scene's and the clip's, 100% until set."""
        holder = self.instrument()
        percent = holder.get_velocity_percent()
        shown = percentages.percent_shown(percentages.UNCHANGED if percent is None else percent)
        return SettingNumberField(page=self._page, document=self._document, label=labels.MSG_VELOCITY_PERCENT_LABEL, holder=holder, name=InstrumentSetting.VELOCITY, shown=shown, start=percentages.UNCHANGED, clear_what=percentages.percent_shown(percentages.UNCHANGED))

    def accent_field(self):
        """Return the Accent field: what a step with its Accent on adds to its velocity on the instrument's tracks, before each track's own accent."""
        accent = self.instrument().get_accent()
        return SettingNumberField(page=self._page, document=self._document, label=labels.MSG_ACCENT_LABEL, holder=self.instrument(), name=InstrumentSetting.ACCENT, in_effect=accent, shown=marks.MSG_ACCENT_SHOWN.format(accent=accent), clear_what=marks.MSG_ACCENT_SHOWN.format(accent=defaults.DEFAULT_INSTRUMENT_ACCENT))

    def lead_field(self):
        """Return the Keyswitch lead field: how many milliseconds before its note a keyswitch is sent, for a plugin that needs it early, nothing unless set."""
        instrument = self.instrument()
        return NumberField(
            page=self._page, label=labels.MSG_KEYSWITCH_LEAD_LABEL, number=instrument.get_keyswitch_lead(), lowest=limits.MIN_KEYSWITCH_LEAD, highest=limits.MAX_KEYSWITCH_LEAD,
            shown=marks.MSG_KEYSWITCH_LEAD_SHOWN.format(milliseconds=instrument.get_keyswitch_lead()),
            title=messages.MSG_KEYSWITCH_LEAD_PROMPT.format(lowest=limits.MIN_KEYSWITCH_LEAD, highest=limits.MAX_KEYSWITCH_LEAD),
            set=lambda milliseconds: self._document.change_set(self._document.get_setlist().get_instrument(self._name).set_keyswitch_lead, milliseconds or None),
        )

    def channel_field(self):
        """Return the Channel field: a number from 1 to 16, or (auto) with nothing to change while the instrument plays through FluidSynth, which gives each track a channel."""
        instrument = self.instrument()
        if instrument.uses_fluidsynth():
            return Field(label=labels.MSG_CHANNEL_LABEL, value=lambda: marks.MSG_AUTO_CHANNEL_SHOWN)
        return NumberField(
            page=self._page, label=labels.MSG_CHANNEL_LABEL, number=instrument.get_channel(), lowest=midi.MIN_CHANNEL, highest=midi.MAX_CHANNEL,
            title=messages.MSG_CHANNEL_PROMPT.format(lowest=midi.MIN_CHANNEL, highest=midi.MAX_CHANNEL),
            set=lambda channel: self._document.change_set(self._document.get_setlist().get_instrument(self._name).set_channel, channel),
        )

    def form(self):
        """Return the page's form: the instrument's name, how its steps' velocities play, its MIDI, Synth and Effects tabs, then the
        Keyswitch Map button."""
        tabs = SoundTabs(page=self._page, document=self._document, name=self._name)
        return [
            NameField(value=lambda: self._name, rename=self._page.rename),
            self.default_velocity_field(),
            self.accent_field(),
            self.velocity_change_field(),
            TabBox(tabs=[self.midi_tab(), tabs.synth_tab(), tabs.effects_tab()]),
            self._page.keyswitch_map_button(),
            self._page.listen_button(),
        ]

    def midi_tab(self):
        """Return the MIDI tab: On across its top, then where it plays and how."""
        instrument = self.instrument()
        on = Toggle(label=labels.MSG_MIDI_ON_LABEL, shown_label=labels.MSG_ON_LABEL, on=instrument.get_kind() == InstrumentKind.MIDI, set=self.set_midi)
        fields = [
            Field(label=labels.MSG_DEVICE_LABEL, value=lambda: instrument.get_device() or marks.MSG_NO_DEVICE_SHOWN, adjust=None, enter=self._page.pick_device, enter_what=legends.What.CHOOSE,
                  clear=lambda: self.set_device(None), clear_what=marks.MSG_NONE_SHOWN),
            self.channel_field(),
            Field(label=labels.MSG_GM_SOUND_LABEL, value=lambda: sound_text(instrument.get_gm_sound()), adjust=self.step_gm_sound, enter=self._page.pick_gm_sound, enter_what=legends.What.CHOOSE,
                  clear=lambda: self.set_gm_sound(None), clear_what=marks.MSG_NONE_SHOWN),
            self.lead_field(),
            self.latency_field(),
        ]
        return Tab(label=labels.MSG_MIDI_TAB, top=[on], columns=[TabColumn(heading=None, fields=fields)], on=instrument.get_kind() == InstrumentKind.MIDI)

    def set_midi(self, on):
        """Make the instrument play through MIDI, or switch it off: neither MIDI nor built in."""
        kind = InstrumentKind.MIDI if on else InstrumentKind.OFF
        self._document.change_set(self._document.get_setlist().get_instrument(self._name).set_kind, kind)

    def latency_field(self):
        """Return the Latency field: how many milliseconds earlier its notes are sent, for a device that is slow to sound."""
        latency = self.instrument().get_latency()
        return NumberField(
            page=self._page, label=labels.MSG_LATENCY_LABEL, number=latency, lowest=limits.MIN_INSTRUMENT_LATENCY, highest=limits.MAX_INSTRUMENT_LATENCY,
            shown=marks.MSG_KEYSWITCH_LEAD_SHOWN.format(milliseconds=latency), title=messages.MSG_LATENCY_PROMPT.format(lowest=limits.MIN_INSTRUMENT_LATENCY, highest=limits.MAX_INSTRUMENT_LATENCY),
            set=lambda milliseconds: self._document.change_set(self._document.get_setlist().get_instrument(self._name).set_latency, milliseconds),
        )

def sound_text(sound):
    """Return how a General MIDI sound is shown: its number and name, or (none)."""
    return marks.MSG_NONE_SHOWN if sound is None else labels.MSG_GM_SOUND_SHOWN.format(number=sound, name=labels.MSG_GM_SOUNDS[sound - limits.MIN_GM_SOUND])
