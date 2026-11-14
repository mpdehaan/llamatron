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

"""A MIDI file as the analyzer hears it: every channel's notes in beats, the drums on General MIDI's channel 10, each channel's
sound the program its notes play under, the tempo and the time signature the ones held longest, its length in seconds by every
tempo it passes through, and its tracks tidied (hearing/cleaning.py), so that a song from anywhere is measured as llamatron's
own are. Read with mido, which the tracker already needs, so the explain tool needs nothing more."""

from collections import Counter

import mido

from llamatron.genres.hearing.cleaning import tidied
from llamatron.genres.hearing.performance import Performance, PlayedNote, PlayedTrack
from llamatron.strings.genres import MSG_DOUBT_METERS, MSG_DOUBT_TEMPOS, MSG_GENRE_LIST_JOIN

# General MIDI's drum channel, counted from 0 as mido counts.
DRUM_CHANNEL = 9
MICROSECONDS_IN_A_MINUTE = 60_000_000
DEFAULT_TEMPO = 120
DEFAULT_SIGNATURE = (4, 4)
SECONDS_IN_A_MINUTE = 60.0
QUARTERS_IN_A_WHOLE = 4
CHANNEL_NAME = 'channel {number}'
UNNAMED = ''
# The kinds of MIDI message the reading uses, as mido names them.
TRACK_NAME_MESSAGE = 'track_name'
TEMPO_MESSAGE = 'set_tempo'
TIME_SIGNATURE_MESSAGE = 'time_signature'
PROGRAM_MESSAGE = 'program_change'
NOTE_ON = 'note_on'
NOTE_OFF = 'note_off'
# General MIDI's pianos, numbered from 1, and the word a track named for a piano holds: a piano's two staves are often written as
# two tracks, which are almost certainly one player, so they are read as one part (the user's direction).
PIANO_PROGRAMS = range(1, 9)
PIANO_WORD = 'piano'
PIANO_PART = 'piano'
METER_TEXT = '{numerator}/{denominator}'


def is_piano(track):
    return not track.drum and (track.sound in PIANO_PROGRAMS or PIANO_WORD in track.name.lower())


def merged_pianos(tracks):
    """Return the tracks with every piano track joined into one part, a piano's staves being one player; a file with one piano
    track or none is left as it is."""
    pianos = [track for track in tracks if is_piano(track)]
    if len(pianos) < 2:
        return tuple(tracks)
    notes = tuple(sorted((note for track in pianos for note in track.notes), key=lambda note: (note.begins, note.pitch)))
    joined = PlayedTrack(name=PIANO_PART, drum=False, sound=pianos[0].sound, notes=notes)
    return tuple([joined] + [track for track in tracks if not is_piano(track)])


def sound_of(played):
    """Return the General MIDI sound a channel plays, counted from 1: the program most of its notes sounded under, never the
    first program the file names, since many files reset every channel to program 0, a piano, before choosing its sound."""
    return played.most_common(1)[0][0] if played else None


def held_longest(*, changes, end):
    """Return the value a file holds longest among changes of something, each a tick and a value, or None where there are
    none: many files open with a default for a beat or less before setting their own, so the first is not the song's."""
    lasting = Counter()
    for (start, value), (stop, _) in zip(changes, changes[1:] + [(max(end, changes[-1][0] + 1) if changes else end, None)]):
        lasting[value] += max(stop - start, 0)
    return lasting.most_common(1)[0][0] if lasting else None


def longest_tempo(*, tempos, end):
    """Return the tempo a file holds longest, in beats a minute, or None where it names none."""
    return held_longest(changes=tempos, end=end)


def seconds_at(*, tempos, tick, ticks):
    """Return how many seconds into a file a tick falls, by every tempo passed on the way, the default tempo until the first."""
    seconds = 0.0
    now = 0
    tempo = DEFAULT_TEMPO
    for start, value in sorted(tempos):
        if start >= tick:
            break
        seconds += (start - now) / ticks * SECONDS_IN_A_MINUTE / tempo
        now = start
        tempo = value
    return seconds + (tick - now) / ticks * SECONDS_IN_A_MINUTE / tempo


def changes_of(values):
    """Return how many times a list of changes moves to a different value."""
    return sum(1 for (_, earlier), (_, later) in zip(values, values[1:]) if earlier != later)


def performance_of_midi(path):
    """Return a MIDI file as a performance: a track for each channel used, named after the track it came from where that has a
    name, its notes in beats from the start, its program as its General MIDI sound counted from 1, the tracks tidied."""
    # A file written carelessly may hold a data byte past 127, which mido refuses unless told to clip it; such files play
    # everywhere, so they are read, the byte held to 127.
    song = mido.MidiFile(str(path), clip=True)
    ticks = float(song.ticks_per_beat)
    sounding = {}
    notes = {}
    # The program in force on each channel as the file is read, and how many notes each channel played under each program.
    current = {}
    played = {}
    tempos = []
    meters = []
    names = {}
    for track in song.tracks:
        time = 0
        track_name = UNNAMED
        for message in track:
            time += message.time
            if message.type == TRACK_NAME_MESSAGE:
                track_name = message.name.strip()
            elif message.type == TEMPO_MESSAGE:
                tempos.append((time, round(MICROSECONDS_IN_A_MINUTE / message.tempo)))
            elif message.type == TIME_SIGNATURE_MESSAGE:
                meters.append((time, (message.numerator, message.denominator)))
            elif message.type == PROGRAM_MESSAGE:
                current[message.channel] = message.program + 1
            elif message.type == NOTE_ON and message.velocity > 0:
                sounding.setdefault((message.channel, message.note), []).append((time, message.velocity))
                played.setdefault(message.channel, Counter())[current.get(message.channel)] += 1
                if track_name:
                    names.setdefault(message.channel, track_name)
            elif message.type in (NOTE_OFF, NOTE_ON):
                started = sounding.get((message.channel, message.note))
                if started:
                    start, velocity = started.pop(0)
                    notes.setdefault(message.channel, []).append(PlayedNote(start=start / ticks, end=max(time, start + 1) / ticks, pitch=message.note, velocity=velocity))
    tempos.sort()
    meters.sort()
    last_tick = max((note.ends for found in notes.values() for note in found), default=0.0) * ticks
    numerator, denominator = held_longest(changes=meters, end=last_tick) or DEFAULT_SIGNATURE
    beats_per_bar = numerator * QUARTERS_IN_A_WHOLE / denominator
    raw = [PlayedTrack(name=names.get(channel) or CHANNEL_NAME.format(number=channel + 1), drum=channel == DRUM_CHANNEL,
                       sound=None if channel == DRUM_CHANNEL else sound_of(played.get(channel)), notes=tuple(sorted(found, key=lambda note: (note.begins, note.pitch))))
           for channel, found in sorted(notes.items())]
    tidy, doubts = tidied(tracks=raw, beats_per_bar=beats_per_bar)
    tracks = merged_pianos(tidy)
    length = max(max((note.ends for track in tracks for note in track.notes), default=beats_per_bar), beats_per_bar)
    doubts = list(doubts)
    if changes_of(tempos):
        doubts.append(MSG_DOUBT_TEMPOS.format(count=changes_of(tempos)))
    if changes_of(meters):
        doubts.append(MSG_DOUBT_METERS.format(meters=MSG_GENRE_LIST_JOIN.join(dict.fromkeys(METER_TEXT.format(numerator=top, denominator=bottom) for _, (top, bottom) in meters))))
    return Performance(tracks=tracks, tempo=longest_tempo(tempos=tempos, end=length * ticks) or DEFAULT_TEMPO, meter=METER_TEXT.format(numerator=numerator, denominator=denominator),
                       beats_per_bar=beats_per_bar, length=length, seconds=seconds_at(tempos=tempos, tick=length * ticks, ticks=ticks), doubts=tuple(doubts))
