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
from llamatron.user_strings import errors, help as help_text, labels, legends, marks, messages



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

    def preview_button(self):
        """Return the Preview pattern button, which opens the instrument's own pattern for designing its sound."""
        return Button(label=labels.MSG_PREVIEW_PATTERN_LABEL, enter=self.open_preview, enter_what=legends.What.EDIT)

    def open_preview(self):
        """Open the pattern editor on the instrument's preview pattern, made first if it has none, with this page's crumbs before
        it, so that ESC comes back here."""
        document = self.document()
        document.make_preview(self.item)
        self.open_editor(section=Section.PATTERNS, name=document.preview_of(self.item), opened_from=self)

    def keyswitch_map_button(self):
        """Return the Keyswitch Map button, showing its key."""
        return Button(label=labels.MSG_KEYSWITCH_MAP_LABEL, key_name=self.KEYS.KEYSWITCH_MAP.name, enter=self.open_keyswitch_map, enter_what=self.KEYS.KEYSWITCH_MAP[2])

    def set_gm_sound(self, sound):
        self.presenter().set_gm_sound(sound)

    def set_device(self, device):
        self.presenter().set_device(device)

    def page_keys(self):
        listening = self.bind(self.KEYS.LISTEN, action=self.listen)
        if self.is_listening():
            listening = self.bind(self.KEYS.STOP_LISTENING, action=self.stop_listening)
        return [self.bind(self.KEYS.KEYSWITCH_MAP, action=self.open_keyswitch_map), listening]

    def fields_depend_on(self):
        """Return what the fields read besides the set: whether the instrument is being listened to, which names the Listen button."""
        return (self.is_listening(),)

    def listen_button(self):
        """Return the Listen button, which does what L does: it starts listening to the instrument, or stops it while it plays."""
        # Both names take the room of the longer, so that the button never changes its width as it changes its name.
        width = max(len(labels.MSG_LISTEN_LABEL), len(labels.MSG_STOP_LISTENING_LABEL))
        if self.is_listening():
            return Button(label=labels.MSG_STOP_LISTENING_LABEL.center(width), key_name=legends.KeyName.L, enter=self.stop_listening, enter_what=legends.MSG_STOP_LISTENING_WHAT)
        return Button(label=labels.MSG_LISTEN_LABEL.center(width), key_name=legends.KeyName.L, enter=self.listen, enter_what=legends.MSG_LISTEN_WHAT)

    def is_listening(self):
        return self.app.pattern_preview().playing_instrument() == self.item

    def listen(self):
        """Play the instrument's preview pattern again and again until stopped, an edit to the instrument or the pattern heard on
        the next pass."""
        preview = self.app.pattern_preview()
        refusal = preview.instrument_refusal(self.item)
        if refusal is not None:
            self.refuse(refusal)
            return
        trial = self.document().preview_data(self.item)
        refusal = self.app.transport.try_play(lambda: preview.play_instrument(instrument=self.item, trial=trial)).refusal
        if refusal is not None:
            self.tell(errors.ERR_CANT_PLAY_TITLE, refusal)
            return
        self.say(messages.MSG_LISTENING_TO_INSTRUMENT.format(name=self.item))

    def stop_listening(self):
        self.app.pattern_preview().stop()
        self.say(messages.MSG_STOPPED)

    def open_keyswitch_map(self):
        """Open the Keyswitch Map, whose ten slots go into the instrument together on OK, as one undo step."""
        dialog = KeyswitchMapDialog(title=messages.MSG_KEYSWITCH_MAP_TITLE.format(instrument=self.item), keyswitches=self.instrument().get_keyswitches(), setlist=self.document().get_setlist())
        self.ask(dialog=dialog, then=lambda keyswitches: self.document().change_set(self.document().get_setlist().get_instrument(self.item).set_keyswitches, keyswitches))


def sounds_of_family(place):
    """Return the General MIDI numbers of the sounds of a family, by the family's place."""
    return range(place * limits.GM_FAMILY_SIZE + limits.MIN_GM_SOUND, (place + 1) * limits.GM_FAMILY_SIZE + limits.MIN_GM_SOUND)
