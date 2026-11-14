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

"""Tidying the tracks of a song that came from anywhere, before anything is measured: a MIDI file made by a fan is chaotic,
and the measures are only as good as the parts they are given. Notes written twice are dropped, a note left sounding is cut, a
track holding a credit or a test is dropped, General MIDI's sound effects are dropped, and percussion on an ordinary channel
(a track of one drum, a percussive program, a track named for a drum) joins the drums, each hit on the drum it most likely is.
Whatever was done is said, as doubts, so that an opinion can say how sure it is of the parts. A song llamatron rendered needs
none of this and is never passed through it."""

from dataclasses import replace
from statistics import median

from llamatron.genres.hearing.performance import PlayedNote, PlayedTrack
from llamatron.strings.genres import (
    MSG_DOUBT_DUPLICATES, MSG_DOUBT_EFFECTS, MSG_DOUBT_JUNK, MSG_DOUBT_NO_KICK, MSG_DOUBT_ONE_DRUM, MSG_DOUBT_PERCUSSION, MSG_DOUBT_STUCK, MSG_GENRE_LIST_JOIN,
)

# A track playing this few notes holds a credit, a count-in or a test, not a part, where the busiest track plays at least
# BUSIER times as many: a short piece's parts are all small, and are kept.
JUNK_NOTES = 4
BUSIER = 10
# A note sounding longer than this many bars was left on by mistake, and is cut to one bar; a drum hit lasts no longer than a beat.
STUCK_BARS = 16
CUT_TO_BARS = 1
# Two hits of one drum closer than this many beats are one hit written twice, and fewer duplicates than WORTH_SAYING go unsaid.
SAME_HIT_BEATS = 0.03
WORTH_SAYING = 10
DRUM_HIT_BEATS = 1.0
# General MIDI's percussive programs and its sound effects, counted from 1.
PERCUSSION_PROGRAMS = range(113, 121)
EFFECT_PROGRAMS = range(121, 129)
# A track of this few pitches and at least this many notes, above the bass register, is one drum hit over and over.
ONE_DRUM_PITCHES = 1
ENOUGH_HITS = 16
ABOVE_THE_BASS = 55
# General MIDI's drum notes.
KICK = 36
ACOUSTIC_KICK = 35
SNARE = 38
CLAP = 39
CLOSED_HAT = 42
LOW_TOM = 45
CRASH = 49
RIDE = 51
TAMBOURINE = 54
COWBELL = 56
CONGA = 63
AGOGO = 67
SHAKER = 70
WOODBLOCK = 76
TRIANGLE = 81
KICKS = (ACOUSTIC_KICK, KICK)
# The drum a track is, by a word in its name, the longer words first so that "bass drum" is found before "bass".
DRUM_WORDS = (('bass drum', KICK), ('kick', KICK), ('snare', SNARE), ('clap', CLAP), ('hi-hat', CLOSED_HAT), ('hihat', CLOSED_HAT), ('hat', CLOSED_HAT),
              ('ride', RIDE), ('cymbal', CRASH), ('crash', CRASH), ('tom', LOW_TOM), ('tamb', TAMBOURINE), ('cowbell', COWBELL), ('conga', CONGA),
              ('bongo', CONGA), ('shaker', SHAKER), ('woodblock', WOODBLOCK), ('triangle', TRIANGLE), ('drum', SNARE), ('perc', COWBELL))
# The drum a percussive program most likely stands for, where the track's name says nothing.
DRUM_OF_PROGRAM = {113: TRIANGLE, 114: AGOGO, 115: COWBELL, 116: WOODBLOCK, 117: LOW_TOM, 118: LOW_TOM, 119: SNARE, 120: CRASH}
DRUMS_NAME = 'drums'


def drum_named(name):
    """Return the drum a track's name says it is, or None where its name names no drum."""
    lowered = name.lower()
    return next((drum for word, drum in DRUM_WORDS if word in lowered), None)


def without_duplicates(track):
    """Return a track with each note kept once: the same pitch starting at the same moment twice is one note written twice,
    and so are two hits of one drum a hair apart."""
    apart = SAME_HIT_BEATS if track.drum else 0.0
    last = {}
    notes = []
    for note in track.notes:
        if note.pitch not in last or note.begins - last[note.pitch] > apart:
            notes.append(note)
        last[note.pitch] = note.begins
    return replace(track, notes=tuple(notes))


def cut(*, note, beats):
    return PlayedNote(start=note.start, end=note.start + beats, pitch=note.pitch, velocity=note.velocity)


def without_stuck(*, track, beats_per_bar):
    """Return a track with no note left sounding: a drum hit held to a beat, and any other note longer than STUCK_BARS cut to
    a bar, so that one forgotten note-off can't double a song's length."""
    if track.drum:
        return replace(track, notes=tuple(note if note.length() <= DRUM_HIT_BEATS else cut(note=note, beats=DRUM_HIT_BEATS) for note in track.notes))
    longest = STUCK_BARS * float(beats_per_bar)
    return replace(track, notes=tuple(note if note.length() <= longest else cut(note=note, beats=CUT_TO_BARS * float(beats_per_bar)) for note in track.notes))


def is_junk(*, track, busiest):
    return len(track.notes) <= JUNK_NOTES and busiest >= BUSIER * max(len(track.notes), 1)


def is_effect(track):
    return not track.drum and track.sound in EFFECT_PROGRAMS


def is_percussion(track):
    """Return whether a track on an ordinary channel is percussion: it plays a percussive program, it is named for a drum and
    plays one pitch or two, or it is one pitch above the bass register struck many times."""
    if track.drum or not track.notes:
        return False
    pitches = {note.pitch for note in track.notes}
    if track.sound in PERCUSSION_PROGRAMS:
        return True
    if drum_named(track.name) is not None and len(pitches) <= ONE_DRUM_PITCHES + 1:
        return True
    return len(pitches) <= ONE_DRUM_PITCHES and len(track.notes) >= ENOUGH_HITS and median(note.pitch for note in track.notes) >= ABOVE_THE_BASS


def as_drum_hits(track):
    """Return a percussion track's notes as hits on the drum the track most likely is: by its name, then by its program, then
    the cowbell, a drum that reads as percussion and as nothing else."""
    drum = drum_named(track.name) or DRUM_OF_PROGRAM.get(track.sound, COWBELL)
    return [PlayedNote(start=note.start, end=note.start + min(note.length(), DRUM_HIT_BEATS), pitch=drum, velocity=note.velocity) for note in track.notes]


def changed(*, before, after):
    return sum(len(track.notes) for track in before) - sum(len(track.notes) for track in after)


def drum_doubts(tracks):
    """Return what is doubtful about the drums as they stand: a kit of one drum, or a kit with no kick."""
    hits = [note.pitch for track in tracks if track.drum for note in track.notes]
    if not hits:
        return []
    if len(set(hits)) == 1:
        return [MSG_DOUBT_ONE_DRUM]
    return [] if any(kick in hits for kick in KICKS) else [MSG_DOUBT_NO_KICK]


def tidied(*, tracks, beats_per_bar):
    """Return a song's tracks tidied and what was doubtful about them, as sentences: duplicates dropped, stuck notes cut, tracks
    of a few notes and sound effects dropped, and percussion on ordinary channels joined to the drums."""
    doubts = []
    once = [without_duplicates(track) for track in tracks]
    if changed(before=tracks, after=once) >= WORTH_SAYING:
        doubts.append(MSG_DOUBT_DUPLICATES.format(count=changed(before=tracks, after=once)))
    held = [without_stuck(track=track, beats_per_bar=beats_per_bar) for track in once]
    stuck = sum(1 for before, after in zip(once, held) for old, new in zip(before.notes, after.notes) if old.ends != new.ends and not before.drum)
    if stuck:
        doubts.append(MSG_DOUBT_STUCK.format(count=stuck))
    busiest = max((len(track.notes) for track in held), default=0)
    junk = [track for track in held if is_junk(track=track, busiest=busiest)]
    if junk:
        doubts.append(MSG_DOUBT_JUNK.format(count=len(junk)))
    effects = [track for track in held if is_effect(track) and track not in junk]
    if effects:
        doubts.append(MSG_DOUBT_EFFECTS.format(names=MSG_GENRE_LIST_JOIN.join(track.name for track in effects)))
    kept = [track for track in held if track not in junk and not is_effect(track)]
    percussion = [track for track in kept if is_percussion(track)]
    if percussion:
        doubts.append(MSG_DOUBT_PERCUSSION.format(names=MSG_GENRE_LIST_JOIN.join(track.name for track in percussion)))
    drums = [track for track in kept if track.drum]
    hits = [note for track in drums for note in track.notes] + [hit for track in percussion for hit in as_drum_hits(track)]
    parts = [track for track in kept if not track.drum and not is_percussion(track)]
    if hits:
        name = drums[0].name if drums else DRUMS_NAME
        parts.append(without_duplicates(PlayedTrack(name=name, drum=True, sound=None, notes=tuple(sorted(hits, key=lambda note: (note.begins, note.pitch))))))
    return tuple(parts), tuple(doubts + drum_doubts(parts))
