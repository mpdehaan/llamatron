// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The song cut into scenes and patterns (the Python importers/cutting.py). Nothing is ever cut: a scene splits only at a
//! step no note is held across. Patterns keep within the longest asked for: the song is cut into phrases of whole bars, each
//! a scene, each voice's clip in it the shortest pattern it can repeat; where a phrase's end isn't clean, the scene ends at
//! the clean step before it and a short scene runs to the clean step after. Splits fall on bar lines where they can, then
//! the fewest patterns and the fewest scenes win. A key or tempo change splits the song first.

use crate::keys::MusicalKey;
use crate::reading::{value_at, Change, MidiPart, PartNote};
use crate::steps::{control_error, controls_between_steps, repeated_pattern, scene_steps, ControlSteps, SceneSteps, Step, Steps};
use crate::voices::Voice;
use llamatron_math::Rational;
use std::collections::{HashMap, HashSet};

pub fn auto_step_sizes() -> Vec<Rational> {
    [4, 8, 12, 16, 24, 32, 48, 64, 96, 192]
        .iter()
        .map(|denominator| Rational::new(1, *denominator))
        .collect()
}

pub fn finest_step_size() -> Rational {
    Rational::new(1, 64)
}

const PHRASE_BARS: [i64; 6] = [4, 8, 2, 16, 1, 32];
const PARTS_OF_A_BAR: [i64; 3] = [2, 4, 8];
const SCENE_COST: f64 = 0.5;
const OFF_THE_BAR_COST: f64 = 1.0;
const CONTROL_TOLERANCE: i64 = 4;

/// A pattern as the cut finds it: whether it is a drum's, its step size, its steps and its CC steps.
pub type CutPattern = (bool, Rational, Steps, ControlSteps);

#[derive(Clone, Debug, PartialEq)]
pub struct SceneClip {
    pub voice: usize,
    pub patterns: Vec<CutPattern>,
    pub repeats: i64,
}

#[derive(Clone, Debug)]
struct VoiceClip {
    size: Rational,
    found: SceneSteps,
    pattern: (Steps, ControlSteps),
    repeats: i64,
    controls_moved: i64,
    error: i64,
}

#[derive(Clone, Debug)]
pub struct CutScene {
    pub start: i64,
    pub end: i64,
    pub key: MusicalKey,
    pub tempo: i64,
    pub clips: Vec<SceneClip>,
    pub repeat: i64,
}

impl CutScene {
    fn same_music(&self, other: &CutScene) -> bool {
        self.end - self.start == other.end - other.start && self.key == other.key && self.tempo == other.tempo && self.clips == other.clips
    }
}

#[derive(Clone, Debug)]
pub struct Cut {
    pub scenes: Vec<CutScene>,
    pub patterns: Vec<CutPattern>,
    pub lengths_changed: i64,
    pub too_low: i64,
    pub controls_moved: i64,
    pub long_patterns: i64,
    pub cost: (i64, f64),
}

/// The step size a file's notes ask for, and whether every note starts on it: the longest step every note starts on, or else
/// the longest nearly all start near, or else the finest allowed.
pub fn step_size_for(parts: &[MidiPart], finest: Rational) -> (Rational, bool) {
    let starts: Vec<Rational> = parts.iter().flat_map(|part| part.notes.iter().map(|note| note.start)).collect();
    let unique: HashSet<Rational> = starts.iter().copied().collect();
    if let Some(size) = longest_step_for(&unique.into_iter().collect::<Vec<_>>()) {
        return (size, true);
    }
    (nearest_step_for(&starts, finest), false)
}

fn nearest_step_for(times: &[Rational], finest: Rational) -> Rational {
    for size in auto_step_sizes() {
        if size < finest {
            break;
        }
        let near = times.iter().filter(|time| distance_to_grid(**time, size) <= Rational::new(1, 8) * size).count();
        if Rational::whole(near as i128) >= Rational::new(98, 100) * Rational::whole(times.len() as i128) {
            return size;
        }
    }
    finest
}

fn distance_to_grid(time: Rational, step_size: Rational) -> Rational {
    (time - Rational::whole((time / step_size).round()) * step_size).abs()
}

fn longest_step_for(times: &[Rational]) -> Option<Rational> {
    auto_step_sizes().into_iter().find(|size| times.iter().all(|time| (*time / *size).is_whole()))
}

/// The grid the cut works on: the step size, or a finer one every CC message falls on, or keeps every lane near the file.
pub fn grid_for(voices: &[Voice], step_size: Rational) -> Rational {
    let times: Vec<Rational> = voices
        .iter()
        .flat_map(|voice| voice.controls.iter().map(|control| control.time))
        .collect::<HashSet<_>>()
        .into_iter()
        .collect();
    let mut controls = longest_step_for(&times);
    if controls.is_none() && !times.is_empty() {
        let sizes = auto_step_sizes();
        controls = Some(
            sizes
                .iter()
                .copied()
                .find(|size| most_off(voices, *size) <= CONTROL_TOLERANCE)
                .unwrap_or(sizes[sizes.len() - 1]),
        );
    }
    match controls {
        Some(controls) if controls < step_size => controls,
        _ => step_size,
    }
}

fn most_off(voices: &[Voice], step_size: Rational) -> i64 {
    let mut error = 0;
    for voice in voices {
        let mut held: HashMap<i64, i64> = HashMap::new();
        let mut step_start = None;
        let mut at_start: HashMap<i64, i64> = HashMap::new();
        for control in &voice.controls {
            let start = Rational::whole((control.time / step_size).floor()) * step_size;
            if step_start != Some(start) {
                step_start = Some(start);
                at_start = held.clone();
            }
            if control.time == start {
                at_start.insert(control.number, control.value);
            }
            error = error.max((control.value - at_start.get(&control.number).copied().unwrap_or(control.value)).abs());
            held.insert(control.number, control.value);
        }
    }
    error
}

/// The parts with every note moved to the nearest step, keeping its length, and how many moved.
pub fn snapped(parts: &[MidiPart], step_size: Rational) -> (Vec<MidiPart>, i64) {
    let mut moved = 0;
    let mut snapped_parts = Vec::new();
    for part in parts {
        let mut notes: Vec<PartNote> = part
            .notes
            .iter()
            .map(|note| {
                let start = Rational::whole((note.start / step_size).round()) * step_size;
                if start != note.start {
                    moved += 1;
                }
                PartNote {
                    start,
                    end: note.end + start - note.start,
                    ..*note
                }
            })
            .collect();
        notes.sort();
        snapped_parts.push(MidiPart { notes, ..part.clone() });
    }
    (snapped_parts, moved)
}

/// Where each bar starts, to the end of the bar the last note ends in, and past holding, the last CC message's time.
pub fn bar_lines(time_signatures: &[Change<(i64, i64)>], end: Rational, holding: Option<Rational>) -> Vec<Rational> {
    let mut lines = Vec::new();
    let mut time = Rational::ZERO;
    while lines.is_empty() || time < end || holding.is_some_and(|holding| time <= holding) {
        lines.push(time);
        let (beats, unit) = value_at(time_signatures, time);
        time = time + Rational::new(beats as i128, unit as i128);
    }
    lines.push(time);
    lines
}

/// The longest a pattern may be: its steps, or its bars where asked, and a bar's length.
#[derive(Clone, Copy, Debug)]
pub struct Longest {
    pub steps: i64,
    pub bars: Option<i64>,
    pub bar: Rational,
}

impl Longest {
    fn is_passed_by(&self, steps: usize, size: Rational) -> bool {
        match self.bars {
            None => steps as i64 > self.steps,
            Some(bars) => Rational::whole(steps as i128) * size > Rational::whole(bars as i128) * self.bar,
        }
    }

    fn steps_at(&self, size: Rational) -> i64 {
        match self.bars {
            None => self.steps,
            Some(bars) => (Rational::whole(bars as i128) * self.bar / size).floor() as i64,
        }
    }
}

pub struct Cutter<'v> {
    voices: &'v [Voice],
    step_size: Rational,
    clip_step_sizes: Vec<Rational>,
    bars: Vec<Rational>,
    keys: Vec<Change<MusicalKey>>,
    tempos: Vec<Change<i64>>,
    longest: Longest,
    end: i64,
    blocked: HashSet<i64>,
    clips: std::cell::RefCell<HashMap<(usize, i64, i64), VoiceClip>>,
}

impl<'v> Cutter<'v> {
    pub fn new(
        voices: &'v [Voice],
        step_size: Rational,
        clip_step_sizes: &[Rational],
        bars: Vec<Rational>,
        keys: Vec<Change<MusicalKey>>,
        tempos: Vec<Change<i64>>,
        longest: Longest,
    ) -> Cutter<'v> {
        let mut sizes: Vec<Rational> = clip_step_sizes.iter().copied().filter(|size| (*size / step_size).is_whole()).collect();
        if sizes.is_empty() {
            sizes = vec![step_size];
        }
        let end = (bars[bars.len() - 1] / step_size).floor() as i64;
        let mut blocked = HashSet::new();
        for voice in voices {
            for played in &voice.played {
                let first = played.start / step_size;
                let last = played.end / step_size;
                for step in first.floor() as i64 + 1..last.ceil() as i64 {
                    blocked.insert(step);
                }
            }
        }
        Cutter {
            voices,
            step_size,
            clip_step_sizes: sizes,
            bars,
            keys,
            tempos,
            longest,
            end,
            blocked,
            clips: std::cell::RefCell::new(HashMap::new()),
        }
    }

    fn time_of(&self, step: i64) -> Rational {
        self.step_size * Rational::whole(step as i128)
    }

    fn can_cut(&self, step: i64) -> bool {
        !self.blocked.contains(&step)
    }

    fn cut_after(&self, mut step: i64) -> i64 {
        while step < self.end && !self.can_cut(step) {
            step += 1;
        }
        step.min(self.end)
    }

    fn boundaries(&self) -> Vec<i64> {
        let mut changes: Vec<i64> = vec![0, self.end];
        let times = self.keys.iter().map(|change| change.time).chain(self.tempos.iter().map(|change| change.time));
        for time in times {
            if time > Rational::ZERO {
                changes.push(self.cut_after((time / self.step_size).ceil() as i64));
            }
        }
        changes.sort();
        changes.dedup();
        changes
    }

    fn phrase_lengths(&self) -> Vec<i64> {
        let bar_steps = (self.bars[1] - self.bars[0]) / self.step_size;
        if !bar_steps.is_whole() {
            return vec![self.longest.steps_at(self.step_size)];
        }
        let bar = bar_steps.floor() as i64;
        let mut lengths: Vec<i64> = PHRASE_BARS.iter().map(|bars| bar * bars).collect();
        for parts in PARTS_OF_A_BAR {
            if (bar_steps / Rational::whole(parts as i128)).is_whole() {
                lengths.push(bar / parts);
            }
        }
        lengths
    }

    fn cuts(&self, length: i64) -> (Vec<i64>, i64) {
        let mut cuts: Vec<i64> = Vec::new();
        let mut off = 0;
        let edges = self.boundaries();
        for pair in edges.windows(2) {
            let (start, end) = (pair[0], pair[1]);
            cuts.push(start);
            let mut line = start + length;
            while line < end {
                if self.can_cut(line) {
                    cuts.push(line);
                    line += length;
                    continue;
                }
                let last_cut = cuts[cuts.len() - 1];
                let before = (last_cut + 1..line).rev().find(|step| self.can_cut(*step));
                let after = self.cut_after(line + 1);
                for step in [before, Some(after)].into_iter().flatten() {
                    if cuts[cuts.len() - 1] < step && step < end {
                        cuts.push(step);
                        off += 1;
                    }
                }
                line = start + ((cuts[cuts.len() - 1].max(line) - start).div_euclid(length) + 1) * length;
            }
        }
        cuts.push(self.end);
        (cuts, off)
    }

    /// A voice's clip from start to end at the longest step size that sends its CC messages as the file does, or keeps them
    /// near, or strays least.
    fn voice_clip(&self, voice: usize, start: i64, end: i64, key: &MusicalKey) -> VoiceClip {
        if let Some(found) = self.clips.borrow().get(&(voice, start, end)) {
            return found.clone();
        }
        let mut clips: Vec<VoiceClip> = Vec::new();
        for size in self.voice_step_sizes(voice, start, end) {
            let clip = self.clip_at(voice, start, end, key, size);
            let exact = clip.controls_moved == 0;
            clips.push(clip);
            if exact {
                break;
            }
        }
        let chosen = clips
            .iter()
            .find(|clip| clip.controls_moved == 0)
            .or_else(|| clips.iter().find(|clip| clip.error <= CONTROL_TOLERANCE))
            .cloned()
            .unwrap_or_else(|| clips.iter().min_by_key(|clip| clip.error).cloned().expect("a clip has a step size"));
        self.clips.borrow_mut().insert((voice, start, end), chosen.clone());
        chosen
    }

    fn clip_at(&self, voice: usize, start: i64, end: i64, key: &MusicalKey, size: Rational) -> VoiceClip {
        let ratio = size / self.step_size;
        let first = (Rational::whole(start as i128) / ratio).floor() as i64;
        let last = (Rational::whole(end as i128) / ratio).floor() as i64;
        let found = scene_steps(&self.voices[voice], first, last, key, size);
        let (pattern, repeats) = repeated_pattern(&found.steps, &found.gated, &found.lanes);
        let moved = controls_between_steps(&self.voices[voice], first, last, size, &pattern.1);
        let error = if moved != 0 {
            control_error(&self.voices[voice], first, last, size, &found)
        } else {
            0
        };
        VoiceClip {
            size,
            found,
            pattern,
            repeats,
            controls_moved: moved,
            error,
        }
    }

    /// The step sizes a voice's clip may take: those every note's start, and a note carried in's end, fall on.
    fn voice_step_sizes(&self, voice: usize, start: i64, end: i64) -> Vec<Rational> {
        let begin = self.time_of(start);
        let played = &self.voices[voice];
        let mut starts: Vec<Rational> = played.played_between(begin, self.time_of(end)).iter().map(|each| each.start - begin).collect();
        if let Some(carried) = played.carried_into(begin) {
            if carried.end < self.time_of(end) {
                starts.push(carried.end - begin);
            }
        }
        let sizes: Vec<Rational> = self
            .clip_step_sizes
            .iter()
            .copied()
            .filter(|size| (begin / *size).is_whole() && (self.time_of(end - start) / *size).is_whole() && starts.iter().all(|time| (*time / *size).is_whole()))
            .collect();
        if sizes.is_empty() {
            vec![self.step_size]
        } else {
            sizes
        }
    }

    fn scenes_of(&self, cuts: &[i64]) -> (Vec<CutScene>, i64, i64, i64) {
        let mut scenes: Vec<CutScene> = Vec::new();
        let (mut lengths_changed, mut too_low, mut controls_moved) = (0, 0, 0);
        for pair in cuts.windows(2) {
            let (start, end) = (pair[0], pair[1]);
            let key = value_at(&self.keys, self.time_of(start));
            let mut clips = Vec::new();
            for voice in 0..self.voices.len() {
                let clip = self.voice_clip(voice, start, end, &key);
                lengths_changed += clip.found.lengths_changed;
                too_low += clip.found.too_low;
                if clip.found.changes || clip.found.steps.iter().any(|step| matches!(step, Some(Step::Note(_)))) {
                    let (sounds, controls) = clip.pattern.clone();
                    clips.push(SceneClip {
                        voice,
                        patterns: vec![(self.voices[voice].drum, clip.size, sounds, controls)],
                        repeats: clip.repeats,
                    });
                    controls_moved += clip.controls_moved;
                }
            }
            if clips.is_empty() {
                let empty: Steps = vec![None; (end - start) as usize];
                let ((sounds, controls), repeats) = repeated_pattern(&empty, &[], &[]);
                clips.push(SceneClip {
                    voice: 0,
                    patterns: vec![(self.voices[0].drum, self.step_size, sounds, controls)],
                    repeats,
                });
            }
            let scene = CutScene {
                start,
                end,
                key,
                tempo: value_at(&self.tempos, self.time_of(start)),
                clips,
                repeat: 1,
            };
            match scenes.last_mut() {
                Some(last) if last.same_music(&scene) => last.repeat += 1,
                _ => scenes.push(scene),
            }
        }
        (scenes, lengths_changed, too_low, controls_moved)
    }

    fn cut(&self, length: i64) -> Cut {
        let (cuts, off) = self.cuts(length);
        let (scenes, lengths_changed, too_low, controls_moved) = self.scenes_of(&cuts);
        let patterns = patterns_of(&scenes);
        let long_patterns = patterns
            .iter()
            .filter(|(_, size, steps, _)| self.longest.is_passed_by(steps.len(), *size))
            .count() as i64;
        let cost = (
            long_patterns,
            patterns.len() as f64 + SCENE_COST * scenes.len() as f64 + OFF_THE_BAR_COST * off as f64,
        );
        Cut {
            scenes,
            patterns,
            lengths_changed,
            too_low,
            controls_moved,
            long_patterns,
            cost,
        }
    }

    /// The cut of the lowest cost among every phrase length, the first of two as low.
    pub fn best_cut(&self) -> Cut {
        let mut best: Option<Cut> = None;
        for length in self.phrase_lengths() {
            let cut = self.cut(length);
            if best
                .as_ref()
                .is_none_or(|found| cut.cost.0 < found.cost.0 || (cut.cost.0 == found.cost.0 && cut.cost.1 < found.cost.1))
            {
                best = Some(cut);
            }
        }
        best.expect("a song has a phrase length")
    }
}

/// Every pattern the scenes play, each once, in the order first played.
fn patterns_of(scenes: &[CutScene]) -> Vec<CutPattern> {
    let mut patterns: Vec<CutPattern> = Vec::new();
    for scene in scenes {
        for clip in &scene.clips {
            for pattern in &clip.patterns {
                if !patterns.contains(pattern) {
                    patterns.push(pattern.clone());
                }
            }
        }
    }
    patterns
}
