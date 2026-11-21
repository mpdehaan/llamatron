# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Values a person gives the song wizard, checked: what a section of the form may be given of its own, field by field, a
line written by hand, a number in a range, and chords typed as degrees, read from text and written back as text."""

import copy

from llamatron.model.schema import limits
from llamatron.model.values import note as note_values
from llamatron.user_strings import errors
from llamatron.wizards.create_song import line_edits, melody as melody_writer, notation as tune_notation, phrasing, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import chord_of, fits_by_halves, shares_a_bar

# The mark typed before a degree for each sharp or flat, the other way round from the marks a person types.
MARKS_OF_ACCIDENTALS = {accidental: mark for mark, accidental in wizard_limits.MARKS_TYPED.items()}
# What a line written by hand may hold besides its notes: a breath in eighths and whether a note comes early.
LINE_FIELDS = {melody_writer.LINE_NOTES, phrasing.LINE_BREATH, phrasing.LINE_EARLY}


# Chords typed as degrees.

def chords_from_text(text):
    """Return chords typed as degrees with a space between, a flat or a sharp before a degree, such as 6 4 1 b7, two chords
    that share a bar joined by a dash, such as 1-5, as the arranger reads them."""
    chords = []
    for word in str(text).split():
        chords.append(_bar_typed(word=word, text=text))
    if not chords:
        raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
    if _has_shared_bar(chords) and not fits_by_halves(chords):
        raise ValueError(errors.ERR_WIZARD_CHORDS_SHARED.format(most=limits.MAX_PROGRESSION_CHORDS // wizard_limits.CHORDS_IN_A_SHARED_BAR, value=text))
    return chords


def _bar_typed(*, word, text):
    """Return the chord a word typed stands for, or the two chords that share a bar where the word joins them with a dash."""
    halves = word.split(wizard_limits.SHARES_A_BAR)
    if len(halves) > wizard_limits.CHORDS_IN_A_SHARED_BAR:
        raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
    if len(halves) == 1:
        return _chord_typed(word=word, text=text)
    return [_chord_typed(word=half, text=text) for half in halves]


def _chord_typed(*, word, text):
    """Return the chord a degree typed stands for, with its flat or sharp, refusing the whole text where the word is not one."""
    mark = None
    number = word
    if word and word[0] in wizard_limits.MARKS_TYPED:
        mark = word[0]
        number = word[1:]
    if not number.isdigit() or not wizard_limits.FIRST_DEGREE_OF_SCALE <= int(number) <= wizard_limits.LAST_DEGREE_OF_SCALE:
        raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
    if mark:
        return {tune_notation.DEGREE: int(number), tune_notation.ACCIDENTAL: wizard_limits.MARKS_TYPED[mark]}
    return int(number)


def _has_shared_bar(chords):
    """Return whether any of the chords is two that share a bar."""
    for chord in chords:
        if shares_a_bar(chord):
            return True
    return False


def chords_as_text(chords):
    """Return chords as they are typed."""
    words = []
    for chord in chords:
        words.append(_bar_as_text(chord))
    return ' '.join(words)


def _bar_as_text(chord):
    """Return a bar's chord as it is typed, or its two chords joined by a dash where they share it."""
    if not shares_a_bar(chord):
        return _chord_as_text(chord)
    halves = [_chord_as_text(half) for half in chord]
    return wizard_limits.SHARES_A_BAR.join(halves)


def _chord_as_text(chord):
    """Return one chord as it is typed: its flat or sharp, then its degree."""
    parsed = chord_of(chord)
    mark = MARKS_OF_ACCIDENTALS.get(parsed.get(tune_notation.ACCIDENTAL), '')
    return mark + str(parsed[tune_notation.DEGREE])


# What a section may be given of its own, field by field.

def checked_own(*, field, value):
    """Return what a section was given of its own for a field, checked, or refuse it: most fields keep the value as given,
    a section's lines are each checked, and chords are read as typed."""
    if field == wizard_limits.LINES_OF_SECTION and isinstance(value, dict):
        return _checked_lines(value)
    if field == wizard_names.ARRANGER_CHORDS:
        return _checked_chords(value)
    allows = OWN_FIELD_CHECKS.get(field)
    if allows is not None and allows(value):
        return value
    raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))


def _is_integer(value):
    """Return whether a value is an integer, true and false aside."""
    return isinstance(value, int) and not isinstance(value, bool)


def is_integer_between(value, *, low, high):
    """Return whether a value is an integer from low to high, true and false aside."""
    return _is_integer(value) and low <= value <= high


def _is_energy(value):
    return _is_integer(value) and wizard_names.LOWEST_ENERGY <= value <= wizard_names.HIGHEST_ENERGY


def _is_fade_level(value):
    return _is_integer(value) and wizard_names.FADED <= value <= wizard_names.LOUDEST_FADE_LEVEL


def _is_fade_length(value):
    return _is_integer(value) and value >= 1


def _is_tempo(value):
    return _is_integer(value) and limits.MIN_TEMPO <= value <= limits.MAX_TEMPO


def _is_leaving(value):
    return value in wizard_limits.LEAVES_AS_JOIN


def _is_no_setup(value):
    return value == wizard_names.NOT_AT_ALL


def _is_switch(value):
    return isinstance(value, bool)


def _is_name(value):
    return isinstance(value, str)


def _is_root(value):
    return value in note_values.ROOT_NAMES


def _is_scale_type(value):
    return value in wizard_limits.SCALE_TYPES


# The check each field of a section's own takes a value by, but for its lines and its chords, which are read as well.
OWN_FIELD_CHECKS = {
    wizard_names.SONG_PLAN_ENERGY: _is_energy,
    wizard_names.JOINS_LEAVES: _is_leaving,
    wizard_names.SONG_PLAN_SETUP: _is_no_setup,
    wizard_names.SONG_PLAN_RISES: _is_switch,
    wizard_names.SONG_PLAN_FADES: _is_switch,
    wizard_limits.INTRO_HOOK: _is_name,
    wizard_names.FADE_LEVEL: _is_fade_level,
    wizard_names.FADE_OVER: _is_fade_length,
    wizard_limits.SHAPE_OF_SECTION: _is_name,
    wizard_names.TEMPO_OF_PLACE: _is_tempo,
    wizard_names.TEMPO_END_OF_PLACE: _is_tempo,
    wizard_names.ROOT_OF_PLACE: _is_root,
    wizard_names.TYPE_OF_PLACE: _is_scale_type,
}


def _checked_chords(value):
    """Return chords a section was given, read as typed, whether given as text or as chords."""
    if isinstance(value, list):
        value = chords_as_text(value)
    return chords_from_text(value)


def _checked_lines(lines):
    """Return what each line of a section was given of its own, checked, by the line's number, leaving out a line given nothing."""
    checked = {}
    for count, given in lines.items():
        if given:
            checked[int(count)] = _checked_line_own(given)
    return checked


def _checked_line_own(given):
    """Return what one line of a section was given of its own, checked: notes written by hand, a breath in eighths and
    whether a note comes early."""
    if not isinstance(given, dict) or not set(given) <= LINE_FIELDS:
        raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=wizard_limits.LINES_OF_SECTION, value=given))
    checked = {}
    if melody_writer.LINE_NOTES in given:
        notes = given[melody_writer.LINE_NOTES]
        checked[melody_writer.LINE_NOTES] = checked_line(line=notes, steps=_steps_of_notes(notes))
    if phrasing.LINE_BREATH in given:
        breath = given[phrasing.LINE_BREATH]
        if not _is_integer(breath) or not phrasing.NO_BREATH <= breath <= phrasing.LONGEST_BREATH:
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=phrasing.LINE_BREATH, value=breath))
        checked[phrasing.LINE_BREATH] = breath
    if phrasing.LINE_EARLY in given:
        early = given[phrasing.LINE_EARLY]
        if not isinstance(early, bool):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=phrasing.LINE_EARLY, value=early))
        checked[phrasing.LINE_EARLY] = early
    return checked


def _steps_of_notes(notes):
    """Return how many steps notes written by hand fill, or none where they are not a list of notes."""
    if not _is_list_of_notes(notes):
        return 0
    return line_edits.steps_of(notes)


# A line written by hand.

def checked_line(*, line, steps):
    """Return a line written by hand, checked: notes of a degree of the scale and rests, each a whole number of steps, as
    long as the line it stands for, with a note in it."""
    if not _is_list_of_notes(line):
        raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=line))
    for note in line:
        _check_note(note)
    if line_edits.steps_of(line) != steps or _is_only_rests(line):
        raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=line))
    return copy.deepcopy(line)


def _is_list_of_notes(line):
    """Return whether a line is a list of notes, each written by name."""
    if not isinstance(line, list):
        return False
    for note in line:
        if not isinstance(note, dict):
            return False
    return True


def _check_note(note):
    """Refuse a note of a line written by hand unless it is a degree of the scale or a rest, a whole number of steps long, and
    within the reach of a line."""
    length = note.get(tune_notation.REST, note.get(tune_notation.STEPS))
    degree = note.get(tune_notation.DEGREE, line_edits.FIRST_DEGREE)
    octave = note.get(tune_notation.OCTAVE, 0)
    whole_numbers = _is_integer(length) and _is_integer(degree) and _is_integer(octave)
    if not whole_numbers or length < 1 or not line_edits.FIRST_DEGREE <= degree <= line_edits.NOTES_IN_SCALE:
        raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=note))
    if tune_notation.REST not in note and not line_edits.LOWEST_PLACE <= line_edits.place_of(note) <= line_edits.HIGHEST_PLACE:
        raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=note))


def _is_only_rests(line):
    """Return whether a line holds rests and no note."""
    for note in line:
        if tune_notation.REST not in note:
            return False
    return True
