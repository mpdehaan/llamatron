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

"""The Clip page: one clip: what it plays, how many times, and whether it morphs into another pattern."""

from rich.text import Text

from llamatron.composition.clip_slot import MORPH_STYLES
from llamatron.composition.defaults import DEFAULT_REPEAT
from llamatron.composition.file_format import SHAPES, shape_setting, strum_setting, FOLLOW_ACTION_CHOICES, ClipSlotSetting, DIRECTIONS, Section
from llamatron.composition.limits import MAX_CLIP_REPEAT, MIN_REPEAT
from llamatron.playback.song_renderer import GRAB_ARROW
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.composition.clip_slot import FIRST_MORPH_STYLE
from llamatron.composition.naming import words
from llamatron.tui.text import clock, sorted_names
from llamatron.tui.drawing import NOTHING, Style
from llamatron.strings.help import HELP_CLIP_PAGE
from llamatron.tui.screens.field import Button, ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.pattern_editor import PatternEditor
from llamatron.tui.screens.listening import listen, stop_listening
from llamatron.tui.screens.shared import columns, scene_name
from llamatron.strings.errors import (
    ERR_ADD_ANOTHER_TRACK, ERR_CIRCULAR_GRAB_TITLE, ERR_GRAB_CIRCLE, ERR_LOOP_SCENES_TITLE, ERR_NO_OTHER_TRACKS_TITLE,
    ERR_REMOVE_OTHER_GRAB,
)
from llamatron.strings.labels import MSG_STRUM_WORDS
from llamatron.strings.labels import MSG_CLIP_CAPTION_NAME, MSG_CLIP_CAPTION_WORD, MSG_EDITING_CAPTION
from llamatron.strings.labels import (
    MSG_TRACK_STRUM_CHOICE,
    MSG_FOLLOW_ACTION_LABEL, MSG_FOLLOW_ACTION_NAMES, MSG_CLIP_CRUMB, Crumb, MSG_DIRECTION_LABEL, MSG_DIRECTION_NAMES, MSG_GRAB_TRACK_LABEL, MSG_LOOP_LABEL,
    MSG_MORPH_DIRECTION_LABEL, MSG_MORPH_TO_LABEL, MSG_PATTERN_DIRECTION_OPTION, MSG_PATTERN_LABEL, MSG_PLAY_LABEL, MSG_REPEAT_LABEL, MSG_STOP_LABEL,
    MSG_SCALE_LABEL, MSG_SCENE_OPTION,
)
from llamatron.strings.legends import (
    KeyName, MSG_LISTEN_WHAT, MSG_STOP_WHAT, MSG_USE_PATTERN_NAME_WHAT, MSG_NO_GRAB_WHAT, MSG_NO_MORPH_WHAT, MSG_PATTERN_DIRECTION_WHAT,
    MSG_USE_PATTERN_DIRECTION_WHAT, MSG_USE_SCENE_SCALE_WHAT, What,
)
from llamatron.strings.marks import (
    MSG_CLIP_NAMED_FOR_PATTERN, MSG_LOOP_OFF_SHOWN, MSG_LOOP_ON_SHOWN, MSG_NONE_SHOWN, MSG_FROM_SET_SHOWN, MSG_FROM_TRACK_SHOWN, MSG_PATTERN_DIRECTION_SHOWN, MSG_SCENE_SCALE_SHOWN,
)
from llamatron.strings.messages import (
    MSG_CLIP_SCALE_TITLE, MSG_NO_SCALE,
    MSG_CLIP_NAME_PROMPT, MSG_CLIP_LENGTH_NOTE, MSG_GRAB_HINT_NOTE, MSG_LOOP_NOTE, MSG_MORPH_HINT_NOTE, MSG_PLAY_DIRECTION_TITLE,
    MSG_PROBLEM_NOTE,
)
from llamatron.tui.uses import loop_error_lines
from llamatron.tui.screens.chains_field import chains_field
from llamatron.tui.screens.shape_fields import shape_section
from llamatron.tui.screens.strum_fields import strum_section
from llamatron.tui import themes
from llamatron.tui import keybindings


class ClipPage(FieldPage):
    """One clip: what it plays, how many times, and whether it morphs into another pattern."""

    THEME = themes.FROM_ARRANGE

    KEYS = keybindings.ClipPage

    HELP = HELP_CLIP_PAGE

    def __init__(self, *, holder, index, track):
        super().__init__(holder)
        self.index = index
        self.track = track

    def still_exists(self):
        song = self.document().song()
        return self.index < len(song.get_scenes()) and song.has_track(self.track) and self.clip_slot() is not None

    def follow_renames(self, renames):
        self.track = renames.get(Section.TRACKS, {}).get(self.track, self.track)

    def crumb_trail(self):
        scene = scene_name(scene=self.document().song().get_scenes()[self.index], index=self.index)
        return (Crumb.ARRANGE, MSG_CLIP_CRUMB.format(scene=scene, track=self.track))

    def caption(self):
        scene = scene_name(scene=self.document().song().get_scenes()[self.index], index=self.index)
        return MSG_EDITING_CAPTION.format(what=MSG_CLIP_CAPTION_WORD.upper(), name=MSG_CLIP_CAPTION_NAME.format(scene=scene, track=self.track))

    def duration(self):
        return self.document().lengths().clip_seconds(index=self.index, track=self.track)

    def clip_slot(self):
        return self.document().clip_slot(index=self.index, track=self.track)

    def page_keys(self):
        listening = self.bind(self.KEYS.STOP_LISTENING, action=self.stop) if self.is_listening() else self.bind(self.KEYS.LISTEN, action=self.listen)
        return [self.bind(self.KEYS.OPEN_PATTERN, action=self.open_pattern), listening]

    def is_listening(self):
        """Return whether the clip plays on its own: through its track's instrument, or through General MIDI while Real Time is off."""
        return self.app.transport.is_clip_playing(index=self.index, track=self.track) or self.app.pattern_preview().playing_clip() == (self.index, self.track)

    def listen(self):
        """Play the clip as its scene would, again and again, through its track's instrument or one picked for this listening."""
        listen(page=self, index=self.index, track=self.track, name=self.clip_slot().get_display_name())

    def stop(self):
        stop_listening(self)

    def open_pattern(self):
        """Open the pattern editor on the clip's pattern, from any field, with this page's crumbs before the pattern's, so that Esc comes back here."""
        self.show_page(PatternEditor(holder=self.holder, name=self.clip_slot().get_pattern_name(), opened_from=self))

    def set_value(self, *, setting, value):
        """Set one of the clip's settings, or None to leave it out and use its default."""
        self.document().set_clip_slot_setting(index=self.index, track=self.track, setting=setting, value=value)

    def clear(self, setting):
        self.set_value(setting=setting, value=None)

    def pick_pattern(self, *, title, current, then):
        """Ask for one of the song's patterns, starting on the current one, and pass its name to then."""
        patterns = sorted_names(self.document().song().get_pattern_names())
        place = patterns.index(current) if current in patterns else 0
        self.ask(dialog=ChoiceDialog(title=title, options=patterns, current=place), then=lambda item: then(patterns[item]))

    def set_morph_target(self, pattern):
        self.document().set_clip_slot_morph_target(index=self.index, track=self.track, pattern=pattern)

    def clear_morph(self):
        self.document().clear_clip_slot_morph(index=self.index, track=self.track)

    def pick_grab_track(self):
        tracks = sorted_names(name for name in self.document().track_names() if name != self.track)
        if not tracks:
            self.tell(ERR_NO_OTHER_TRACKS_TITLE, ERR_ADD_ANOTHER_TRACK)
            return
        options = [MSG_NONE_SHOWN, *tracks]
        current = self.clip_slot().get_grab_track()

        def chosen(item):
            if item == 0:
                self.clear(ClipSlotSetting.GRAB_TRACK)
                return
            other = tracks[item - 1]
            circle = self.document().grab_circle(index=self.index, track=self.track, other=other)
            if circle:
                self.tell(ERR_CIRCULAR_GRAB_TITLE, ERR_GRAB_CIRCLE.format(track=other, circle=GRAB_ARROW.join(circle)), ERR_REMOVE_OTHER_GRAB)
                return
            self.set_value(setting=ClipSlotSetting.GRAB_TRACK, value=other)
        self.ask(dialog=ChoiceDialog(title=MSG_GRAB_TRACK_LABEL, options=options, current=options.index(current) if current in options else 0), then=chosen)

    def scale_text(self):
        """Return the clip's own scale, or the scene's it takes, which is the song's when the scene has none."""
        own = self.clip_slot().get_scale_name()
        if own is not None:
            return own
        scene = self.document().song().get_scenes()[self.index]
        return MSG_SCENE_SCALE_SHOWN.format(scale=scene.get_scale_name() or self.document().song().get_scale_name() or MSG_NO_SCALE)

    def pick_scale(self):
        """Ask for one of the song's scales for the clip alone, or the scene's."""
        scales = sorted_names(self.document().song().get_scale_names())
        options = [MSG_SCENE_OPTION, *scales]
        current = self.clip_slot().get_scale_name()

        def chosen(item):
            self.set_value(setting=ClipSlotSetting.SCALE, value=None if item == 0 else scales[item - 1])
        self.ask(dialog=ChoiceDialog(title=MSG_CLIP_SCALE_TITLE, options=options, current=options.index(current) if current in options else 0), then=chosen)


    def set_repeat(self, value):
        self.document().set_clip_slot_repeat(index=self.index, track=self.track, repeat=value)

    def set_direction(self, direction):
        self.set_value(setting=ClipSlotSetting.DIRECTION, value=direction)

    def step_direction(self, offset):
        options = [None, *DIRECTIONS]
        place = options.index(self.clip_slot().get_direction())
        self.set_direction(options[(place + offset) % len(options)])

    def pick_direction(self):
        options = [None, *DIRECTIONS]
        labels = columns([
            (MSG_PATTERN_DIRECTION_OPTION, MSG_PATTERN_DIRECTION_WHAT),
            *[(words(name), MSG_DIRECTION_NAMES[name]) for name in DIRECTIONS],
        ])
        place = options.index(self.clip_slot().get_direction())
        self.ask(dialog=ChoiceDialog(title=MSG_PLAY_DIRECTION_TITLE, options=labels, current=place), then=lambda chosen: self.set_direction(options[chosen]))

    def direction_text(self):
        direction = self.clip_slot().get_direction()
        if direction:
            return words(direction)
        pattern = self.document().song().get_pattern(self.clip_slot().get_pattern_name())
        return MSG_PATTERN_DIRECTION_SHOWN.format(direction=words(pattern.get_direction()))

    def set_loop(self, loops):
        """Make the clip loop or play its repeats, and say so when that leaves every clip of the scene looping, since such a scene never ends."""
        self.set_value(setting=ClipSlotSetting.LOOP, value=True if loops else None)
        if self.document().song().get_scenes()[self.index].every_clip_loops():
            self.tell(ERR_LOOP_SCENES_TITLE, *loop_error_lines(self.document().song()))

    def morph_style(self):
        return self.clip_slot().get_morph_style_name() or FIRST_MORPH_STYLE

    def step_style(self, offset):
        styles = list(MORPH_STYLES)
        place = styles.index(self.morph_style())
        self.set_value(setting=ClipSlotSetting.MORPH_STYLE, value=styles[(place + offset) % len(styles)])

    def fields(self):
        clip_slot = self.clip_slot()
        repeat = clip_slot.get_repeat()
        result = [
            NameField(value=self.name_text, rename=self.rename, clear=lambda: self.clear(ClipSlotSetting.NAME), clear_what=MSG_USE_PATTERN_NAME_WHAT),
            Field(label=MSG_PATTERN_LABEL, value=clip_slot.get_pattern_name, adjust=None,
                  enter=lambda: self.pick_pattern(title=MSG_PATTERN_LABEL, current=clip_slot.get_pattern_name(), then=lambda name: self.set_value(setting=ClipSlotSetting.PATTERN, value=name)), enter_what=What.CHOOSE),
            Field(label=MSG_SCALE_LABEL, value=self.scale_text, adjust=None, enter=self.pick_scale, enter_what=What.CHOOSE,
                  clear=lambda: self.clear(ClipSlotSetting.SCALE), clear_what=MSG_USE_SCENE_SCALE_WHAT),
            chains_field(page=self, names=lambda: self.clip_slot().get_chain_names(),
                         store=lambda names: self.set_value(setting=ClipSlotSetting.CHAINS, value=names or None)),
            NumberField(page=self, label=MSG_REPEAT_LABEL, number=repeat, lowest=MIN_REPEAT, highest=MAX_CLIP_REPEAT, set=self.set_repeat),
            Toggle(label=MSG_LOOP_LABEL, on=clip_slot.loops(), set=self.set_loop, shown_on=MSG_LOOP_ON_SHOWN, shown_off=MSG_LOOP_OFF_SHOWN),
            Field(label=MSG_DIRECTION_LABEL, value=self.direction_text, adjust=self.step_direction, enter=self.pick_direction, enter_what=What.CHOOSE,
                  clear=lambda: self.clear(ClipSlotSetting.DIRECTION), clear_what=MSG_USE_PATTERN_DIRECTION_WHAT),
        ]
        if repeat > DEFAULT_REPEAT:
            result.append(Field(label=MSG_MORPH_TO_LABEL, value=lambda: clip_slot.get_morph_target() or MSG_NONE_SHOWN, adjust=None,
                                enter=lambda: self.pick_pattern(title=MSG_MORPH_TO_LABEL, current=clip_slot.get_morph_target(), then=self.set_morph_target), enter_what=What.CHOOSE,
                                clear=self.clear_morph, clear_what=MSG_NO_MORPH_WHAT))
            if clip_slot.get_morph_target():
                result.append(Field(label=MSG_MORPH_DIRECTION_LABEL, value=self.morph_style, adjust=self.step_style, enter=lambda: self.step_style(1), enter_what=What.NEXT))
        result += [
            Field(label=MSG_GRAB_TRACK_LABEL, value=lambda: clip_slot.get_grab_track() or MSG_NONE_SHOWN, adjust=None, enter=self.pick_grab_track, enter_what=What.CHOOSE,
                  clear=lambda: self.clear(ClipSlotSetting.GRAB_TRACK), clear_what=MSG_NO_GRAB_WHAT),
            self.follow_action_field(),
            *self.strum_section(),
            *[field for shape in SHAPES for field in self.shape_section(shape)],
            # Real-time playback's buttons, which do what L does, drawn below the settings after a blank line as every page's buttons are.
            Button(label=MSG_PLAY_LABEL, key_name=KeyName.L, enter=self.listen, enter_what=MSG_LISTEN_WHAT),
            Button(label=MSG_STOP_LABEL, key_name=KeyName.L, enter=self.stop, enter_what=MSG_STOP_WHAT),
        ]
        return result

    def strum_section(self):
        """Return the clip's + Strum section: how it strums its chords, over its track's."""
        clip_slot = self.clip_slot()
        strum = self.document().song().get_track(self.track).get_strum()
        taken = MSG_STRUM_WORDS.get(strum.direction, strum.direction) if strum is not None else MSG_NONE_SHOWN
        return strum_section(
            page=self, value=lambda part: clip_slot.get_setting(strum_setting(part)), first=MSG_TRACK_STRUM_CHOICE,
            inherited=MSG_FROM_TRACK_SHOWN.format(value=taken),
            store=lambda part, value: self.document().set_clip_strum_setting(index=self.index, track=self.track, part=part, value=value),
        )

    def shape_section(self, shape):
        """Return a shape's section: how busy, loud or long the clip plays over it, over its scene's."""
        clip_slot = self.clip_slot()
        return shape_section(
            page=self, shape=shape, value=lambda part: clip_slot.get_setting(shape_setting(shape=shape, part=part)),
            store=lambda part, value: self.document().set_clip_shape_setting(index=self.index, track=self.track, name=shape_setting(shape=shape, part=part), value=value),
        )

    def follow_action_field(self):
        """Return the Follow action field: what the clip sends down in real-time playback when its scene is done, shown as the set's default when the clip sets none, with no (default) choice (the user, 2026-11-09)."""
        advance = self.document().setlist().follow_action_of(self.clip_slot())
        return ChoiceField(page=self, label=MSG_FOLLOW_ACTION_LABEL, choices=FOLLOW_ACTION_CHOICES, current=advance,
                           names=[MSG_FOLLOW_ACTION_NAMES[choice] for choice in FOLLOW_ACTION_CHOICES],
                           shown=MSG_FOLLOW_ACTION_NAMES[advance] if self.clip_slot().get_written_follow_action() is not None
                           else MSG_FROM_SET_SHOWN.format(value=MSG_FOLLOW_ACTION_NAMES[advance]),
                           set=lambda value: self.set_value(setting=ClipSlotSetting.FOLLOW_ACTION, value=value))

    def name_text(self):
        """Return the clip's own name, or which pattern it's named for."""
        clip_slot = self.clip_slot()
        return clip_slot.get_name() or MSG_CLIP_NAMED_FOR_PATTERN.format(pattern=clip_slot.get_pattern_name())

    def rename(self):
        """Give the clip a name of its own; a blank goes back to its pattern's name."""
        self.ask(dialog=PromptDialog(title=MSG_CLIP_NAME_PROMPT, value=self.clip_slot().get_name() or NOTHING), then=lambda text: self.set_value(setting=ClipSlotSetting.NAME, value=text.strip()))

    def notes(self, width):
        document = self.document()
        clip_slot = self.clip_slot()
        length = clock(document.lengths().clip_seconds(index=self.index, track=self.track))
        lines = [Text(MSG_CLIP_LENGTH_NOTE.format(length=length, scene=clock(document.lengths().scene_seconds(self.index))), style=Style.DIM)]
        if clip_slot.loops():
            lines.append(Text(MSG_LOOP_NOTE, style=Style.DIM))
        elif clip_slot.get_repeat() == DEFAULT_REPEAT:
            lines.append(Text(MSG_MORPH_HINT_NOTE, style=Style.DIM))
        if clip_slot.get_grab_track() is not None and not self.document().has_grab_steps(clip_slot.get_pattern_name()):
            lines.append(Text(MSG_GRAB_HINT_NOTE, style=Style.DIM))
        problem = document.lengths().scene_problem(self.index)
        if problem:
            lines.append(Text(MSG_PROBLEM_NOTE.format(problem=problem)[:width]))
        return lines
