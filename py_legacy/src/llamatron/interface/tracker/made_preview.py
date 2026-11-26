# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The wizard's preview: a song the wizard would make, heard before it is made.

The song wizard makes the song its choices stand for, in a set of its own that is thrown away, and this transport plays a part
of it through General MIDI in FluidSynth, beside whatever the tracker's own transport plays: one section once, with everybody
who plays in it, or one player's clip again and again, as a hook or a tune.
"""

from llamatron.interface.tracker.transport import Transport
from llamatron.user_strings import errors

MADE_REVISION = 0
FIRST_SCENE = 0


class MadeSong:
    """What the preview's transport reads as its document: the set made to be heard, and its one song."""

    __slots__ = ('_setlist', '_name')

    def __init__(self, *, setlist, name):
        self._setlist = setlist
        self._name = name

    def get_setlist(self):
        return self._setlist

    def song(self):
        return self._setlist.get_song(self._name)

    def get_current_song_name(self):
        return self._name

    def get_revision(self):
        """Return the one revision the set ever has: it is made, heard and thrown away, never edited."""
        return MADE_REVISION


class MadePreview(Transport):
    """Plays a part of a song made to be heard, beside whatever the song's transport plays."""

    __slots__ = ('_made', '_what')

    def __init__(self, *, beside):
        """beside is the song's transport, whose clock, FluidSynth and way of making a sender the preview shares."""
        super().__init__(**beside.shared())
        self._made = None
        self._what = None

    def document(self):
        return self._made

    def may_play(self):
        """Return that a preview plays whatever the open set's Real Time switch says."""
        return True

    def can_sound(self):
        """Return whether anything could be heard: the made song plays through FluidSynth."""
        return self._fluidsynth_installed()

    def play_section(self, *, setlist, name, index, what):
        """Play one section of the made song once, everybody who plays in it: the other scenes are taken out of the song, so that it ends with the section."""
        self.stop()
        song = setlist.get_song(name)
        for other in reversed(range(len(song.get_scenes()))):
            if other != index:
                song.remove_scene(other)
        self._begin(setlist=setlist, name=name, what=what, play=lambda: self.play_scene(index=FIRST_SCENE))

    def play_line(self, *, setlist, name, index, track, what, with_drums=True):
        """Play one player's clip of a section again and again: with the drums of the section under it where the section has drums,
        which a part is judged against, or with nothing under it. A player with no clip in the section is refused, so that the
        drums are never heard alone in the player's place."""
        self.stop()
        song = setlist.get_song(name)
        scene = song.get_scenes()[index]
        if not scene.has_clip_slot(track):
            raise ValueError(errors.ERR_WIZARD_NOTHING_TO_LISTEN_TO)
        drums = [other for other in song.get_track_names() if other != track and song.get_track(other).is_drum() and scene.get_clip_slot(other) is not None] if with_drums else []
        self._begin(setlist=setlist, name=name, what=what, play=lambda: self.play_clips(index=index, tracks=[track, *drums]))

    def _begin(self, *, setlist, name, what, play):
        self._made = MadeSong(setlist=setlist, name=name)
        self._what = what
        try:
            play()
        except Exception:
            self.stop()
            raise

    def playing(self):
        """Return what is heard, as the asker named it, or None."""
        return self._what if self._made is not None and self.is_playing() else None

    def stop(self):
        if self._made is not None:
            self.stop_all()
        self._made = None
        self._what = None
        self._drop_score()

    def forget(self):
        self.stop()

    def close(self):
        """Stop and end the preview's process, as the tracker quits; FluidSynth is the song's transport's to end."""
        self.stop()
        self._end_playback()

    def tick(self):
        if self._made is None:
            self._stop_timer()
            return
        super().tick()
        if not self.is_playing():
            self.stop()
