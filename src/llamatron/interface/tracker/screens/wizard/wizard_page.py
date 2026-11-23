# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The song wizard's page: a tree of the song's parts at the left, and at the right the fields of the part under the cursor.

The cursor is in the tree or in the fields. In the tree, Up and Down move, Left and Right
close and open a branch, the fields of the branch under the cursor show dim, and ENTER or Tab
moves into them. In the fields the keys are a settings page's, and ESC or Tab moves back to the
tree. ESC in the tree closes the wizard, asking first when anything was chosen. Nothing in the
set changes until the Create button, which adds the song with all it uses as one change, so
that one undo takes it away again, and shows Arrange on it.

The page knows nothing of any one branch (branch.py): it draws what the branches say.
"""

import functools
from rich.text import Text

from llamatron.caching.cached import cached_while, forget_cached
from llamatron.engine.generators import musician as musician_plugin, phrasing as phrasing_plugin
from llamatron.interface.forms import moves
from llamatron.interface.forms.cursor import place_of
from llamatron.interface.forms.text import clock
from llamatron.interface.pages.wizard import starts
from llamatron.interface.pages.wizard.band_branch import BandBranch
from llamatron.interface.pages.wizard.composition_branch import CompositionBranch
from llamatron.interface.pages.wizard.create_branch import CreateBranch
from llamatron.interface.pages.wizard.form_branch import FormBranch
from llamatron.interface.pages.wizard.genre_branch import GenreBranch
from llamatron.interface.pages.wizard.subgenre_branch import SubgenreBranch
from llamatron.interface.tracker import drawing, keybindings, themes
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.dialogs.new_riff_dialog import NewRiffDialog
from llamatron.interface.tracker.dialogs.row_dialog import RowDialog
from llamatron.interface.tracker.dialogs.sound_dialog import SoundDialog
from llamatron.interface.tracker.document import Document
from llamatron.interface.tracker.drawing import Box, cursor_mark, Style
from llamatron.interface.tracker.key_table import first_key
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.pattern.pattern_editor import PatternEditor
from llamatron.interface.tracker.screens.set.instrument_editor import sound_families
from llamatron.interface.tracker.screens.shared import sound_trial
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.plugin_editor import PluginEditor
from llamatron.interface.tracker.screens.shared.sound_trial import hits_of, run_of, SoundTrial
from llamatron.model.file import version
from llamatron.model.file.checks import listed
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects.naming import new_name
from llamatron.music_theory.composing import notation
from llamatron.user_strings import errors, help as help_text, labels, marks, messages, names, song_wizard as wizard_text
from llamatron.wizards.create_song import wizard_limits
from llamatron.wizards.create_song.wizard_choices import WizardChoices

# How wide the tree is, with its cursor's mark, and the least the fields beside it are given.
TREE_WIDTH = 24
LEAST_FIELDS_WIDTH = 20
# Where the fields' cursor is while the cursor is in the tree: on no field.
NO_PLACE = -1
FIRST_PLACE = 0
# What the picker of a kit piece's sound answers for the piece's own drum, which is no drum's name.
OWN_DRUM = ''
# The line and the space between the tree and the fields.
DIVIDER = Box.BAR + drawing.SPACE
# The style of the tree's selected branch: bold, in the wizard's theme colour.
BOLD_IN_COLOUR = '{bold} {colour}'

# What a field keeps its label as.
LABEL_OF_FIELD = 'label'
CHOICES_OF_FIELD = 'choices'
# What the page keeps the tree's rows and a branch's fields under.

# The branches that start open: the Band and Form branches among them, so that the players and the sections, and the keys that
# add, copy, remove and move a section, show themselves with no key to learn.
OPEN_AT_START = (
    labels.MSG_WIZARD_GENRE_BRANCH,
    labels.MSG_WIZARD_BAND_BRANCH,
    labels.MSG_WIZARD_COMPOSITION_BRANCH,
    labels.MSG_WIZARD_MELODIES_BRANCH,
    labels.MSG_WIZARD_FORM_BRANCH,
)


def said_of(answer):
    """Return what a kept answer says, to hold against the same answer worked out again: each row's depth and branch by name,
    or each field's kind, label and choices."""
    said = []
    for item in answer:
        if isinstance(item, tuple):
            depth, branch = item
            said.append((depth, branch.key()))
        else:
            said.append((type(item).__name__, getattr(item, LABEL_OF_FIELD, None), getattr(item, CHOICES_OF_FIELD, None)))
    return said


def _pattern_data(draft, *, name):
    """Return the data of a pattern of a draft of the set, or None where the draft has no pattern of the name."""
    setlist = draft.get_setlist()
    if not setlist.has_pattern(name):
        return None
    pattern = setlist.get_pattern(name)
    return pattern.to_data()


def _generator_data(draft, *, kind, name):
    """Return the settings of a generator of a draft of the set, or None where the draft has no generator of the kind and name."""
    setlist = draft.get_setlist()
    if not setlist.has_generator(kind=kind, name=name):
        return None
    settings = setlist.get_generator_settings(kind=kind, name=name)
    return settings.to_data()


def _run_played(sound, *, run):
    """Return how a sound is tried: a run of the song's scale in the player's octave."""
    return run, sound_trial.RUN_STEP, sound


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
        song = self.document().song()
        self._last = song.get_wizard_choices()
        self._start = None
        self._open = set(OPEN_AT_START)
        self.tree_place = FIRST_PLACE
        self.in_fields = False
        # The part of the intro the Intro panel's buttons act on: the part the cursor was last on or in, by its number.
        self.marked_part = None
        # Move mode, the tracker's: whether M has picked up the branch under the tree's cursor.
        self.moving = False
        # The tune whose notes the pattern editor has open over the wizard: its kind of section, its pattern's name in the draft set and
        # the pattern as it was when opened. None when no tune is being edited.
        self._tune_open = None
        # The tree's rows and each branch's fields as last worked out, by what they were worked out from (caching/cached.py).
        self._cached = {}
        # The cell whose change holds what the panel offers (cursor_place), or None while nothing is held.
        self._held_at = None
        if start is not None:
            self.start_with(start)

    # What the branches read and change.

    def get_choices(self):
        return self._choices

    def get_song_name(self):
        return self._song_name

    def choosing(self, setter):
        """Return a setter that also notes that something was chosen, so that closing the wizard asks before the choices are lost."""
        def chosen(value):
            label = self.label_under_cursor()
            chords = self._choices.get_tunes().own_tune_chords()
            # What the panel offers is held while this cell is changed, and found again once the cursor leaves the cell.
            self._choices.hold_offers()
            result = setter(value)
            self.stay_on(label)
            self._held_at = self.cursor_place()
            self._changed = True
            # What was heard is no longer what the choices make.
            self.app.made_preview().stop()
            self.ask_to_fit_tunes(before=chords)
            return result
        return chosen

    def refusing(self, setter):
        """Return a setter made as choosing() makes one, which says why on the status line where the song cannot take the value."""
        chosen = self.choosing(setter)

        def set_value(value):
            try:
                chosen(value)
            except ValueError as problem:
                self.refuse(str(problem))
        return set_value

    def ask_to_fit_tunes(self, *, before):
        """Ask whether to fit each tune written by hand whose chords a choice just changed: YES moves its long notes that clash to
        the nearest note of the new chord, and NO keeps the tune as written."""
        after = self._choices.get_tunes().own_tune_chords()
        kinds = [kind for kind in after if kind in before and after[kind] != before[kind]]
        if not kinds:
            return

        def fit(_):
            for kind in kinds:
                try:
                    self._choices.get_tunes().fit_tune(kind)
                except ValueError as problem:
                    self.refuse(str(problem))
                    return
            self.say(messages.MSG_WIZARD_TUNES_FITTED.format(kinds=listed(kinds)))
        question = messages.MSG_WIZARD_FIT_TUNE_QUESTION.format(kinds=listed(kinds))
        self.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_FIT_TUNE_TITLE, messages=[question, messages.MSG_WIZARD_FIT_TUNE_SAYS]), then=fit)

    def panel_under_cursor(self):
        """Return the name of the wizard panel the tree's cursor is on."""
        return self.branch().name()

    def key_toward_panel(self, name):
        """Return the key that brings the tree's cursor nearer the wizard panel of a name, the first of that name the tree shows,
        or None when the cursor is on it and in the tree."""
        if self.in_fields:
            return first_key(self.KEYS.TO_TREE)
        names = [branch.name() for _, branch in self.rows()]
        there = place_of(screen=self, names=names, target=name)
        return moves.toward(here=self.tree_place, there=there)

    def label_under_cursor(self):
        """Return the label of the field the cursor is on, or None in the tree or on a field with no label."""
        return getattr(self.field(), LABEL_OF_FIELD, None)

    def go_to_field(self, label):
        """Put the cursor on the field of a label, where one shows."""
        places = [place for place, field in enumerate(self.shown_fields()) if getattr(field, LABEL_OF_FIELD, None) == label]
        if places:
            self.cursor.set_place(places[0])

    def stay_on(self, label):
        """Keep the cursor on the field of a label: a choice may make a field appear or leave above the one chosen, which would
        otherwise put the cursor on its neighbour."""
        if label is None:
            return
        places = [place for place, field in enumerate(self.shown_fields()) if getattr(field, LABEL_OF_FIELD, None) == label]
        if places and self.cursor.get_place() not in places:
            self.cursor.set_place(min(places, key=lambda place: abs(place - self.cursor.get_place())))

    # Editing a tune's notes: the pattern editor opened over the wizard, on a draft of the set the choices make.

    def edit_tune(self, kind):
        """Open the pattern editor on a kind of section's tune. The editor works on a draft of the set the choices make, held by the
        app until the editor closes; the notes are kept as the kind's own tune then, if they were changed."""
        try:
            setlist, _ = self._choices.made_for_listening()
            name = self._choices.get_tunes().tune_pattern_name(kind)
        except (ValueError, SongFileError) as problem:
            self.refuse(str(problem))
            return
        if name is None:
            self.refuse(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
            return
        self.open_pattern(setlist=setlist, name=name, keep=lambda pattern: self._choices.get_tunes().set_tune_pattern(kind=kind, pattern=pattern),
                          kept=messages.MSG_WIZARD_TUNE_KEPT.format(kind=kind), unchanged=messages.MSG_WIZARD_TUNE_UNCHANGED.format(kind=kind))

    def edit_intro(self, *, place=None):
        """Open the pattern editor on the melody of a part of the intro, the notes of the player who says the hook there; the
        notes are saved as that part's own when the editor closes, if they were changed."""
        try:
            setlist, _ = self._choices.made_for_listening()
            name = self._choices.intro_pattern_name(place=place)
        except (ValueError, SongFileError) as problem:
            self.refuse(str(problem))
            return
        if name is None:
            self.refuse(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
            return
        keep = functools.partial(self._keep_intro, place=place)
        kept = messages.MSG_WIZARD_TUNE_KEPT.format(kind=wizard_limits.INTRO)
        unchanged = messages.MSG_WIZARD_TUNE_UNCHANGED.format(kind=wizard_limits.INTRO)
        self.open_pattern(setlist=setlist, name=name, keep=keep, kept=kept, unchanged=unchanged)

    def _keep_intro(self, pattern, *, place):
        """Save a pattern as the own melody of a part of the intro."""
        self._choices.set_intro_pattern(place=place, pattern=pattern)

    def edit_solo(self, place):
        """Open the pattern editor on the solo at a place of the form, its player's notes; the notes are saved as that solo's own
        when the editor closes, if they were changed."""
        solos = self._choices.get_solos()
        try:
            setlist, _ = self._choices.made_for_listening()
            name = solos.solo_pattern_name(place)
        except (ValueError, SongFileError) as problem:
            self.refuse(str(problem))
            return
        if name is None:
            self.refuse(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
            return
        keep = functools.partial(self._keep_solo, place=place)
        kept = messages.MSG_WIZARD_TUNE_KEPT.format(kind=wizard_limits.SOLO)
        unchanged = messages.MSG_WIZARD_TUNE_UNCHANGED.format(kind=wizard_limits.SOLO)
        self.open_pattern(setlist=setlist, name=name, keep=keep, kept=kept, unchanged=unchanged)

    def _keep_solo(self, pattern, *, place):
        """Save a pattern as the own notes of the solo at a place of the form."""
        solos = self._choices.get_solos()
        solos.set_solo_pattern(place=place, pattern=pattern)

    def edit_riff(self, riff):
        """Open the pattern editor on a riff's notes as the player the riff was written for plays them, in a song where that player
        plays the riff, whoever plays it in the song itself; the notes are kept as the riff's own when the editor closes, if they
        were changed."""
        try:
            setlist, _, _, _, name = self._choices.get_riffs().riff_heard(riff)
        except (ValueError, SongFileError) as problem:
            self.refuse(str(problem))
            return
        self.open_pattern(setlist=setlist, name=name, keep=lambda pattern: self._choices.get_riffs().set_riff_pattern(riff=riff, pattern=pattern),
                          kept=messages.MSG_WIZARD_RIFF_KEPT.format(riff=riff), unchanged=messages.MSG_WIZARD_RIFF_UNCHANGED.format(riff=riff))

    def open_pattern(self, *, setlist, name, keep, kept, unchanged):
        """Open the pattern editor on a pattern of a draft of the set the choices make. When the editor closes, keep() is given
        the pattern's data if it changed, and the status line says saved or unchanged."""
        read = functools.partial(_pattern_data, name=name)
        screen = functools.partial(PatternEditor, holder=self.holder, name=name, opened_from=self)
        self.open_in_draft(setlist=setlist, read=read, screen=screen, keep=keep, kept=kept, unchanged=unchanged)

    def open_in_draft(self, *, setlist, read, screen, keep, kept, unchanged):
        """Open a page on a draft of the set the choices make. read(draft) gives the data of the thing the page edits, or None once
        the thing is gone; when the page closes, keep() is given that data if it changed, and the status line says which happened."""
        self.app.made_preview().stop()
        draft = Document(setlist=setlist)
        self._tune_open = (read, read(draft), keep, kept, unchanged)
        self.app.open_draft(draft)
        self.show_page(screen())

    def edit_tune_phrasing(self):
        """Open the Phrasing page on the Phrasing the tune's clips run, in a draft of the set the choices make."""
        name = wizard_text.MSG_TUNE_PHRASING_NAME
        setlist = self._set_to_draft()
        if setlist is None:
            return
        read = functools.partial(_generator_data, kind=phrasing_plugin.NAME, name=name)
        if read(Document(setlist=setlist)) is None:
            self.refuse(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
            return
        screen = functools.partial(PluginEditor, holder=self.holder, name=name, section=phrasing_plugin.SECTION)
        self.open_in_draft(setlist=setlist, read=read, screen=screen, keep=self._choices.set_tune_phrasing,
                           kept=messages.MSG_WIZARD_PHRASING_KEPT, unchanged=messages.MSG_WIZARD_PHRASING_UNCHANGED)

    def _set_to_draft(self):
        """Return the set the choices make, to draft in, or None after saying on the status line why it cannot be made."""
        try:
            setlist, _ = self._choices.made_for_listening()
        except (ValueError, SongFileError) as problem:
            self.refuse(str(problem))
            return None
        return setlist

    def edit_player(self, role):
        """Open the Musician page on the Musician that plays a player's clips, in a draft of the set the choices make."""
        player = self._choices.player(role)
        name = player.musician_name()
        setlist = self._set_to_draft()
        if setlist is None:
            return
        read = functools.partial(_generator_data, kind=musician_plugin.NAME, name=name)
        if read(Document(setlist=setlist)) is None:
            # A player who plays in no section of the song has no clips, and so no Musician to open.
            self.refuse(errors.ERR_WIZARD_PLAYER_PLAYS_NOTHING)
            return
        screen = functools.partial(PluginEditor, holder=self.holder, name=name, section=musician_plugin.SECTION)
        self.open_in_draft(setlist=setlist, read=read, screen=screen, keep=functools.partial(self._keep_musician, role=role),
                           kept=messages.MSG_WIZARD_PLAYER_KEPT, unchanged=messages.MSG_WIZARD_PLAYER_UNCHANGED)

    def _keep_musician(self, settings, *, role):
        """Give a player a Musician of the person's own."""
        player = self._choices.player(role)
        player.set_musician(settings=settings)

    def on_screen_resume(self):
        """Take a tune's or a riff's notes back from the pattern editor, which has closed, before the page is drawn again."""
        # A dialog closing over the page resumes it too, so the notes are taken back only once the page itself is on top.
        if self._tune_open is not None and self.app.is_drafting() and self.app.screen is self:
            self.keep_tune_edited(self.app.close_draft())
        super().on_screen_resume()

    def keep_tune_edited(self, draft):
        """Keep the notes of the pattern that was open as the person's own, where the editor changed them, and say which happened. A
        pattern that was renamed or deleted in the editor is not found, and nothing is kept."""
        read, before, keep, kept, unchanged = self._tune_open
        self._tune_open = None
        after = read(draft)
        if after is None or after == before:
            self.say(unchanged)
            return
        try:
            self.choosing(keep)(after)
        except ValueError as problem:
            self.refuse(str(problem))
            return
        self.say(kept)

    # Listening: a part of the song as it would be made, heard through FluidSynth and thrown away.

    def ask_row(self, *, title, row, then):
        """Ask for a row of numbers, edited cell by cell (a RowAsked), and pass the row typed to then unless it is cancelled."""
        dialog = RowDialog(title=title, values=row.values, lowest=row.lowest, highest=row.highest, fewest=row.fewest, most=row.most, usual=row.usual)
        self.ask(dialog=dialog, then=then)

    def ask_new_riff(self, *, player, then):
        """Ask how a new riff for a player is written, and pass the settings chosen to then, or None where it is cancelled."""
        self.ask(dialog=NewRiffDialog(player=player), then=then)

    def listen_keys(self):
        """Return the key that listens to what the branch under the cursor has to hear, or stops it while it plays, and none for a branch with nothing to hear."""
        heard = self.branch().listens()
        if heard is None:
            return []
        if self.app.made_preview().playing() == heard[0]:
            return [self.bind(self.KEYS.STOP_LISTENING, action=self.stop_listening)]
        return [self.bind(self.KEYS.LISTEN, action=self.listen)]

    def listen(self):
        self.listen_to(self.branch().listens())

    def listen_to(self, heard):
        """Play what a panel names: what it is called, the place of its section, the player whose clip alone plays, and, where it
        is heard in another song than the one the choices make, as a riff nobody plays yet is, that song's set and name."""
        if heard is None:
            self.refuse(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
            return
        what, index, track, *made = heard
        elsewhere = None
        if made:
            elsewhere = made[0]
        branch = self.branch()
        problem = self.problem_listening(what=what, index=index, track=track, made=elsewhere, alone=branch.listens_alone())
        if problem is not None:
            self.refuse(problem)
            return
        self.say(messages.MSG_WIZARD_LISTENING.format(what=what))

    def problem_listening(self, *, what, index, track, made=None, alone=False):
        """Play a section of the song as it would be made, or one track of the section, and return why it could not be heard, or
        None. A dialog over the page listens through this too."""
        preview = self.app.made_preview()
        if not preview.can_sound():
            return errors.ERR_WIZARD_CANNOT_LISTEN
        try:
            setlist, name = made or self._choices.made_for_listening()
            song = setlist.get_song(name)
            if index >= len(song.get_scenes()):
                raise ValueError(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
            if track is None:
                play = functools.partial(preview.play_section, setlist=setlist, name=name, index=index, what=what)
            else:
                play = functools.partial(preview.play_line, setlist=setlist, name=name, index=index, track=track, what=what, with_drums=not alone)
            return preview.sender_refusal(play)
        except (ValueError, SongFileError):
            return errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO

    def stop_listening(self):
        self.app.made_preview().stop()
        self.say(messages.MSG_STOPPED)

    def ask_song_name(self):
        """Ask for the name of the song the wizard makes."""
        document = self.document()
        self.ask_name(title=messages.MSG_WIZARD_SONG_NAME_PROMPT, value=self._song_name, taken=document.song_names(), then=self.choosing(self.set_song_name))

    def set_song_name(self, name):
        self._song_name = name

    # How the run starts, which a dialog asks before the wizard opens on a song the wizard made (LlamatronApp.show_wizard).

    def get_start(self):
        """Return the way of starting chosen, or None on a song the wizard did not make, where a new song is started from scratch."""
        return self._start

    def start_with(self, start):
        """Start the run one of the four ways: from the choices the current song kept or from none, a new song or the current song replaced.
        Nothing is chosen yet, so the wizard still closes without asking."""
        self._start = start
        self._choices = WizardChoices.from_data(self._last) if start in starts.FROM_LAST else WizardChoices()
        # Every run of the wizard rolls the dice afresh, and at its start, so that what a panel shows of the song, as its hook, is
        # what Apply makes: a run from the last settings keeps the settings and never the seed.
        self._choices.draw_seed()
        document = self.document()
        self._song_name = document.get_current_song_name() if self.replaces() else new_name(word=names.MSG_NEW_SONG_WORD, taken=document.song_names())

    def replaces(self):
        """Return whether Create replaces the current song, where otherwise a song is added."""
        return self._start in starts.REPLACING

    def refusal_of(self, branch):
        """Return why the cursor cannot move into a branch's fields yet, or None when it can."""
        return branch.refusal()

    def has_choices_to_lose(self):
        return self._changed

    # The tree.

    def roots(self):
        """Return the tree's top branches, in the order a song is thought through: each is a page of the wizard, the genre and then the subgenre unlocking the rest."""
        return [
            GenreBranch(page=self),
            SubgenreBranch(page=self),
            BandBranch(page=self),
            CompositionBranch(page=self),
            FormBranch(page=self),
            CreateBranch(page=self),
        ]

    def cursor_place(self):
        """Where the cursor is: the branch of the tree, and the field while the cursor is in the fields."""
        return (self.tree_place, self.in_fields, self.cursor.get_place() if self.in_fields else NO_PLACE)

    def release_offers_once_left(self):
        """Let the held offers go once the cursor has left the cell whose change held them, and forget what the page kept, which
        was made from them: the panel then shows the fields and the values that the choices as they now stand offer, with the
        cursor on the field the cursor moved to."""
        if self._held_at is not None and self.cursor_place() != self._held_at:
            self._held_at = None
            # The cursor has moved to a field of the panel as it was drawn; fields may now appear or leave above that field,
            # so the cursor stays on the field by its label.
            label = self.label_under_cursor()
            self._choices.release_offers()
            forget_cached(self)
            if self.in_fields:
                self.stay_on(label)

    def shown_state(self):
        """Return everything the tree's rows and a branch's fields are made from, the key they are kept by: the choices, the song's
        name, the open branches, move mode and the sections of fields that are open. One key asks for the rows and the fields
        dozens of times, to find the cursor, to list the keys and to draw, and each asking built every branch and field again
        from the choices, which made every key slow. The held offers are let go first, once the cursor has left their cell."""
        self.release_offers_once_left()
        choices = repr(self._choices.to_data())
        open_branches = tuple(sorted(self._open))
        open_sections = tuple(sorted(self.app.open_field_sections))
        return (choices, self._song_name, open_branches, self.moving, self._start, open_sections)

    @cached_while(shown_state, said=said_of)
    def rows(self):
        """Return the branches the tree shows, each with how deep it is: every top branch, and the branches under each open one, however deep."""
        rows = []

        def listed(*, branch, depth):
            rows.append((depth, branch))
            # A locked branch shows nothing under it, whatever was open before the choice that locked it.
            if branch.key() in self._open and not self.refusal_of(branch):
                for child in branch.children():
                    listed(branch=child, depth=depth + 1)
        for root in self.roots():
            listed(branch=root, depth=0)
        return rows

    def row(self):
        """Return the depth and the branch under the tree's cursor, the cursor held within the tree, which a choice can shorten."""
        rows = self.rows()
        self.tree_place = max(min(self.tree_place, len(rows) - 1), FIRST_PLACE)
        return rows[self.tree_place]

    def branch(self):
        return self.row()[1]

    def shows_children(self, branch):
        """Return whether a branch of the tree is open, showing the branches under it, which a locked branch never is."""
        return branch.key() in self._open and not self.refusal_of(branch)

    def move_in_tree(self, name):
        self.tree_place = moves.moved(place=self.tree_place, name=name, count=len(self.rows()))

    def fold(self, name):
        """Open the branch under the cursor with Right and close it with Left; Left on a branch inside another, closed or with nothing under it, goes to the branch that holds it."""
        depth, branch = self.row()
        if name == Key.RIGHT:
            if self.refusal_of(branch):
                self.refuse(self.refusal_of(branch))
            elif branch.children():
                self._open.add(branch.key())
            return
        if depth and not (branch.children() and self.shows_children(branch)):
            while self.rows()[self.tree_place][0] >= depth:
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
        first = FIRST_PLACE
        for place, field in enumerate(self.shown_fields()):
            if field.enter or field.adjust:
                first = place
                break
        self.cursor.set_place(first)

    def to_tree(self):
        self.in_fields = False

    # The fields, a settings page's, of the branch under the tree's cursor.

    def fields(self):
        return self.fields_at(place=self.tree_place)

    def fields_state(self):
        """Return no key, so that a settings page's keeping of its fields keeps nothing here: the wizard keeps its own, by the
        choices and the tree (fields_at), which a settings page's key knows nothing of."""
        return None

    @cached_while(shown_state, said=said_of)
    def fields_at(self, *, place):
        """Return the fields of the branch at a place of the tree, the branch under the cursor."""
        return self.branch().fields()

    def remarks(self, width):
        return self.branch().remarks(width)

    def field(self):
        """Return the field under the cursor, or None while the cursor is in the tree."""
        return super().field() if self.in_fields else None

    def keys(self):
        if self.in_fields:
            # A settings page's keys, but for ESC, which goes back to the tree here and not from the page.
            settings_keys = super().keys()[1:]
            branch = self.branch()
            return [self.bind(self.KEYS.TO_TREE, action=self.to_tree), *settings_keys, *branch.field_keys(), *self.listen_keys()]
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
            result.append(self.bind(self.KEYS.COPY, action=self.copy_listed))
            result.append(self.bind(self.KEYS.DELETE, action=self.remove_listed))
            result.append(self.bind(self.KEYS.MOVE, action=self.start_moving))
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
        """Ask which kind of thing to insert and put one before the branch under the cursor, the cursor staying on the new one, as
        on Arrange."""
        branch = self.branch()
        kinds = branch.kinds_to_add()
        dialog = ChoiceDialog(title=labels.MSG_WIZARD_INSERT_SECTION_TITLE, options=kinds)
        self.ask(dialog=dialog, then=functools.partial(self._insert_kind, branch=branch, kinds=kinds))

    def _insert_kind(self, place, *, branch, kinds):
        """Insert the kind picked before the branch under the cursor."""
        self.choosing(branch.insert)(kinds[place])

    def pick_sound(self, role):
        """Choose a player's sound from a list: the band's first, which takes the sound from the band again, then the genre's
        own sounds that suit the player, then a row that opens every General MIDI sound that plays notes."""
        sounds = self._choices.get_sounds()
        own = sounds.genre_sounds(role)
        options = self._sound_options(role=role, own=own)
        last = len(options) - 1
        player = self._choices.player(role)
        title = labels.MSG_WIZARD_SOUND_TITLE.format(player=player.title())
        dialog = ChoiceDialog(title=title, options=options, current=self._sound_place(role=role, own=own, last=last))
        self.ask(dialog=dialog, then=functools.partial(self._sound_chosen, role=role, own=own, last=last))

    def _sound_options(self, *, role, own):
        """Return the sounds a player is offered: the band's, the genre's own that suit the player, and the row of every sound."""
        sounds = self._choices.get_sounds()
        band_sound = sounds.sound_name(sounds.band_sound(role))
        options = [marks.MSG_WIZARD_FROM_BAND.format(sound=band_sound)]
        for sound in own:
            options.append(sounds.sound_name(sound))
        options.append(labels.MSG_WIZARD_MORE_SOUNDS)
        return options

    def _sound_place(self, *, role, own, last):
        """Return where the list of sounds opens: on the player's own sound, the row of every sound for one not among the
        genre's, or the band's."""
        sounds = self._choices.get_sounds()
        if not sounds.has_own_sound(role):
            return FIRST_PLACE
        sound = sounds.get_sound(role)
        if sound in own:
            return own.index(sound) + 1
        return last

    def _sound_chosen(self, place, *, role, own, last):
        """Give the player the sound picked, the band's again, or open every sound."""
        if place == last:
            self.pick_any_sound(role)
            return
        sound = None
        if place != FIRST_PLACE:
            sound = own[place - 1]
        self.choosing(functools.partial(self._set_sound, role=role))(sound)

    def _set_sound(self, sound, *, role):
        """Give a player a sound of its own, or the band's with None."""
        sounds = self._choices.get_sounds()
        sounds.set_sound(role=role, sound=sound)

    def pick_any_sound(self, role):
        """Choose a player's sound from every General MIDI sound, by family; a sound is tried as a run of the song's scale in the
        player's octave."""
        sounds = self._choices.get_sounds()
        player = self._choices.player(role)
        run = run_of(root=self._choices.root_half_steps(), steps=self._choices.scale_half_steps(), octave=player.get_octave())
        trial = SoundTrial(page=self, played=functools.partial(_run_played, run=run))
        dialog = SoundDialog(title=labels.MSG_WIZARD_MORE_SOUNDS_TITLE, groups=sound_families(), current=sounds.get_sound(role), trial=trial)
        self.ask(dialog=dialog, then=functools.partial(self._any_sound_chosen, role=role))

    def _any_sound_chosen(self, sound, *, role):
        """Give the player the sound picked from every sound, where one was."""
        if sound is not None:
            self.choosing(functools.partial(self._set_sound, role=role))(sound)

    def pick_piece_sound(self, piece):
        """Choose what a piece of the kit sounds as: its own drum first, then the kit's drums, then every General MIDI sound by
        family, and on the Note row under them the note a General MIDI sound plays. A drum is tried as four hits of the kit, and
        a General MIDI sound as four notes, on the note the row shows."""
        kit = self._choices.get_kit()
        drums = []
        for drum in kit.drums():
            if drum != piece:
                drums.append((marks.MSG_WIZARD_KIT_DRUM_SHOWN.format(drum=drum), drum))

        def played(sound):
            if not isinstance(sound, str):
                return hits_of(dialog.note), sound_trial.HITS_STEP, sound
            drum = sound
            if sound == OWN_DRUM:
                drum = piece
            return hits_of(notation.NOTATION_KIT[drum]), sound_trial.HITS_STEP, None
        top = [(marks.MSG_WIZARD_OWN_DRUM_SHOWN.format(piece=piece), OWN_DRUM)]
        groups = [(labels.MSG_WIZARD_KIT_DRUMS, drums), *sound_families()]
        current = kit.piece_sound(piece) or OWN_DRUM
        note = kit.piece_note(piece) or wizard_limits.USUAL_PIECE_NOTE
        trial = SoundTrial(page=self, played=played)
        dialog = SoundDialog(title=labels.MSG_WIZARD_PIECE_SOUND_TITLE.format(piece=piece), top=top, groups=groups, current=current, trial=trial, note=note)
        self.ask(dialog=dialog, then=self.choosing(functools.partial(self._piece_sound_chosen, piece=piece)))

    def _piece_sound_chosen(self, answer, *, piece):
        """Have a piece of the kit sound as what was picked: its own drum, another drum of the kit, or a sound on a note."""
        sound, note = answer
        kit = self._choices.get_kit()
        if not isinstance(sound, str):
            kit.set_piece_sound(piece=piece, sound=sound)
            kit.set_piece_note(piece=piece, note=note)
            return
        if sound == OWN_DRUM:
            sound = None
        kit.set_piece_sound(piece=piece, sound=sound)

    def pick_suggested_form(self):
        """Offer the forms the subgenre suggests in a dialog, each with its sections and its length at the tempo chosen, and
        take the one picked; where a person changed the sections, ask first, since the form picked replaces them."""
        form = self._choices.get_song_form()
        if form.has_own_form():
            self.ask(dialog=self._replace_sections_dialog(), then=self._pick_form_if_yes)
        else:
            self._pick_form()

    def _replace_sections_dialog(self):
        """Return the dialog that asks whether the person's own sections may be replaced."""
        return ConfirmDialog(title=labels.MSG_WIZARD_REPLACE_SECTIONS_TITLE, messages=[messages.MSG_WIZARD_REPLACE_SECTIONS_QUESTION])

    def _pick_form_if_yes(self, yes):
        if yes:
            self._pick_form()

    def _pick_form(self):
        """Offer the forms the subgenre suggests, each with its count of sections and its length, opening on the form chosen."""
        form = self._choices.get_song_form()
        forms = form.forms()
        options = []
        for name in forms:
            length = clock(form.form_seconds(form=name))
            options.append(marks.MSG_WIZARD_SUGGESTED_FORM.format(form=name, count=form.form_section_count(name), length=length))
        dialog = ChoiceDialog(title=labels.MSG_WIZARD_SUGGESTED_FORM_TITLE, options=options, current=forms.index(form.get_form()))
        self.ask(dialog=dialog, then=functools.partial(self._form_picked, forms=forms))

    def _form_picked(self, place, *, forms):
        """Take the form picked."""
        form = self._choices.get_song_form()
        self.choosing(form.set_form)(forms[place])

    def ask_form_questions(self):
        """Ask the questions a form is made from, one dialog a question, each opening on its usual answer, and make the form the
        answers ask for the song's own; ESC at any question leaves the form as it was, and where a person changed the sections,
        the last step asks first."""
        form = self._choices.get_song_form()
        self._ask_form_question(questions=form.form_questions(), place=FIRST_PLACE, answers={})

    def _ask_form_question(self, *, questions, place, answers):
        """Ask the form's question at a place, or, once every one is answered, make the form."""
        if place == len(questions):
            self._finish_form(answers)
            return
        name, offered, usual = questions[place]
        dialog = ChoiceDialog(title=labels.MSG_WIZARD_FORM_QUESTION_TITLES[name], options=list(offered), current=offered.index(usual))
        self.ask(dialog=dialog, then=functools.partial(self._form_answered, questions=questions, place=place, answers=answers))

    def _form_answered(self, chosen, *, questions, place, answers):
        """Keep the answer picked to the form's question at a place, and ask the next."""
        name, offered, _ = questions[place]
        answers[name] = offered[chosen]
        self._ask_form_question(questions=questions, place=place + 1, answers=answers)

    def _finish_form(self, answers):
        """Make the form the answers ask for, asking first where a person changed the sections."""
        form = self._choices.get_song_form()
        if form.has_own_form():
            self.ask(dialog=self._replace_sections_dialog(), then=functools.partial(self._make_form_if_yes, answers=answers))
        else:
            self._make_form(answers)

    def _make_form_if_yes(self, yes, *, answers):
        if yes:
            self._make_form(answers)

    def _make_form(self, answers):
        """Make the form the answers ask for the song's own, and open the Form panel."""
        form = self._choices.get_song_form()
        try:
            self.choosing(form.set_form_from_answers)(answers)
        except ValueError as problem:
            self.refuse(str(problem))
            return
        self._open.add(labels.MSG_WIZARD_FORM_BRANCH)

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
        if self.choosing(self.branch().shift)(offset):
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

    def history_refusal(self):
        return messages.MSG_WIZARD_NOTHING_TO_UNDO

    # Create.

    def create(self):
        """Make the song from the choices and the seed the run drew when it started, add it to the set with all it uses as one
        change, and show Arrange on it."""
        try:
            made = self._choices.made_setlist(name=self._song_name, version=version.VERSION)
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
        """Return the tree's lines: each branch after its cursor's mark, indented by its depth, with its open or closed mark, its
        note dim, and at the line's end the mark of the branch whose fields hold the cursor."""
        lines = []
        for place, (depth, branch) in enumerate(self.rows()):
            lines.append(self._tree_line(depth=depth, branch=branch, under_cursor=place == self.tree_place))
        return lines

    def _tree_line(self, *, depth, branch, under_cursor):
        """Return one branch's line of the tree."""
        line = Text(no_wrap=True)
        line.append(cursor_mark(under_cursor and not self.in_fields))
        line.append(drawing.INDENT * depth)
        if not branch.children():
            line.append(drawing.INDENT)
        elif self.shows_children(branch):
            line.append(marks.MSG_WIZARD_BRANCH_OPEN + drawing.SPACE)
        else:
            line.append(marks.MSG_WIZARD_BRANCH_CLOSED + drawing.SPACE)
        name = branch.name()
        if self.moving and under_cursor:
            name = marks.MSG_WIZARD_CARRIED.format(name=name)
        line.append(name, style=self.name_style(branch=branch, under_cursor=under_cursor))
        if branch.note():
            line.append(drawing.SPACE + branch.note(), style=Style.DIM)
        line.truncate(TREE_WIDTH - 2)
        line.pad_right(TREE_WIDTH - 2 - len(line.plain))
        edited = drawing.SPACE
        if under_cursor and self.in_fields:
            edited = marks.MSG_WIZARD_EDITED_BRANCH
        line.append(edited + drawing.SPACE)
        return line

    def name_style(self, *, branch, under_cursor):
        """Return the style of a branch's name in the tree: the branch under the cursor bold in the wizard's theme colour, so that the
        selection is seen at a glance, a locked branch dim, and the rest plain."""
        if under_cursor:
            return BOLD_IN_COLOUR.format(bold=Style.BOLD, colour=themes.text_style(self.THEME))
        return Style.DIM if self.refusal_of(branch) else Style.PLAIN

    def field_lines(self, *, width, height):
        """Return the right side's lines: the branch's title, then its fields as a settings page draws them, all dim while the cursor is in the tree."""
        place = self.cursor.get_place()
        if not self.in_fields:
            self.cursor.set_place(NO_PLACE)
        lines = [Text(drawing.SPACE + self.branch().title(), style=Style.BOLD), *FieldPage.body(self, width=width, height=max(height - 1, 1))]
        self.cursor.set_place(place)
        if not self.in_fields:
            for line in lines:
                line.stylize(Style.DIM)
        return lines

    def body(self, *, width, height):
        tree = self.window_of_tree(lines=self.tree_lines(), height=height)
        fields = self.field_lines(width=max(width - TREE_WIDTH - len(DIVIDER), LEAST_FIELDS_WIDTH), height=height)
        lines = []
        for place in range(max(len(tree), len(fields), height)):
            tree_part = Text(drawing.SPACE * TREE_WIDTH)
            if place < len(tree):
                tree_part = tree[place]
            fields_part = Text(drawing.NOTHING)
            if place < len(fields):
                fields_part = fields[place]
            line = Text(no_wrap=True)
            line.append_text(tree_part)
            line.append(DIVIDER, style=Style.DIM)
            line.append_text(fields_part)
            lines.append(line)
        return lines

    def window_of_tree(self, *, lines, height):
        """Return the tree's lines that fit the height, scrolled so that the branch under the cursor shows, a long form having more sections than a console has lines."""
        if len(lines) <= height:
            return lines
        first = max(min(self.tree_place - height // 2, len(lines) - height), FIRST_PLACE)
        return lines[first:first + height]
