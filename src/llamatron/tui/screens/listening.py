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

"""Listening: how the clip page and the pattern editor play one clip again and again, the user's design of 2026-11-09.

A clip is played as its scene would play it, with its chain, its grabs from the scene's grab track,
its scale and its direction, looping until stopped. When the clip's track has no instrument, a
picker asks which of the set's instruments to play through, for this listening alone. The pattern
editor listens to a pattern through a track: the one track that plays it, or any of them when they
share one instrument, and otherwise a track picked from the song's; a track that plays the pattern
nowhere gets a scene of its own in a copy of the song, where grab steps play their own note.
"""

from llamatron.composition.clip_slot import ClipSlot
from llamatron.composition.file_format import Section
from llamatron.composition.scene import Scene
from llamatron.composition.setlist import Setlist
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.screens.shared import play_through
from llamatron.tui.text import sorted_names
from llamatron.strings.messages import MSG_CLIP_ON_TRACK, MSG_LISTEN_INSTRUMENT_TITLE, MSG_LISTEN_TRACK_TITLE, MSG_LISTENING, MSG_STOPPED

FIRST_NUMBER = 1


def listen(*, page, index, track, song=None, name):
    """Play one clip of a song, the current one or the one given, on its own and again and again, asking for an instrument when its track has none."""
    transport = page.app.transport
    problem = transport.problem(track=track)
    if problem is not None:
        page.tell(problem.title, *problem.lines)
        return
    setlist = page.document().setlist()
    instrument = page.document().song().get_track(track).get_instrument_name()
    said = MSG_LISTENING.format(name=name, track=track)
    what = MSG_CLIP_ON_TRACK.format(name=name, track=track)
    if instrument and setlist.get_instrument(instrument).has_device():
        play_through(page=page, play=lambda: transport.play_clip(index=index, track=track, song=song, forever=True), what=what, said=said)
        return
    choices = sorted_names(setlist.get_instrument_names())

    def chosen(place):
        play_through(page=page, play=lambda: transport.play_clip(index=index, track=track, song=song, instead={track: choices[place]}, forever=True), what=what, said=said)
    page.ask(dialog=ChoiceDialog(title=MSG_LISTEN_INSTRUMENT_TITLE, options=choices), then=chosen)


def stop_listening(page):
    page.app.transport.stop_all()
    page.say(MSG_STOPPED)


def listen_to_pattern(*, page, pattern):
    """Play a pattern through a track: at once when the tracks playing it share one instrument, and otherwise through a track picked from the song's."""
    song = page.document().song()
    uses = song.clip_slots_naming(section=Section.PATTERNS, name=pattern)
    tracks = list(dict.fromkeys(track for _, _, track in uses))
    instruments = {song.get_track(track).get_instrument_name() for track in tracks}
    if tracks and len(instruments) == 1 and None not in instruments:
        number, _, track = uses[0]
        listen(page=page, index=number - FIRST_NUMBER, track=track, name=pattern)
        return
    choices = list(song.get_track_names())

    def chosen(place):
        listen_through(page=page, pattern=pattern, track=choices[place])
    page.ask(dialog=ChoiceDialog(title=MSG_LISTEN_TRACK_TITLE, options=choices), then=chosen)


def listen_through(*, page, pattern, track):
    """Play a pattern through a track: from the first scene where the track plays it, or from a scene added to a copy of the song where it plays nowhere."""
    song = page.document().song()
    for number, _, played_on in song.clip_slots_naming(section=Section.PATTERNS, name=pattern):
        if played_on == track:
            listen(page=page, index=number - FIRST_NUMBER, track=track, name=pattern)
            return
    copied = Setlist.from_data(data=page.document().setlist().to_data()).get_song(page.document().current_song_name())
    clip_slot = ClipSlot()
    clip_slot.set_pattern_name(name=pattern, song=copied)
    scene = Scene(clip_slots={})
    copied.add_scene(index=len(copied.get_scenes()), scene=scene)
    scene.set_clip_slot(track=track, clip_slot=clip_slot, song=copied)
    listen(page=page, index=len(copied.get_scenes()) - FIRST_NUMBER, track=track, song=copied, name=pattern)
