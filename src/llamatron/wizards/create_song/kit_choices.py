# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's choices of the drum kit: its pieces, what each sounds as, the fills, the snare's quiet notes and a drum break."""

from llamatron.model.schema import limits
from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, characters, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import arranged, player_of
from llamatron.wizards.create_song.breaks import break_names
from llamatron.wizards.create_song.choices_part import ChoicesPart, kept_until_choices_change, set_each_kept


class KitChoices(ChoicesPart):
    """What was chosen of the drum kit: the pieces switched off, what a piece sounds as, how often a fill comes, whether the
    snare plays its quiet notes, and the drum break with how far it is cut up."""

    __slots__ = ('_pieces_off', '_fills', '_quiet_notes', '_break', '_break_cut', '_piece_sounds')

    def __init__(self, *, choices):
        ChoicesPart.__init__(self, choices=choices)
        self.reset()

    def reset(self):
        """Go back to the kit the subgenre gives: every piece on and sounding as itself, the drummer's own fills, the quiet notes played, the subgenre's break."""
        # The pieces of the drum kit switched off.
        self._pieces_off = []
        # How often a fill comes, a position from FEWEST_FILLS to MOST_FILLS, or None while the drummer decides; and whether the snare's quiet notes are played.
        self._fills = None
        self._quiet_notes = True
        self._break = None
        self._break_cut = None
        self._piece_sounds = {}

    # What a song keeps of the kit, and what the kit adds to the song made.

    def to_data(self):
        """Return what a song keeps of the kit, as plain data: only what was chosen."""
        held = {wizard_limits.PIECES_OFF_KEPT: list(self._pieces_off) or None, wizard_limits.FILLS_KEPT: self._fills,
                wizard_limits.QUIET_NOTES_KEPT: None if self._quiet_notes else False, wizard_limits.BREAK_KEPT: self._break, wizard_limits.BREAK_CUT_KEPT: self._break_cut,
                wizard_limits.PIECE_SOUNDS_KEPT: {piece: dict(sounds_as) for piece, sounds_as in self._piece_sounds.items()} or None}
        return {field: value for field, value in held.items() if value is not None}

    def read(self, data):
        """Take back what a song kept of the kit, leaving out whatever is no longer allowed."""
        set_each_kept([
            (self.set_piece_on, [dict(piece=piece, on=False) for piece in data.get(wizard_limits.PIECES_OFF_KEPT) or []]),
            (self.set_fills, [dict(position=data[wizard_limits.FILLS_KEPT])] if data.get(wizard_limits.FILLS_KEPT) is not None else []),
            (self.set_quiet_notes, [dict(on=False)] if data.get(wizard_limits.QUIET_NOTES_KEPT) is False else []),
            (self._set_kept_break, [dict(name=data[wizard_limits.BREAK_KEPT])] if data.get(wizard_limits.BREAK_KEPT) else []),
            (self._set_kept_piece_sound, [dict(piece=piece, sounds_as=sounds_as) for piece, sounds_as in (data.get(wizard_limits.PIECE_SOUNDS_KEPT) or {}).items()]),
            (self.set_break_cut, [dict(position=data[wizard_limits.BREAK_CUT_KEPT])] if data.get(wizard_limits.BREAK_CUT_KEPT) is not None else [])])

    def counted(self):
        """Return every setting of the kit, each under a name of its own, so that two kits can be compared setting by setting."""
        by_name = {(wizard_limits.GENRE_SETTING, name): value for name, value in (
            (wizard_limits.PIECES_OFF_KEPT, sorted(self._pieces_off)), (wizard_limits.FILLS_KEPT, self._fills), (wizard_limits.QUIET_NOTES_KEPT, self._quiet_notes),
            (wizard_limits.BREAK_KEPT, self._break), (wizard_limits.BREAK_CUT_KEPT, self._break_cut))}
        for piece, sounds_as in self._piece_sounds.items():
            by_name.update({(wizard_limits.PIECE_SOUNDS_KEPT, piece, inner): each for inner, each in sounds_as.items()})
        return by_name

    def trait_picks(self):
        """Return the song's picks of a break and its cut, where either was chosen."""
        return {**({arranger.BREAK: self._break} if self._break is not None else {}), **({arranger.BREAK_CUT: self._break_cut} if self._break_cut is not None else {})}

    def song_settings(self):
        """Return what the kit adds to the song's settings: the pieces left out, what a piece sounds as, how often a fill comes and the quiet notes left out."""
        return {**({arranger.WITHOUT_PIECES: list(self._pieces_off)} if self._pieces_off else {}),
                **({arranger.PIECE_SOUNDS: {piece: dict(sounds_as) for piece, sounds_as in self._piece_sounds.items()}} if self._piece_sounds else {}),
                **({arranger.FILLS_COME: wizard_limits.FILLS_EVERY[self._fills]} if self._fills is not None else {}),
                **({} if self._quiet_notes else {arranger.QUIET_NOTES: False})}

    # The kit's pieces, each switched on or off: a stroke on a piece that is off is left out, never moved to another piece.

    def pieces(self):
        """Return the pieces of the kit the drums play in the song as chosen, in the order the song has them, on or off."""
        return list(self._pieces())

    @kept_until_choices_change
    def _pieces(self):
        choices = self._choices
        if not choices.is_ready():
            return []
        song = {**choices.song_picks(choices.get_subgenre()), arranger.WITHOUT_PIECES: [], arranger.PIECE_SOUNDS: {}}
        return list(arranged(style=choices.style(), song=song)[arranger.DRUM_TRACKS])

    def piece_is_on(self, piece):
        return piece not in self._pieces_off

    def set_piece_on(self, *, piece, on):
        """Switch a piece of the kit on or off. The last piece stays on: a band with no drums leaves the drums out."""
        if piece not in self.pieces():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PIECE.format(value=piece))
        if on:
            if piece in self._pieces_off:
                self._pieces_off.remove(piece)
            return
        if [name for name in self.pieces() if self.piece_is_on(name)] == [piece]:
            raise ValueError(errors.ERR_WIZARD_LAST_PIECE)
        if piece not in self._pieces_off:
            self._pieces_off.append(piece)

    # How often the drummer plays a fill, and the snare's quiet notes.

    def _drummer(self):
        """Return what the genre says of its drummer at the level the drums are busy."""
        choices = self._choices
        drums = next((role for role in choices.get_band().roles() if not choices.get_sounds().has_sound(role)), None)
        return player_of(style=choices.style(), instrument=arranger.DRUMS, character=choices.get_band().character(arranger.DRUMS)) if drums else {}

    def get_fills(self):
        """Return how often a fill comes, from FEWEST_FILLS, never, to MOST_FILLS: the position chosen, or the one nearest to
        what the drummer does at the level the drums are busy."""
        if self._fills is not None:
            return self._fills
        every = self._drummer().get(characters.FILL_EVERY, self._choices.style().get(arranger.PHRASE_BARS, arranger.DEFAULT_PHRASE_BARS))
        if every == 0:
            return wizard_limits.FEWEST_FILLS
        return next((position for position, bars in wizard_limits.FILLS_EVERY.items() if isinstance(bars, int) and 0 < every <= bars), wizard_limits.EACH_SECTION_FILLS)

    def set_fills(self, position):
        if isinstance(position, bool) or not isinstance(position, int) or not wizard_limits.FEWEST_FILLS <= position <= wizard_limits.MOST_FILLS:
            raise ValueError(errors.ERR_WIZARD_FILLS.format(value=position))
        self._fills = position

    def has_quiet_notes(self):
        """Return whether the snare of the song as chosen has quiet notes, soft strokes between the main ones, to switch off."""
        return self._choices.offered(key=wizard_limits.QUIET_NOTES_ANSWER, compute=self._has_quiet_notes)

    def _has_quiet_notes(self):
        choices = self._choices
        if not choices.is_ready():
            return False
        song = {name: value for name, value in choices.song_picks(choices.get_subgenre()).items() if name != arranger.QUIET_NOTES}
        style = choices.style()
        # Found by arranging the song both ways, since a drummer's unevenness has made numbers of the strokes by then.
        return arranged(style=style, song=song)[arranger.PARTS] != arranged(style=style, song={**song, arranger.QUIET_NOTES: False})[arranger.PARTS]

    def plays_quiet_notes(self):
        return self._quiet_notes

    def set_quiet_notes(self, on):
        if not isinstance(on, bool):
            raise ValueError(errors.ERR_WIZARD_QUIET_NOTES.format(value=on))
        self._quiet_notes = on

    # What a piece of the kit sounds as: its own drum, another drum of the kit, or a General MIDI sound on one note.

    def drums(self):
        """Return the drums of the kit a piece may sound as."""
        return list(wizard_names.NOTATION_KIT)

    def piece_sound(self, piece):
        """Return what a piece of the kit sounds as: None for its own drum, the name of another drum of the kit, or a General MIDI sound's number."""
        sounds_as = self._piece_sounds.get(piece, {})
        return sounds_as.get(arranger.PLAYED_DRUM, sounds_as.get(arranger.PLAYED_SOUND))

    def piece_note(self, piece):
        """Return the MIDI note a piece plays in its General MIDI sound, or None for a piece that sounds as a drum."""
        return self._piece_sounds.get(piece, {}).get(arranger.PLAYED_NOTE)

    def set_piece_sound(self, *, piece, sound):
        """Have a piece of the kit sound as another drum of the kit, by name, or as a General MIDI sound, by number, on the note the
        piece had or the usual one; or None, as its own drum again."""
        if piece not in self.pieces():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PIECE.format(value=piece))
        if sound is None or sound == piece:
            self._piece_sounds.pop(piece, None)
        elif isinstance(sound, str) and sound in wizard_names.NOTATION_KIT:
            self._piece_sounds[piece] = {arranger.PLAYED_DRUM: sound}
        elif not isinstance(sound, (bool, str)) and isinstance(sound, int) and limits.MIN_GM_SOUND <= sound <= limits.MAX_GM_SOUND:
            self._piece_sounds[piece] = {arranger.PLAYED_SOUND: sound, arranger.PLAYED_NOTE: self.piece_note(piece) or wizard_limits.USUAL_PIECE_NOTE}
        else:
            raise ValueError(errors.ERR_WIZARD_PIECE_SOUND.format(value=sound))

    def set_piece_note(self, *, piece, note):
        """Choose the note a piece plays in its General MIDI sound."""
        if self.piece_note(piece) is None:
            raise ValueError(errors.ERR_WIZARD_PIECE_HAS_NO_NOTE.format(value=piece))
        if isinstance(note, bool) or not isinstance(note, int) or not arranger.LOWEST_NOTE <= note <= arranger.HIGHEST_NOTE:
            raise ValueError(errors.ERR_WIZARD_PIECE_NOTE.format(low=arranger.LOWEST_NOTE, high=arranger.HIGHEST_NOTE, value=note))
        self._piece_sounds[piece][arranger.PLAYED_NOTE] = note

    def _set_kept_piece_sound(self, *, piece, sounds_as):
        self.set_piece_sound(piece=piece, sound=sounds_as.get(arranger.PLAYED_DRUM, sounds_as.get(arranger.PLAYED_SOUND)))
        if arranger.PLAYED_NOTE in sounds_as:
            self.set_piece_note(piece=piece, note=sounds_as[arranger.PLAYED_NOTE])

    # The drum break: a bar of drums played as one thing, in place of the kick's, the snare's and the cymbal's own ways.

    def breaks(self):
        """Return the drum breaks the song may play: every break where the band has drums and the meter is the one a break
        is written in, and none otherwise."""
        choices = self._choices
        if not choices.is_ready() or choices.meter() != arranger.COMMON_TIME or not any(not choices.get_sounds().has_sound(role) for role in choices.get_band().roles()):
            return []
        return break_names()

    def get_break(self):
        """Return the break the drums play, the one chosen or the subgenre's own, or None where they play none."""
        if not self.breaks():
            return None
        name = self._break if self._break is not None else self._choices.picks().get(arranger.BREAK, arranger.NO_BREAK)
        return None if name == arranger.NO_BREAK else name

    def set_break(self, name):
        """Choose the break the drums play, or None for none."""
        if name is not None and name not in self.breaks():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_BREAK.format(value=name))
        self._break = arranger.NO_BREAK if name is None else name

    def _set_kept_break(self, *, name):
        self.set_break(None if name == arranger.NO_BREAK else name)

    def get_break_cut(self):
        """Return how far the break is cut up, from LEAST_CUT, as written, to MOST_CUT."""
        return self._break_cut if self._break_cut is not None else self._choices.picks().get(arranger.BREAK_CUT, wizard_names.LEAST_CUT)

    def set_break_cut(self, position):
        if isinstance(position, bool) or not isinstance(position, int) or not wizard_names.LEAST_CUT <= position <= wizard_names.MOST_CUT:
            raise ValueError(errors.ERR_WIZARD_BREAK_CUT.format(low=wizard_names.LEAST_CUT, high=wizard_names.MOST_CUT, value=position))
        self._break_cut = position
