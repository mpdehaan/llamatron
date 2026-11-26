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

from llamatron.engine.generators.musician import model as musician_model, schema
from llamatron.engine.generators.musician.model import MusicianSetting
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
    PIANO: schema.BACKING_PIANO, ORGAN: schema.BACKING_ORGAN, GUITAR: schema.RHYTHM_GUITARIST, BASS: schema.BASSIST, STRINGS: schema.STRING_SECTION,
    VOICES: schema.BACKUP_SINGERS, HORNS: schema.HORN_SECTION, SYNTH: schema.BACKING_SYNTH,
}
LEADING = {PIANO: schema.LEAD_PIANO, ORGAN: schema.LEAD_ORGAN, GUITAR: schema.LEAD_GUITARIST, BASS: schema.BASSIST, SYNTH: schema.LEAD_SYNTH}
# The musician a player is where the sound says nothing, by the player's instrument in the band.
BACKING_PLAYERS = {players.BASS: schema.BASSIST, players.RHYTHM: schema.RHYTHM_GUITARIST, players.KEYS: schema.BACKING_PIANO}
LEADING_PLAYERS = {players.BASS: schema.BASSIST, players.LEAD: schema.LEAD_GUITARIST}


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
        return schema.BASSIST
    family = family_of(member.sound)
    if member.answers:
        return schema.ANSWERING_PLAYER
    if member.backing:
        return BACKING.get(family) or BACKING_PLAYERS.get(member.player, schema.BACKING_SYNTH)
    return LEADING.get(family) or LEADING_PLAYERS.get(member.player, schema.LEAD_SYNTH)


def usual_musician(member):
    """Return the settings of the musician a player is given: the instrument, for a player of lines giving way to nobody and the notes as written, and for a player of short notes the notes as written."""
    instrument = instrument_of(member)
    settings = {MusicianSetting.INSTRUMENT: instrument}
    if member.backing:
        if musician_model.usual_notes(instrument) == schema.SHORT_NOTES:
            # A figure written for the horns already says how long each stab is.
            settings[MusicianSetting.NOTES] = schema.AS_WRITTEN
        return settings
    gives_way = schema.GIVES_WAY_SOME if member.answers else schema.NO_GIVING_WAY
    if musician_model.usual_gives_way(instrument) != gives_way:
        settings[MusicianSetting.GIVES_WAY] = gives_way
    if musician_model.usual_notes(instrument) != schema.AS_WRITTEN:
        settings[MusicianSetting.NOTES] = schema.AS_WRITTEN
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
        settings = dict(own[drummer]) if drummer in own else {MusicianSetting.INSTRUMENT: schema.DRUMMER}
        settings.pop(MusicianSetting.TUNE_FROM, None)
        if tune_track is not None:
            settings[MusicianSetting.TUNE_FROM] = tune_track
        musicians[musician_name(drummer)] = settings
        of_track.update({piece: musician_name(drummer) for piece in drum_tracks})
    return musicians, of_track
