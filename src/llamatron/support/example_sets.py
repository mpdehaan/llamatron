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

"""Where the example sets live: examples/, in a folder for each purpose, the user's layout.

examples/learning holds the demos in the order a newcomer learns the features, examples/other the demos that fit no
other folder, the Euclidean mask so far, and examples/by_genre every other song, the pieces and the songs in the manner of
others alike, in a folder for each genre, named by genre_folder, since one folder of them was too many to explore, the
user's layout.
examples/midi holds MIDI files to import, which are not sets. Everything that lists the example
sets, the tests, the tools and the demo tables, asks example_sets() here, so that a folder can be
added in one place.
"""

import glob
import os

EXAMPLES_FOLDER = 'examples'
LEARNING = 'learning'
OTHER = 'other'
BY_GENRE = 'by_genre'
# The folders of sets, in the order they are listed.
SET_FOLDERS = (LEARNING, OTHER, BY_GENRE)
SET_FILES = '*.yml'
# The folders within a folder of sets, as by_genre's genres are, at any depth.
ANY_FOLDERS = '**'
# What a genre's folder name turns into an underscore.
GENRE_SEPARATORS = (' ', '-')
UNDERSCORE = '_'


def example_sets(*, root=None):
    """Return every example set's path, folder by folder and by path within each, under root, the current folder unless given."""
    top = EXAMPLES_FOLDER if root is None else os.path.join(root, EXAMPLES_FOLDER)
    return [path for folder in SET_FOLDERS for path in sets_within(os.path.join(top, folder))]


def sets_within(folder):
    """Return the paths of the sets in folder and the folders within it, sorted."""
    return sorted(glob.glob(os.path.join(folder, ANY_FOLDERS, SET_FILES), recursive=True))


def folder_of_example(path):
    """Return the folder of examples/ that holds the set at path, such as by_genre, however deep within it the set is."""
    parts = os.path.normpath(path).split(os.sep)
    return parts[parts.index(EXAMPLES_FOLDER) + 1]


def genre_folder(genre):
    """Return the name of a genre's folder in by_genre: the genre in lower case with its spaces and hyphens made underscores, such as tv_theme for TV theme."""
    name = genre.lower()
    for separator in GENRE_SEPARATORS:
        name = name.replace(separator, UNDERSCORE)
    return name
