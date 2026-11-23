# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Scene page: one scene's settings, and how long it lasts."""

from rich.text import Text

from llamatron.interface.forms.text import clock, scene_name
from llamatron.interface.pages.scene import ScenePresenter
from llamatron.interface.tracker import drawing, keybindings, themes
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels, messages


class ScenePage(FieldPage):
    """A scene's settings, and how long it lasts: the Scene presenter's form (interface/pages/scene.py), with the scene's place
    among the scenes, its crumbs and the notes under its settings drawn in the tracker's dim."""

    THEME = themes.FROM_ARRANGE

    KEYS = keybindings.ScenePage

    HELP = help_text.HELP_SCENE_PAGE

    def __init__(self, *, holder, index):
        super().__init__(holder)
        self.index = index
        # Scenes go by their place, so the name tells an undo that took this scene away from one that only moved it.
        self.shown_name = self.scene().get_name()

    def still_exists(self):
        song = self.document().song()
        return self.index < len(song.get_scenes()) and self.scene().get_name() == self.shown_name

    def follow_renames(self, renames):
        # Scenes are renamed by their place, and a name can be taken away as well as changed.
        renamed_scenes = renames.get(Section.SCENES, {})
        if self.index in renamed_scenes:
            self.shown_name = renamed_scenes[self.index]

    def crumb_trail(self):
        name = scene_name(scene=self.scene(), index=self.index)
        return (labels.Crumb.ARRANGE, labels.MSG_SCENE_CRUMB.format(name=name))

    def caption(self):
        name = scene_name(scene=self.scene(), index=self.index)
        return labels.MSG_EDITING_CAPTION.format(what=labels.MSG_SCENE_CAPTION_WORD.upper(), name=name)

    def duration(self):
        lengths = self.document().lengths()
        return lengths.scene_seconds(self.index)

    def presenter(self):
        """Return what the page shows and does, for its scene as it is now."""
        return ScenePresenter(page=self, document=self.document(), index=self.index)

    def scene(self):
        return self.presenter().scene()

    def fields(self):
        return self.presenter().form()

    def rename(self):
        scene = self.scene()
        self.ask_text(title=messages.MSG_SCENE_NAME_PROMPT, value=scene.get_name() or drawing.NOTHING, then=self._renamed, is_name=True)

    def remarks(self, width):
        lengths = self.document().lengths()
        length = clock(lengths.scene_seconds(self.index))
        lines = [Text(messages.MSG_SCENE_LENGTH_NOTE.format(length=length), style=Style.DIM)]
        problem = lengths.scene_problem(self.index)
        if problem:
            lines.append(Text(messages.MSG_PROBLEM_NOTE.format(problem=problem)[:width]))
        return lines

    def _renamed(self, text):
        """Give the scene the name typed, unless it is blank, and follow it in the crumbs."""
        text = text.strip()
        if not text:
            return
        self.document().change_set(self.scene().set_name, text)
        self.shown_name = text
        self.crumbs = (labels.Crumb.ARRANGE, labels.MSG_SCENE_CRUMB.format(name=text))
