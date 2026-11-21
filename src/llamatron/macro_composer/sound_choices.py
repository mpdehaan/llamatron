# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's choices of the sounds: the band's Sounds, which every player follows, and a player's own General MIDI sound."""

from llamatron.composition import limits
from llamatron.macro_composer import arranger, wizard_limits
from llamatron.macro_composer.arranger import values_of
from llamatron.macro_composer.choices_part import ChoicesPart, set_each_kept
from llamatron.strings import errors, labels as labels_text


def family_of(sound):
    """Return the place of the General MIDI family a sound is in."""
    return (sound - limits.MIN_GM_SOUND) // limits.GM_FAMILY_SIZE


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
        """Return what a song keeps of the sounds, as plain data: only what was chosen."""
        held = {wizard_limits.SOUNDS_KEPT: dict(self._sounds) or None, wizard_limits.BAND_SOUNDS_KEPT: self._band_sounds if self._band_sounds != wizard_limits.USUAL_SOUNDS else None}
        return {field: value for field, value in held.items() if value is not None}

    def read(self, data):
        """Take back what a song kept of the sounds, leaving out whatever is no longer allowed."""
        set_each_kept([
            (self._set_kept_band_sounds, [dict(sounds=data[wizard_limits.BAND_SOUNDS_KEPT])] if data.get(wizard_limits.BAND_SOUNDS_KEPT) else []),
            (self.set_sound, [dict(role=role, sound=sound) for role, sound in (data.get(wizard_limits.SOUNDS_KEPT) or {}).items()])])

    def counted(self):
        """Return every setting of the sounds, each under a name of its own, so that two bands can be compared setting by setting."""
        return {(wizard_limits.GENRE_SETTING, wizard_limits.BAND_SOUNDS_KEPT): self._band_sounds, **{(wizard_limits.SOUNDS_KEPT, role): sound for role, sound in self._sounds.items()}}

    # A player's sound: the one the player's way of playing has, moved by the band's Sounds, unless the player has a sound of its own.

    def has_sound(self, role):
        """Return whether a player's sound can be chosen: a player of notes, never the drums, whose kit the grooves are written for."""
        return not self._choices.get_band().role_named(role).get(arranger.DRUMS)

    def usual_sound(self, role):
        """Return the General MIDI sound a player usually plays with: what the genre has stand in for the player in the subgenre,
        as it does for a singer, whose voice General MIDI plays poorly, or the sound of the player's way."""
        style = self._choices.style()
        stands_in = style.get(wizard_limits.STAND_INS, {}).get(role, {}).get(self._choices.get_subgenre())
        return style[arranger.SOUNDS][stands_in] if stands_in else self._way_sound(role)

    def _way_sound(self, role):
        """Return the General MIDI sound a player's way of playing has, which the arranger gives the player unless the song says another."""
        style = self._choices.style()
        entry = values_of(style=style, trait=self._choices.get_band().role_named(role)[arranger.TRAIT])[self._choices.get_band().get_way(self._choices.get_band().role_named(role)[arranger.TRAIT])]
        return style[arranger.SOUNDS][entry[arranger.SOUND]]

    def get_band_sounds(self):
        return self._band_sounds

    def set_band_sounds(self, sounds):
        if sounds not in wizard_limits.BAND_SOUNDS:
            raise ValueError(errors.ERR_WIZARD_BAND_SOUNDS.format(value=sounds))
        self._band_sounds = sounds

    def _set_kept_band_sounds(self, *, sounds):
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
        """Return the genre's own sounds that suit a player, each a General MIDI number: the sounds of the ways the player can play."""
        style = self._choices.style()
        found = []
        for entry in values_of(style=style, trait=self._choices.get_band().role_named(role)[arranger.TRAIT]).values():
            if arranger.SOUND in entry and style[arranger.SOUNDS][entry[arranger.SOUND]] not in found:
                found.append(style[arranger.SOUNDS][entry[arranger.SOUND]])
        for stands_in in style.get(wizard_limits.STAND_INS, {}).get(role, {}).values():
            if style[arranger.SOUNDS][stands_in] not in found:
                found.append(style[arranger.SOUNDS][stands_in])
        return found

    def sound_name(self, sound):
        """Return what a General MIDI sound is called: by the genre where the genre names it, or by General MIDI."""
        named = [name for name, number in self._choices.style()[arranger.SOUNDS].items() if number == sound]
        return named[0] if named else labels_text.MSG_GM_SOUNDS[sound - limits.MIN_GM_SOUND]

    def sounds_of_song(self):
        """Return the sounds the song chooses itself, by player: each player in the band whose sound is not its way's usual one."""
        return {role: self.get_sound(role) for role in self._choices.get_band().roles_in() if self.has_sound(role) and self._choices.player(role).can_play() and self.get_sound(role) != self._way_sound(role)}
