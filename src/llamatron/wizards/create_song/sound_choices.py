# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's choices of the sounds: the band's Sounds, which every player follows, and a player's own General MIDI sound."""

from llamatron.model.schema import limits
from llamatron.user_strings import errors, labels as labels_text
from llamatron.wizards.create_song import arranger, wizard_limits
from llamatron.wizards.create_song.arranger import values_of
from llamatron.wizards.create_song.choices_part import ChoicesPart, chosen_only


def family_of(sound):
    """Return the place of the General MIDI family a sound is in."""
    return (sound - limits.MIN_GM_SOUND) // limits.GM_FAMILY_SIZE


def _add_new(*, found, sound):
    """Add a sound to those found, unless it is among them already."""
    if sound not in found:
        found.append(sound)


class SoundChoices(ChoicesPart):
    """What was chosen of the sounds: the band's, one of BAND_SOUNDS, which every player follows, and each player's own General MIDI sound, which overrides it."""

    __slots__ = ('_band_sounds', '_sounds')

    def __init__(self, *, choices):
        ChoicesPart.__init__(self, choices=choices)
        self.reset()

    def reset(self):
        """Go back to the sounds the subgenre gives: the usual Sounds for the band, and no player with a sound of the player's own."""
        self._band_sounds = wizard_limits.USUAL_SOUNDS
        self._sounds = {}

    # What a song keeps of the sounds.

    def to_data(self):
        """Return what a song keeps of the sounds, as plain data a song file saves: only what was chosen."""
        band_sounds = self._band_sounds
        if band_sounds == wizard_limits.USUAL_SOUNDS:
            band_sounds = None
        held = {
            wizard_limits.SOUNDS_SAVED: dict(self._sounds) or None,
            wizard_limits.BAND_SOUNDS_SAVED: band_sounds,
        }
        return chosen_only(held)

    def restore(self, saved):
        """Restore what a song saved of the sounds, leaving out whatever is no longer allowed."""
        band_sounds = saved.value(wizard_limits.BAND_SOUNDS_SAVED)
        if band_sounds:
            saved.apply(self._restore_band_sounds, sounds=band_sounds)
        sounds = saved.mapping(wizard_limits.SOUNDS_SAVED)
        for role, sound in sounds.items():
            saved.apply(self.set_sound, role=role, sound=sound)

    def counted(self):
        """Return every setting of the sounds, each under a name of its own, so that two bands can be compared setting by setting."""
        counted = {(wizard_limits.GENRE_SETTING, wizard_limits.BAND_SOUNDS_SAVED): self._band_sounds}
        for role, sound in self._sounds.items():
            counted[(wizard_limits.SOUNDS_SAVED, role)] = sound
        return counted

    # A player's sound: the one the player's way of playing has, moved by the band's Sounds, unless the player has a sound of its own.

    def has_sound(self, role):
        """Return whether a player's sound can be chosen: a player of notes, never the drums, whose kit the grooves are written for."""
        band = self._choices.get_band()
        entry = band.role_named(role)
        return not entry.get(arranger.DRUMS)

    def usual_sound(self, role):
        """Return the General MIDI sound a player usually plays with: what the genre has stand in for the player in the subgenre,
        as it does for a singer, whose voice General MIDI plays poorly, or the sound of the player's way."""
        style = self._choices.style()
        stand_ins = style.get(wizard_limits.STAND_INS, {})
        of_role = stand_ins.get(role, {})
        stands_in = of_role.get(self._choices.get_subgenre())
        if stands_in:
            return style[arranger.SOUNDS][stands_in]
        return self._way_sound(role)

    def _way_sound(self, role):
        """Return the General MIDI sound a player's way of playing has, which the arranger gives the player unless the song says another."""
        style = self._choices.style()
        band = self._choices.get_band()
        trait = band.role_named(role)[arranger.TRAIT]
        ways = values_of(style=style, trait=trait)
        entry = ways[band.get_way(trait)]
        return style[arranger.SOUNDS][entry[arranger.SOUND]]

    def get_band_sounds(self):
        return self._band_sounds

    def set_band_sounds(self, sounds):
        if sounds not in wizard_limits.BAND_SOUNDS:
            raise ValueError(errors.ERR_WIZARD_BAND_SOUNDS.format(value=sounds))
        self._band_sounds = sounds

    def _restore_band_sounds(self, *, sounds):
        self.set_band_sounds(sounds)

    def band_sound(self, role):
        """Return the sound the band's Sounds gives a player: the usual one, or the nearest of the family chosen, a sound
        already of that family staying as it is."""
        usual = self.usual_sound(role)
        if self._band_sounds == wizard_limits.USUAL_SOUNDS or usual in wizard_limits.KEPT_BY[self._band_sounds]:
            return usual
        return wizard_limits.NEAREST[self._band_sounds].get(family_of(usual), usual)

    def has_own_sound(self, role):
        return role in self._sounds

    def get_sound(self, role):
        """Return the General MIDI sound a player plays with: the player's own, or the band's."""
        return self._sounds.get(role, self.band_sound(role)) if role in self._sounds else self.band_sound(role)

    def set_sound(self, *, role, sound):
        """Give a player a sound of its own, any General MIDI sound; or None, to follow the band's again."""
        if not self.has_sound(role):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER.format(value=role))
        if sound is None:
            self._sounds.pop(role, None)
            return
        if isinstance(sound, bool) or not isinstance(sound, int) or not limits.MIN_GM_SOUND <= sound <= limits.MAX_GM_SOUND:
            raise ValueError(errors.ERR_WIZARD_SOUND.format(low=limits.MIN_GM_SOUND, high=limits.MAX_GM_SOUND, value=sound))
        self._sounds[role] = sound

    def genre_sounds(self, role):
        """Return the genre's own sounds that suit a player, each a General MIDI number: the sounds of the ways the player can
        play, then of what stands in for the player."""
        style = self._choices.style()
        band = self._choices.get_band()
        sounds = style[arranger.SOUNDS]
        ways = values_of(style=style, trait=band.role_named(role)[arranger.TRAIT])
        found = []
        for entry in ways.values():
            if arranger.SOUND in entry:
                _add_new(found=found, sound=sounds[entry[arranger.SOUND]])
        stand_ins = style.get(wizard_limits.STAND_INS, {})
        for stands_in in stand_ins.get(role, {}).values():
            _add_new(found=found, sound=sounds[stands_in])
        return found

    def sound_name(self, sound):
        """Return what a General MIDI sound is called: by the genre where the genre names it, or by General MIDI."""
        named = [name for name, number in self._choices.style()[arranger.SOUNDS].items() if number == sound]
        return named[0] if named else labels_text.MSG_GM_SOUNDS[sound - limits.MIN_GM_SOUND]

    def add_picks(self, picks):
        """Add the sounds the song chooses itself to the song's picks, by player, where there are any."""
        band = self._choices.get_band()
        sounds = {}
        for role in band.roles_in():
            if self._chooses_own_sound(role):
                sounds[role] = self.get_sound(role)
        if sounds:
            picks[arranger.ROLE_SOUNDS] = sounds

    def _chooses_own_sound(self, role):
        """Return whether the song chooses a player's sound itself: a player of notes who can play, whose sound is not its way's usual one."""
        if not self.has_sound(role):
            return False
        player = self._choices.player(role)
        if not player.can_play():
            return False
        return self.get_sound(role) != self._way_sound(role)
