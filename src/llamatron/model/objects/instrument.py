# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""An instrument: a MIDI device and channel that real-time playback sends a track to.

Instruments are a named section of the set, like patterns, and each track chooses one or none.
A track with no
instrument is left out of real-time playback and gets no play keys. The device is the name of a
MIDI output port of the computer, as the port lists itself, or blank until one is chosen, and the
channel is numbered 1 to 16 as people and devices number them, so the byte sent is one less. Two
instruments may share a device and a channel. Its General MIDI sound, if it has one, is what the
General MIDI export gives its tracks; no other export reads an instrument. A device of
FLUIDSYNTH_DEVICE plays through FluidSynth, which the tracker starts (realtime/devices/fluidsynth.py): the
channel is then ignored, each track getting one as the General MIDI export gives them, and the
sound is sent as a program change, which no MIDI port's instrument is sent.

Its keyswitches are for a plugin whose articulations a note switches: ten slots,
numbered from 0, each with a name and a MIDI note, either of which may be missing. A pattern's
Keyswitch row names slots, and a slot with no note plays nothing until it has one. Its keyswitch
lead is how many milliseconds before its note a keyswitch is sent, nothing unless set.

An instrument's kind is MIDI unless it is Built-in, a sound llamatron makes itself through the Synthesis Process
(realtime/synth_process/), its sound's settings stored under it (model/objects/built_in_sound.py). A MIDI instrument's latency
is how many milliseconds earlier its notes are sent, for a synth slow to sound, 0 unless set.
"""

from typing import NamedTuple

from llamatron.caching.revised import notes_change
from llamatron.model.file import corrections
from llamatron.model.file.checks import pass_over_unknown, reading
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.built_in_sound import check_sound, sound_value, synth_spec
from llamatron.model.objects.llama_data import HoldsSettings, or_default, own_copy, settings_by_name, written_settings
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import InstrumentKind, InstrumentSetting, KeyswitchSetting
from llamatron.model.schema.setting import check_settings, Checked, Choice, described, Text, WholeNumber
from llamatron.model.values import midi
from llamatron.user_strings import errors

class Keyswitch(NamedTuple):
    """One keyswitch slot as an instrument answers it: its name and its MIDI note, each None when the slot has none."""

    name: str
    note: int

    def is_empty(self):
        return self.name is None and self.note is None


NO_KEYSWITCH = Keyswitch(None, None)


def check_keyswitch_name(name):
    """Refuse a keyswitch's name that isn't text short enough for a name."""
    if not isinstance(name, str) or not name or len(name) > limits.MAX_NAME_LENGTH:
        raise InvalidValue(errors.ERR_BAD_KEYSWITCH_NAME.format(most=limits.MAX_NAME_LENGTH, value=name))


def check_keyswitch_note(note):
    """Refuse a keyswitch's note that isn't a MIDI note number."""
    if type(note) is not int or not midi.MIN_MIDI_NUMBER <= note <= midi.MAX_MIDI_NUMBER:
        raise InvalidValue(errors.ERR_BAD_KEYSWITCH_NOTE.format(lowest=midi.MIN_MIDI_NUMBER, highest=midi.MAX_MIDI_NUMBER, value=note))


# One keyswitch slot's settings, each described once, in the order they're written to a file.
KEYSWITCH_SETTINGS = described(
    Checked(name=KeyswitchSetting.NAME, check=check_keyswitch_name),
    Checked(name=KeyswitchSetting.NOTE, check=check_keyswitch_note),
)


def check_keyswitch_slot(slot):
    """Refuse a slot's number that no instrument has."""
    if type(slot) is not int or slot not in file_format.KEYSWITCH_SLOTS:
        raise InvalidValue(errors.ERR_BAD_KEYSWITCH_SLOT.format(lowest=file_format.KEYSWITCH_SLOTS[0], highest=file_format.KEYSWITCH_SLOTS[-1], value=slot))


def check_keyswitches(value):
    """Refuse keyswitches that aren't a list of the ten slots, each blank or holding a name, a note or both."""
    if not isinstance(value, list) or len(value) != file_format.KEYSWITCH_SLOT_COUNT:
        raise InvalidValue(errors.ERR_BAD_KEYSWITCHES.format(count=file_format.KEYSWITCH_SLOT_COUNT, value=value))
    for slot in value:
        if slot is None:
            continue
        if not isinstance(slot, dict) or not slot or not set(slot) <= set(KEYSWITCH_SETTINGS):
            raise InvalidValue(errors.ERR_BAD_KEYSWITCHES.format(count=file_format.KEYSWITCH_SLOT_COUNT, value=value))
        check_settings(settings=KEYSWITCH_SETTINGS, data=slot)


def _slot_data(keyswitch):
    """Return one slot as a file holds it: its name and note, whichever it has, or None for an empty slot."""
    if keyswitch.is_empty():
        return None
    data = {}
    if keyswitch.name is not None:
        data[KeyswitchSetting.NAME] = keyswitch.name
    if keyswitch.note is not None:
        data[KeyswitchSetting.NOTE] = keyswitch.note
    return data


# An instrument's settings, each described once, in the order they're written to a file.
SETTINGS = described(
    Text(name=InstrumentSetting.DEVICE, error=errors.ERR_DEVICE_NOT_TEXT),
    WholeNumber(name=InstrumentSetting.CHANNEL, lowest=midi.MIN_CHANNEL, highest=midi.MAX_CHANNEL, error=errors.ERR_BAD_CHANNEL),
    WholeNumber(name=InstrumentSetting.GM_SOUND, lowest=limits.MIN_GM_SOUND, highest=limits.MAX_GM_SOUND, error=errors.ERR_BAD_GM_SOUND),
    Checked(name=InstrumentSetting.KEYSWITCHES, check=check_keyswitches),
    WholeNumber(name=InstrumentSetting.KEYSWITCH_LEAD, lowest=limits.MIN_KEYSWITCH_LEAD, highest=limits.MAX_KEYSWITCH_LEAD, error=errors.ERR_BAD_KEYSWITCH_LEAD),
    WholeNumber(name=InstrumentSetting.DEFAULT_VELOCITY, lowest=midi.MIN_VELOCITY, highest=midi.MAX_VELOCITY, error=errors.ERR_BAD_DEFAULT_VELOCITY),
    WholeNumber(name=InstrumentSetting.ACCENT, lowest=limits.MIN_STEP_ACCENT, highest=limits.MAX_STEP_ACCENT, error=errors.ERR_BAD_ACCENT),
    WholeNumber(name=InstrumentSetting.VELOCITY, lowest=limits.MIN_VELOCITY_PERCENT, highest=limits.MAX_VELOCITY_PERCENT, error=errors.ERR_BAD_SHAPE_PERCENT),
    Choice(name=InstrumentSetting.KIND, choices=file_format.INSTRUMENT_KINDS, default=corrections.LEFT_OUT, error=errors.ERR_BAD_INSTRUMENT_KIND),
    WholeNumber(name=InstrumentSetting.LATENCY, lowest=limits.MIN_INSTRUMENT_LATENCY, highest=limits.MAX_INSTRUMENT_LATENCY, error=errors.ERR_BAD_LATENCY),
    Checked(name=InstrumentSetting.SOUND, check=check_sound),
)


# The settings a built-in instrument adds, passed to the constructor by name.
BUILT_IN_SETTINGS = (InstrumentSetting.KIND, InstrumentSetting.LATENCY, InstrumentSetting.SOUND)


class Instrument(HoldsSettings):
    """A MIDI device, by its port's name, and a channel from 1 to 16."""

    __slots__ = ()

    SETTINGS = SETTINGS

    def __init__(self, *, device=None, channel=None, gm_sound=None, keyswitches=None, keyswitch_lead=None, default_velocity=None, accent=None, velocity=None, **built_in):
        """built_in holds a built-in instrument's kind, latency and sound, by their setting names."""
        self.note_change()
        self._settings = settings_by_name(names=SETTINGS, given={
            InstrumentSetting.DEVICE: device, InstrumentSetting.CHANNEL: channel, InstrumentSetting.GM_SOUND: gm_sound,
            InstrumentSetting.KEYSWITCHES: own_copy(keyswitches), InstrumentSetting.KEYSWITCH_LEAD: keyswitch_lead,
            InstrumentSetting.DEFAULT_VELOCITY: default_velocity, InstrumentSetting.ACCENT: accent, InstrumentSetting.VELOCITY: velocity,
            InstrumentSetting.KIND: built_in.get(InstrumentSetting.KIND), InstrumentSetting.LATENCY: built_in.get(InstrumentSetting.LATENCY),
            InstrumentSetting.SOUND: own_copy(built_in.get(InstrumentSetting.SOUND)),
        })
        check_settings(settings=SETTINGS, data=written_settings(self._settings))

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(errors.ERR_INSTRUMENT_EXPECTED_SETTINGS.format(data=data))
            pass_over_unknown(data=data, allowed=SETTINGS)
            return cls(
                device=data.get(InstrumentSetting.DEVICE), channel=data.get(InstrumentSetting.CHANNEL), gm_sound=data.get(InstrumentSetting.GM_SOUND),
                keyswitches=data.get(InstrumentSetting.KEYSWITCHES), keyswitch_lead=data.get(InstrumentSetting.KEYSWITCH_LEAD),
                default_velocity=data.get(InstrumentSetting.DEFAULT_VELOCITY), accent=data.get(InstrumentSetting.ACCENT),
                velocity=data.get(InstrumentSetting.VELOCITY), **{name: data.get(name) for name in BUILT_IN_SETTINGS},
            )

    def copy(self):
        return Instrument(
            device=self.get_device(), channel=self.get_written_channel(), gm_sound=self.get_gm_sound(),
            keyswitches=self._settings[InstrumentSetting.KEYSWITCHES], keyswitch_lead=self.get_written_keyswitch_lead(),
            default_velocity=self.get_default_velocity(), accent=self.get_written_accent(), velocity=self.get_velocity_percent(),
            **{name: self._settings[name] for name in BUILT_IN_SETTINGS},
        )

    def get_kind(self):
        """Return what it is: a MIDI device and channel, or a sound llamatron makes itself (InstrumentKind)."""
        return or_default(value=self._settings[InstrumentSetting.KIND], default=InstrumentKind.MIDI)

    def is_built_in(self):
        return self.get_kind() == InstrumentKind.BUILT_IN

    @notes_change
    def set_kind(self, kind):
        SETTINGS[InstrumentSetting.KIND].check(kind)
        self._settings[InstrumentSetting.KIND] = None if kind == InstrumentKind.MIDI else kind

    def get_latency(self):
        """Return how many milliseconds earlier its notes are sent, for a MIDI synth slow to sound."""
        return or_default(value=self._settings[InstrumentSetting.LATENCY], default=defaults.DEFAULT_INSTRUMENT_LATENCY)

    @notes_change
    def set_latency(self, milliseconds):
        SETTINGS[InstrumentSetting.LATENCY].check(milliseconds)
        self._settings[InstrumentSetting.LATENCY] = None if milliseconds == defaults.DEFAULT_INSTRUMENT_LATENCY else milliseconds

    def get_sound(self, name):
        """Return one of its built-in sound's settings (SoundSetting), the default where it has none."""
        return sound_value(sound=self._settings[InstrumentSetting.SOUND], name=name)

    @notes_change
    def set_sound(self, *, name, value):
        """Store one of its built-in sound's settings, refusing a value out of range."""
        sound = dict(self._settings[InstrumentSetting.SOUND] or {})
        sound[name] = own_copy(value)
        check_sound(sound)
        self._settings[InstrumentSetting.SOUND] = sound

    def synth_spec(self):
        """Return its built-in sound as the Synthesis Process compiles it."""
        return synth_spec(self._settings[InstrumentSetting.SOUND])

    def get_device(self):
        """Return the name of its MIDI output port, or None until one is chosen."""
        return self._settings[InstrumentSetting.DEVICE]

    def get_channel(self):
        """Return its channel as people number them, 1 to 16."""
        return or_default(value=self._settings[InstrumentSetting.CHANNEL], default=defaults.DEFAULT_CHANNEL)

    def get_written_channel(self):
        """Return its channel as the file holds it, or None for the default."""
        return self._settings[InstrumentSetting.CHANNEL]

    def has_device(self):
        return self.get_device() is not None

    def uses_fluidsynth(self):
        """Return whether it plays through FluidSynth, which the tracker starts, rather than through a MIDI port: its channel is then chosen for each track and its General MIDI sound sent."""
        return self.get_device() == file_format.FLUIDSYNTH_DEVICE

    def set_device(self, device):
        """Name its MIDI output port, or None to choose none."""
        self.set_written(name=InstrumentSetting.DEVICE, value=device)

    def get_gm_sound(self):
        """Return the General MIDI sound a General MIDI export gives its tracks, 1 to 128, or None for none."""
        return self._settings[InstrumentSetting.GM_SOUND]

    def set_gm_sound(self, sound):
        """Choose its General MIDI sound, 1 to 128, or None for none."""
        self.set_written(name=InstrumentSetting.GM_SOUND, value=sound)

    @notes_change
    def set_channel(self, channel):
        SETTINGS[InstrumentSetting.CHANNEL].check(channel)
        self._settings[InstrumentSetting.CHANNEL] = channel

    def get_keyswitches(self):
        """Return its ten keyswitch slots in order, each a Keyswitch with its name and note, or None for whichever it lacks."""
        written = self._settings[InstrumentSetting.KEYSWITCHES]
        if written is None:
            return [NO_KEYSWITCH] * file_format.KEYSWITCH_SLOT_COUNT
        keyswitches = []
        for slot in written:
            keyswitches.append(_keyswitch_of(slot))
        return keyswitches

    def get_keyswitch(self, slot):
        """Return one keyswitch slot, numbered from 0."""
        check_keyswitch_slot(slot)
        return self.get_keyswitches()[slot]

    def has_keyswitches(self):
        """Return whether any slot has a name or a note."""
        return self._settings[InstrumentSetting.KEYSWITCHES] is not None

    def get_keyswitch_notes(self):
        """Return the MIDI note of every slot that has one, by slot, which is all that playing asks."""
        notes = {}
        for slot, keyswitch in enumerate(self.get_keyswitches()):
            if keyswitch.note is not None:
                notes[slot] = keyswitch.note
        return notes

    @notes_change
    def set_keyswitch(self, *, slot, name=None, note=None):
        """Give a slot its name and its note, where None leaves the slot without one, so both None empties the slot."""
        check_keyswitch_slot(slot)
        if name is not None:
            check_keyswitch_name(name)
        if note is not None:
            check_keyswitch_note(note)
        keyswitches = self.get_keyswitches()
        keyswitches[slot] = Keyswitch(name, note)
        self._settings[InstrumentSetting.KEYSWITCHES] = _written_slots(keyswitches)

    @notes_change
    def set_keyswitches(self, keyswitches):
        """Give every slot its name and note at once, from ten Keyswitches in order, as the Keyswitch Map dialog answers them."""
        if len(keyswitches) != file_format.KEYSWITCH_SLOT_COUNT:
            raise InvalidValue(errors.ERR_BAD_KEYSWITCHES.format(count=file_format.KEYSWITCH_SLOT_COUNT, value=list(keyswitches)))
        given = []
        for keyswitch in keyswitches:
            given.append(Keyswitch(*keyswitch))
        written = _written_slots(given)
        if written is not None:
            check_keyswitches(written)
        self._settings[InstrumentSetting.KEYSWITCHES] = written

    def get_default_velocity(self):
        """Return the velocity a step with none typed plays at on its tracks, or None for the loudest, as a track with no instrument plays."""
        return self._settings[InstrumentSetting.DEFAULT_VELOCITY]

    def get_velocity_percent(self):
        """Return the percentage of its written velocity every clip of its tracks plays, or None for 100%."""
        return self._settings[InstrumentSetting.VELOCITY]

    def get_accent(self):
        """Return what an accented step adds to its velocity on its tracks, before each track's own accent."""
        return or_default(value=self._settings[InstrumentSetting.ACCENT], default=defaults.DEFAULT_INSTRUMENT_ACCENT)

    def get_written_accent(self):
        """Return its accent as the file holds it, or None for the default."""
        return self._settings[InstrumentSetting.ACCENT]

    def set_default_velocity(self, velocity):
        """Set the velocity a step with none typed plays at on its tracks, or None for the loudest."""
        self.set_written(name=InstrumentSetting.DEFAULT_VELOCITY, value=velocity)

    def set_accent(self, accent):
        """Set what an accented step adds on its tracks, or None for the default."""
        self.set_written(name=InstrumentSetting.ACCENT, value=accent)

    def get_keyswitch_lead(self):
        """Return how many milliseconds before its note a keyswitch is sent, 0 for at the same moment."""
        return or_default(value=self._settings[InstrumentSetting.KEYSWITCH_LEAD], default=defaults.DEFAULT_KEYSWITCH_LEAD)

    def get_written_keyswitch_lead(self):
        """Return its keyswitch lead as the file holds it, or None for the default."""
        return self._settings[InstrumentSetting.KEYSWITCH_LEAD]

    @notes_change
    def set_keyswitch_lead(self, milliseconds):
        """Set how early its keyswitches are sent, in milliseconds, or None for the default."""
        if milliseconds is not None:
            SETTINGS[InstrumentSetting.KEYSWITCH_LEAD].check(milliseconds)
        self._settings[InstrumentSetting.KEYSWITCH_LEAD] = milliseconds


def _keyswitch_of(slot):
    """Return one slot as the file holds it as a Keyswitch, or NO_KEYSWITCH for an empty slot."""
    if slot is None:
        return NO_KEYSWITCH
    return Keyswitch(slot.get(KeyswitchSetting.NAME), slot.get(KeyswitchSetting.NOTE))


def _written_slots(keyswitches):
    """Return the slots as a file holds them, or None when every slot is empty, which the file leaves out."""
    written = []
    for keyswitch in keyswitches:
        written.append(_slot_data(keyswitch))
    for slot in written:
        if slot is not None:
            return written
    return None
