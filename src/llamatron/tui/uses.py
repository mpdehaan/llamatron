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
"""The words for what uses an item, so that a page can refuse to delete something still in use and list its uses.

The set and its songs answer what uses what; this only puts the answers into words. A use is one
line of text for each thing that uses the item, naming the song it's in, since every song shares
the set's patterns, chains, generators and scales.
"""

from llamatron.composition.file_format import Section
from llamatron.strings.errors import ERR_AND_MORE, ERR_LOOP_SCENES_INTRO
from llamatron.strings.messages import MSG_USE_CHAIN, MSG_USE_SCENE, MSG_USE_SONG, MSG_USE_SONG_SCENE, MSG_USE_SONG_SCENE_TRACK, MSG_USE_SONG_TRACK
from llamatron.strings.names import MSG_DOCUMENT_UNNAMED_SCENE

# How many scenes the loop errors dialog lists before saying how many more there are.
LOOP_ERRORS_SHOWN = 10


def scene_label(*, number, scene):
    """Return how a scene is named in a use: its number and its name, if it has one."""
    name = scene.get_name()
    return MSG_USE_SCENE.format(number=number, name=MSG_DOCUMENT_UNNAMED_SCENE if name is None else name)


def _clip_slot_uses(clip_slots):
    """Return a use for each (song name, number, scene, track) of a clip slot anywhere in the set."""
    return [MSG_USE_SONG_SCENE_TRACK.format(song=song, scene=scene_label(number=number, scene=scene), track=track) for song, number, scene, track in clip_slots]


def _song_uses(songs):
    """Return a use for each song that chose something as its own."""
    return [MSG_USE_SONG.format(name=song) for song in songs]


def _scene_uses(scenes):
    """Return a use for each (song name, number, scene) of a scene that chose something."""
    return [MSG_USE_SONG_SCENE.format(song=song, scene=scene_label(number=number, scene=scene)) for song, number, scene in scenes]


def _track_uses(tracks):
    """Return a use for each (song name, track name) of a track that chose something."""
    return [MSG_USE_SONG_TRACK.format(song=song, track=track) for song, track in tracks]


def _chain_uses(chains):
    """Return a use for each chain that runs something."""
    return [MSG_USE_CHAIN.format(name=chain) for chain in chains]


def uses_of(*, setlist, section, name):
    """Return every use of a named item of a section anywhere in the set, each worded for a page.

    The songs, scenes and tracks that chose it come first, then the clips that play it or run
    it, then the chains that run it. Which of those can name an item of the section is for the
    composition objects to say, so a scale is listed by its songs and scenes, a groove by its
    tracks too, a pattern or a chain by its clips and a generator by its chains.
    """
    return [
        *_song_uses(setlist.songs_naming(section=section, name=name)),
        *_scene_uses(setlist.scenes_naming(section=section, name=name)),
        *_track_uses(setlist.tracks_naming(section=section, name=name)),
        *_clip_slot_uses(setlist.clip_slots_naming(section=section, name=name)),
        *_chain_uses(setlist.chains_naming(section=section, name=name)),
    ]


def grabbers(*, song, song_name, track):
    """Return the clips of a song that grab from one of its tracks, worded like every other use."""
    return _clip_slot_uses([(song_name, number, scene, other) for number, scene, other in song.clip_slots_naming(section=Section.TRACKS, name=track)])


def looping_scenes(song):
    """Return the label of each scene in which every clip loops, so that the scene would never end."""
    return [scene_label(number=number, scene=scene) for number, scene in song.scenes_that_never_end()]


def loop_error_lines(song):
    """Return the lines of the loop errors dialog, or nothing when every scene can end."""
    scenes = looping_scenes(song)
    if not scenes:
        return []
    lines = [ERR_LOOP_SCENES_INTRO, *scenes[:LOOP_ERRORS_SHOWN]]
    if len(scenes) > LOOP_ERRORS_SHOWN:
        lines.append(ERR_AND_MORE.format(count=len(scenes) - LOOP_ERRORS_SHOWN))
    return lines
