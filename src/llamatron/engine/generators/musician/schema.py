# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Musician plugin's schema: the players, instruments, activities and habits its settings may name, and their ranges, which its model checks, its editor offers and the song wizard writes."""

# The musicians, by the instrument each plays.
RHYTHM_GUITARIST = 'rhythm guitarist'
BASSIST = 'bassist'
DRUMMER = 'drummer'
BACKING_PIANO = 'backing piano'
BACKING_ORGAN = 'backing organ'
BACKING_SYNTH = 'backing synth'
LEAD_GUITARIST = 'lead guitarist'
LEAD_ORGAN = 'lead organ'
LEAD_PIANO = 'lead piano'
LEAD_SYNTH = 'lead synth'
ANSWERING_PLAYER = 'answering player'
BACKUP_SINGERS = 'backup singers'
HORN_SECTION = 'horn section'
STRING_SECTION = 'string section'
PERCUSSIONIST = 'percussionist'
# How much of a part a musician plays: fewer of its notes, all of them, or its long notes struck again.
SPARSE = 'sparse'
LIGHT = 'light'
AS_WRITTEN = 'as written'
BUSY = 'busy'
VERY_BUSY = 'very busy'
ACTIVITIES = (SPARSE, LIGHT, AS_WRITTEN, BUSY, VERY_BUSY)
# How loud a musician plays against the part as written, in steps, and what one step is in velocity.
QUIETEST = -3
LOUDEST = 3
# How far a loose musician's loudness wanders from note to note, in steps, and what one step is in velocity.
TIGHT = 0
LOOSEST = 3
# What a musician does while the tune sounds on another track.
NO_GIVING_WAY = 'none'
GIVES_WAY_SOME = 'some'
GIVES_WAY_OFTEN = 'often'
IN_THE_GAPS = 'plays in the gaps'
GIVES_WAY = (NO_GIVING_WAY, GIVES_WAY_SOME, GIVES_WAY_OFTEN, IN_THE_GAPS)
# Which notes of a bar a musician leans on.
NO_ACCENTS = 'none'
DOWNBEAT = 'downbeat'
BACKBEAT = 'backbeat'
OFFBEATS = 'offbeats'
ACCENTS = (NO_ACCENTS, DOWNBEAT, BACKBEAT, OFFBEATS)
# How a musician's notes are held: as the part writes them, each until the next, or short.
HELD_NOTES = 'held'
SHORT_NOTES = 'short'
NOTE_LENGTHS = (AS_WRITTEN, HELD_NOTES, SHORT_NOTES)
# Where on the instrument a musician plays: as written, or an octave lower or higher, always inside what the instrument can play.
LOW = 'low'
HIGH = 'high'
RANGES = (LOW, AS_WRITTEN, HIGH)
# What a musician does with its part in a kind of section.
WHOLE = 'whole'
SOFTER = 'softer'
THINNED = 'thinned'
HEAD_ONLY = 'head only'
MUTED = 'muted'
HITS = 'hits'
FORMS = (WHOLE, SOFTER, THINNED, HEAD_ONLY, MUTED, HITS)
# The settings a kind of section has of its own.
PLAYS = 'plays'
PLAYED = 'played'
# Every instrument a musician plays, in the order they are offered.
INSTRUMENTS = (
    RHYTHM_GUITARIST, BASSIST, DRUMMER, BACKING_PIANO, BACKING_ORGAN, BACKING_SYNTH, LEAD_GUITARIST, LEAD_ORGAN, LEAD_PIANO, LEAD_SYNTH,
    ANSWERING_PLAYER, BACKUP_SINGERS, HORN_SECTION, STRING_SECTION, PERCUSSIONIST,
)
