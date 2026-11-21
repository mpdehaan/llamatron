# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The musicians of a made song: for each player of the band, the Musician generator that plays the player's clips.

The arranger writes what each player plays; a Musician says how a player of that instrument
plays it in a band. Each player gets one, first in the chains of every clip of the player's
track, and the drummer's one plays every piece of the kit. Which musician a player is follows
the player's place in the band and the sound the player plays with: a backing player with an
organ sound is a backing organ, who holds each chord and plays softer under the tune. A
player who plays lines, the tune or a voice beside it, is told to give way to nobody and to
play its notes as written, since the lines were written to sound together.
"""

from llamatron.engine.generators.musician import generator as musician
from llamatron.engine.generators.musician.settings import MusicianSetting
from llamatron.user_strings import song_wizard as wizard_text
from llamatron.wizards.create_song import players

# The genres whose songs are given no musicians: their players are machines, played another way.
ELECTRONIC = 'Electronic'
EXPERIMENTAL = 'Experimental'
GENRES_WITHOUT_MUSICIANS = (ELECTRONIC, EXPERIMENTAL)

# The families of General MIDI sounds that say which musician plays them, each the first and the last sound's number.
PIANO = 'piano'
ORGAN = 'organ'
GUITAR = 'guitar'
BASS = 'bass'
STRINGS = 'strings'
VOICES = 'voices'
HORNS = 'horns'
SYNTH = 'synth'
FAMILIES = (
    (PIANO, 1, 8), (ORGAN, 17, 24), (GUITAR, 25, 32), (BASS, 33, 40), (STRINGS, 41, 52), (VOICES, 53, 55), (HORNS, 57, 72), (SYNTH, 81, 104),
)
# The musician who plays a family of sounds under the band, and the one who plays its lines.
BACKING = {
    PIANO: musician.BACKING_PIANO, ORGAN: musician.BACKING_ORGAN, GUITAR: musician.RHYTHM_GUITARIST, BASS: musician.BASSIST, STRINGS: musician.STRING_SECTION,
    VOICES: musician.BACKUP_SINGERS, HORNS: musician.HORN_SECTION, SYNTH: musician.BACKING_SYNTH,
}
LEADING = {PIANO: musician.LEAD_PIANO, ORGAN: musician.LEAD_ORGAN, GUITAR: musician.LEAD_GUITARIST, BASS: musician.BASSIST, SYNTH: musician.LEAD_SYNTH}
# The musician a player is where the sound says nothing, by the player's instrument in the band.
BACKING_PLAYERS = {players.BASS: musician.BASSIST, players.RHYTHM: musician.RHYTHM_GUITARIST, players.KEYS: musician.BACKING_PIANO}
LEADING_PLAYERS = {players.BASS: musician.BASSIST, players.LEAD: musician.LEAD_GUITARIST}


class BandMember:
    """One player of a made song's band, as the arranger knows the player: the track, the instrument in the band, whether the player backs the band with a figure,
    whether the player answers the tune, and the number of the General MIDI sound the player plays with, or None."""

    __slots__ = ('track', 'player', 'backing', 'answers', 'sound')

    def __init__(self, *, track, player, backing, answers, sound):
        self.track = track
        self.player = player
        self.backing = backing
        self.answers = answers
        self.sound = sound


def family_of(sound):
    """Return the family a General MIDI sound's number belongs to, or None for a sound of no family that names a musician."""
    if not isinstance(sound, int):
        return None
    return next((family for family, first, last in FAMILIES if first <= sound <= last), None)


def instrument_of(member):
    """Return the musician a player of the band is: by the sound, and where the sound says nothing by the player's instrument in the band."""
    if member.player == players.BASS:
        return musician.BASSIST
    family = family_of(member.sound)
    if member.answers:
        return musician.ANSWERING_PLAYER
    if member.backing:
        return BACKING.get(family) or BACKING_PLAYERS.get(member.player, musician.BACKING_SYNTH)
    return LEADING.get(family) or LEADING_PLAYERS.get(member.player, musician.LEAD_SYNTH)


def usual_musician(member):
    """Return the settings of the musician a player is given: the instrument, for a player of lines giving way to nobody and the notes as written, and for a player of short notes the notes as written."""
    instrument = instrument_of(member)
    settings = {MusicianSetting.INSTRUMENT: instrument}
    of_instrument = musician.MUSICIANS[instrument]
    if member.backing:
        if of_instrument.USUAL_NOTES == musician.SHORT_NOTES:
            # A figure written for the horns already says how long each stab is.
            settings[MusicianSetting.NOTES] = musician.AS_WRITTEN
        return settings
    gives_way = musician.GIVES_WAY_SOME if member.answers else musician.NO_GIVING_WAY
    if of_instrument.USUAL_GIVES_WAY != gives_way:
        settings[MusicianSetting.GIVES_WAY] = gives_way
    if of_instrument.USUAL_NOTES != musician.AS_WRITTEN:
        settings[MusicianSetting.NOTES] = musician.AS_WRITTEN
    return settings


def musician_name(role):
    """Return what the musician of a player is called, and the chain that runs it."""
    return wizard_text.MSG_MUSICIAN_NAME.format(role)


def band_of(*, members, drummer, drum_tracks, tune_track, own):
    """Return the musicians of a band, their settings by name, and the name of the musician of each track.

    Each member's musician is the usual one, or the song's own for the player in its place, and
    hears the tune on the tune's track, unless the track is the member's own. The drummer's one
    musician plays every drum track.
    """
    musicians = {}
    of_track = {}
    for member in members:
        settings = dict(own[member.track]) if member.track in own else usual_musician(member)
        settings.pop(MusicianSetting.TUNE_FROM, None)
        if tune_track is not None and tune_track != member.track:
            settings[MusicianSetting.TUNE_FROM] = tune_track
        musicians[musician_name(member.track)] = settings
        of_track[member.track] = musician_name(member.track)
    if drummer is not None and drum_tracks:
        settings = dict(own[drummer]) if drummer in own else {MusicianSetting.INSTRUMENT: musician.DRUMMER}
        settings.pop(MusicianSetting.TUNE_FROM, None)
        if tune_track is not None:
            settings[MusicianSetting.TUNE_FROM] = tune_track
        musicians[musician_name(drummer)] = settings
        of_track.update({piece: musician_name(drummer) for piece in drum_tracks})
    return musicians, of_track
