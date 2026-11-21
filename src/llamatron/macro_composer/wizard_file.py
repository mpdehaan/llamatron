# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A song file: the song wizard's choices written down, which the wizard makes a song of with nobody at the keys.

The file is a mapping. It holds the choices the wizard keeps with a song (genre, subgenre, root, type, tempo, seed, players
and the rest), any of them left out to take its usual value, and three things besides:

  name       what the song is called; the file's name where left out.
  form       a form's name, as the wizard offers them, or a list of sections in the order they play. A section is its kind,
             as verse, or a mapping with a kind and whatever the section is given: its bars and who plays, and, for this
             place of the form alone, its energy, its chords, its tunes, what it leaves with and anything else a section holds.
  song_plan  true, or left out, for a song planned section by section (song_plan.py); false for a song arranged as the
             wizard has always arranged one; or a mapping of the plan's own settings, as its contrast.
  song       picks laid over the song the choices make, as the arranger reads them: for whatever the wizard has no choice for.

A seed left out is drawn anew at every run, so that each run makes another song of the same choices.
"""

import os

from llamatron.macro_composer import arranger, notation as tune_notation, song_plan, wizard_limits
from llamatron.macro_composer.wizard_choices import data_laid_over, WizardChoices
from llamatron.model.file import files
from llamatron.model.file.safe_yaml import load_safely
from llamatron.user_strings import errors

NAME = 'name'
KIND = 'kind'
# What the wizard keeps of a section of a song's own form; the rest of an entry is the song plan's, for that place.
KEPT_OF_SECTION = (KIND, 'bars', 'plays')


def form_entries(*, form, path):
    """A written form's sections, each as a mapping with its kind."""
    entries = []
    for place, entry in enumerate(form, start=1):
        if isinstance(entry, str):
            entry = {KIND: entry}
        if not isinstance(entry, dict) or not isinstance(entry.get(KIND), str):
            raise ValueError(errors.ERR_SONG_FILE_FORM_ENTRY.format(path=path, place=place, value=entry))
        entries.append(entry)
    return entries


def choices_of(*, data, path, seed=None):
    """The wizard's choices a song file's data describes, with a seed in place of the file's where one is given."""
    if not isinstance(data, dict):
        raise ValueError(errors.ERR_SONG_FILE_NOT_A_MAPPING.format(path=path))
    kept = {field: value for field, value in data.items() if field not in (NAME, song_plan.PLAN_OF_SONG, wizard_limits.EXTRAS_KEPT)}
    plan = data.get(song_plan.PLAN_OF_SONG, True)
    plan = dict(plan) if isinstance(plan, dict) else ({} if plan else None)
    written = isinstance(data.get(arranger.FORM), list)
    if written:
        entries = form_entries(form=data[arranger.FORM], path=path)
        del kept[arranger.FORM]
        kept[wizard_limits.OWN_SECTIONS] = [tune_notation.with_fields_only(entry=entry, fields=KEPT_OF_SECTION) for entry in entries]
        if plan is not None:
            plan[song_plan.BY_PLACE] = [tune_notation.without_fields(entry=entry, fields=KEPT_OF_SECTION) for entry in entries]
    if seed is not None:
        kept[arranger.SEED] = seed
    choices = WizardChoices.from_data(kept)
    if not choices.is_ready():
        raise ValueError(errors.ERR_SONG_FILE_NOT_READY.format(path=path))
    if written and not choices.get_song_form().has_own_form():
        raise ValueError(errors.ERR_SONG_FILE_FORM.format(path=path))
    extras = data_laid_over(under={song_plan.PLAN_OF_SONG: plan} if plan is not None else {}, over=data.get(wizard_limits.EXTRAS_KEPT) or {})
    if extras:
        choices.set_song_extras(extras)
    return choices


def song_name(*, data, path):
    """What a song file's song is called: the name it gives, or the file's."""
    return (data.get(NAME) if isinstance(data, dict) else None) or os.path.splitext(os.path.basename(path))[0]


def made_of_file(*, path, version, seed=None):
    """The set a song file makes: the one song, with all it uses, the song keeping the choices that made it."""
    with open(path, encoding=files.FILE_ENCODING) as file:
        data = load_safely(file)
    return choices_of(data=data, path=path, seed=seed).made_setlist(name=song_name(data=data, path=path), version=version)
