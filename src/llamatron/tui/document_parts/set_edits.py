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

"""The Document's edits to what the whole set shares: its settings, songs, scales, generators, chains and grooves.

Renaming, copying, deleting, moving and sorting any of them is in named_edits.py, which takes
the section. What's here is what each kind alone has: how a new one starts, and its own settings.
"""


from llamatron.composition.chain import Chain
from llamatron.composition.file_format import Section
from llamatron.composition.groove import new_groove
from llamatron.composition.instrument import Instrument
from llamatron.composition.generator_settings import GENERATOR_SETTINGS, ProgressionSetting
from llamatron.music.note import FLAT_SIGN
from llamatron.composition.named_scale import NamedScale, scale_type_name
from llamatron.composition.sections import GENERATOR_KINDS
from llamatron.importers.writing import add_imported
from llamatron.composition.naming import default_scale_name, is_default_scale_name, words
from llamatron.strings.marks import MSG_SCALE_NOTES_TEXT



class SetEdits:
    """The changes the File, Songs, Scales, Generators, Chains and Grooves pages make, each through the set's own setters.

    It holds no data of its own: it works on what Document keeps, through `self._setlist`,
    `self.song()` and `self._change(method, ...)`, which makes one change through an object's own
    method and notes it.
    """

    __slots__ = ()

    # The set's own settings, from the File page.

    def set_default_step_size(self, step_size):
        """Set how long a step is in every pattern that doesn't set its own."""
        self._change(self._setlist.set_step_size, step_size)

    def set_default_octave(self, octave):
        self._change(self._setlist.set_default_octave, octave)

    def set_default_drum_octave(self, octave):
        self._change(self._setlist.set_default_drum_octave, octave)

    def set_octave_labels(self, labels):
        self._change(self._setlist.set_octave_labels, labels)

    def set_visualizer(self, name):
        """Name the visualizer mode Arrange shows first, unless a song names its own, or None for the first in the list."""
        self._change(self._setlist.set_visualizer, name)

    def set_visualizer_hidden(self, *, name, hidden):
        """Leave a visualizer mode out of Arrange's visualizer key, or put it back."""
        self._change(self._setlist.set_visualizer_hidden, name=name, hidden=hidden)

    def set_default_follow_action(self, advance):
        """Set what a clip sends down in real-time playback when its scene is done, unless the clip says otherwise."""
        self._change(self._setlist.set_default_follow_action, advance)

    def set_title(self, text):
        self._change(self._setlist.set_title, text)

    def set_protected(self, value):
        """Protect the set's file from being saved over, or stop protecting it."""
        self._change(self._setlist.set_protected, value)

    def set_author(self, text):
        self._change(self._setlist.set_author, text)

    def set_description(self, text):
        """Set the one line that says what the set is. Blank text removes it."""
        self._change(self._setlist.set_description, text)

    def set_notes(self, text):
        """Set the notes, kept as given, so that their lines stay as written. Blank text removes them."""
        self._change(self._setlist.set_notes, text)

    # The songs of the set.

    def song_names(self):
        return self._setlist.get_song_names()

    def add_song(self, name):
        """Add a song with its first track and scene at the end of the set, and make it current."""
        self._change(self._setlist.add_started_song, name)
        self.select_song(name)

    def import_song(self, imported):
        """Add a song the MIDI import made, with its patterns and scales, as one change, and make it current."""
        add_imported(setlist=self._setlist, imported=imported)
        self.changed()
        self.select_song(imported.name)

    # Scales.

    def _scale(self, name):
        return self._setlist.get_named_scale(name)

    def scale_size(self, name):
        return self._scale(name).get_size()

    def scale_half_steps(self, name):
        """Return a scale's degrees as half steps above its root, starting with 0."""
        return self._scale(name).get_half_steps()

    def scale_spells_flats(self, name):
        """Return whether a scale's root is spelled with a flat, so that a note between two of its degrees is named as a flat too."""
        return self._scale(name).get_root().endswith(FLAT_SIGN)

    def scale_note_at(self, *, name, octave, half_steps):
        """Return the name and sounding octave of the note some half steps above a scale's root in an octave, spelled as the root is, for a piano roll row between two degrees."""
        return self._scale(name).scale_at(octave).get_root().spelled_half_step(half_steps)

    def scale_degree_octave(self, *, name, octave, place):
        """Return the octave the degree at a place of a scale sounds in when its root is in an octave, for the piano roll's row labels."""
        return self._scale(name).octave_of_degree(octave=octave, place=place)

    def scale_notes_text(self, name):
        """Return what a named scale is, like F minor."""
        scale = self._scale(name)
        return MSG_SCALE_NOTES_TEXT.format(root=scale.get_root(), kind=words(scale_type_name(scale.get_scale_type())))

    def scale_name_says_what_it_is(self, name):
        """Return whether a scale is still named after its root and kind, like C Major, so that showing both would say it twice."""
        scale = self._scale(name)
        return is_default_scale_name(name=name, root=scale.get_root(), kind=scale.get_kind())

    def add_scale(self, *, name, root, kind):
        self._change(self._setlist.add_item, section=Section.SCALES, name=name, item=NamedScale(root=root, kind=kind))

    def change_scale(self, *, name, root, kind):
        """Change what a named scale is, which changes everything that uses it."""
        self._change(self._setlist.replace_item, section=Section.SCALES, name=name, item=NamedScale(root=root, kind=kind))

    def set_scale_root(self, *, name, root):
        """Change a named scale's root, which moves everything that uses it, and return the scale's name, which may have followed."""
        scale = self._scale(name)
        was_default = is_default_scale_name(name=name, root=scale.get_root(), kind=scale.get_kind())
        self._change(scale.set_root, root)
        return self._scale_name_following_its_notes(name=name, was_default=was_default)

    def set_scale_kind(self, *, name, kind):
        """Change a named scale's kind, which changes everything that uses it, and return the scale's name, which may have followed."""
        scale = self._scale(name)
        was_default = is_default_scale_name(name=name, root=scale.get_root(), kind=scale.get_kind())
        self._change(scale.set_kind, kind)
        return self._scale_name_following_its_notes(name=name, was_default=was_default)

    def _scale_name_following_its_notes(self, *, name, was_default):
        """Rename a scale that was still named after its root and kind, like C Major, to say what it is now, and return its name.

        A scale with a name of the user's own, like main, keeps it, and so does one whose new
        name is already taken. The user asked for this on 2026-11-07, so that a scale can't be
        called C Major and play D minor.
        """
        scale = self._scale(name)
        new = default_scale_name(root=scale.get_root(), kind=scale.get_kind())
        if not was_default or new == name or self._setlist.has_scale(new):
            return name
        self.rename_named(section=Section.SCALES, old=name, new=new)
        return new

    # Arps and chains.

    def _generator(self, *, section, name):
        return self._setlist.get_generator_settings(kind=GENERATOR_KINDS[section], name=name)

    def add_generator(self, *, section, name):
        """Add an arp or an AutoRatchet with the settings a new one starts with."""
        kind = GENERATOR_KINDS[section]
        settings = GENERATOR_SETTINGS[kind].new()
        self._change(self._setlist.add_item, section=section, name=name, item=settings)

    def set_generator_setting(self, *, section, name, setting, value):
        """Set one setting of a named arp or AutoRatchet, or None to leave it out and use its default."""
        self._change(self._generator(section=section, name=name).set_setting, name=setting, value=value)

    def set_progression(self, *, name, chords, accidentals, inversions, scales=None, qualities=None, tensions=None):
        """Set a progression's chords, with a sharp or flat, an inversion, a borrowed scale type, a quality and tensions for each, a row of nothing left out."""
        progression = self._generator(section=Section.PROGRESSIONS, name=name)
        nothing = [None] * len(chords)
        rows = {
            ProgressionSetting.CHORDS: chords, ProgressionSetting.ACCIDENTALS: accidentals, ProgressionSetting.INVERSIONS: inversions,
            ProgressionSetting.SCALES: scales or nothing, ProgressionSetting.QUALITIES: qualities or nothing,
            ProgressionSetting.TENSIONS: [None if value is None else list(value) for value in tensions or nothing],
        }
        for setting, values in rows.items():
            self._change(progression.set_setting, name=setting, value=list(values) if any(value is not None for value in values) else None)

    def set_arp_offset(self, *, name, step, offset):
        """Set one step of an arp's offsets, where None is a silent step."""
        self._change(self._generator(section=Section.ARPS, name=name).set_offset, step=step, offset=offset)

    def insert_arp_offset(self, *, name, step):
        """Add a step of 0 before a step of an arp's offsets."""
        self._change(self._generator(section=Section.ARPS, name=name).insert_offset, step)

    def set_arp_step_add(self, *, name, register, step, add):
        """Set what one step of an arp's offsets adds to a register, where None or 0 adds nothing."""
        self._change(self._generator(section=Section.ARPS, name=name).set_step_add, register=register, step=step, add=add)

    def remove_arp_offset(self, *, name, step):
        self._change(self._generator(section=Section.ARPS, name=name).remove_offset, step)

    def _chain(self, name):
        return self._setlist.get_chain(name)

    def add_chain(self, name):
        self._change(self._setlist.add_item, section=Section.CHAINS, name=name, item=Chain([]))

    def add_chain_step(self, *, chain, kind, name):
        """Add a generator, by kind and name, to the end of a chain."""
        self._change(self._chain(chain).add_step, kind=kind, name=name, setlist=self._setlist)

    def set_chain_step(self, *, chain, place, kind, name):
        self._change(self._chain(chain).set_step, place=place, kind=kind, name=name, setlist=self._setlist)

    def copy_chain_step(self, *, chain, place):
        """Put a copy of a chain's step right after it."""
        self._change(self._chain(chain).copy_step, place)

    def remove_chain_step(self, *, chain, place):
        self._change(self._chain(chain).remove_step, place)

    def move_chain_step(self, *, chain, place, offset):
        """Move a chain's step up or down, and return whether it moved."""
        if not self._chain(chain).move_step(place=place, offset=offset):
            return False
        self.changed()
        return True

    # Grooves, of the set, beside the factory grooves every set has, which can be copied but not changed.

    def add_instrument(self, name):
        """Add an instrument with no device yet under a name. The first instrument turns real-time playback on (the user's design of 2026-11-09)."""
        first = not self._setlist.get_instrument_names()
        self._change(self._setlist.add_item, section=Section.INSTRUMENTS, name=name, item=Instrument())
        if first:
            self._change(self._setlist.set_real_time, True)

    def set_instrument_device(self, *, name, device):
        self._change(self._setlist.get_instrument(name).set_device, device)

    def set_instrument_channel(self, *, name, channel):
        self._change(self._setlist.get_instrument(name).set_channel, channel)

    def set_instrument_gm_sound(self, *, name, sound):
        """Choose an instrument's General MIDI sound, 1 to 128, or None for none."""
        self._change(self._setlist.get_instrument(name).set_gm_sound, sound)

    def set_real_time(self, value):
        """Turn real-time playback on or off, the main screen's Real Time switch."""
        self._change(self._setlist.set_real_time, value)

    def add_groove(self, name):
        """Add a straight groove of one bar of 16ths under a name, which can't be a factory groove's."""
        self._change(self._setlist.add_item, section=Section.GROOVES, name=name, item=new_groove())

    def set_groove_cell(self, *, name, step, amount):
        self._change(self._setlist.get_groove(name).set_cell, step=step, amount=amount)

    def insert_groove_cell(self, *, name, step):
        """Add a straight cell before a cell of one of the set's grooves."""
        self._change(self._setlist.get_groove(name).insert_cell, step)

    def remove_groove_cell(self, *, name, step):
        self._change(self._setlist.get_groove(name).remove_cell, step)

    def set_groove_cell_length(self, *, name, length):
        """Set how long a groove's cells are, as the file writes it, like 1/8."""
        self._change(self._setlist.get_groove(name).set_cell_length, length)
