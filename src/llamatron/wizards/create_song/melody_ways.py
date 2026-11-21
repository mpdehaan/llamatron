# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How the song's melodies go, as the song wizard's choices hold it: how busy they are, how wide they range, how much they
repeat, their character and each kind of section's own melody, reached as choices.melody_ways()."""

from llamatron.model.file.song_file_error import SongFileError
from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, melody as melody_writer, notation as tune_notation, wizard_limits
from llamatron.wizards.create_song.arranger import arranged
from llamatron.wizards.create_song.riffs import flattened_in
from llamatron.wizards.create_song.section_melody import SectionMelody


def _choices_module():
    """Return the module of the wizard's choices, imported as it is first needed: it holds these choices, and its functions
    that find whether a melody style works make a song from choices of their own."""
    from llamatron.wizards.create_song import wizard_choices
    return wizard_choices


class MelodyWays:
    """What was chosen of how the song's melodies go: how busy, how wide and how repeating they are, their character, and
    each kind of section's own melody, all held in the song's extras, each the genre's own until chosen."""

    __slots__ = ('_choices',)

    def __init__(self, *, choices):
        self._choices = choices

    def fields(self):
        """Return the fields of the whole song's melodies that are heard in the subgenre, in the order shown."""
        if not self._choices.is_ready() or not self._choices.get_tunes().tune_kinds():
            return []
        return [field for field in wizard_limits.MELODY_WAYS if len(self.ways_offered(field)) > 1]

    def ways_offered(self, field):
        """Return the values of a field of the whole song's melodies that are heard in the song as it stands: the genre's own,
        each other that makes another song, and the one chosen."""
        heard = self.values_heard(field=field)
        return [value for value in wizard_limits.MELODY_WAYS[field] if value == wizard_limits.USUAL_MELODY_WAYS[field] or value in heard or value == self.get_way(field)]

    def values_heard(self, *, field, kind=None):
        """The values of a melody field, of the song or of a kind of section, that make another song than the field left
        unchosen does, found by arranging the song each way, once, until a choice changes."""
        return self._choices.offered(key=(wizard_limits.MELODY_HEARD_ANSWER, field, kind), compute=lambda: self._found_values_heard(field=field, kind=kind))

    def _found_values_heard(self, *, field, kind):
        made = {}
        for value in (None, *(wizard_limits.SECTION_MELODY_WAYS if kind is not None else wizard_limits.MELODY_WAYS)[field]):
            trial = type(self._choices).from_data(self._choices.to_data())
            trial.melody_ways().keep_chosen(field=field, value=value, kind=kind)
            try:
                made[value] = arranged(style=_choices_module().style_of(self._choices.get_genre()), song=trial.song_picks(self._choices.get_subgenre()))[arranger.PARTS]
            except (ValueError, IndexError, KeyError, SongFileError):
                made[value] = made.get(None)
        return [value for value in made if value is not None and made[value] != made[None]]

    def get_way(self, field):
        """Return what the song says of its melodies in one field: the genre's own until another is chosen."""
        chosen = (self._choices.get_extra(wizard_limits.MELODY_CHOSEN) or {}).get(field)
        return chosen if chosen in wizard_limits.MELODY_WAYS[field] else wizard_limits.USUAL_MELODY_WAYS[field]

    def genre_way(self, field):
        """Return the genre's own value of a field of the whole song's melodies."""
        return wizard_limits.USUAL_MELODY_WAYS[field]

    def set_way(self, *, field, value):
        """Choose how busy the song's melodies are, how wide they range or how much they repeat; the genre's own is asked for by its name."""
        if field not in wizard_limits.MELODY_WAYS or value not in wizard_limits.MELODY_WAYS[field]:
            raise ValueError(errors.ERR_WIZARD_MELODY_WAY.format(field=field, value=value))
        self.keep_chosen(field=field, value=None if value == wizard_limits.USUAL_MELODY_WAYS[field] else value)

    def keep_chosen(self, *, field, value, kind=None):
        """Keep one thing chosen of the melodies, for the song or for a kind of section, or forget it with None."""
        chosen = dict(self._choices.get_extra(wizard_limits.MELODY_CHOSEN) or {})
        self._choices.set_extra(name=wizard_limits.MELODY_CHOSEN, value=chosen)
        held = chosen if kind is None else chosen.setdefault(melody_writer.BY_KIND, {}).setdefault(kind, {})
        held.pop(field, None)
        if value is not None:
            held[field] = value
        if kind is not None:
            chosen[melody_writer.BY_KIND] = {name: own for name, own in chosen[melody_writer.BY_KIND].items() if own}
            if not chosen[melody_writer.BY_KIND]:
                del chosen[melody_writer.BY_KIND]
        if not chosen:
            self._choices.set_extra(name=wizard_limits.MELODY_CHOSEN, value=None)
        self._choices.clear_answers()

    def characters_offered(self):
        """Return the characters a melody of the subgenre can be given: each whose engine can write the subgenre's melodies, an
        engine with no gauges only where the genre does not write by it already."""
        if not self._choices.is_ready() or not self._choices.get_tunes().tune_kinds():
            return []
        given = dict(genre=self._choices.get_genre(), subgenre=self._choices.get_subgenre(), variant=self._choices.get_variant())
        offered = []
        for character in wizard_limits.CHARACTERS:
            engine = wizard_limits.CHARACTER_ENGINES[character]
            if _choices_module().melody_works(style=engine, **given) and (engine in wizard_limits.GAUGED_STYLES or not _choices_module().melody_is_usual(style=engine, **given)):
                offered.append(character)
        return offered

    def get_character(self):
        """Return the character chosen for the song's melodies, or None while they are written as the genre writes them."""
        chosen = (self._choices.get_extra(wizard_limits.MELODY_CHOSEN) or {}).get(wizard_limits.MELODY_CHARACTER)
        return chosen if chosen in self.characters_offered() else None

    def set_character(self, character):
        """Choose the character of the song's melodies, or the genre's own with None."""
        if character is not None and character not in self.characters_offered():
            raise ValueError(errors.ERR_WIZARD_MELODY_WAY.format(field=wizard_limits.MELODY_CHARACTER, value=character))
        self.keep_chosen(field=wizard_limits.MELODY_CHARACTER, value=character)

    def of_kind(self, kind):
        """Return a kind of section's own melody: how high it sits and how busy it is."""
        return SectionMelody(choices=self._choices, kind=kind)

    def picks_over(self, picks):
        """Return what the arranger is handed of the melodies chosen, over the song's picks: what is asked of the plans' lines,
        the engine a character writes by, and the habits a range and a character change."""
        chosen = self._choices.get_extra(wizard_limits.MELODY_CHOSEN)
        if not chosen or not self._choices.is_ready():
            return {}
        said = {}
        asks = self._asks(chosen)
        if asks:
            said[melody_writer.MELODY_ASKS] = asks
        habits = dict(picks.get(arranger.MELODY, {}))
        self._change_span(habits=habits, chosen=chosen)
        character = self.get_character()
        if character is not None:
            said[arranger.MELODY_ENGINE] = wizard_limits.CHARACTER_ENGINES[character]
            self._give_character(habits=habits, character=character)
        if habits:
            said[arranger.MELODY] = habits
        return said

    def _asks(self, chosen):
        """Return what the arranger is asked of the lines: how much they repeat and how busy they are, and each kind of section's own."""
        asks = {}
        repeats = chosen.get(melody_writer.REPEATS)
        if repeats in melody_writer.REPEATS_WAYS:
            asks[melody_writer.REPEATS] = repeats
        busy = chosen.get(wizard_limits.MELODY_BUSY)
        if busy in wizard_limits.BUSY_POSITIONS:
            asks[melody_writer.LINE_BUSY] = wizard_limits.BUSY_POSITIONS[busy]
        by_kind = {}
        for kind in chosen.get(melody_writer.BY_KIND, {}):
            section = self.of_kind(kind)
            of_kind = section.asks()
            if of_kind:
                by_kind[kind] = of_kind
        if by_kind:
            asks[melody_writer.BY_KIND] = by_kind
        return asks

    def _change_span(self, *, habits, chosen):
        """Widen or narrow how far the melody ranges, as chosen, from the genre's own span, never below the least."""
        range_chosen = chosen.get(wizard_limits.MELODY_RANGE)
        melody = self._choices.melody()
        genre_habits = melody.habits()
        if range_chosen in wizard_limits.SPAN_CHANGES and melody_writer.SPAN in genre_habits:
            span = genre_habits[melody_writer.SPAN] + wizard_limits.SPAN_CHANGES[range_chosen]
            habits[melody_writer.SPAN] = max(wizard_limits.LEAST_SPAN, span)

    def _give_character(self, *, habits, character):
        """Give the melody's habits what a character changes: its gauges, and for a bluesy one the blues ladder and home."""
        if character in wizard_limits.CHARACTER_GAUGES:
            melody = self._choices.melody()
            gauges = {name: melody.get_style_gauge(name) for name in melody_writer.DEFAULT_GAUGES}
            gauges.update(wizard_limits.CHARACTER_GAUGES[character])
            habits[melody_writer.SMART] = gauges
        if character == wizard_limits.BLUESY:
            habits[melody_writer.LADDER] = self._blues_ladder()
            habits[melody_writer.HOME] = {tune_notation.DEGREE: wizard_limits.BLUES_HOME}

    def _blues_ladder(self):
        """Return the degrees a bluesy melody climbs, each flattened where the song's scale type flattens it."""
        flattened = flattened_in(self._choices.get_scale_type())
        ladder = []
        for degree in wizard_limits.BLUES_DEGREES:
            step = {tune_notation.DEGREE: degree}
            if degree in flattened:
                step[tune_notation.ACCIDENTAL] = tune_notation.FLAT
            ladder.append(step)
        return ladder
