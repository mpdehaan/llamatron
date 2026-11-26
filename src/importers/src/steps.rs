// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A voice's notes and CC values as a pattern's steps (the Python importers/steps.py). Every note starts on a step: a note
//! lasting whole steps is its step and ties on the steps after it, as the piano roll writes one, and a note that doesn't is
//! its step with an exact gate. A clip plays one pattern some times, a note held over a pass a tie at the pattern's start,
//! silence on the first pass. A voice's CC lanes are read as the value in force at each step's start; a run of steps whose
//! values lie on a straight line, as a slide sends them, is one value with Slide on.

use crate::keys::{degree_of, drum_note_of, MusicalKey};
use crate::voices::{Played, Voice};
use llamatron_math::Rational;
use llamatron_model::schema::generated::file_format::BASS_NOTES;

const SCALE_DEGREES: i64 = 7;
const ROUNDING: f64 = 0.5;
const SLOPE_MARGIN: f64 = 1e-9;
const MAX_GATE: i128 = 4;

/// What a step's degree row holds: a scale degree, or for a drum the letter of its note.
#[derive(Clone, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum StepDegree {
    Number(i64),
    Letter(String),
}

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct NoteStep {
    pub degree: StepDegree,
    pub accidental: Option<&'static str>,
    pub octave: i64,
    pub chord: Option<&'static str>,
    pub gate: Option<Rational>,
    pub velocity: i64,
    pub inversion: i64,
    pub glide: bool,
    pub doubling: Option<&'static str>,
    pub omission: Option<&'static str>,
    pub bass: Option<&'static str>,
    pub bass_octave: bool,
    pub tension: Option<&'static str>,
}

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum Step {
    Note(Box<NoteStep>),
    Tied,
}

/// A pass's CC values at one step: each lane's value or None, and whether they slide to the next.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct ControlStep {
    pub values: Vec<Option<i64>>,
    pub slide: bool,
}

pub type Steps = Vec<Option<Step>>;
pub type ControlSteps = Vec<Option<ControlStep>>;

#[derive(Clone, Debug, PartialEq)]
pub struct SceneSteps {
    pub steps: Steps,
    pub gated: Vec<(i64, Rational)>,
    pub lanes: Vec<Vec<Option<i64>>>,
    pub changes: bool,
    pub lengths_changed: i64,
    pub too_low: i64,
}

fn rational_floor(value: Rational) -> i64 {
    value.floor() as i64
}

/// A voice's steps from start to end, which a scene plays.
pub fn scene_steps(voice: &Voice, start: i64, end: i64, key: &MusicalKey, step_size: Rational) -> SceneSteps {
    let mut steps = held_on_steps(voice, start, end, step_size);
    let mut gated = Vec::new();
    let (mut lengths_changed, mut too_low) = (0, 0);
    let at = |step: i64| step_size * Rational::whole(step as i128);
    for played in voice.played_between(at(start), at(end)) {
        let first = played.start / step_size;
        let place = rational_floor(first) - start;
        let written = if voice.drum {
            let (letter, accidental, octave) = drum_note_of(played.pitches[0]);
            Some((StepDegree::Letter(letter), accidental, octave))
        } else {
            degree_of(played.written_pitch(), key).map(|(degree, accidental, octave)| (StepDegree::Number(degree), accidental, octave))
        };
        let Some(written) = written else {
            too_low += 1;
            continue;
        };
        let length = (played.end - played.start) / step_size;
        let mut gate = None;
        if !length.is_whole() || played.rings {
            if played.end - played.start <= Rational::whole(MAX_GATE) {
                gate = Some(played.end - played.start);
                gated.push((place, Rational::whole(place as i128) + length));
            } else {
                lengths_changed += 1;
            }
        }
        steps[place as usize] = Some(note_step(played, written, gate, key, voice.drum));
        if gate.is_none() {
            let last = (place + rational_floor(length).max(1)).min(steps.len() as i64);
            for tied in place + 1..last {
                steps[tied as usize] = Some(Step::Tied);
            }
        }
    }
    let lanes: Vec<Vec<Option<i64>>> = voice.lanes.iter().map(|number| lane_values(voice, *number, start, end, step_size)).collect();
    let changes = voice
        .lanes
        .iter()
        .zip(&lanes)
        .any(|(number, values)| lane_changes(values, value_in_force(voice, *number, at(start), true)));
    SceneSteps {
        steps,
        gated,
        lanes,
        changes,
        lengths_changed,
        too_low,
    }
}

fn note_step(played: &Played, written: (StepDegree, Option<&'static str>, i64), gate: Option<Rational>, key: &MusicalKey, drum: bool) -> Step {
    let (degree, accidental, octave) = written;
    let bass = if drum { None } else { bass_note_of(played, key) };
    Step::Note(Box::new(NoteStep {
        degree,
        accidental,
        octave,
        chord: played.chord,
        gate,
        velocity: played.velocity,
        inversion: played.inversion,
        glide: played.glide,
        doubling: played.doubling,
        omission: played.omission,
        bass,
        bass_octave: played.bass_octave,
        tension: played.tension,
    }))
}

/// A chord's Bass as a scale note some steps above its root, off it by its sharp or flat, or None where it has none.
fn bass_note_of(played: &Played, key: &MusicalKey) -> Option<&'static str> {
    let bass = played.bass?;
    let (root_degree, _, _) = degree_of(played.written_pitch(), key)?;
    let (bass_degree, bass_accidental, _) = degree_of(bass, key)?;
    let steps = (bass_degree - root_degree).rem_euclid(SCALE_DEGREES);
    let half = match bass_accidental {
        Some("#") => 1,
        Some("b") => -1,
        _ => 0,
    };
    BASS_NOTES
        .iter()
        .rev()
        .find(|(_, parts)| parts[0] == steps && parts[1] == half)
        .map(|(name, _)| *name)
}

/// The steps a note carried into a scene from before holds, as ties.
fn held_on_steps(voice: &Voice, start: i64, end: i64, step_size: Rational) -> Steps {
    let mut steps: Steps = vec![None; (end - start) as usize];
    if let Some(carried) = voice.carried_into(step_size * Rational::whole(start as i128)) {
        let reach = ((carried.end / step_size).ceil() as i64).min(end) - start;
        for tied in 0..reach.max(0) {
            steps[tied as usize] = Some(Step::Tied);
        }
    }
    steps
}

fn lane_changes(values: &[Option<i64>], before: Option<i64>) -> bool {
    std::iter::once(before)
        .chain(values.iter().copied())
        .zip(values)
        .any(|(earlier, later)| earlier != *later)
}

/// The value of a CC number in force at a time, or just before it.
fn value_in_force(voice: &Voice, number: i64, time: Rational, before: bool) -> Option<i64> {
    let mut value = None;
    for control in &voice.controls {
        if control.time > time || (before && control.time == time) {
            break;
        }
        if control.number == number {
            value = Some(control.value);
        }
    }
    value
}

fn lane_values(voice: &Voice, number: i64, start: i64, end: i64, step_size: Rational) -> Vec<Option<i64>> {
    let sent: Vec<_> = voice.controls.iter().filter(|control| control.number == number).collect();
    (start..end)
        .map(|step| {
            let time = step_size * Rational::whole(step as i128);
            let place = sent.partition_point(|control| control.time <= time);
            (place > 0).then(|| sent[place - 1].value)
        })
        .collect()
}

fn has_a_value(values: &[Option<i64>]) -> bool {
    values.iter().any(Option::is_some)
}

/// The CC steps of one pass from begin, each lane's value at the pass's first step and each change, a run lying on a straight
/// line one value with Slide on, ramping to the run's end.
fn pass_controls(lanes: &[Vec<Option<i64>>], begin: usize, length: usize) -> ControlSteps {
    if lanes.is_empty() {
        return vec![None; length];
    }
    let mut points: Vec<Vec<Option<i64>>> = vec![vec![None; length]; lanes.len()];
    for (lane, values) in lanes.iter().enumerate() {
        for place in 0..length {
            let value = values[begin + place];
            if value.is_some() && (place == 0 || values[begin + place - 1] != value) {
                points[lane][place] = value;
            }
        }
    }
    let mut slides = vec![false; length];
    for place in 0..length {
        let holding: Vec<usize> = (0..lanes.len()).filter(|lane| points[*lane][place].is_some()).collect();
        let runs: Vec<(usize, Option<usize>)> = holding
            .iter()
            .map(|lane| (*lane, straight_run(&lanes[*lane], begin + place, begin + length - 1)))
            .collect();
        let steady = runs
            .iter()
            .filter(|(lane, run)| run.is_none() && !has_a_value(&points[*lane][place + 1..]))
            .count();
        let running = runs.iter().filter(|(_, run)| run.is_some()).count();
        if running == 0 || steady + running < holding.len() {
            continue;
        }
        for (lane, run) in &runs {
            if let Some(run) = run {
                for point in &mut points[*lane][place + 1..run - begin] {
                    *point = None;
                }
                points[*lane][run - begin] = lanes[*lane][*run];
            }
        }
        slides[place] = true;
    }
    (0..length)
        .map(|place| {
            let values: Vec<Option<i64>> = (0..lanes.len()).map(|lane| points[lane][place]).collect();
            (!values.iter().all(Option::is_none)).then_some(ControlStep { values, slide: slides[place] })
        })
        .collect()
}

/// The furthest step a slide from begin reaches on a straight line, rounded to whole numbers, or None.
fn straight_run(values: &[Option<i64>], begin: usize, last: usize) -> Option<usize> {
    let runs = runs_of(values, begin, last);
    let reach = furthest_reach(values, begin, &runs);
    let mut end = reach;
    while end > begin + 1 {
        if values[end].is_some() && values[end] != values[begin] && run_ends(&runs, end).iter().all(|step| on_the_line(begin, end, values, *step)) {
            return Some(end);
        }
        end -= 1;
    }
    None
}

fn runs_of(values: &[Option<i64>], begin: usize, last: usize) -> Vec<(usize, usize)> {
    let mut runs = Vec::new();
    let mut first = begin;
    for step in begin + 1..=last {
        if values[step] != values[step - 1] {
            runs.push((first, step - 1));
            first = step;
        }
    }
    runs.push((first, last));
    runs
}

fn furthest_reach(values: &[Option<i64>], begin: usize, runs: &[(usize, usize)]) -> usize {
    let (mut low, mut high) = (f64::NEG_INFINITY, f64::INFINITY);
    let start = values[begin].unwrap_or(0) as f64;
    for (first, final_step) in runs {
        for step in [*first, *final_step] {
            if step == begin {
                continue;
            }
            let gap = (step - begin) as f64;
            let value = values[step].map(|value| value as f64).unwrap_or(f64::NAN);
            low = low.max((value - start - ROUNDING) / gap - SLOPE_MARGIN);
            high = high.min((value - start + ROUNDING) / gap + SLOPE_MARGIN);
            if low > high {
                return step;
            }
        }
    }
    runs[runs.len() - 1].1
}

fn run_ends(runs: &[(usize, usize)], end: usize) -> Vec<usize> {
    let mut ends = Vec::new();
    for (first, final_step) in runs {
        if *first > end {
            break;
        }
        ends.push(*first);
        ends.push((*final_step).min(end));
    }
    ends
}

/// Whether a step's value lies on the straight line from begin to end, rounded to the nearest whole number, a half to the
/// even one, worked out in whole numbers.
fn on_the_line(begin: usize, end: usize, values: &[Option<i64>], step: usize) -> bool {
    let span = (end - begin) as i64;
    let (Some(first), Some(last)) = (values[begin], values[end]) else {
        return false;
    };
    let total = first * span + (last - first) * (step - begin) as i64;
    let (mut whole, remainder) = (total.div_euclid(span), total.rem_euclid(span));
    if remainder * 2 > span || (remainder * 2 == span && whole.rem_euclid(2) != 0) {
        whole += 1;
    }
    values[step] == Some(whole)
}

/// The value a slide passes through at a time, rounded, as an export sends it.
fn value_on_the_way(start: Rational, value: i64, end: Rational, target: i64, now: Rational) -> i64 {
    (Rational::whole(value as i128) + Rational::whole((target - value) as i128) * (now - start) / (end - start)).round() as i64
}

const SLIDE_STEP: (i128, i128) = (1, 64);

/// How many of a voice's CC messages from start to end a pattern's CC steps don't send where and as the file does.
pub fn controls_between_steps(voice: &Voice, start: i64, end: i64, step_size: Rational, controls: &ControlSteps) -> i64 {
    let length = controls.len() as i128;
    let begin = step_size * Rational::whole(start as i128);
    let finish = step_size * Rational::whole(end as i128);
    let mut count = 0;
    for control in &voice.controls {
        if !(begin <= control.time && control.time < finish) {
            continue;
        }
        let offset = (control.time - begin) / step_size;
        if offset.is_whole() {
            continue;
        }
        let place = offset - Rational::whole(offset.floor().div_euclid(length) * length);
        let lane = voice.lanes.iter().position(|number| *number == control.number).unwrap_or(0);
        if !on_a_slide(controls, lane, place, control.value, step_size) {
            count += 1;
        }
    }
    count + slides_astray(voice, start, end, step_size, controls)
}

fn slides_astray(voice: &Voice, start: i64, end: i64, step_size: Rational, controls: &ControlSteps) -> i64 {
    let length = controls.len();
    let held: Vec<(Vec<Rational>, Vec<i64>)> = voice
        .lanes
        .iter()
        .map(|number| {
            let sent: Vec<_> = voice.controls.iter().filter(|control| control.number == *number).collect();
            (
                sent.iter().map(|control| control.time).collect(),
                sent.iter().map(|control| control.value).collect(),
            )
        })
        .collect();
    let slide_step = Rational::new(SLIDE_STEP.0, SLIDE_STEP.1);
    let mut count = 0;
    let mut pass_start = start;
    while pass_start < end {
        for (place, step) in controls.iter().enumerate() {
            let Some(step) = step.as_ref().filter(|step| step.slide) else { continue };
            for (lane, value) in step.values.iter().enumerate() {
                let following = (place + 1..length).find(|later| controls[*later].as_ref().is_some_and(|step| step.values[lane].is_some()));
                let (Some(value), Some(following)) = (value, following) else { continue };
                let begin = step_size * Rational::whole((pass_start + place as i64) as i128);
                let finish = step_size * Rational::whole((pass_start + following as i64) as i128);
                let target = controls[following].as_ref().and_then(|step| step.values[lane]).unwrap_or(0);
                let (times, values) = &held[lane];
                let mut now = begin + slide_step;
                while now < finish {
                    let found = times.partition_point(|time| *time <= now);
                    if found == 0 || values[found - 1] != value_on_the_way(begin, *value, finish, target, now) {
                        count += 1;
                        break;
                    }
                    now = now + slide_step;
                }
            }
        }
        pass_start += length as i64;
    }
    count
}

/// How far the file's CC values stray from what a scene's steps send, the most of any message.
pub fn control_error(voice: &Voice, start: i64, end: i64, step_size: Rational, found: &SceneSteps) -> i64 {
    let begin = step_size * Rational::whole(start as i128);
    let finish = step_size * Rational::whole(end as i128);
    let mut error = 0;
    for control in &voice.controls {
        if begin <= control.time && control.time < finish {
            let step = ((control.time - begin) / step_size).floor() as usize;
            let lane = voice.lanes.iter().position(|number| *number == control.number).unwrap_or(0);
            let held = found.lanes[lane][step].unwrap_or(control.value);
            error = error.max((control.value - held).abs());
        }
    }
    error
}

fn on_a_slide(controls: &ControlSteps, lane: usize, place: Rational, value: i64, step_size: Rational) -> bool {
    let first = place.floor() as usize;
    let holds = |step: usize| controls[step].as_ref().is_some_and(|step| step.values[lane].is_some());
    let Some(start) = (0..=first).rev().find(|step| holds(*step)) else {
        return false;
    };
    if !controls[start].as_ref().is_some_and(|step| step.slide) {
        return false;
    }
    let Some(end) = (first + 1..controls.len()).find(|step| holds(*step)) else {
        return false;
    };
    let time = (place - Rational::whole(start as i128)) * step_size;
    if !(time / Rational::new(SLIDE_STEP.0, SLIDE_STEP.1)).is_whole() {
        return false;
    }
    let lane_value = |step: usize| controls[step].as_ref().and_then(|step| step.values[lane]).unwrap_or(0);
    value_on_the_way(
        Rational::ZERO,
        lane_value(start),
        Rational::whole((end - start) as i128) * step_size,
        lane_value(end),
        time,
    ) == value
}

fn leading_ties_cleared(steps: &[Option<Step>]) -> Steps {
    let mut cleared = steps.to_vec();
    for step in cleared.iter_mut() {
        if *step != Some(Step::Tied) {
            break;
        }
        *step = None;
    }
    cleared
}

fn gate_crosses_a_pass(gated: &[(i64, Rational)], length: i64) -> bool {
    gated
        .iter()
        .any(|(begin, finish)| *finish > Rational::whole(((begin.div_euclid(length) + 1) * length) as i128))
}

/// The shortest pattern the steps repeat, its CC steps, and how many times it plays: every pass but the first the same
/// steps, the first the same with the ties at its start left empty, and no gate running past a pass's end.
pub fn repeated_pattern(steps: &[Option<Step>], gated: &[(i64, Rational)], lanes: &[Vec<Option<i64>>]) -> ((Steps, ControlSteps), i64) {
    let count = steps.len();
    for length in 1..=count {
        if !count.is_multiple_of(length) || gate_crosses_a_pass(gated, length as i64) {
            continue;
        }
        let passes: Vec<&[Option<Step>]> = steps.chunks(length).collect();
        let controls: Vec<ControlSteps> = (0..count).step_by(length).map(|at| pass_controls(lanes, at, length)).collect();
        let pattern = if passes.len() > 1 { passes[1] } else { passes[0] };
        let pattern_controls = if controls.len() > 1 { &controls[1] } else { &controls[0] };
        if passes[1..].iter().all(|each| *each == pattern)
            && passes[0] == leading_ties_cleared(pattern).as_slice()
            && controls.iter().all(|each| each == pattern_controls)
        {
            return ((pattern.to_vec(), pattern_controls.clone()), passes.len() as i64);
        }
    }
    ((steps.to_vec(), pass_controls(lanes, 0, count)), 1)
}
