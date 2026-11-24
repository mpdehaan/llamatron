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
from llamatron.importers.steps import pass_controls, repeated_pattern

# The most phrases a section of the phrase cut holds: four phrases of eight bars, a section of thirty-two, the longest a
# person usually hears as one part of a form.
MOST_PHRASES_A_SECTION = 4
# The cuts of a phrase the phrase cut tries, whole first, then halves and quarters, and how often a piece must be heard in the
# song, its own phrase and twice more, to be a pattern of its own rather than part of its phrase.
WHOLE_PHRASE = 1
PHRASE_PARTS = (WHOLE_PHRASE, 2, 4)
WITHIN_AND_TWICE_MORE = 3


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
        cuts, off = self.cuts(self._longest.steps_at(self._step_size))
        phrases = [self.phrase_at(start=start, end=end) for start, end in zip(cuts, cuts[1:])]
        pieces = self.phrase_pieces(phrases)
        scenes = []
        totals = Changed()
        for section in sections_of(phrases=phrases, boundaries=set(self.boundaries())):
            scene = self.section_scene(section=section, totals=totals, pieces=pieces)
            if scenes and scenes[-1].same_music(scene):
                scenes[-1].repeat += 1
            else:
                scenes.append(scene)
        patterns = patterns_of(scenes)
        long_patterns = sum(1 for _, size, steps, _ in patterns if self._longest.is_passed_by(steps=len(steps), size=size))
        cost = (long_patterns, len(patterns) + cutting.SCENE_COST * len(scenes) + cutting.OFF_THE_BAR_COST * off)
        return Cut(
            scenes=scenes, patterns=patterns, lengths_changed=totals.lengths_changed, too_low=totals.too_low,
            controls_moved=totals.controls_moved, long_patterns=long_patterns, cost=cost,
        )

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
        rests in a pattern of rests."""
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
        return CutScene(start=first.start, end=section[-1].end, key=first.key, tempo=first.tempo, clips=clips)


def sections_of(*, phrases, boundaries):
    """Return the phrases gathered into sections: a section ends at a key or tempo change, where a phrase that began an earlier
    section comes back, as a refrain does, and after MOST_PHRASES_A_SECTION phrases, so that a section is a part of the form a
    person would name."""
    sections = []
    starts = set()
    for phrase in phrases:
        heard = phrase.heard()
        new = not sections or phrase.start in boundaries or len(sections[-1]) >= MOST_PHRASES_A_SECTION or heard in starts
        if new:
            sections.append([])
            starts.add(heard)
        sections[-1].append(phrase)
    return sections


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


