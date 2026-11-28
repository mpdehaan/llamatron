// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Naming the chord some pitches sound (the Python music_theory/harmony/chord_naming.py), the readings tried in the order a
//! player names a chord, plainest first: a chord in root position or an inversion; that with one change, notes doubled an
//! octave away, chord tones left out of a four-note chord, or one tension added; that with two of those; and a slash chord.
//! Where two readings fit at one rank, a root in the key wins, then the chord of the step before.

use llamatron_model::fundamentals::role_of;
use llamatron_model::schema::generated::file_format::{OMITTED_ROLES, TENSIONS};
use llamatron_names::file_format;
use std::collections::HashMap;
use std::sync::OnceLock;

const OCTAVE: i64 = 12;
const SLASH_GAP: i64 = 7;
const OMISSIONS: [&str; 5] = ["no3", "no5", "no1", "no35", "no15"];
const INTERVAL_CHORDS: [&str; 6] = ["+P8", "+m3", "+M3", "+P4", "+m6", "+M6"];
const DOUBLINGS: [&str; 4] = ["low_up", "all_up", "all_down", "top_down"];

fn omission_rank(omission: Option<&str>, with_tension: bool) -> i64 {
    let order: &[&str] = if with_tension {
        &[
            file_format::Omission::NO_ROOT_FIFTH,
            file_format::Omission::NO_ROOT,
            file_format::Omission::NO_FIFTH,
            file_format::Omission::NO_THIRD,
            file_format::Omission::NO_THIRD_FIFTH,
        ]
    } else {
        &OMISSIONS
    };
    omission
        .and_then(|omission| order.iter().position(|found| *found == omission))
        .map(|place| place as i64 + 1)
        .unwrap_or(0)
}

fn tension_rank(tension: Option<&str>) -> i64 {
    let order = ["13", "9", "b9", "#11", "11", "#9", "b13"];
    tension
        .and_then(|tension| order.iter().position(|found| *found == tension))
        .map(|place| place as i64 + 1)
        .unwrap_or(0)
}

fn omitted_symbol_rank(symbol: &str) -> i64 {
    let order = ["dom7", "m7", "M7", "m7b5", "dim7", "7sus4", "mM7", "aug7", "augM7", "add9", "madd9", "M6", "m6"];
    order.iter().position(|found| *found == symbol).map(|place| place as i64 + 1).unwrap_or(0)
}

/// A chord named: its symbol, None for a note doubled alone, its inversion, the MIDI number its degree is written from, its
/// Double and Omit, its Bass with whether the Bass Octave plays, and its one tension.
#[derive(Clone, Debug, PartialEq)]
pub struct NamedChord {
    pub symbol: Option<&'static str>,
    pub inversion: i64,
    pub root: i64,
    pub doubling: Option<&'static str>,
    pub omission: Option<&'static str>,
    pub bass: Option<i64>,
    pub bass_octave: bool,
    pub tension: Option<&'static str>,
}

impl NamedChord {
    fn same_chord(&self, other: Option<&NamedChord>) -> bool {
        other.is_some_and(|other| self.symbol == other.symbol && self.root.rem_euclid(OCTAVE) == other.root.rem_euclid(OCTAVE))
    }
}

/// What a chord is heard against: the key's pitch classes, or None where it isn't known, and the reading of the step before.
#[derive(Clone, Debug, Default)]
pub struct Hearing {
    pub in_key: Option<Vec<i64>>,
    pub before: Option<NamedChord>,
}

impl Hearing {
    fn ranked(&self, readings: Vec<NamedChord>) -> NamedChord {
        let mut readings = readings;
        readings.sort_by_key(|named| (!self.has_root_in_key(named), !named.same_chord(self.before.as_ref())));
        readings.remove(0)
    }

    fn has_root_in_key(&self, named: &NamedChord) -> bool {
        self.in_key.as_ref().is_none_or(|key| key.contains(&named.root.rem_euclid(OCTAVE)))
    }

    pub fn after(&self, named: &NamedChord) -> Hearing {
        Hearing {
            in_key: self.in_key.clone(),
            before: Some(named.clone()),
        }
    }
}

#[derive(Clone, Debug)]
struct Reading {
    symbol: &'static str,
    omission: Option<&'static str>,
    tension: Option<&'static str>,
    inversion: i64,
    root: i64,
}

impl Reading {
    fn kind_rank(&self) -> (i64, i64) {
        (omission_rank(self.omission, self.tension.is_some()), tension_rank(self.tension))
    }

    fn rank(&self) -> (i64, i64, i64, i64) {
        let (omitted, tensioned) = self.kind_rank();
        if self.omission.is_some() {
            return (omitted, tensioned, omitted_symbol_rank(self.symbol), self.inversion);
        }
        (omitted, tensioned, self.inversion, 0)
    }
}

/// The notes a chord sounds as the Realizer voices it, its tension added and the tones it leaves out gone, or None.
fn sounding(shape: &[i64], omission: Option<&str>, tension: Option<&str>) -> Option<Vec<i64>> {
    let mut notes = vec![0];
    notes.extend(shape);
    let tension_steps = tension
        .and_then(|tension| TENSIONS.iter().find(|(name, _)| *name == tension))
        .map(|(_, steps)| *steps);
    if tension_steps.is_some_and(|steps| notes.contains(&steps)) {
        return None;
    }
    if let Some(omission) = omission {
        let roles = OMITTED_ROLES.iter().find(|(name, _)| *name == omission).map(|(_, roles)| *roles).unwrap_or(&[]);
        notes.retain(|note| role_of(*note).is_none_or(|role| !roles.contains(&role)));
    }
    if let Some(steps) = tension_steps {
        notes.push(steps);
    }
    if notes.len() < 2 {
        return None;
    }
    notes.sort();
    Some(notes)
}

fn inverted(notes: &[i64], inversion: usize) -> Option<Vec<i64>> {
    if inversion > notes.len() - 1 {
        return None;
    }
    let mut voiced: Vec<i64> = notes[inversion..].to_vec();
    voiced.extend(notes[..inversion].iter().map(|note| note + OCTAVE));
    voiced.sort();
    Some(voiced)
}

/// Every shape a chord can sound, by its notes' half steps above its lowest, with each reading, in the order they were made.
fn voicings() -> &'static HashMap<Vec<i64>, Vec<Reading>> {
    static TABLE: OnceLock<HashMap<Vec<i64>, Vec<Reading>>> = OnceLock::new();
    TABLE.get_or_init(|| {
        let mut table: HashMap<Vec<i64>, Vec<Reading>> = HashMap::new();
        for omission in std::iter::once(None).chain(OMISSIONS.iter().map(|omission| Some(*omission))) {
            for tension in std::iter::once(None).chain(TENSIONS.iter().map(|(name, _)| Some(*name))) {
                for (symbol, shape) in crate_fixed_chords() {
                    if omission.is_some() && shape.len() != 3 {
                        continue;
                    }
                    if tension.is_some() && INTERVAL_CHORDS.contains(symbol) {
                        continue;
                    }
                    let Some(notes) = sounding(shape, omission, tension) else { continue };
                    for inversion in 0..=3 {
                        let Some(voiced) = inverted(&notes, inversion) else { continue };
                        let lowest = voiced[0];
                        let key: Vec<i64> = voiced.iter().map(|note| note - lowest).collect();
                        table.entry(key).or_default().push(Reading {
                            symbol,
                            omission,
                            tension,
                            inversion: inversion as i64,
                            root: -lowest,
                        });
                    }
                }
            }
        }
        table
    })
}

fn crate_fixed_chords() -> &'static [(&'static str, &'static [i64])] {
    llamatron_engine::tables::FIXED_CHORDS
}

fn voiced_chord(pitches: &[i64], hearing: &Hearing, omitted: bool, tensioned: bool) -> Option<NamedChord> {
    let mut unique = pitches.to_vec();
    unique.dedup();
    if pitches.len() < 2 || unique.len() != pitches.len() {
        return None;
    }
    let lowest = pitches[0];
    let key: Vec<i64> = pitches.iter().map(|pitch| pitch - lowest).collect();
    let mut readings: Vec<Reading> = voicings()
        .get(&key)
        .map(|found| {
            found
                .iter()
                .filter(|reading| reading.omission.is_some() == omitted && reading.tension.is_some() == tensioned)
                .cloned()
                .collect()
        })
        .unwrap_or_default();
    if readings.is_empty() {
        return None;
    }
    let soonest = readings.iter().map(Reading::kind_rank).min()?;
    readings.sort_by_key(Reading::rank);
    let named: Vec<NamedChord> = readings
        .iter()
        .filter(|reading| reading.kind_rank() == soonest)
        .map(|reading| NamedChord {
            symbol: Some(reading.symbol),
            inversion: reading.inversion,
            root: lowest + reading.root,
            doubling: None,
            omission: reading.omission,
            bass: None,
            bass_octave: false,
            tension: reading.tension,
        })
        .collect();
    Some(hearing.ranked(named))
}

fn doubled_notes(doubling: &str) -> (isize, Option<isize>, i64) {
    match doubling {
        file_format::Doubling::LOW_UP => (0, Some(1), 1),
        file_format::Doubling::ALL_UP => (0, None, 1),
        file_format::Doubling::ALL_DOWN => (0, None, -1),
        _ => (-1, None, -1),
    }
}

fn sliced(pitches: &[i64], first: isize, last: Option<isize>) -> Vec<i64> {
    let count = pitches.len() as isize;
    let place = |index: isize| (if index < 0 { (count + index).max(0) } else { index.min(count) }) as usize;
    let (start, end) = (place(first), last.map(place).unwrap_or(pitches.len()));
    if start < end {
        pitches[start..end].to_vec()
    } else {
        Vec::new()
    }
}

fn undoubled_pitches(pitches: &[i64], doubling: &str) -> Option<Vec<i64>> {
    let (first, last, octaves) = doubled_notes(doubling);
    let half_steps = octaves * OCTAVE;
    if last.is_some() || first != 0 {
        let copied = sliced(pitches, first, last).first()? + half_steps;
        if !pitches.contains(&copied) {
            return None;
        }
        return Some(pitches.iter().copied().filter(|pitch| *pitch != copied).collect());
    }
    let mut ordered = pitches.to_vec();
    ordered.sort();
    if half_steps < 0 {
        ordered.reverse();
    }
    let mut kept = Vec::new();
    let mut covered = Vec::new();
    for pitch in ordered {
        if !covered.contains(&pitch) {
            kept.push(pitch);
            covered.push(pitch + half_steps);
        }
    }
    kept.sort();
    Some(kept)
}

fn doubled_pitches(pitches: &[i64], doubling: &str) -> Vec<i64> {
    let (first, last, octaves) = doubled_notes(doubling);
    let mut all = pitches.to_vec();
    all.extend(sliced(pitches, first, last).iter().map(|pitch| pitch + octaves * OCTAVE));
    all.sort();
    all.dedup();
    all
}

fn doubled_chord(pitches: &[i64], hearing: &Hearing, omitted: bool, tensioned: bool) -> Option<NamedChord> {
    for doubling in DOUBLINGS {
        let Some(undoubled) = undoubled_pitches(pitches, doubling) else { continue };
        if doubled_pitches(&undoubled, doubling) != pitches {
            continue;
        }
        if undoubled.len() == 1 && !omitted && !tensioned {
            return Some(NamedChord {
                symbol: None,
                inversion: 0,
                root: undoubled[0],
                doubling: Some(doubling),
                omission: None,
                bass: None,
                bass_octave: false,
                tension: None,
            });
        }
        if let Some(named) = voiced_chord(&undoubled, hearing, omitted, tensioned) {
            return Some(NamedChord {
                doubling: Some(doubling),
                ..named
            });
        }
    }
    None
}

fn plain_chord(pitches: &[i64], hearing: &Hearing) -> Option<NamedChord> {
    voiced_chord(pitches, hearing, false, false)
}

fn chord_with_one_change(pitches: &[i64], hearing: &Hearing) -> Option<NamedChord> {
    doubled_chord(pitches, hearing, false, false)
        .or_else(|| voiced_chord(pitches, hearing, true, false))
        .or_else(|| voiced_chord(pitches, hearing, false, true))
}

fn chord_with_two_changes(pitches: &[i64], hearing: &Hearing) -> Option<NamedChord> {
    doubled_chord(pitches, hearing, true, false)
        .or_else(|| doubled_chord(pitches, hearing, false, true))
        .or_else(|| voiced_chord(pitches, hearing, true, true))
}

fn slash_chord(pitches: &[i64], hearing: &Hearing) -> Option<NamedChord> {
    let bass_octave = pitches.len() > 3 && pitches[1] - pitches[0] == OCTAVE;
    let under = if bass_octave { 2 } else { 1 };
    let (bass, rest) = (pitches[under - 1], &pitches[under..]);
    if rest.len() < 2 || rest[0] - bass < SLASH_GAP || rest[0] - bass >= OCTAVE {
        return None;
    }
    for reading in [plain_chord, chord_with_one_change] {
        if let Some(named) = reading(rest, hearing) {
            if named.root.rem_euclid(OCTAVE) != bass.rem_euclid(OCTAVE) {
                return Some(NamedChord {
                    bass: Some(bass),
                    bass_octave,
                    ..named
                });
            }
        }
    }
    None
}

/// The chord some pitches, lowest first, sound, or None for none a pattern's step can play.
pub fn chord_named(pitches: &[i64], hearing: &Hearing) -> Option<NamedChord> {
    for reading in [plain_chord, chord_with_one_change, chord_with_two_changes, slash_chord] {
        if let Some(named) = reading(pitches, hearing) {
            return Some(named);
        }
    }
    None
}
