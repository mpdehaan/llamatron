// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A part's notes split into voices (the Python importers/voices.py), since a pattern's step holds one note or one chord and
//! a step's note lasts until it ends, so that nothing is ever cut or left out: drums by sound; a part playing both hands into
//! its treble and its bass; notes together in a chord's shape one chord; and whatever still overlaps into voices by rank at
//! each moment, so that a melody keeps to its voice as long as it can.

use crate::chord_naming::{chord_named, Hearing};
use crate::reading::{HeardControl, MidiPart, PartNote};
use llamatron_math::Rational;
use llamatron_strings::texts::importing;
use std::collections::HashMap;

const MIDDLE_C: i64 = 60;
const HAND_REACH: i64 = 16;
const HAND_SHARE: f64 = 0.1;
const MONOPHONIC_SOUNDS: [(i64, i64); 4] = [(33, 45), (53, 56), (57, 62), (65, 89)];
const CC_PRIORITY: [i64; 3] = [1, 7, 64];
const FIRST_CHANNEL_MODE: i64 = 120;
const MAX_GATE: i128 = 4;

/// One thing a voice plays: when it starts and ends, its pitches lowest first, its velocity, and as a chord its symbol, its
/// inversion and its root, with its Double, Omit, Bass and Tension; whether it glides into the next, and whether it rings on
/// under what follows.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Played {
    pub start: Rational,
    pub end: Rational,
    pub pitches: Vec<i64>,
    pub velocity: i64,
    pub chord: Option<&'static str>,
    pub inversion: i64,
    pub root: Option<i64>,
    pub glide: bool,
    pub doubling: Option<&'static str>,
    pub omission: Option<&'static str>,
    pub bass: Option<i64>,
    pub bass_octave: bool,
    pub tension: Option<&'static str>,
    pub rings: bool,
}

impl Played {
    fn single(note: &PartNote) -> Played {
        Played {
            start: note.start,
            end: note.end,
            pitches: vec![note.pitch],
            velocity: note.velocity,
            chord: None,
            inversion: 0,
            root: None,
            glide: false,
            doubling: None,
            omission: None,
            bass: None,
            bass_octave: false,
            tension: None,
            rings: false,
        }
    }

    /// The pitch its step's degree is written from: a chord's root, else its note.
    pub fn written_pitch(&self) -> i64 {
        self.root.unwrap_or(self.pitches[0])
    }
}

#[derive(Clone, Debug)]
pub struct Voice {
    pub name: String,
    pub drum: bool,
    pub played: Vec<Played>,
    pub lanes: Vec<i64>,
    pub controls: Vec<HeardControl>,
    pub sound: Option<i64>,
}

impl Voice {
    /// What the voice plays that is still sounding at a time, started before it.
    pub fn carried_into(&self, time: Rational) -> Option<&Played> {
        let place = self.played.partition_point(|played| played.start < time);
        (place > 0 && self.played[place - 1].end > time).then(|| &self.played[place - 1])
    }

    /// What the voice plays that starts from begin to before end.
    pub fn played_between(&self, begin: Rational, end: Rational) -> &[Played] {
        let first = self.played.partition_point(|played| played.start < begin);
        let last = self.played.partition_point(|played| played.start < end);
        &self.played[first..last.max(first)]
    }
}

/// A part's voices; with controls, the first voice takes the part's CC messages of the numbers the import brings in.
pub fn voices_of(part: &MidiPart, chords: bool, controls: bool, in_key: Option<Vec<i64>>) -> Vec<Voice> {
    let mut voices = if part.is_drums() {
        drum_voices(part)
    } else {
        let mut voices = Vec::new();
        for (name, notes, from_top) in hands(part) {
            let units = if chords {
                chord_units(&notes, in_key.clone())
            } else {
                notes.iter().map(Played::single).collect()
            };
            let monophonic = plays_one_note_at_a_time(part);
            let units = legato_line(units, monophonic);
            voices.extend(named_voices(&name, false, lines_of(units, from_top, !monophonic)));
        }
        let sound = part.program.map(|program| program + 1).unwrap_or(1);
        for voice in &mut voices {
            voice.sound = Some(sound);
        }
        voices
    };
    let lanes = if controls { control_lanes(part) } else { Vec::new() };
    if !lanes.is_empty() {
        voices[0].controls = part.controls.iter().filter(|control| lanes.contains(&control.number)).copied().collect();
        voices[0].lanes = lanes;
    }
    voices
}

fn plays_one_note_at_a_time(part: &MidiPart) -> bool {
    part.program
        .is_some_and(|program| MONOPHONIC_SOUNDS.iter().any(|(low, high)| (*low..*high).contains(&(program + 1))))
}

fn is_legato(earlier: &Played, later: &Played) -> bool {
    earlier.start < later.start && later.start < earlier.end && earlier.end - later.start < Rational::new(1, 2) * (earlier.end - earlier.start)
}

/// A line slurred where its notes overlap as a horn or a voice slurs, each slurred note ending where the next starts, with
/// Glide; anything else as it was.
fn legato_line(units: Vec<Played>, monophonic: bool) -> Vec<Played> {
    let mut ordered = units.clone();
    ordered.sort_by_key(|unit| unit.start);
    let pairs: Vec<(&Played, &Played)> = ordered.iter().zip(ordered.iter().skip(1)).collect();
    if ordered.iter().any(|unit| unit.pitches.len() > 1) || pairs.iter().any(|(earlier, later)| later.start == earlier.start) {
        return units;
    }
    if !pairs.iter().any(|(earlier, later)| earlier.end > later.start) {
        return units;
    }
    if !monophonic {
        let short = pairs.iter().enumerate().all(|(place, (earlier, later))| {
            let after = ordered.get(place + 2);
            earlier.end <= later.start || (is_legato(earlier, later) && after.is_none_or(|after| earlier.end <= after.start))
        });
        if !short {
            return units;
        }
    }
    let mut joined = Vec::new();
    for (place, earlier) in ordered.iter().enumerate() {
        match ordered.get(place + 1) {
            Some(later) if earlier.end > later.start => joined.push(Played {
                end: later.start,
                glide: true,
                ..earlier.clone()
            }),
            _ => joined.push(earlier.clone()),
        }
    }
    joined
}

fn control_lanes(part: &MidiPart) -> Vec<i64> {
    let mut sent: Vec<(i64, usize)> = Vec::new();
    for control in part.controls.iter().filter(|control| control.number < FIRST_CHANNEL_MODE) {
        match sent.iter_mut().find(|(number, _)| *number == control.number) {
            Some((_, count)) => *count += 1,
            None => sent.push((control.number, 1)),
        }
    }
    let mut lanes: Vec<i64> = CC_PRIORITY
        .iter()
        .copied()
        .filter(|number| sent.iter().any(|(found, _)| found == number))
        .collect();
    let mut others: Vec<(i64, usize)> = sent.iter().copied().filter(|(number, _)| !CC_PRIORITY.contains(number)).collect();
    others.sort_by_key(|(number, count)| (std::cmp::Reverse(*count), *number));
    lanes.extend(others.iter().map(|(number, _)| *number));
    lanes.truncate(4);
    lanes
}

fn drum_voices(part: &MidiPart) -> Vec<Voice> {
    let mut pitches: Vec<i64> = part.notes.iter().map(|note| note.pitch).collect();
    pitches.sort();
    pitches.dedup();
    let mut voices = Vec::new();
    let mut unnamed = 1;
    for pitch in pitches {
        let name = match importing::MSG_DRUM_NAMES.iter().find(|(found, _)| *found == pitch) {
            Some((_, name)) => name.to_string(),
            None => {
                let name = format!("perc {unnamed}");
                unnamed += 1;
                name
            }
        };
        let units: Vec<Played> = part.notes.iter().filter(|note| note.pitch == pitch).map(Played::single).collect();
        voices.extend(named_voices(&name, true, lines_of(units, true, false)));
    }
    voices
}

/// A part's hands: its treble and its bass where it plays notes together on both sides of middle C often enough, else the
/// part whole.
fn hands(part: &MidiPart) -> Vec<(String, Vec<PartNote>, bool)> {
    let below: Vec<PartNote> = part.notes.iter().copied().filter(|note| note.pitch < MIDDLE_C).collect();
    let above: Vec<PartNote> = part.notes.iter().copied().filter(|note| note.pitch >= MIDDLE_C).collect();
    if !below.is_empty() && !above.is_empty() && (beyond_one_hand(&part.notes) as f64) >= HAND_SHARE * part.notes.len() as f64 {
        return vec![(format!("{} treble", part.name), above, true), (format!("{} bass", part.name), below, false)];
    }
    vec![(part.name.clone(), part.notes.clone(), true)]
}

fn beyond_one_hand(notes: &[PartNote]) -> usize {
    let mut far: Vec<usize> = Vec::new();
    let mut sounding: Vec<(usize, PartNote)> = Vec::new();
    for (place, note) in notes.iter().enumerate() {
        sounding.retain(|(_, before)| before.end > note.start);
        for (other, before) in &sounding {
            if (before.pitch - note.pitch).abs() > HAND_REACH {
                for index in [*other, place] {
                    if !far.contains(&index) {
                        far.push(index);
                    }
                }
            }
        }
        sounding.push((place, *note));
    }
    far.len()
}

fn chord_units(notes: &[PartNote], in_key: Option<Vec<i64>>) -> Vec<Played> {
    let mut together: Vec<((Rational, Rational, i64), Vec<i64>)> = Vec::new();
    for note in notes {
        let key = (note.start, note.end, note.velocity);
        match together.iter_mut().find(|(found, _)| *found == key) {
            Some((_, pitches)) => pitches.push(note.pitch),
            None => together.push((key, vec![note.pitch])),
        }
    }
    together.sort_by_key(|(key, _)| *key);
    let mut units = Vec::new();
    let mut hearing = Hearing { in_key, before: None };
    for ((start, end, velocity), mut pitches) in together {
        pitches.sort();
        let Some(named) = chord_named(&pitches, &hearing) else {
            units.extend(pitches.iter().map(|pitch| {
                Played::single(&PartNote {
                    start,
                    end,
                    pitch: *pitch,
                    velocity,
                })
            }));
            continue;
        };
        hearing = hearing.after(&named);
        units.push(Played {
            start,
            end,
            pitches,
            velocity,
            chord: named.symbol,
            inversion: named.inversion,
            root: Some(named.root),
            glide: false,
            doubling: named.doubling,
            omission: named.omission,
            bass: named.bass,
            bass_octave: named.bass_octave,
            tension: named.tension,
            rings: false,
        });
    }
    units.sort();
    units
}

/// The units in voices: each at its start into the first voice free then, ranked from the top or the bottom, more voices
/// made as they are needed; where may_ring, a voice is free too while what it plays rings on under the unit, which is marked.
fn lines_of(units: Vec<Played>, from_top: bool, may_ring: bool) -> Vec<Vec<Played>> {
    let mut starts: Vec<Rational> = Vec::new();
    let mut by_start: HashMap<Rational, Vec<usize>> = HashMap::new();
    for (place, unit) in units.iter().enumerate() {
        if !by_start.contains_key(&unit.start) {
            starts.push(unit.start);
        }
        by_start.entry(unit.start).or_default().push(place);
    }
    starts.sort();
    let mut lines: Vec<Vec<usize>> = Vec::new();
    let mut sounding: Vec<Vec<usize>> = Vec::new();
    let mut ringing: Vec<usize> = Vec::new();
    for start in starts {
        let mut ranked = by_start[&start].clone();
        if from_top {
            ranked
                .sort_by(|first, second| units[*second].pitches[units[*second].pitches.len() - 1].cmp(&units[*first].pitches[units[*first].pitches.len() - 1]));
        } else {
            ranked.sort_by_key(|place| units[*place].pitches[0]);
        }
        for held in &mut sounding {
            held.retain(|place| units[*place].end > start);
        }
        let mut taken: Vec<usize> = Vec::new();
        for unit in ranked {
            let free = (0..sounding.len()).find(|place| {
                !taken.contains(place)
                    && (sounding[*place].is_empty() || (may_ring && sounding[*place].iter().all(|held| can_ring(&units[*held], &units[unit]))))
            });
            let place = match free {
                Some(place) => place,
                None => {
                    lines.push(Vec::new());
                    sounding.push(Vec::new());
                    lines.len() - 1
                }
            };
            taken.push(place);
            ringing.extend(sounding[place].iter().copied());
            lines[place].push(unit);
            sounding[place].push(unit);
        }
    }
    lines
        .into_iter()
        .map(|line| {
            line.into_iter()
                .map(|place| Played {
                    rings: units[place].rings || ringing.contains(&place),
                    ..units[place].clone()
                })
                .collect()
        })
        .collect()
}

fn can_ring(held: &Played, under: &Played) -> bool {
    held.end - held.start <= Rational::whole(MAX_GATE) && !held.pitches.iter().any(|pitch| under.pitches.contains(pitch))
}

fn voice_letter(place: usize) -> String {
    let letters: Vec<char> = "abcdefghijklmnopqrstuvwxyz".chars().collect();
    if place < letters.len() {
        return letters[place].to_string();
    }
    format!("{}{}", voice_letter(place / letters.len() - 1), letters[place % letters.len()])
}

fn named_voices(name: &str, drum: bool, lines: Vec<Vec<Played>>) -> Vec<Voice> {
    let voice = |name: String, played: Vec<Played>| Voice {
        name,
        drum,
        played,
        lanes: Vec::new(),
        controls: Vec::new(),
        sound: None,
    };
    if lines.len() == 1 {
        return vec![voice(name.to_string(), lines.into_iter().next().unwrap_or_default())];
    }
    lines
        .into_iter()
        .enumerate()
        .map(|(place, line)| voice(format!("{name} {}", voice_letter(place)), line))
        .collect()
}
