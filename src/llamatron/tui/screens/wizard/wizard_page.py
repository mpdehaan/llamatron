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
"""The song wizard's page: a tree of the song's parts at the left, and at the right the fields of the part under the cursor.

The cursor is in the tree or in the fields. In the tree, Up and Down move, Left and Right
close and open a branch, the fields of the branch under the cursor show dim, and ENTER or Tab
moves into them. In the fields the keys are a settings page's, and ESC or Tab moves back to the
tree. ESC in the tree closes the wizard, asking first when anything was chosen. Nothing in the
set changes until the Create button, which adds the song with all it uses as one change, so
that one undo takes it away again, and shows Arrange on it.

The page knows nothing of any one branch (branch.py): it draws what the branches say.
"""

from rich.text import Text

from llamatron.composition.checks import listed
from llamatron.composition.naming import new_name
from llamatron.composition.song_file_error import SongFileError
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.realtime.sender_process import SenderNotStarted
from llamatron.strings import errors, help as help_text, labels, marks, messages, names
from llamatron.macro_composer.notation import KIT
from llamatron.macro_composer.wizard_choices import USUAL_PIECE_NOTE
from llamatron.support.version import VERSION
from llamatron.tui import keybindings, themes
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.document import Document
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.dialogs.sound_dialog import SoundDialog
from llamatron.tui.screens.set.instrument_editor import sound_families
from llamatron.tui.screens.shared.sound_trial import HITS_STEP, RUN_STEP, SoundTrial, hits_of, run_of
from llamatron.tui.text import clock
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import Box, cursor_mark, INDENT, NOTHING, SPACE, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.wizard.band_branch import BandBranch
from llamatron.tui.screens.wizard.composition_branch import CompositionBranch
from llamatron.tui.screens.wizard.create_branch import CreateBranch
from llamatron.tui.screens.wizard.form_branch import FormBranch
from llamatron.tui.screens.wizard.genre_branch import GenreBranch
from llamatron.tui.screens.wizard.starts import FROM_LAST, REPLACING

# How wide the tree is, with its cursor's mark, and the least the fields beside it are given.
TREE_WIDTH = 24
LEAST_FIELDS_WIDTH = 20
# Where the fields' cursor is while the cursor is in the tree: on no field.
NO_PLACE = -1
FIRST_PLACE = 0
# What the picker of a kit piece's sound answers for the piece's own drum, which is no drum's name.
OWN_DRUM = ''
# The line and the space between the tree and the fields.
DIVIDER = Box.BAR + SPACE

# What a field keeps its label as.
LABEL_OF_FIELD = 'label'


class WizardPage(FieldPage):
    """The song wizard: a tree of branches beside the fields of the branch under the cursor."""

    THEME = themes.WIZARD

    KEYS = keybindings.WizardPage

    HELP = help_text.HELP_WIZARD_PAGE

    crumbs = (labels.Crumb.WIZARD,)

    def __init__(self, holder, *, start=None):
        super().__init__(holder)
        self._choices = WizardChoices()
        self._choices.draw_seed()
        self._song_name = new_name(word=names.MSG_NEW_SONG_WORD, taken=self.document().song_names())
        self._changed = False
        # What the current song kept of the run that made it, the way of starting chosen in the dialog that opens the wizard on
        # such a song.
        self._last = self.document().song().get_wizard_choices()
        self._start = None
        # The Band and Form branches start open, so that the players and the sections, and the keys that add, copy,
        # remove and move a section, show themselves with no key to learn.
        self._open = {labels.MSG_WIZARD_GENRE_BRANCH, labels.MSG_WIZARD_BAND_BRANCH, labels.MSG_WIZARD_COMPOSITION_BRANCH, labels.MSG_WIZARD_FORM_BRANCH}
        self.tree_place = FIRST_PLACE
        self.in_fields = False
        # Move mode, the tracker's: whether M has picked up the branch under the tree's cursor.
        self.moving = False
        # The tune whose notes the pattern editor has open over the wizard: its kind of section, its pattern's name in the draft set and
        # the pattern as it was when opened. None when no tune is being edited.
        self._tune_open = None
        if start is not None:
            self.start_with(start)

    # What the branches read and change.

    def choices(self):
        return self._choices

    def song_name(self):
        return self._song_name

    def choosing(self, setter):
        """Return a setter that also notes that something was chosen, so that closing the wizard asks before the choices are lost."""
        def chosen(value):
            label = self.label_under_cursor()
            chords = self._choices.own_tune_chords()
            result = setter(value)
            self.stay_on(label)
            self._changed = True
            # What was heard is no longer what the choices make.
            self.app.made_preview().stop()
            self.ask_to_fit_tunes(before=chords)
            return result
        return chosen

    def ask_to_fit_tunes(self, *, before):
        """Ask whether to fit each tune written by hand whose chords a choice just changed: YES moves its long notes that clash to
        the nearest note of the new chord, and NO keeps the tune as written."""
        after = self._choices.own_tune_chords()
        kinds = [kind for kind in after if kind in before and after[kind] != before[kind]]
        if not kinds:
            return

        def fit(_):
            for kind in kinds:
                try:
                    self._choices.fit_tune(kind)
                except ValueError as problem:
                    self.refuse(str(problem))
                    return
            self.say(messages.MSG_WIZARD_TUNES_FITTED.format(kinds=listed(kinds)))
        question = messages.MSG_WIZARD_FIT_TUNE_QUESTION.format(kinds=listed(kinds))
        self.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_FIT_TUNE_TITLE, messages=[question, messages.MSG_WIZARD_FIT_TUNE_SAYS]), then=fit)

    def label_under_cursor(self):
        """Return the label of the field the cursor is on, or None in the tree or on a field with no label."""
        return getattr(self.field(), LABEL_OF_FIELD, None)

    def stay_on(self, label):
        """Keep the cursor on the field of a label: a choice may make a field appear or leave above the one chosen, which would
        otherwise put the cursor on its neighbour."""
        if label is None:
            return
        places = [place for place, field in enumerate(self.shown_fields()) if getattr(field, LABEL_OF_FIELD, None) == label]
        if places and self.place not in places:
            self.place = min(places, key=lambda place: abs(place - self.place))

    # Editing a tune's notes: the pattern editor opened over the wizard, on a draft of the set the choices make.

    def edit_tune(self, kind):
        """Open the pattern editor on a kind of section's tune. The editor works on a draft of the set the choices make, held by the
        app until the editor closes; the notes are kept as the kind's own tune then, if they were changed."""
        try:
            setlist, _ = self._choices.made_for_listening()
            name = self._choices.tune_pattern_name(kind)
        except (ValueError, SongFileError) as problem:
            self.refuse(str(problem))
            return
        if name is None:
            self.refuse(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
            return
        self.open_pattern(setlist=setlist, name=name, keep=lambda pattern: self._choices.set_tune_pattern(kind=kind, pattern=pattern),
                          kept=messages.MSG_WIZARD_TUNE_KEPT.format(kind=kind), unchanged=messages.MSG_WIZARD_TUNE_UNCHANGED.format(kind=kind))

    def edit_riff(self, riff):
        """Open the pattern editor on a riff's notes as its first player plays them, kept as the riff's own when the editor closes, if
        they were changed."""
        try:
            setlist, _ = self._choices.made_for_listening()
            name = self._choices.riff_pattern_name(riff)
        except (ValueError, SongFileError) as problem:
            self.refuse(str(problem))
            return
        if not setlist.has_pattern(name):
            self.refuse(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
            return
        self.open_pattern(setlist=setlist, name=name, keep=lambda pattern: self._choices.set_riff_pattern(riff=riff, pattern=pattern),
                          kept=messages.MSG_WIZARD_RIFF_KEPT.format(riff=riff), unchanged=messages.MSG_WIZARD_RIFF_UNCHANGED.format(riff=riff))

    def edit_song_riff(self):
        """Open the pattern editor on the notes of the song's first riff, as its first player plays them."""
        try:
            setlist, _ = self._choices.made_for_listening()
            name = self._choices.song_riff_pattern_name()
        except (ValueError, SongFileError) as problem:
            self.refuse(str(problem))
            return
        if name is None:
            self.refuse(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
            return
        riff = labels.MSG_WIZARD_GROUP_RIFF
        self.open_pattern(setlist=setlist, name=name, keep=self._choices.set_song_riff_pattern, kept=messages.MSG_WIZARD_RIFF_KEPT.format(riff=riff),
                          unchanged=messages.MSG_WIZARD_RIFF_UNCHANGED.format(riff=riff))

    def open_pattern(self, *, setlist, name, keep, kept, unchanged):
        """Open the pattern editor on a pattern of a draft of the set the choices make. When the editor closes, keep() is given the
        pattern's data if it changed, and the status line says kept or unchanged."""
        self.app.made_preview().stop()
        draft = Document(setlist=setlist)
        self._tune_open = (name, draft.setlist().get_pattern(name).to_data(), keep, kept, unchanged)
        self.app.open_draft(draft)
        self.show_page(PatternEditor(holder=self.holder, name=name, opened_from=self))

    def on_screen_resume(self):
        """Take a tune's or a riff's notes back from the pattern editor, which has closed, before the page is drawn again."""
        # A dialog closing over the page resumes it too, so the notes are taken back only once the page itself is on top.
        if self._tune_open is not None and self.app.is_drafting() and self.app.screen is self:
            self.keep_tune_edited(self.app.close_draft())
        super().on_screen_resume()

    def keep_tune_edited(self, draft):
        """Keep the notes of the pattern that was open as the person's own, where the editor changed them, and say which happened. A
        pattern that was renamed or deleted in the editor is not found, and nothing is kept."""
        name, before, keep, kept, unchanged = self._tune_open
        self._tune_open = None
        setlist = draft.setlist()
        after = setlist.get_pattern(name).to_data() if setlist.has_pattern(name) else before
        if after == before:
            self.say(unchanged)
            return
        try:
            self.choosing(keep)(after)
        except ValueError as problem:
            self.refuse(str(problem))
            return
        self.say(kept)

    # Listening: a part of the song as it would be made, heard through FluidSynth and thrown away.

    def listen_keys(self):
        """Return the key that listens to what the branch under the cursor has to hear, or stops it while it plays, and none for a branch with nothing to hear."""
        heard = self.branch().listens()
        if heard is None:
            return []
        if self.app.made_preview().playing() == heard[0]:
            return [self.bind(self.KEYS.STOP_LISTENING, action=self.stop_listening)]
        return [self.bind(self.KEYS.LISTEN, action=self.listen)]

    def listen(self):
        what, index, track = self.branch().listens()
        problem = self.problem_listening(what=what, index=index, track=track)
        if problem is not None:
            self.refuse(problem)
            return
        self.say(messages.MSG_WIZARD_LISTENING.format(what=what))

    def problem_listening(self, *, what, index, track):
        """Play a section of the song as it would be made, or one track of the section, and return why it could not be heard, or None. A dialog over the page listens through this too."""
        preview = self.app.made_preview()
        if not preview.can_sound():
            return errors.ERR_WIZARD_CANNOT_LISTEN
        try:
            setlist, name = self._choices.made_for_listening()
            if index >= len(setlist.get_song(name).get_scenes()):
                raise ValueError(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
            if track is None:
                preview.play_section(setlist=setlist, name=name, index=index, what=what)
            else:
                preview.play_line(setlist=setlist, name=name, index=index, track=track, what=what)
        except (ValueError, SongFileError, SenderNotStarted) as problem:
            return str(problem) if isinstance(problem, SenderNotStarted) else errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO
        return None

    def stop_listening(self):
        self.app.made_preview().stop()
        self.say(messages.MSG_STOPPED)

    def ask_song_name(self):
        self.ask_name(title=messages.MSG_WIZARD_SONG_NAME_PROMPT, value=self._song_name, taken=self.document().song_names(), then=self.choosing(self.name_song))

    def name_song(self, name):
        self._song_name = name

    # How the run starts, which a dialog asks before the wizard opens on a song the wizard made (LlamatronApp.show_wizard).

    def start(self):
        """Return the way of starting chosen, or None on a song the wizard did not make, where a new song is started from scratch."""
        return self._start

    def start_with(self, start):
        """Start the run one of the four ways: from the choices the current song kept or from none, a new song or the current song replaced.
        Nothing is chosen yet, so the wizard still closes without asking."""
        self._start = start
        self._choices = WizardChoices.from_data(self._last) if start in FROM_LAST else WizardChoices()
        # Every run of the wizard rolls the dice afresh, and at its start, so that what a panel shows of the song, as its hook, is
        # what Apply makes: a run from the last settings keeps the settings and never the seed.
        self._choices.draw_seed()
        document = self.document()
        self._song_name = document.current_song_name() if self.replaces() else new_name(word=names.MSG_NEW_SONG_WORD, taken=document.song_names())

    def replaces(self):
        """Return whether Create replaces the current song, where otherwise a song is added."""
        return self._start in REPLACING

    def refusal_of(self, branch):
        """Return why the cursor cannot move into a branch's fields yet, or None when it can."""
        return branch.refusal()

    def has_choices_to_lose(self):
        return self._changed

    # The tree.

    def roots(self):
        """Return the tree's top branches, in the order a song is thought through."""
        return [GenreBranch(page=self), BandBranch(page=self), CompositionBranch(page=self), FormBranch(page=self), CreateBranch(page=self)]

    def rows(self):
        """Return the branches the tree shows, each with how deep it is: every top branch, and the branches under each open one."""
        rows = []
        for root in self.roots():
            rows.append((0, root))
            if root.key() in self._open:
                rows += [(1, child) for child in root.children()]
        return rows

    def row(self):
        """Return the depth and the branch under the tree's cursor, the cursor held within the tree, which a choice can shorten."""
        rows = self.rows()
        self.tree_place = max(min(self.tree_place, len(rows) - 1), FIRST_PLACE)
        return rows[self.tree_place]

    def branch(self):
        return self.row()[1]

    def shows_children(self, branch):
        """Return whether a branch of the tree is open, showing the branches under it."""
        return branch.key() in self._open

    def move_in_tree(self, name):
        self.tree_place = cursor_moved(place=self.tree_place, name=name, count=len(self.rows()))

    def fold(self, name):
        """Open the branch under the cursor with Right and close it with Left; Left on a branch inside another goes to the branch that holds it."""
        depth, branch = self.row()
        if name == Key.RIGHT:
            if branch.children():
                self._open.add(branch.key())
            return
        if depth:
            while self.rows()[self.tree_place][0]:
                self.tree_place -= 1
            return
        self._open.discard(branch.key())

    def into_fields(self):
        """Move the cursor into the fields of the branch under it, onto the first field that does something, or say why not yet."""
        branch = self.branch()
        if self.refusal_of(branch):
            self.refuse(self.refusal_of(branch))
            return
        self.in_fields = True
        fields = self.shown_fields()
        self.place = next((place for place, field in enumerate(fields) if field.enter or field.adjust), FIRST_PLACE)

    def to_tree(self):
        self.in_fields = False

    # The fields, a settings page's, of the branch under the tree's cursor.

    def fields(self):
        return self.branch().fields()

    def notes(self, width):
        return self.branch().notes(width)

    def field(self):
        """Return the field under the cursor, or None while the cursor is in the tree."""
        return super().field() if self.in_fields else None

    def keys(self):
        if self.in_fields:
            # A settings page's keys, but for ESC, which goes back to the tree here and not from the page.
            take = self.branch().takes()
            takes = [self.bind(self.KEYS.NEW_TAKE, action=take)] if take is not None else []
            return [self.bind(self.KEYS.TO_TREE, action=self.to_tree), *super().keys()[1:], *takes, *self.listen_keys()]
        if self.moving:
            # While a branch is carried, only the keys that carry and drop it work, as in every move mode.
            return [self.bind(self.KEYS.DROP, action=self.drop), self.bind(self.KEYS.CARRY, action=self.carry)]
        depth, branch = self.row()
        result = [self.bind(self.KEYS.CLOSE, action=self.go_back), self.bind(self.KEYS.TREE, action=self.move_in_tree, wants_key=True)]
        if depth or branch.children():
            result.append(self.bind(self.KEYS.FOLD, action=self.fold, wants_key=True))
        if self.refusal_of(branch) or branch.can_be_edited():
            result.append(self.bind(self.KEYS.INTO_FIELDS, action=self.into_fields))
        if branch.is_listed():
            result.append(self.bind(self.KEYS.INSERT, action=self.insert_in_list))
        if branch.adds():
            result.append(self.bind(self.KEYS.ADD, action=self.add_to_list))
        if branch.is_listed():
            result += [self.bind(self.KEYS.COPY, action=self.copy_listed), self.bind(self.KEYS.DELETE, action=self.remove_listed), self.bind(self.KEYS.MOVE, action=self.start_moving)]
        return result + self.listen_keys()

    # A branch that is one of a list: added to, copied, removed and moved with the keys every list of the tracker has.

    def add_to_list(self):
        """Ask which kind of thing to add and add one at the end of the list, as A does on every list: the cursor stays, and the
        branch that holds the list opens to show it."""
        branch = self.branch()
        kinds = branch.kinds_to_add()

        def chosen(place):
            self.choosing(branch.add)(kinds[place])
            if not branch.is_listed():
                self._open.add(branch.key())
        self.ask(dialog=ChoiceDialog(title=labels.MSG_WIZARD_ADD_SECTION_TITLE, options=kinds), then=chosen)

    def insert_in_list(self):
        """Ask which kind of thing to insert and put one before the branch under the cursor, the cursor staying on the new one, as on Arrange."""
        branch = self.branch()
        kinds = branch.kinds_to_add()
        self.ask(dialog=ChoiceDialog(title=labels.MSG_WIZARD_INSERT_SECTION_TITLE, options=kinds), then=lambda place: self.choosing(branch.insert)(kinds[place]))

    def pick_sound(self, role):
        """Choose a player's sound from a list: the band's first, which takes the sound from the band again, then the genre's
        own sounds that suit the player, then a row that opens every General MIDI sound that plays notes."""
        choices = self._choices
        own = choices.genre_sounds(role)
        options = [marks.MSG_WIZARD_FROM_BAND.format(sound=choices.sound_name(choices.band_sound(role))), *(choices.sound_name(sound) for sound in own), labels.MSG_WIZARD_MORE_SOUNDS]
        current = own.index(choices.get_sound(role)) + 1 if choices.has_own_sound(role) and choices.get_sound(role) in own else (len(options) - 1 if choices.has_own_sound(role) else FIRST_PLACE)

        def chosen(place):
            if place == len(options) - 1:
                self.pick_any_sound(role)
            else:
                self.choosing(lambda sound: choices.set_sound(role=role, sound=sound))(None if place == FIRST_PLACE else own[place - 1])
        self.ask(dialog=ChoiceDialog(title=labels.MSG_WIZARD_SOUND_TITLE.format(player=choices.role_title(role)), options=options, current=current), then=chosen)

    def pick_any_sound(self, role):
        """Choose a player's sound from every General MIDI sound, by family; a sound is tried as a run of the song's scale in the player's octave."""
        choices = self._choices
        run = run_of(root=choices.root_half_steps(), steps=choices.scale_half_steps(), octave=choices.role_octave(role))
        dialog = SoundDialog(title=labels.MSG_WIZARD_MORE_SOUNDS_TITLE, groups=sound_families(), current=choices.get_sound(role), trial=SoundTrial(page=self, played=lambda sound: (run, RUN_STEP, sound)))

        def chosen(sound):
            if sound is not None:
                self.choosing(lambda picked: choices.set_sound(role=role, sound=picked))(sound)
        self.ask(dialog=dialog, then=chosen)

    def pick_piece_sound(self, piece):
        """Choose what a piece of the kit sounds as: its own drum first, then the kit's drums, then every General MIDI sound by family, and
        on the Note row under them the note a General MIDI sound plays. A drum is tried as four hits of the kit, and a General MIDI sound
        as four notes, on the note the row shows."""
        choices = self._choices
        drums = [(marks.MSG_WIZARD_KIT_DRUM_SHOWN.format(drum=drum), drum) for drum in choices.kit_drums() if drum != piece]

        def played(sound):
            if isinstance(sound, str):
                return hits_of(KIT[piece if sound == OWN_DRUM else sound]), HITS_STEP, None
            return hits_of(dialog.note), HITS_STEP, sound

        def chosen(answer):
            sound, note = answer
            if isinstance(sound, str):
                choices.set_piece_sound(piece=piece, sound=None if sound == OWN_DRUM else sound)
            else:
                choices.set_piece_sound(piece=piece, sound=sound)
                choices.set_piece_note(piece=piece, note=note)
        dialog = SoundDialog(title=labels.MSG_WIZARD_PIECE_SOUND_TITLE.format(piece=piece), top=[(marks.MSG_WIZARD_OWN_DRUM_SHOWN.format(piece=piece), OWN_DRUM)],
                             groups=[(labels.MSG_WIZARD_KIT_DRUMS, drums), *sound_families()], current=choices.piece_sound(piece) or OWN_DRUM, trial=SoundTrial(page=self, played=played),
                             note=choices.piece_note(piece) or USUAL_PIECE_NOTE)
        self.ask(dialog=dialog, then=self.choosing(chosen))

    def pick_suggested_form(self):
        """Offer the forms the subgenre suggests in a dialog, each with its sections and its length at the tempo chosen, and
        take the one picked; where a person changed the sections, ask first, since the form picked replaces them."""
        choices = self._choices
        forms = choices.forms()
        options = [marks.MSG_WIZARD_SUGGESTED_FORM.format(form=form, count=choices.form_section_count(form), length=clock(choices.form_seconds(form=form))) for form in forms]

        def pick():
            self.ask(dialog=ChoiceDialog(title=labels.MSG_WIZARD_SUGGESTED_FORM_TITLE, options=options, current=forms.index(choices.get_form())),
                     then=lambda place: self.choosing(choices.set_form)(forms[place]))

        def answered(yes):
            if yes:
                pick()
        if choices.has_own_form():
            self.ask(dialog=ConfirmDialog(title=labels.MSG_WIZARD_REPLACE_SECTIONS_TITLE, messages=[messages.MSG_WIZARD_REPLACE_SECTIONS_QUESTION]), then=answered)
        else:
            pick()

    def ask_form_questions(self):
        """Ask the questions a form is made from, one dialog a question, each opening on its usual answer, and make the form the answers ask for
        the song's own; ESC at any question leaves the form as it was, and where a person changed the sections, the last step asks first."""
        choices = self._choices
        questions = choices.form_questions()
        answers = {}

        def make():
            try:
                self.choosing(choices.set_form_from_answers)(answers)
            except ValueError as problem:
                self.refuse(str(problem))
                return
            self._open.add(labels.MSG_WIZARD_FORM_BRANCH)

        def finish():
            if choices.has_own_form():
                self.ask(dialog=ConfirmDialog(title=labels.MSG_WIZARD_REPLACE_SECTIONS_TITLE, messages=[messages.MSG_WIZARD_REPLACE_SECTIONS_QUESTION]), then=lambda yes: make() if yes else None)
            else:
                make()

        def ask(place):
            if place == len(questions):
                finish()
                return
            name, offered, usual = questions[place]

            def answered(chosen):
                answers[name] = offered[chosen]
                ask(place + 1)
            self.ask(dialog=ChoiceDialog(title=labels.MSG_WIZARD_FORM_QUESTION_TITLES[name], options=list(offered), current=offered.index(usual)), then=answered)
        ask(FIRST_PLACE)

    def copy_listed(self):
        self.choosing(lambda branch: branch.copy())(self.branch())
        self.tree_place += 1

    def remove_listed(self):
        """Remove the branch under the cursor from its list, with no question, since nothing is in the set yet; the last of a list stays."""
        try:
            self.choosing(lambda branch: branch.remove())(self.branch())
        except ValueError as problem:
            self.refuse(str(problem))
            return
        if not self.branch().is_listed():
            # The last of the list went, so the cursor goes to the one that is last now.
            self.tree_place -= 1

    def start_moving(self):
        self.moving = True
        self.say(messages.MSG_WIZARD_MOVING.format(name=self.branch().name()))

    def carry(self, offset):
        """Carry the branch picked up one place earlier or later in its list, the cursor going with it."""
        if self.choosing(self.branch().move)(offset):
            self.tree_place += offset
        self.say(messages.MSG_WIZARD_MOVING.format(name=self.branch().name()))

    def drop(self):
        self.moving = False

    # Closing, and undo, which has nothing to act on here.

    def go_back(self):
        """Close the wizard, which is easy to do by accident, so it always asks first, with No selected, and says what is lost when
        anything was chosen."""
        self.app.made_preview().stop()

        def answered(yes):
            if yes:
                FieldPage.go_back(self)
        question = messages.MSG_WIZARD_CLOSE_QUESTION if self.has_choices_to_lose() else messages.MSG_WIZARD_CLOSE_UNCHANGED_QUESTION
        self.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_CLOSE_TITLE, messages=[question], starts_on_no=True), then=answered)

    def steps_history(self):
        return False

    def why_no_history(self):
        return messages.MSG_WIZARD_NOTHING_TO_UNDO

    # Create.

    def create(self):
        """Make the song from the choices and the seed the run drew when it started, add it to the set with all it uses as one
        change, and show Arrange on it."""
        try:
            made = self._choices.made_setlist(name=self._song_name, version=VERSION)
        except (ValueError, SongFileError) as problem:
            # A form of the song's own can ask for what the genre's parts cannot fill, which is said and nothing made.
            self.to_tree()
            self.refuse(str(problem))
            return
        self.app.made_preview().stop()
        document = self.document()
        replaces = self.replaces()
        if replaces:
            name = document.replace_with_made_song(made)
        elif document.current_song_is_untouched():
            # A song nothing was done to, as a new set's, is filled in place of a song added beside it.
            name = document.replace_with_made_song(made, new=self._song_name)
        else:
            name = document.add_made_song(made)
        self.holder.show_arrange_on_new_song()
        self.say((messages.MSG_WIZARD_REPLACED if replaces else messages.MSG_WIZARD_CREATED).format(name=name))

    # Drawing.

    def caption(self):
        return (labels.MSG_WIZARD_REPLACE_CAPTION if self.replaces() else labels.MSG_WIZARD_CAPTION).format(name=self._song_name)

    def tree_lines(self):
        """Return the tree's lines: each branch after its cursor's mark, indented by its depth, with its open or closed mark, its note dim,
        and at the line's end the mark of the branch whose fields hold the cursor."""
        lines = []
        for place, (depth, branch) in enumerate(self.rows()):
            under_cursor = place == self.tree_place
            line = Text(no_wrap=True)
            line.append(cursor_mark(under_cursor and not self.in_fields))
            line.append(INDENT * depth)
            if branch.children():
                line.append((marks.MSG_WIZARD_BRANCH_OPEN if self.shows_children(branch) else marks.MSG_WIZARD_BRANCH_CLOSED) + SPACE)
            else:
                line.append(INDENT)
            carried = self.moving and under_cursor
            line.append(marks.MSG_WIZARD_CARRIED.format(name=branch.name()) if carried else branch.name(), style=Style.DIM if self.refusal_of(branch) else (Style.BOLD if under_cursor else Style.PLAIN))
            if branch.note():
                line.append(SPACE + branch.note(), style=Style.DIM)
            line.truncate(TREE_WIDTH - 2)
            line.pad_right(TREE_WIDTH - 2 - len(line.plain))
            line.append((marks.MSG_WIZARD_EDITED_BRANCH if under_cursor and self.in_fields else SPACE) + SPACE)
            lines.append(line)
        return lines

    def field_lines(self, *, width, height):
        """Return the right side's lines: the branch's title, then its fields as a settings page draws them, all dim while the cursor is in the tree."""
        place = self.place
        if not self.in_fields:
            self.place = NO_PLACE
        lines = [Text(SPACE + self.branch().title(), style=Style.BOLD), *FieldPage.body(self, width=width, height=max(height - 1, 1))]
        self.place = place
        if not self.in_fields:
            for line in lines:
                line.stylize(Style.DIM)
        return lines

    def body(self, *, width, height):
        tree = self.window_of_tree(lines=self.tree_lines(), height=height)
        fields = self.field_lines(width=max(width - TREE_WIDTH - len(DIVIDER), LEAST_FIELDS_WIDTH), height=height)
        lines = []
        for place in range(max(len(tree), len(fields), height)):
            line = Text(no_wrap=True)
            line.append_text(tree[place] if place < len(tree) else Text(SPACE * TREE_WIDTH))
            line.append(DIVIDER, style=Style.DIM)
            line.append_text(fields[place] if place < len(fields) else Text(NOTHING))
            lines.append(line)
        return lines

    def window_of_tree(self, *, lines, height):
        """Return the tree's lines that fit the height, scrolled so that the branch under the cursor shows, a long form having more sections than a console has lines."""
        if len(lines) <= height:
            return lines
        first = max(min(self.tree_place - height // 2, len(lines) - height), FIRST_PLACE)
        return lines[first:first + height]
