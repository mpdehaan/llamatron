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

"""A song measured from what it plays into the traits a style is described by, so that it can be fitted to any style and
compared with any song: the profile of a song, made from its performance."""

from dataclasses import dataclass, replace

from llamatron.genres.hearing.counterpoint import voice_leading_of
from llamatron.genres.hearing.harmony import harmony_of, modulation_of
from llamatron.genres.hearing.hooks import hook_of
from llamatron.genres.hearing.lines import bass_of, bottom_line, expectation_of, melody_of, phrasing_of, top_line, vocal_of
from llamatron.genres.hearing.performance import PlayedTrack
from llamatron.genres.hearing.rhythm import drums_of, groove_of
from llamatron.genres.hearing.roles import roles_of, tracks_in_role
from llamatron.genres.hearing.spacing import spacing_of
from llamatron.genres.hearing.transitions import transitions_of
from llamatron.genres.hearing.shape import bar_energy, energy_of, familiarity_of, shape_of, texture_of
from llamatron.genres.hearing.sonorities import BAR_SPAN, CHORDAL, PLANING, RICH, WHOLE_TONE, sonorities_of
from llamatron.genres.measures.subject import Basis, Evidence, Subject, SubjectKind
from llamatron.genres.measures.traits import BassMotion, Meter, Role, Sounds, Tempo, Trait


@dataclass(slots=True, kw_only=True, frozen=True)
class SongProfile(Subject):
    """A song as the library sees it: its name, its traits measured from its notes, the role each track plays, the keys it
    moves through, its shape over time, how its parts are spaced in pitch, and how it moves from scene to scene; as a subject,
    a song or a stretch of one, every value of which was heard from its own notes."""

    name: str
    traits: dict
    roles: dict
    keys: tuple
    shape: object
    spacing: object
    transitions: tuple
    kind: str = SubjectKind.SONG

    def trait(self, name):
        return self.traits.get(name)

    def evidence_of(self, name):
        return Evidence(basis=Basis.HEARD, origin=self.name)


def sounds_of(roles):
    """Return the General MIDI sounds the song gives each role."""
    result = {}
    for track, role in roles.items():
        if track.sound is not None and role != Role.DRUMS:
            result.setdefault(role, ())
            result[role] = tuple(dict.fromkeys(result[role] + (track.sound,)))
    return Sounds(roles=result)


# A part whose notes sit on average below this MIDI number can be heard as the bass when no part plays one, as a piano's left hand.
LOW_REGISTER = 55
# Middle C, below which the lowest line of a part holding both hands is taken for the left hand, when at least this share of
# the line lies there.
HANDS_SPLIT = 60
LEFT_HAND_SHARE = 0.33


def bass_track(*, roles, performance):
    """Return the track heard as the bass: the one playing that role, or, when none does, the lowest line of the lowest-sounding
    part other than the lead, as a piano's left hand is heard (the lead itself when it is the only part, a piano played as one);
    or None when nothing sits low enough. Two hands written in one part sit higher on average than a left hand alone, so there
    the notes of the lowest line below middle C are the bass, when they are a fair share of it."""
    basses = tracks_in_role(roles=roles, role=Role.BASS)
    if basses:
        return basses[0]
    melodic = [track for track in performance.melodic() if roles.get(track) != Role.LEAD] or performance.melodic()
    if not melodic:
        return None
    lines = {track: bottom_line(track) for track in melodic}
    low = min(melodic, key=lambda track: sum(note.pitch for note in lines[track]) / len(lines[track]))
    line = lines[low]
    if sum(note.pitch for note in line) / len(line) >= LOW_REGISTER:
        line = [note for note in line if note.pitch < HANDS_SPLIT]
        if len(line) < len(lines[low]) * LEFT_HAND_SHARE:
            return None
    return PlayedTrack(name=low.name, drum=False, sound=low.sound, notes=tuple(line))


class Listening:
    """One hearing of a performance: each trait is heard on its own by the method HEARERS names for it, and what several
    traits are heard from (the roles, the lead's line, its phrases, the keys, the drums, the energy bar by bar) is worked out
    once, when first asked for, and kept. So one measure can be heard without the rest, and a new trait is one more method."""

    __slots__ = ('performance', 'kept')

    def __init__(self, performance):
        self.performance = performance
        self.kept = {}

    def remembered(self, *, key, compute):
        if key not in self.kept:
            self.kept[key] = compute()
        return self.kept[key]

    def roles(self):
        return self.remembered(key=self.roles, compute=lambda: roles_of(self.performance))

    def lead(self):
        """Return the track that plays the lead, or None."""
        leads = tracks_in_role(roles=self.roles(), role=Role.LEAD)
        return leads[0] if leads else None

    def line(self):
        """Return the lead's line, its top notes in order."""
        return self.remembered(key=self.line, compute=lambda: top_line(self.lead()) if self.lead() is not None else [])

    def melody_and_phrases(self):
        return self.remembered(key=self.melody_and_phrases, compute=lambda: melody_of(line=self.line(), beats_per_bar=self.performance.beats_per_bar))

    def phrases(self):
        return self.melody_and_phrases()[1]

    def harmony_and_keys(self):
        return self.remembered(key=self.harmony_and_keys, compute=lambda: harmony_of(performance=self.performance, roles=self.roles(), lead=self.lead()))

    def keys(self):
        return self.harmony_and_keys()[1]

    def levels_and_parts(self):
        """Return the energy and the parts sounding, bar by bar."""
        return self.remembered(key=self.levels_and_parts, compute=lambda: bar_energy(performance=self.performance))

    def levels(self):
        return self.levels_and_parts()[0]

    def tempo(self):
        return Tempo(low=self.performance.tempo, high=self.performance.tempo)

    def meter(self):
        return Meter(usual=self.performance.meter, others=(), changes=0.0)

    def sonorities(self):
        return self.remembered(key=self.sonorities, compute=lambda: sonorities_of(self.performance))

    def harmony(self):
        found = self.sonorities()
        return replace(self.harmony_and_keys()[0], rich=found.get(RICH), planing=found.get(PLANING), whole_tone=found.get(WHOLE_TONE))

    def modulation(self):
        return modulation_of(keys=self.keys())

    def drums(self):
        return self.remembered(key=self.drums, compute=lambda: drums_of(self.performance))

    def groove(self):
        return groove_of(performance=self.performance, drums=self.drums())

    def bass(self):
        bass = bass_of(track=bass_track(roles=self.roles(), performance=self.performance), performance=self.performance)
        return bass if bass.motion == BassMotion.NONE else replace(bass, bar_span=self.sonorities().get(BAR_SPAN))

    def melody(self):
        return self.melody_and_phrases()[0]

    def expectation(self):
        return expectation_of(phrases=self.phrases(), line=self.line(), bars_heard=familiarity_of(self.performance))

    def phrasing(self):
        return phrasing_of(line=self.line(), phrases=self.phrases(), length=self.performance.length)

    def hook(self):
        return hook_of(performance=self.performance, levels=self.levels(), roles=self.roles())

    def voice_leading(self):
        return voice_leading_of(self.performance)

    def vocal(self):
        lead = self.lead()
        return vocal_of(line=self.line(), melody=self.melody(), phrases=self.phrases(), sound=lead.sound if lead is not None else None,
                        beats_per_bar=self.performance.beats_per_bar)

    def texture(self):
        return replace(texture_of(performance=self.performance, roles=self.roles(), parts=self.levels_and_parts()[1]), chordal=self.sonorities().get(CHORDAL))

    def sounds(self):
        return sounds_of(self.roles())

    def energy(self):
        return energy_of(self.levels())

    def unheard(self):
        """Return None, for a trait the analyzer doesn't find in a song yet."""
        return None

    def trait(self, name):
        """Return one trait, heard from the performance."""
        return HEARERS[name](self)

    def traits(self):
        """Return every trait, heard from the performance, in the order the traits are compared."""
        return {name: self.trait(name) for name in HEARERS}

    def shape(self):
        return shape_of(levels=self.levels(), performance=self.performance)

    def spacing(self):
        return spacing_of(performance=self.performance, roles=self.roles())

    def transitions(self):
        return transitions_of(performance=self.performance, levels=self.levels())


# How each trait is heard from a performance.
HEARERS = {
    Trait.TEMPO: Listening.tempo,
    Trait.METER: Listening.meter,
    Trait.HARMONY: Listening.harmony,
    Trait.MODULATION: Listening.modulation,
    Trait.DRUMS: Listening.drums,
    Trait.GROOVE: Listening.groove,
    Trait.BASS: Listening.bass,
    Trait.MELODY: Listening.melody,
    Trait.EXPECTATION: Listening.expectation,
    Trait.PHRASING: Listening.phrasing,
    Trait.HOOK: Listening.hook,
    Trait.VOICE_LEADING: Listening.voice_leading,
    Trait.VOCAL: Listening.vocal,
    Trait.TEXTURE: Listening.texture,
    Trait.SOUNDS: Listening.sounds,
    Trait.ENERGY: Listening.energy,
    Trait.FORM: Listening.unheard,
    Trait.SOLOS: Listening.unheard,
}


def profile_of_performance(*, performance, name, kind=SubjectKind.SONG):
    """Return the profile of a song's performance, or of a stretch of one when the kind says so."""
    heard = Listening(performance)
    return SongProfile(name=name, traits=heard.traits(), roles=heard.roles(), keys=tuple(heard.keys()), shape=heard.shape(), spacing=heard.spacing(),
                       transitions=heard.transitions(), kind=kind)


