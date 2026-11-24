# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Import Wizard's cut: a song cut into phrases and the phrases gathered into sections, so that a person learns its form.

The song is cut into phrases of the longest pattern's length, eight bars unless asked, a phrase being a whole musical thought,
a question and its answer. Each voice's phrase is a pattern that every phrase playing the same notes shares, or, where the
phrase is heard nowhere else, its halves or quarters that come back are patterns of their own; so a refrain that returns plays
the patterns it played the first time, and a figure a melody or a riff keeps returning to is written once. Phrases gather into
sections, one a scene, whose clips play their phrases' patterns as a list, or one pattern repeated where every phrase repeats
it. Every note plays as the file plays it, as in every cut (cutting.py)."""

from collections import Counter
from dataclasses import dataclass
import functools
from typing import NamedTuple

from llamatron.importers import cutting
from llamatron.importers.cutting import Cut, CutScene, Cutter, patterns_of, SceneClip, sounds_in
from llamatron.importers.midi_reading import value_at
from llamatron.importers.steps import NoteStep, pass_controls, repeated_pattern
from llamatron.user_strings import importing

# The most phrases a section of the phrase cut holds: four phrases of eight bars, a section of thirty-two, the longest a
# person usually hears as one part of a form.
MOST_PHRASES_A_SECTION = 4
# The cuts of a phrase the phrase cut tries, whole first, then halves and quarters, and how often a piece must be heard in the
# song, its own phrase and twice more, to be a pattern of its own rather than part of its phrase.
WHOLE_PHRASE = 1
PHRASE_PARTS = (WHOLE_PHRASE, 2, 4)
WITHIN_AND_TWICE_MORE = 3
# How alike two sections must be, the share of their steps alike, for the later to take the earlier's letter with a prime: a
# verse sung again over the same chords to other notes, or a refrain varied (Claude's judgment, to try by ear).
LIKE_ENOUGH = 0.7


class Phrase(NamedTuple):
    """One phrase of the song, as the phrase cut finds it: the grid steps it starts and ends at, its key and tempo, and each
    voice's clip across it (VoiceClip)."""

    start: int
    end: int
    key: object
    tempo: int
    clips: tuple

    def heard(self):
        """Return what the phrase plays, apart from where it falls: two phrases alike play the same in every voice."""
        return (self.end - self.start, self.key, self.tempo, tuple((clip.size, clip.pattern, clip.repeats) for clip in self.clips))


@dataclass(slots=True, kw_only=True)
class Changed:
    """What had to change across a cut, added up phrase by phrase: lengths changed, notes too low, CC messages moved."""

    lengths_changed: int = 0
    too_low: int = 0
    controls_moved: int = 0

    def add(self, clip):
        self.lengths_changed += clip.found.lengths_changed
        self.too_low += clip.found.too_low
        if sounds_in(clip.found):
            self.controls_moved += clip.controls_moved


class PhraseCutter(Cutter):
    """What cuts one song into phrases and sections, as the Import Wizard asks: a Cutter whose best cut is the phrase cut."""

    __slots__ = ()

    def best_cut(self):
        """Return the song cut into phrases of the longest pattern's length, each voice's phrase a pattern that every phrase
        playing the same notes shares, and the phrases gathered into sections, each a scene whose clips play their phrases' patterns
        as a list: so a refrain that returns plays the patterns it played the first time, and a part that repeats one figure
        through a section is one pattern with a repeat count."""
        phrases, off = self.lined_up_phrases()
        pieces = self.phrase_pieces(phrases)
        scenes = []
        totals = Changed()
        for section in sections_of(phrases=phrases, boundaries=set(self.boundaries()), families=phrase_families(phrases)):
            scene = self.section_scene(section=section, totals=totals, pieces=pieces)
            if scenes and scenes[-1].same_music(scene):
                scenes[-1].repeat += 1
            else:
                scenes.append(scene)
        lettered(scenes)
        patterns = patterns_of(scenes)
        long_patterns = sum(1 for _, size, steps, _ in patterns if self._longest.is_passed_by(steps=len(steps), size=size))
        cost = (long_patterns, len(patterns) + cutting.SCENE_COST * len(scenes) + cutting.OFF_THE_BAR_COST * off)
        return Cut(
            scenes=scenes, patterns=patterns, lengths_changed=totals.lengths_changed, too_low=totals.too_low,
            controls_moved=totals.controls_moved, long_patterns=long_patterns, cost=cost,
        )

    def lined_up_phrases(self):
        """Return the song's phrases, and how many cuts fall off their lines, lined up with the music: the phrases start after a
        lead of whole bars, none for most songs, an introduction or a pickup for others, the one that makes the most phrases a
        voice plays again elsewhere, so that a chorus that starts a bar after the eight-bar lines still repeats as a whole."""
        length = self._longest.steps_at(self._step_size)
        bar = self.step_of(self._bars[1] - self._bars[0])
        best = None
        for lead in range(0, length, bar):
            if lead and not self.is_clean(lead):
                continue
            cuts, off = self.cuts(length, lead=lead)
            phrases = [self.phrase_at(start=start, end=end) for start, end in zip(cuts, cuts[1:])]
            repeats = phrases_heard_again(phrases)
            if best is None or repeats > best[0]:
                best = (repeats, phrases, off)
        return best[1], best[2]

    def phrase_pieces(self, phrases):
        """Return the pieces each voice's phrase is played as in a list, by (voice, the phrase's start): the phrase whole, unless
        it is played nowhere else and its halves, or its quarters, come back at least twice elsewhere in the song, as a figure of
        two or four bars that a melody or a riff keeps returning to does; a phrase is never cut where a note is held across, and
        a figure heard only inside its own phrase stays part of it, so that patterns stay whole thoughts."""
        pieces = {}
        for voice in range(len(self._voices)):
            split, heard = self.cut_every_way(voice=voice, phrases=phrases)
            for phrase in phrases:
                merged = functools.partial(self.merged_pieces, voice=voice, key=phrase.key)
                pieces[(voice, phrase.start)] = chosen_pieces(phrase=phrase, split=split, heard=heard, merged=merged)
        return pieces

    def cut_every_way(self, *, voice, phrases):
        """Return a voice's phrases cut whole, in halves and in quarters, by (the phrase's start, the parts), and how often each
        piece is heard in the song, by the parts."""
        heard = {parts: Counter() for parts in PHRASE_PARTS}
        split = {}
        for phrase in phrases:
            for parts in PHRASE_PARTS:
                clips = self.parts_of(voice=voice, phrase=phrase, parts=parts)
                split[(phrase.start, parts)] = clips
                heard[parts].update(played_as(clip) for clip in clips or ())
        return split, heard

    def merged_pieces(self, *, voice, key, clips, shared):
        """Return a phrase's pieces with each run of pieces that don't come back made one, so that only a returning figure is
        a pattern of its own."""
        pieces = []
        run = []
        for clip, alone in zip(clips, shared):
            if alone:
                pieces += self.joined(voice=voice, key=key, run=run)
                pieces.append(clip)
                run = []
            else:
                run.append(clip)
        return pieces + self.joined(voice=voice, key=key, run=run)

    def joined(self, *, voice, key, run):
        """Return a run of a voice's pieces as one clip across them, or nothing for no run."""
        if not run:
            return []
        return [self.voice_clip(voice=voice, start=run[0].start, end=run[-1].end, key=key)]

    def parts_of(self, *, voice, phrase, parts):
        """Return a voice's clips across a phrase cut into so many equal parts, or None where a part would end where a note is
        held across or off the grid."""
        length = phrase.end - phrase.start
        if length % parts:
            return None
        size = length // parts
        edges = [phrase.start + size * place for place in range(parts + 1)]
        if not all(self.is_clean(edge) for edge in edges[1:-1]):
            return None
        return [self.voice_clip(voice=voice, start=start, end=end, key=phrase.key) for start, end in zip(edges, edges[1:])]

    def phrase_at(self, *, start, end):
        """Return one phrase of the song: where it starts and ends, its key and tempo, and each voice's clip across it."""
        key = value_at(changes=self._keys, time=self.time_of(start))
        clips = [self.voice_clip(voice=voice, start=start, end=end, key=key) for voice in range(len(self._voices))]
        return Phrase(start=start, end=end, key=key, tempo=value_at(changes=self._tempos, time=self.time_of(start)), clips=tuple(clips))

    def section_scene(self, *, section, totals, pieces):
        """Return the scene of a section, its phrases one after another: each voice that plays in it a clip of one pattern
        repeated where every phrase repeats the same one, else of its phrases' pieces as a list (phrase_pieces), a phrase it
        rests in a pattern of rests. The section comes as (phrase, family) pairs (sections_of)."""
        families = tuple(family for _, family in section)
        section = [phrase for phrase, _ in section]
        clips = []
        for voice in range(len(self._voices)):
            played = [phrase.clips[voice] for phrase in section]
            for clip in played:
                totals.add(clip)
            if not any(sounds_in(clip.found) for clip in played):
                continue
            drum = self._voices[voice].drum
            if len({clip.pattern for clip in played}) == 1 and len({clip.size for clip in played}) == 1:
                clips.append(SceneClip(voice, ((drum, played[0].size, *played[0].pattern),), sum(clip.repeats for clip in played)))
                continue
            listed = []
            for phrase in section:
                listed += [(drum, clip.size, *whole_pattern(clip.found)) for clip in pieces[(voice, phrase.start)]]
            clips.append(SceneClip(voice, tuple(listed), cutting.NO_REPEAT))
        if not clips:
            (sounds, controls), repeats = repeated_pattern(steps=[None] * (section[-1].end - section[0].start), gated=[])
            clips.append(SceneClip(cutting.FIRST_STEP, ((self._voices[cutting.FIRST_STEP].drum, self._step_size, sounds, controls),), repeats))
        first = section[0]
        material = tuple(phrase.heard() for phrase in section)
        return CutScene(start=first.start, end=section[-1].end, key=first.key, tempo=first.tempo, clips=clips, material=material, families=families)


def phrases_heard_again(phrases):
    """Return how many voices' phrases play what the same voice plays in another phrase, counting each after its first."""
    again = 0
    for voice in range(len(phrases[0].clips)):
        heard = Counter(played_as(phrase.clips[voice]) for phrase in phrases if sounds_in(phrase.clips[voice].found))
        again += sum(count - 1 for count in heard.values())
    return again


def lettered(scenes):
    """Give each scene the letter of its material, as a person names a form, without changing a note: a section playing exactly
    what an earlier one played, or phrases of the same families, takes its letter; one that begins as an earlier one began and
    then goes elsewhere, a verse cut short or a refrain extended, its letter with a prime, A', A''; any other the next letter."""
    by_families = {}
    by_first = {}
    primes = Counter()
    for scene in scenes:
        first = scene.families[:1]
        if scene.families in by_families:
            scene.letter = by_families[scene.families]
            continue
        if first in by_first:
            base = by_first[first]
            primes[base] += 1
            scene.letter = base + importing.MSG_SECTION_PRIME * primes[base]
        else:
            scene.letter = section_letter(len(by_first))
            by_first[first] = scene.letter
        by_families[scene.families] = scene.letter


def steps_alike(*, first, second):
    """Return the share of two runs of steps that hold the same, a note's degree, accidental, octave and chord, or both nothing;
    0 for runs of different lengths, written at different step sizes."""
    if len(first) != len(second) or not first:
        return 0.0
    alike = sum(1 for mine, theirs in zip(first, second) if step_heard(mine) == step_heard(theirs))
    return alike / len(first)


def step_heard(step):
    """Return what a step plays as two steps are compared, leaving out its velocity and its gate."""
    if isinstance(step, NoteStep):
        return (step.degree, step.accidental, step.octave, step.chord)
    return step


def section_letter(place):
    """Return the letter of a section's material counted from 0, A, B, and on as AA, AB after Z."""
    if place < len(importing.MSG_SECTION_LETTERS):
        return importing.MSG_SECTION_LETTERS[place]
    return section_letter(place // len(importing.MSG_SECTION_LETTERS) - 1) + importing.MSG_SECTION_LETTERS[place % len(importing.MSG_SECTION_LETTERS)]


def sections_of(*, phrases, boundaries, families):
    """Return the phrases gathered into sections, each phrase with its family: a section ends at a key or tempo change, where
    music the song plays more than once begins, the first time as every time after, as a refrain or a verse does, where that
    music gives way to music heard once, and after MOST_PHRASES_A_SECTION phrases, so that a section is a part of the form a
    person would name. Music begins where a phrase of a family the song plays again follows one it never followed before; a run
    of phrases heard together before stays together."""
    recurring = {family for family, count in Counter(families).items() if count > 1}
    sections = []
    followed = set()
    before = None
    for phrase, family in zip(phrases, families):
        begins = family in recurring and (before, family) not in followed
        gives_way = before in recurring and family not in recurring
        if not sections or phrase.start in boundaries or len(sections[-1]) >= MOST_PHRASES_A_SECTION or begins or gives_way:
            sections.append([])
        sections[-1].append((phrase, family))
        followed.add((before, family))
        before = family
    return sections


def phrase_families(phrases):
    """Return each phrase's family, a number: the family of the earlier phrase most like it, where that one is LIKE_ENOUGH like
    it, as a verse sung again to other notes or a refrain varied is; else a family of its own. No note is changed by it: a
    family only says which phrases a person hears as the same part."""
    families = []
    for place, phrase in enumerate(phrases):
        nearest = max(range(place), key=lambda earlier: phrases_alike(first=phrase, second=phrases[earlier]), default=None)
        if nearest is not None and phrases_alike(first=phrase, second=phrases[nearest]) >= LIKE_ENOUGH:
            families.append(families[nearest])
        else:
            families.append(len(set(families)))
    return families


def phrases_alike(*, first, second):
    """Return how alike two phrases are, from 0 to 1: the share of steps alike, voice by voice, among the voices playing in
    either."""
    shares = [steps_alike(first=mine.found.steps, second=theirs.found.steps) for mine, theirs in zip(first.clips, second.clips) if sounds_in(mine.found) or sounds_in(theirs.found)]
    if not shares:
        return 0.0
    return sum(shares) / len(shares)


def played_as(clip):
    """Return what tells one voice's piece apart from another: its step size and its steps and CC steps, played once."""
    return clip.size, whole_pattern(clip.found)


def chosen_pieces(*, phrase, split, heard, merged):
    """Return the pieces a voice plays a phrase as: the phrase whole where it comes back anywhere; else the halves or the
    quarters that come back, each a piece of its own, the stretches between them each one piece (merged); else the phrase whole."""
    whole = split[(phrase.start, WHOLE_PHRASE)]
    if heard[WHOLE_PHRASE][played_as(whole[0])] > 1:
        return whole
    for parts in PHRASE_PARTS[1:]:
        clips = split[(phrase.start, parts)]
        if clips is None:
            continue
        shared = [sounds_in(clip.found) and heard[parts][played_as(clip)] >= WITHIN_AND_TWICE_MORE for clip in clips]
        if any(shared):
            return merged(clips=clips, shared=shared)
    return whole


def whole_pattern(found):
    """Return a voice's steps across a phrase as one pattern played once, (steps, CC steps), for a clip's list."""
    return tuple(found.steps), pass_controls(lanes=found.lanes, begin=0, length=len(found.steps))


