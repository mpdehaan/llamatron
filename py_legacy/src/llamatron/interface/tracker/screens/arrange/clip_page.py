# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Clip page: one clip: what it plays, how many times, and whether it morphs into another pattern."""

from rich.text import Text

from llamatron.interface.forms.nodes import Button
from llamatron.interface.forms.text import clock, scene_name
from llamatron.interface.pages.clip import AddRow, ClipPresenter, PatternRow
from llamatron.interface.tracker import keybindings, themes
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.listening import listen, stop_listening
from llamatron.model.schema import defaults
from llamatron.model.schema.file_format import ClipSlotSetting, Section
from llamatron.user_strings import help as help_text, labels as labels_text, legends, messages


class ClipPage(FieldPage):
    """One clip: what it plays, how many times, and whether it morphs into another pattern: the Clip presenter's form
    (interface/pages/clip.py), with listening, move mode for its list of patterns, opening a pattern, and the notes under its
    settings drawn in the tracker's dim."""

    THEME = themes.FROM_ARRANGE

    KEYS = keybindings.ClipPage

    HELP = help_text.HELP_CLIP_PAGE

    def __init__(self, *, holder, index, track):
        super().__init__(holder)
        self.index = index
        # Move mode: whether M has picked up the pattern under the cursor, and whether it has been carried yet, so that one move is one undo step.
        self.moving = False
        self.carried = False
        self.track = track

    def still_exists(self):
        song = self.document().song()
        return self.index < len(song.get_scenes()) and song.has_track(self.track) and self.clip_slot() is not None

    def follow_renames(self, renames):
        track_renames = renames.get(Section.TRACKS, {})
        self.track = track_renames.get(self.track, self.track)

    def crumb_trail(self):
        scene = scene_name(scene=self._scene(), index=self.index)
        return (labels_text.Crumb.ARRANGE, labels_text.MSG_CLIP_CRUMB.format(scene=scene, track=self.track))

    def caption(self):
        scene = scene_name(scene=self._scene(), index=self.index)
        name = labels_text.MSG_CLIP_CAPTION_NAME.format(scene=scene, track=self.track)
        what = labels_text.MSG_CLIP_CAPTION_WORD.upper()
        return labels_text.MSG_EDITING_CAPTION.format(what=what, name=name)

    def duration(self):
        lengths = self.document().lengths()
        return lengths.clip_seconds(index=self.index, track=self.track)

    def presenter(self):
        """Return what the page shows and does, for its clip as it is now."""
        return ClipPresenter(page=self, document=self.document(), index=self.index, track=self.track)

    def clip_slot(self):
        return self.document().clip_slot(index=self.index, track=self.track)

    def fields(self):
        return self.presenter().form()

    def page_keys(self):
        if self.is_listening():
            listening = self.bind(self.KEYS.STOP_LISTENING, action=self.stop)
        else:
            listening = self.bind(self.KEYS.LISTEN, action=self.listen)
        result = [self.bind(self.KEYS.ADD_PATTERN, action=self._add_pattern)]
        if isinstance(self.field(), PatternRow):
            result.append(self.bind(self.KEYS.MOVE_PATTERN, action=self.start_moving))
        return [*result, self.bind(self.KEYS.OPEN_PATTERN, action=self.open_pattern), listening]

    def fields_depend_on(self):
        """Return what the fields read besides the set: whether the clip plays on its own, which names the Listen button."""
        return (self.is_listening(),)

    def is_listening(self):
        """Return whether the clip plays on its own: through its track's instrument, or through General MIDI while Real Time is
        off."""
        if self.app.transport.is_clip_playing(index=self.index, track=self.track):
            return True
        preview = self.app.pattern_preview()
        return preview.playing_clip() == (self.index, self.track)

    def listen(self):
        """Play the clip as its scene would, again and again, through its track's instrument or one picked for this listening."""
        clip_slot = self.clip_slot()
        listen(page=self, index=self.index, track=self.track, name=clip_slot.get_display_name())

    def stop(self):
        stop_listening(self)

    def open_pattern(self):
        """Open the pattern editor on the clip's pattern, from any field, with this page's crumbs before the pattern's, so that
        ESC comes back here."""
        row = self.field()
        place = 0
        if isinstance(row, PatternRow):
            place = row.place
        self.open_pattern_at(place)

    def open_pattern_at(self, place):
        """Open the pattern editor on one pattern of the clip's list."""
        clip_slot = self.clip_slot()
        names = clip_slot.get_pattern_names()
        self.open_editor(section=Section.PATTERNS, name=names[place], opened_from=self, track=self.track)

    def keys(self):
        if self.moving:
            return [self.bind(self.KEYS.DROP, action=self.drop), self.bind(self.KEYS.CARRY, action=self.carry)]
        return super().keys()

    def start_moving(self):
        self.moving = True
        self.carried = False
        self.say_moving()

    def say_moving(self):
        clip_slot = self.clip_slot()
        names = clip_slot.get_pattern_names()
        row = messages.MSG_MOVING_ROW.format(name=names[self.field().place])
        self.say(messages.MSG_MOVING.format(what=row))

    def carry(self, offset):
        """Carry the picked-up pattern one place up or down its list, every carry of one move making one undo step."""
        names = self.clip_slot().get_pattern_names()
        place = self.field().place
        to = place + offset
        if not 0 <= to < len(names):
            return
        if self.carried:
            self.document().continue_edit()
        self.carried = True
        names[place], names[to] = names[to], names[place]
        self.presenter().set_value(setting=ClipSlotSetting.PATTERNS, value=names)
        self.cursor.shift(offset)
        self.say_moving()

    def drop(self):
        self.moving = False

    def ends_a_list(self, field):
        return isinstance(field, AddRow)

    def is_carrying(self, place):
        row = self.field()
        return self.moving and isinstance(row, PatternRow) and row.place == place

    def listen_button(self):
        """Return the Listen button, drawn below the settings after a blank line as every page's buttons are, which does what L
        does: it starts listening to the clip, or stops it while the clip plays."""
        # Both names take the room of the longer, so that the button never changes its width as it changes its name.
        width = max(len(labels_text.MSG_LISTEN_LABEL), len(labels_text.MSG_STOP_LISTENING_LABEL))
        if self.is_listening():
            return Button(label=labels_text.MSG_STOP_LISTENING_LABEL.center(width), key_name=legends.KeyName.L, enter=self.stop, enter_what=legends.MSG_STOP_LISTENING_WHAT)
        return Button(label=labels_text.MSG_LISTEN_LABEL.center(width), key_name=legends.KeyName.L, enter=self.listen, enter_what=legends.MSG_LISTEN_WHAT)

    def remarks(self, width):
        document = self.document()
        lengths = document.lengths()
        clip_slot = self.clip_slot()
        length = clock(lengths.clip_seconds(index=self.index, track=self.track))
        scene_length = clock(lengths.scene_seconds(self.index))
        lines = [Text(messages.MSG_CLIP_LENGTH_NOTE.format(length=length, scene=scene_length), style=Style.DIM)]
        if clip_slot.loops():
            lines.append(Text(messages.MSG_LOOP_NOTE, style=Style.DIM))
        elif clip_slot.get_repeat() == defaults.DEFAULT_REPEAT:
            lines.append(Text(messages.MSG_MORPH_HINT_NOTE, style=Style.DIM))
        if clip_slot.get_grab_track() is not None and not self._grabs_anywhere():
            lines.append(Text(messages.MSG_GRAB_HINT_NOTE, style=Style.DIM))
        problem = lengths.scene_problem(self.index)
        if problem:
            lines.append(Text(messages.MSG_PROBLEM_NOTE.format(problem=problem)[:width]))
        return lines

    def _grabs_anywhere(self):
        """Return whether any pattern of the clip's list has a step that grabs."""
        clip_slot = self.clip_slot()
        document = self.document()
        for name in clip_slot.get_pattern_names():
            if document.has_grab_steps(name):
                return True
        return False

    def _scene(self):
        """Return the scene the clip is in."""
        song = self.document().song()
        scenes = song.get_scenes()
        return scenes[self.index]


    def _add_pattern(self):
        self.presenter().add_pattern()
