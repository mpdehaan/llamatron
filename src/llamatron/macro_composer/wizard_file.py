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

from llamatron.macro_composer.song_plan import BY_PLACE, PLAN_OF_SONG
from llamatron.macro_composer.wizard_choices import EXTRAS_KEPT, FORM, OWN_SECTIONS, SEED, WizardChoices, data_laid_over
from llamatron.strings import errors
from llamatron.support.safe_yaml import load_safely
from llamatron.support import files

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
    kept = {field: value for field, value in data.items() if field not in (NAME, PLAN_OF_SONG, EXTRAS_KEPT)}
    plan = data.get(PLAN_OF_SONG, True)
    plan = dict(plan) if isinstance(plan, dict) else ({} if plan else None)
    written = isinstance(data.get(FORM), list)
    if written:
        entries = form_entries(form=data[FORM], path=path)
        del kept[FORM]
        kept[OWN_SECTIONS] = [{field: value for field, value in entry.items() if field in KEPT_OF_SECTION} for entry in entries]
        if plan is not None:
            plan[BY_PLACE] = [{field: value for field, value in entry.items() if field not in KEPT_OF_SECTION} for entry in entries]
    if seed is not None:
        kept[SEED] = seed
    choices = WizardChoices.from_data(kept)
    if not choices.is_ready():
        raise ValueError(errors.ERR_SONG_FILE_NOT_READY.format(path=path))
    if written and not choices.has_own_form():
        raise ValueError(errors.ERR_SONG_FILE_FORM.format(path=path))
    extras = data_laid_over(under={PLAN_OF_SONG: plan} if plan is not None else {}, over=data.get(EXTRAS_KEPT) or {})
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
