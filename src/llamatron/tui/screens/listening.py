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
picker asks which of the set's instruments to play through, for this listening alone. The Patterns
page and the pattern editor listen to a pattern through the pattern preview (tui/pattern_preview.py),
which plays beside the song with one key and asks nothing.
"""

from llamatron.composition.song_file_error import SongFileError
from llamatron.realtime.sender_process import SenderNotStarted
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.screens.shared import play_through
from llamatron.tui.text import sorted_names
from llamatron.strings.errors import ERR_CANT_PLAY_TITLE
from llamatron.strings.messages import MSG_CLIP_ON_TRACK, MSG_LISTEN_INSTRUMENT_TITLE, MSG_LISTENING, MSG_LISTENING_GENERAL_MIDI, MSG_LISTENING_IN_SCALE, MSG_LISTENING_TO_PATTERN, MSG_STOPPED


def listen(*, page, index, track, song=None, name):
    """Play one clip of a song, the current one or the one given, on its own and again and again, asking for an instrument when its track has none."""
    transport = page.app.transport
    preview = page.app.pattern_preview()
    # With the set's Real Time switch off, the clip plays through General MIDI in FluidSynth, where FluidSynth is installed (the user's rule).
    if song is None and not page.document().setlist().is_real_time() and preview.general_midi_is_installed():
        try:
            preview.play_clip_of_song(index=index, track=track)
        except (SongFileError, SenderNotStarted) as error:
            page.tell(ERR_CANT_PLAY_TITLE, str(error))
            return
        page.say(MSG_LISTENING_GENERAL_MIDI.format(name=name))
        return
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
    page.app.pattern_preview().stop()
    page.app.transport.stop_all()
    page.say(MSG_STOPPED)


def listen_to_pattern(*, page, pattern):
    """Play a pattern at once, again and again, beside whatever the song plays (tui/pattern_preview.py), and say the scale it plays in."""
    preview = page.app.pattern_preview()
    refusal = preview.refusal(pattern)
    if refusal is not None:
        page.refuse(refusal)
        return
    try:
        preview.play(pattern)
    except (SongFileError, SenderNotStarted) as error:
        page.tell(ERR_CANT_PLAY_TITLE, str(error))
        return
    scale = preview.scale()
    page.say(MSG_LISTENING_TO_PATTERN.format(name=pattern) if scale is None else MSG_LISTENING_IN_SCALE.format(name=pattern, scale=scale))


def stop_listening_to_pattern(page):
    """Stop the pattern's preview alone, leaving a song played from Arrange playing."""
    page.app.pattern_preview().stop()
    page.say(MSG_STOPPED)


def pattern_listen_keys(*, page, pattern):
    """Return the key that listens to a pattern, or stops it while it is the one playing, and none when nothing could sound: the song names no
    Preview instrument and FluidSynth is not installed (the user's rule)."""
    preview = page.app.pattern_preview()
    if pattern is None:
        return []
    if preview.playing_pattern() == pattern:
        return [page.bind(page.KEYS.STOP_LISTENING, action=lambda: stop_listening_to_pattern(page))]
    if not preview.can_sound(pattern):
        return []
    return [page.bind(page.KEYS.LISTEN, action=lambda: listen_to_pattern(page=page, pattern=pattern))]
