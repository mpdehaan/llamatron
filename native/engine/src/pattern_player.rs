// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Playing one pass through a pattern, step by step, into notes, chords and rests (the Python
//! engine/realizer/pattern_player.py).
//!
//! Every step takes its step size. A step that plays sounds for its gate, which can run past later steps but not past the
//! end of the pass. A tied step plays nothing and keeps the note before it sounding to the tied step's end, whatever its
//! gate. Ties at the very start of a pass are left for whoever joins the passes, who lengthens the note the pass before
//! ended with.

use crate::error::{RenderError, Rendered};
use crate::order::{DrawnWhenAsked, StepOrder};
use crate::sound::{scale_sound, NoteSound, OutOfRange, Sound};
use crate::tables::{fixed_chord, gate_modifier};
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::pattern::Pattern;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::{Song, Track};
use llamatron_model::schema::checking::written_length;
use llamatron_model::schema::generated::defaults::{DEFAULT_PROBABILITY, DEFAULT_RATCHET};
use llamatron_model::schema::generated::file_format::{Direction, Row, ACCIDENTALS, PATTERN_ROWS, SCALE_CHORDS};
use llamatron_model::schema::generated::limits::{MAX_GATE, MAX_PROBABILITY};
use llamatron_model::schema::generated::midi::{MAX_VELOCITY, MIN_VELOCITY};
use llamatron_model::values::generated::note::{MAX_OCTAVE, MIN_OCTAVE};
use llamatron_model::values::scale::Scale;
use llamatron_strings::{errors, named};

/// How many octaves away a moved note may go to find one that fits the MIDI range.
const MAX_OCTAVE_CHANGE: i64 = 10;

/// The rows the port plays so far; a pattern holding anything on another row is not ported yet.
const PLAYED_ROWS: &[&str] = &[
    Row::DEGREE,
    Row::GATE,
    Row::DOT,
    Row::ACCIDENTAL,
    Row::OCTAVE,
    Row::CHORD,
    Row::VELOCITY,
    Row::ACCENT,
    Row::PROBABILITY,
    Row::GLIDE,
    Row::TIE,
    Row::RATCHET,
    Row::RATCHET_OFFSET,
];

/// One pass through a pattern: its sounds, how long the ties at its start last, and how long the pass lasts.
#[derive(Clone, Debug)]
pub struct Pass {
    pub sounds: Vec<Sound>,
    pub tied_from_before: Rational,
    pub length: Rational,
    pub done: bool,
}

/// What one step holds on the rows a pass plays.
#[derive(Clone, Debug, Default)]
struct StepValues {
    degree: Option<Data>,
    gate: Option<Data>,
    dot: Option<String>,
    accidental: Option<String>,
    octave: Option<i64>,
    chord: Option<String>,
    velocity: Option<i64>,
    accent: bool,
    probability: Option<i64>,
    glide: bool,
    tie: bool,
    ratchet: Option<i64>,
    ratchet_offset: Option<i64>,
}

fn truthy(value: &Data) -> bool {
    match value {
        Data::Null | Data::Bool(false) => false,
        Data::Whole(number) => *number != 0,
        Data::Text(text) => !text.is_empty(),
        Data::List(items) => !items.is_empty(),
        _ => true,
    }
}

fn whole(value: &Data) -> Option<i64> {
    value.as_whole().map(|value| value as i64)
}

fn text(value: &Data) -> Option<String> {
    (!value.is_null()).then(|| value.python_str())
}

/// Every step's values, or the row the port does not play yet that a step of the pattern holds something on.
fn every_step_values(pattern: &Pattern) -> Rendered<Vec<StepValues>> {
    for row in PATTERN_ROWS {
        if !PLAYED_ROWS.contains(row) && pattern.row(row).is_some_and(|values| values.iter().any(truthy)) {
            return Err(RenderError::NotPorted(format!("the {row} row")));
        }
    }
    let mut steps = vec![StepValues::default(); pattern.get_steps() as usize];
    let column = |row: &str| pattern.row(row).map(<[Data]>::to_vec);
    for (row, values) in PLAYED_ROWS.iter().filter_map(|row| column(row).map(|values| (*row, values))) {
        for (step, value) in steps.iter_mut().zip(&values) {
            match row {
                Row::DEGREE => step.degree = (!value.is_null()).then(|| value.clone()),
                Row::GATE => step.gate = (!value.is_null()).then(|| value.clone()),
                Row::DOT => step.dot = text(value),
                Row::ACCIDENTAL => step.accidental = text(value),
                Row::OCTAVE => step.octave = whole(value),
                Row::CHORD => step.chord = text(value),
                Row::VELOCITY => step.velocity = whole(value),
                Row::ACCENT => step.accent = truthy(value),
                Row::PROBABILITY => step.probability = whole(value),
                Row::GLIDE => step.glide = truthy(value),
                Row::TIE => step.tie = truthy(value),
                Row::RATCHET => step.ratchet = whole(value),
                _ => step.ratchet_offset = whole(value),
            }
        }
    }
    Ok(steps)
}

/// Plays a track's patterns in one scene, a pass at a time.
pub struct PatternPlayer<'a> {
    setlist: &'a Setlist,
    scene_number: i64,
    scale_name: Option<String>,
    transpose: i64,
    default_velocity: i64,
    accent: i64,
    default_octave: i64,
    default_drum_octave: i64,
}

impl<'a> PatternPlayer<'a> {
    pub fn new(setlist: &'a Setlist, song: &Song, track: &Track, scene_number: i64, scale_name: Option<String>) -> PatternPlayer<'a> {
        PatternPlayer {
            setlist,
            scene_number,
            scale_name,
            transpose: track.get_transpose(),
            default_velocity: song.default_velocity_of(track, setlist),
            accent: song.accent_of(track, setlist),
            default_octave: setlist.get_default_octave(),
            default_drum_octave: setlist.get_default_drum_octave(),
        }
    }

    pub fn pattern(&self, name: &str) -> Rendered<&'a Pattern> {
        self.setlist
            .get_pattern(name)
            .ok_or_else(|| RenderError::Refused(format!("no pattern called ({name})")))
    }

    /// How long one pass through a pattern lasts.
    pub fn pattern_length(&self, pattern: &Pattern) -> Rational {
        self.setlist.get_pattern_length(pattern)
    }

    /// One pass through a pattern, its steps in the pattern's direction unless direction overrides it.
    pub fn play_pass(&self, pattern_name: &str, direction: Option<&str>, rolls: &mut DrawnWhenAsked, order: &mut StepOrder) -> Rendered<Pass> {
        let pattern = self.pattern(pattern_name)?;
        let step_length = self.setlist.get_pattern_step_size(pattern);
        let pass_length = self.pattern_length(pattern);
        let where_ = named(errors::ERR_WHERE_PATTERN, &[("name", pattern_name.into())]);
        let values = every_step_values(pattern)?;
        let drum = pattern.is_drum();
        let own_direction = pattern.get_direction().unwrap_or(Direction::FORWARD.to_string());
        let direction = direction.map(str::to_string).unwrap_or(own_direction);
        let steps = order.next_steps(&format!("steps/{pattern_name}"), values.len(), &direction);
        // What each step that plays sounds: when it starts in the pass, and its pieces, a note or chord for each ratchet.
        let mut sounding: Vec<(Rational, Vec<Sound>)> = Vec::new();
        let mut tied_to: Option<usize> = None;
        let mut leading_ties = 0;
        for (slot, step) in steps.iter().enumerate() {
            let time = step_length * Rational::whole(slot as i128);
            let values = &values[*step];
            if values.tie {
                if let Some(place) = tied_to {
                    sounding[place] = tied(&sounding[place], time + step_length);
                } else if slot == leading_ties {
                    leading_ties += 1;
                }
                continue;
            }
            if values.degree.is_none() {
                tied_to = None;
                continue;
            }
            tied_to = Some(sounding.len());
            let velocity_added = if values.accent { self.accent } else { 0 };
            let gate = gate_of(values, step_length).min(pass_length - time);
            sounding.push((time, self.step(values, gate, drum, &where_, velocity_added, rolls)?));
        }
        let sounds = in_sequence(&sounding, pass_length, step_length);
        Ok(Pass {
            sounds,
            tied_from_before: step_length * Rational::whole(leading_ties as i128),
            length: pass_length,
            done: false,
        })
    }

    /// What one step plays, lasting its gate, as more than one sound if it ratchets.
    fn step(&self, values: &StepValues, length: Rational, drum: bool, where_: &str, velocity_added: i64, rolls: &mut DrawnWhenAsked) -> Rendered<Vec<Sound>> {
        let octave = values.octave.unwrap_or(if drum { self.default_drum_octave } else { self.default_octave });
        let velocity = (values.velocity.unwrap_or(self.default_velocity) + velocity_added).clamp(MIN_VELOCITY, MAX_VELOCITY);
        let ratchet = values.ratchet.filter(|ratchet| *ratchet != 0).unwrap_or(DEFAULT_RATCHET);
        let offset = values.ratchet_offset.unwrap_or(0);
        let transpose = if drum { 0 } else { self.transpose };
        let slice_length = length / Rational::whole(ratchet as i128);
        let mut slices = Vec::new();
        for place in 0..ratchet {
            let shift = transpose + place * offset;
            // Only the last slice glides into what follows the step.
            let glide = values.glide && place == ratchet - 1;
            slices.push(self.sound(values, drum, slice_length, velocity, glide, octave, shift, where_)?);
        }
        Ok(played_by_chance(slices, values.probability, rolls))
    }

    /// A step's note or chord, moved by scale degrees or, for drums, half steps; a note moved outside the MIDI range goes
    /// to the nearest octave that fits.
    #[allow(clippy::too_many_arguments)]
    fn sound(&self, values: &StepValues, drum: bool, length: Rational, velocity: i64, glide: bool, octave: i64, shift: i64, where_: &str) -> Rendered<Sound> {
        let size = self.notes_per_octave(drum)?;
        let (octaves, shift) = (shift.div_euclid(size), shift.rem_euclid(size));
        let octave = (octave + octaves).clamp(MIN_OCTAVE, MAX_OCTAVE);
        let attempt = |at_octave: i64| -> Rendered<Result<Sound, OutOfRange>> {
            if drum {
                Ok(drum_sound(values, at_octave, length, velocity, glide, shift))
            } else {
                self.degree_sound(values, length, velocity, glide, at_octave, shift, where_)
            }
        };
        let problem = match attempt(octave)? {
            Ok(sound) => return Ok(sound),
            Err(problem) => problem,
        };
        if shift != 0 || octaves != 0 {
            for size in 1..=MAX_OCTAVE_CHANGE {
                for change in [-size, size] {
                    if let Ok(sound) = attempt(octave + change)? {
                        return Ok(sound);
                    }
                }
            }
        }
        Err(RenderError::Refused(named(
            errors::ERR_CANT_PLAY,
            &[("where", where_.into()), ("problem", problem.0.as_str().into())],
        )))
    }

    /// How many notes a move needs to go up an octave: the size of the scale, or 12 half steps for drums.
    fn notes_per_octave(&self, drum: bool) -> Rendered<i64> {
        let Some(name) = self.scale_name.as_ref().filter(|_| !drum) else {
            return Ok(12);
        };
        let scale = self
            .named_scale(name)?
            .scale_at(MIN_OCTAVE)
            .map_err(|problem| RenderError::Refused(problem.0))?;
        Ok(scale.get_type().get_shape().len() as i64)
    }

    fn named_scale(&self, name: &str) -> Rendered<&'a llamatron_model::objects::named::NamedScale> {
        self.setlist
            .get_named_scale(name)
            .ok_or_else(|| RenderError::NotPorted(format!("a scale the set does not name ({name})")))
    }

    /// A step's note or chord of the scale; the outer error refuses the set, the inner is a note that does not fit.
    #[allow(clippy::too_many_arguments)]
    fn degree_sound(
        &self,
        values: &StepValues,
        length: Rational,
        velocity: i64,
        glide: bool,
        octave: i64,
        shift: i64,
        where_: &str,
    ) -> Rendered<Result<Sound, OutOfRange>> {
        let Some(scale_name) = &self.scale_name else {
            return Err(RenderError::Refused(named(
                errors::ERR_NO_SCALE,
                &[("where", where_.into()), ("scene", self.scene_number.into())],
            )));
        };
        let scale: Scale = match self.named_scale(scale_name)?.scale_at(octave) {
            Ok(scale) => scale,
            Err(problem) => return Ok(Err(OutOfRange(problem.0))),
        };
        let half_steps = values
            .accidental
            .as_deref()
            .and_then(|accidental| ACCIDENTALS.iter().find(|(found, _)| *found == accidental))
            .map(|(_, steps)| *steps)
            .unwrap_or(0);
        let degree = values.degree.as_ref().and_then(Data::as_whole).unwrap_or(0) as i64;
        let at = |degree: i64| scale_sound(&scale, degree, shift, half_steps, Some(length), Some(velocity), glide);
        let symbol = values.chord.as_deref();
        if let Some(symbol) = symbol.filter(|symbol| fixed_chord(symbol).is_none()) {
            // A chord of scale notes: the step's degree and the scale degrees above it that a symbol like 7 names.
            let Some((_, above)) = SCALE_CHORDS.iter().find(|(found, _)| *found == symbol) else {
                return Err(RenderError::Refused(format!("no chord called {symbol}")));
            };
            let notes: Result<Vec<NoteSound>, OutOfRange> = above.iter().map(|above| at(degree + above)).collect();
            return Ok(notes.map(Sound::chord));
        }
        let root = match at(degree) {
            Ok(root) => root,
            Err(problem) => return Ok(Err(problem)),
        };
        Ok(match symbol.and_then(fixed_chord) {
            None => Ok(Sound::Note(root)),
            Some(shape) => Sound::chord_above(root, shape),
        })
    }
}

/// A drum step's note, named by its letter and accidental, moved some half steps.
fn drum_sound(values: &StepValues, octave: i64, length: Rational, velocity: i64, glide: bool, shift: i64) -> Result<Sound, OutOfRange> {
    let letter = values.degree.as_ref().map(Data::python_str).unwrap_or_default();
    let name = format!("{letter}{}", values.accidental.as_deref().unwrap_or(""));
    let note = Sound::named_note(&name, octave, Some(length), Some(velocity), glide)?;
    if shift == 0 {
        return Ok(Sound::Note(note));
    }
    note.half_step(shift)
        .map(Sound::Note)
        .ok_or_else(|| OutOfRange(format!("{name} moved {shift} half steps leaves the MIDI range")))
}

/// How long a step's note sounds: its gate, or one step, made dotted or a triplet by its Dot row.
fn gate_of(values: &StepValues, step_length: Rational) -> Rational {
    let gate = values
        .gate
        .as_ref()
        .and_then(|gate| written_length(gate, Rational::whole(MAX_GATE as i128)).ok())
        .map(llamatron_math::Number::Exact)
        .map(crate::sound::exact_length)
        .unwrap_or(step_length);
    match values.dot.as_deref().and_then(gate_modifier) {
        None => gate,
        Some(modifier) => gate * modifier,
    }
}

/// A step's slices as its probability plays them, each a rest where its roll fails.
fn played_by_chance(slices: Vec<Sound>, probability: Option<i64>, rolls: &mut DrawnWhenAsked) -> Vec<Sound> {
    let probability = probability.unwrap_or(DEFAULT_PROBABILITY);
    if probability >= MAX_PROBABILITY {
        return slices;
    }
    slices
        .into_iter()
        .map(|piece| {
            if rolls.random() * (MAX_PROBABILITY as f64) < probability as f64 {
                piece
            } else {
                Sound::Rest(piece.place())
            }
        })
        .collect()
}

fn total_length(pieces: &[Sound]) -> Rational {
    pieces.iter().fold(Rational::ZERO, |total, piece| total + piece.place())
}

/// What a step sounds, lasting exactly until end, for a tie on the step that ends there: the last piece lengthened, or
/// where the gate reached past the tie, the pieces sharing the tied span equally, so that a ratchet keeps its count.
fn tied(sounding: &(Rational, Vec<Sound>), end: Rational) -> (Rational, Vec<Sound>) {
    let (start, pieces) = sounding;
    let extra = end - (*start + total_length(pieces));
    let last = &pieces[pieces.len() - 1];
    if extra == Rational::ZERO || last.is_rest() {
        return sounding.clone();
    }
    if extra > Rational::ZERO {
        let mut lengthened = pieces[..pieces.len() - 1].to_vec();
        lengthened.push(last.lasting(Some(last.place() + extra)));
        return (*start, lengthened);
    }
    let span = (end - *start) / Rational::whole(pieces.len() as i128);
    (*start, pieces.iter().map(|piece| piece.lasting(Some(span))).collect())
}

/// The notes of a pass as a clip's sequence of sounds: a note whose gate reaches exactly to the next is an ordinary position,
/// a shorter one is followed by rests a step each, and a longer one is held so that the next starts while it sounds.
fn in_sequence(sounding: &[(Rational, Vec<Sound>)], length: Rational, step_length: Rational) -> Vec<Sound> {
    let mut positions = Vec::new();
    let mut now = Rational::ZERO;
    for (place, (start, played)) in sounding.iter().enumerate() {
        let following = sounding.get(place + 1).map(|(start, _)| *start).unwrap_or(length);
        if now < *start {
            positions.extend(rests(now, *start, step_length));
        }
        let gate = total_length(played);
        let gap = following - *start;
        if gap < gate {
            if played.len() == 1 && played[0].is_rest() {
                // Probability dropped the note, so there is nothing to hold over the next note: its steps are silent.
                positions.extend(rests(*start, following, step_length));
            } else if played.len() > 1 {
                positions.push(Sound::phrase(played.clone(), gap));
            } else {
                positions.push(Sound::held(played[0].clone(), gap));
            }
            now = following;
        } else {
            positions.extend(played.iter().cloned());
            now = *start + gate;
        }
    }
    if now < length {
        positions.extend(rests(now, length, step_length));
    }
    positions
}

/// The rests from a start to an end, one a step, the first ending at the next step.
fn rests(start: Rational, end: Rational, step_length: Rational) -> Vec<Sound> {
    let mut rests = Vec::new();
    let mut now = start;
    let mut step_end = step_length * Rational::whole((start / step_length).floor() + 1);
    while now < end {
        let piece_end = step_end.min(end);
        rests.push(Sound::Rest(piece_end - now));
        now = piece_end;
        step_end = step_end + step_length;
    }
    rests
}
