# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the tracks of a song played, as other tracks' clips read it while the Realizer plays them: the notes a clip grabs from
another track, the chords and the tune it follows, and the notes a generator deals out among the clips naming it."""

import contextlib

from llamatron.engine.generators import registry
from llamatron.engine.realizer.chord_source import ChordSource
from llamatron.engine.realizer.dealing_place import DealingPlace
from llamatron.engine.realizer.grab_source import GrabSource
from llamatron.engine.realizer.tune_source import TuneSource
from llamatron.engine.timing.handed_note import HandedNote
from llamatron.engine.timing.timing import timed_events
from llamatron.model.file.song_file_error import SongFileError
from llamatron.user_strings import errors, marks

# The controller's method that deals a track's notes out among the clips naming its generator.
DEALS_NOTES = 'notes_dealt'


class TrackOutput:
    """What every track of one render played, as the clips that read another track's notes find it, each answer worked out
    once for a written-out scene and kept, and the tracks waiting on one another, which finds a circle of them."""

    __slots__ = ('_realizer', '_song', '_grabbing', '_following', '_chord_sources', '_tune_sources', '_dealt', '_source_turns')

    def __init__(self, *, realizer, song):
        self._realizer = realizer
        self._song = song
        # The tracks whose clips are waiting on a grab, to catch clips that grab in a circle.
        self._grabbing = []
        # The clips waiting on the chords or tune of a track they follow, as (scene, track), to catch tracks following each other in a circle.
        self._following = []
        # What each followed track plays in each written scene, its chords and its tune, the notes each generator that deals notes out hands each
        # track, and each source track's notes as turns, each worked out once.
        self._chord_sources = {}
        self._tune_sources = {}
        self._dealt = {}
        self._source_turns = {}

    def take_scenes(self, *, earlier, kept):
        """Take what an earlier render's output worked out about the written scenes that kept says to keep, a function of a key's scene number."""
        self._dealt = {key: value for key, value in earlier._dealt.items() if kept(key[0])}
        self._source_turns = {key: value for key, value in earlier._source_turns.items() if kept(key[0])}
        self._chord_sources = {key: value for key, value in earlier._chord_sources.items() if kept(key[0])}
        self._tune_sources = {key: value for key, value in earlier._tune_sources.items() if kept(key[0])}

    def forget_scene(self, number):
        """Forget the chords and tunes other clips followed in a written scene, worked out while how long it lasts was a guess."""
        for kept in (self._chord_sources, self._tune_sources):
            for key in [key for key in kept if key[0] == number]:
                del kept[key]

    @contextlib.contextmanager
    def grabs_set_aside(self):
        """Set the clips waiting on grabs aside while earlier clips are worked out, since a clip before can't be part of a grab circle with this one."""
        waiting = self._grabbing
        self._grabbing = []
        try:
            yield
        finally:
            self._grabbing = waiting

    def deals_out(self, scene):
        """Return whether a clip of a written scene runs a generator that deals a track's notes out among the clips naming it."""
        return any(registry.fills(name=step.kind, method=DEALS_NOTES) for track in scene.get_track_names() for step in self._realizer.chain_steps(scene=scene, track=track))

    def handed_notes(self, *, scene, track):
        """Return the notes the generators a track's clip names deal it in a written-out scene, in time order, or none."""
        handed = []
        for step in self._dealing_steps(scene=scene, track=track):
            handed += self.notes_dealt(scene=scene, step=step).get(track, [])
        return sorted(handed)

    def _dealing_steps(self, *, scene, track):
        """Return the steps of a track's clip's chains in a written-out scene whose generators deal notes out, each generator once, in order."""
        steps = [step for step in self._realizer.chain_steps(scene=scene, track=track) if registry.fills(name=step.kind, method=DEALS_NOTES)]
        return list(dict.fromkeys(steps))

    def tracks_naming(self, *, scene, name):
        """Return the tracks whose clips' chains name a generator in a written-out scene, in the song's track order."""
        return [track for track in self._song.get_track_names() if self._names_generator(scene=scene, track=track, name=name)]

    def _names_generator(self, *, scene, track, name):
        """Return whether a track's clip's chains name a generator in a written-out scene."""
        return any(step.name == name for step in self._realizer.chain_steps(scene=scene, track=track))

    def notes_dealt(self, *, scene, step):
        """Return the notes a generator that deals notes out hands each track in a written-out scene, by the track, worked out once for the scene."""
        key = (scene.get_number(), step.name)
        if key not in self._dealt:
            settings = self._song.get_generator_settings(kind=step.kind, name=step.name)
            self._dealt[key] = registry.controller_of(step.kind).notes_dealt(settings=settings, place=DealingPlace(realizer=self._realizer, output=self, scene=scene, name=step.name))
        return self._dealt[key]

    def plays_source(self, *, scene, source):
        """Return whether a source track of notes dealt out is a track of the song with a clip in a written-out scene."""
        return source in self._song.get_track_names() and scene.get_clip_slot(source) is not None

    def source_turns(self, *, scene, source):
        """Return a source track's notes in a written-out scene as turns: the notes that start together, each a HandedNote, in time order, before any groove."""
        key = (scene.get_number(), source)
        if key not in self._source_turns:
            clip = self._realizer.get_clip(scene=scene, track=source)
            notes, _ = timed_events(clip=clip, scale=clip.get_scale(), grooved=False)
            turns = {}
            for note in sorted(notes):
                turns.setdefault(note.start, []).append(HandedNote(note.start, note.end, note.midi_number, note.velocity))
            self._source_turns[key] = list(turns.values())
        return self._source_turns[key]

    def get_grab_source(self, *, scene, track):
        """Return the notes the track that a track's clip slot grabs from plays in a scene, or None if it plays nothing there."""
        other = scene.get_clip_slot(track).get_grab_track()
        if scene.get_clip_slot(other) is None:
            return None
        waiting = [*self._grabbing, track]
        if other in waiting:
            raise SongFileError(errors.ERR_CIRCULAR_GRAB.format(scene=scene.describe(), loop=_grab_loop(waiting=waiting, track=other)))
        self._grabbing.append(track)
        try:
            source = self._realizer.get_clip(scene=scene, track=other)
        finally:
            self._grabbing.pop()
        return GrabSource(source)

    def chords_followed(self, *, scene, track, source, counting):
        """Return the chords a track followed plays in a written-out scene, after its own chains, or None when it plays nothing there, is no track of the song or is the track that follows.

        In the pass that counts register changes the chords are read from that pass's clip, played
        without grabs or register values, since no finished clip can be had yet.
        """
        if source is None or source == track or source not in self._song.get_track_names() or scene.get_clip_slot(source) is None:
            return None
        key = (scene.get_number(), source, counting)
        if key not in self._chord_sources:
            waiting = [*self._following, (scene.get_number(), track)]
            if (scene.get_number(), source) in waiting:
                tracks = [name for _, name in waiting[waiting.index((scene.get_number(), source)):]]
                raise SongFileError(errors.ERR_CIRCULAR_FOLLOW.format(scene=scene.describe(), loop=marks.MSG_CIRCLE_ARROW.join([*tracks, source])))
            self._following.append((scene.get_number(), track))
            try:
                clip = self._realizer.counted_clip(scene=scene, track=source)[0] if counting else self._realizer.get_clip(scene=scene, track=source)
            finally:
                self._following.pop()
            self._chord_sources[key] = ChordSource(clip)
        return self._chord_sources[key]

    def tune_heard(self, *, scene, track, source, counting):
        """Return when the tune sounds on the track a musician reads it from, in a written-out scene, after that track's own chains, or None when the track plays nothing there, is no track of the song or is the musician's own.

        The track's finished clip is found as a followed track's chords are, so tracks that read each other in a circle are refused the same way.
        """
        if source is None or source == track or source not in self._song.get_track_names() or scene.get_clip_slot(source) is None:
            return None
        key = (scene.get_number(), source, counting)
        if key not in self._tune_sources:
            waiting = [*self._following, (scene.get_number(), track)]
            if (scene.get_number(), source) in waiting:
                tracks = [name for _, name in waiting[waiting.index((scene.get_number(), source)):]]
                raise SongFileError(errors.ERR_CIRCULAR_FOLLOW.format(scene=scene.describe(), loop=marks.MSG_CIRCLE_ARROW.join([*tracks, source])))
            self._following.append((scene.get_number(), track))
            try:
                clip = self._realizer.counted_clip(scene=scene, track=source)[0] if counting else self._realizer.get_clip(scene=scene, track=source)
            finally:
                self._following.pop()
            self._tune_sources[key] = TuneSource(clip)
        return self._tune_sources[key]

def _grab_loop(*, waiting, track):
    """Return the tracks that grab from each other in a circle, from where the circle starts, like a → b → a."""
    return marks.MSG_CIRCLE_ARROW.join([*waiting[waiting.index(track):], track])
