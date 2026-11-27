// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Arp generator (the Python engine/generators/arp/): each chord played one note at a time, a step long, for as long as
//! the chord lasts, in its order, climbing through its octave range, each note moved along the scale by its offsets, a
//! silent offset a rest that uses up no note. With offsets or an octave range a single note is a chord of one.

use crate::clip::Clip;
use crate::error::{RenderError, Rendered};
use crate::generators::GeneratorState;
use crate::positions::fit_to_length;
use crate::sound::{along_scale, NoteSound, Sound};
use llamatron_math::{PythonRandom, Rational, Seed};
use llamatron_model::file::data::Data;
use llamatron_model::schema::checking::{time_length, TimeLength};
use llamatron_model::schema::generated::file_format::{GENERATOR_ENABLED, GENERATOR_RESTART};
use llamatron_model::values::scale::Scale;
use std::cell::RefCell;

const STEP: &str = "step";
const ORDER: &str = "order";
const OCTAVE_RANGE: &str = "octave_range";
const OCTAVE_JUMP: &str = "octave_jump";
const OFFSETS: &str = "offsets";
const PORTED: &[&str] = &[GENERATOR_ENABLED, GENERATOR_RESTART, STEP, ORDER, OCTAVE_RANGE, OCTAVE_JUMP, OFFSETS];

#[derive(Clone, Copy, PartialEq)]
enum Order {
    Up,
    Down,
    UpDown,
    DownUp,
    Random,
}

pub struct Arp {
    step: Rational,
    order: Order,
    seed: Option<i128>,
    octave_range: i64,
    after_each_note: bool,
    offsets: Option<Vec<Option<i64>>>,
    // Where the draws of the same track's clip before in the run reached, for an Arp that carries on, and where this one's do.
    start_state: Option<PythonRandom>,
    end_state: RefCell<Option<PythonRandom>>,
}

impl Arp {
    /// An arpeggiator from its settings at a clip's place: the clip's pattern's step unless its own is set, a step in bars
    /// that many of the song's bars, and the seed its place gives.
    pub fn of(settings: &Data, pattern_step: Rational, bar: Rational, seed: Option<i128>, start_state: Option<GeneratorState>) -> Rendered<Arp> {
        for (key, value) in settings.as_map().unwrap_or(&[]) {
            let name = key.python_str();
            if !PORTED.contains(&name.as_str()) && !value.is_null() {
                return Err(RenderError::NotPorted(format!("the Arp generator's {name} setting")));
            }
        }
        let written = |name: &str| settings.get(name).filter(|value| !value.is_null());
        let step = match written(STEP) {
            None => pattern_step,
            Some(step) => match time_length(step).map_err(|problem| RenderError::Refused(problem.message))? {
                TimeLength::Bars(count) => bar * Rational::whole(count as i128),
                TimeLength::Length(length) => length,
            },
        };
        let order = match written(ORDER).map(Data::python_str).as_deref() {
            None | Some("up") => Order::Up,
            Some("down") => Order::Down,
            Some("up_down") => Order::UpDown,
            Some("down_up") => Order::DownUp,
            Some(_) => Order::Random,
        };
        let offsets = written(OFFSETS)
            .and_then(Data::as_list)
            .map(|offsets| offsets.iter().map(|offset| offset.as_whole().map(|offset| offset as i64)).collect());
        Ok(Arp {
            step,
            order,
            seed,
            octave_range: written(OCTAVE_RANGE).and_then(Data::as_whole).map(|range| range as i64).unwrap_or(1),
            after_each_note: written(OCTAVE_JUMP).map(Data::python_str).as_deref() == Some("after_each_note"),
            offsets,
            start_state: match start_state {
                Some(GeneratorState::Random(random)) => Some(*random),
                _ => None,
            },
            end_state: RefCell::new(None),
        })
    }

    pub fn generate(&self, clip: &Clip) -> Rendered<Clip> {
        let mut random = match (self.seed, &self.start_state) {
            (Some(_), Some(state)) => state.clone(),
            (Some(seed), None) => PythonRandom::new(Seed::Whole(seed)),
            (None, _) => PythonRandom::unseeded(),
        };
        let original = clip.resolved_sounds()?;
        let scale = clip.scale.as_ref();
        let mut positions = self.arpeggiate(&original, &mut random, scale)?;
        if let Some(wanted) = clip.length {
            let mut total = positions.iter().fold(Rational::ZERO, |total, position| total + position.place());
            while !positions.is_empty() && total < wanted {
                let more = self.arpeggiate(&original, &mut random, scale)?;
                total = more.iter().fold(total, |total, position| total + position.place());
                positions.extend(more);
            }
            positions = fit_to_length(&positions, wanted);
        }
        if self.seed.is_some() {
            *self.end_state.borrow_mut() = Some(random);
        }
        Ok(Clip {
            sounds: positions,
            time_signature: None,
            looping: true,
            groove: None,
            ..clip.clone()
        })
    }

    /// Where its draws reached, for the same track's next clip in its run to carry on from.
    pub fn end_state(&self) -> Option<GeneratorState> {
        self.end_state.borrow().clone().map(|random| GeneratorState::Random(Box::new(random)))
    }

    fn plays_single_notes(&self) -> bool {
        self.offsets.is_some() || self.octave_range > 1
    }

    fn arpeggiate(&self, positions: &[Sound], random: &mut PythonRandom, scale: Option<&Scale>) -> Rendered<Vec<Sound>> {
        let mut result = Vec::new();
        for position in positions {
            match position {
                Sound::Held { length, sound } => result.push(Sound::phrase(self.arpeggiate(std::slice::from_ref(sound), random, scale)?, *length)),
                Sound::Phrase { length, parts } => result.push(Sound::phrase(self.arpeggiate(parts, random, scale)?, *length)),
                Sound::Chord { notes, length } => {
                    result.extend(self.arpeggiate_chord(lowest_to_highest(notes), length.unwrap_or(Rational::ZERO), random, scale)?)
                }
                Sound::Note(note) if self.plays_single_notes() => {
                    result.extend(self.arpeggiate_chord(vec![*note], note.length.unwrap_or(Rational::ZERO), random, scale)?)
                }
                other => result.push(other.clone()),
            }
        }
        Ok(result)
    }

    fn arpeggiate_chord(&self, chord: Vec<NoteSound>, length: Rational, random: &mut PythonRandom, scale: Option<&Scale>) -> Rendered<Vec<Sound>> {
        let notes = self.climb(&chord)?;
        let pattern = self.pattern(&notes);
        let mut result = Vec::new();
        let mut remaining = length;
        let mut index = 0;
        let mut place = 0;
        while remaining > Rational::ZERO {
            let length = self.step.min(remaining);
            let offset = match &self.offsets {
                Some(offsets) => offsets[place % offsets.len()],
                None => Some(0),
            };
            place += 1;
            match offset {
                None => result.push(Sound::Rest(length)),
                Some(offset) => {
                    let note = match &pattern {
                        Some(pattern) => pattern[index % pattern.len()],
                        None => *random.choice(&notes),
                    };
                    let moved = along_scale(note, offset, scale).map_err(|problem| RenderError::Refused(problem.0))?;
                    result.push(Sound::Note(NoteSound { length: Some(length), ..moved }));
                    index += 1;
                }
            }
            remaining = remaining - length;
        }
        Ok(result)
    }

    /// The chord's notes going up through the octave range, in the octave jump's order.
    fn climb(&self, notes: &[NoteSound]) -> Rendered<Vec<NoteSound>> {
        let up = |note: &NoteSound, octave: i64| {
            note.half_step(12 * octave)
                .ok_or_else(|| RenderError::Refused("an arpeggiated note leaves the MIDI range".to_string()))
        };
        let mut climbed = Vec::new();
        if self.after_each_note {
            for note in notes {
                for octave in 0..self.octave_range {
                    climbed.push(up(note, octave)?);
                }
            }
        } else {
            for octave in 0..self.octave_range {
                for note in notes {
                    climbed.push(up(note, octave)?);
                }
            }
        }
        Ok(climbed)
    }

    /// The notes in the order they repeat, or None for a random order; a turn plays neither end twice.
    fn pattern(&self, notes: &[NoteSound]) -> Option<Vec<NoteSound>> {
        let down: Vec<NoteSound> = notes.iter().rev().copied().collect();
        let turn = |notes: &[NoteSound]| -> Vec<NoteSound> {
            if notes.len() < 3 {
                return Vec::new();
            }
            notes[1..notes.len() - 1].iter().rev().copied().collect()
        };
        Some(match self.order {
            Order::Up => notes.to_vec(),
            Order::Down => down,
            Order::UpDown => [notes.to_vec(), turn(notes)].concat(),
            Order::DownUp => [down.clone(), turn(&down)].concat(),
            Order::Random => return None,
        })
    }
}

/// A chord's notes from lowest to highest, each pitch once, the first of a pitch kept.
fn lowest_to_highest(notes: &[NoteSound]) -> Vec<NoteSound> {
    let mut kept: Vec<NoteSound> = Vec::new();
    for note in notes {
        if !kept.iter().any(|found| found.midi == note.midi) {
            kept.push(*note);
        }
    }
    kept.sort_by_key(|note| note.midi);
    kept
}
