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

use crate::clip::Control;
use crate::drift::{DriftPlay, StepEffects};
use crate::error::{RenderError, Rendered};
use crate::grab_source::GrabSource;
use crate::order::{DrawnWhenAsked, StepOrder};
use crate::registers::{holds, Registers};
use crate::sound::{along_scale, scale_sound, NoteSound, OutOfRange, Sound};
use crate::statements::Statement;
use crate::tables::{doubled_notes, fixed_chord, gate_modifier};
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::fundamentals::role_of;
use llamatron_model::objects::pattern::Pattern;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::{Song, Track};
use llamatron_model::schema::checking::written_length;
use llamatron_model::schema::generated::defaults::{DEFAULT_PROBABILITY, DEFAULT_RATCHET};
use llamatron_model::schema::generated::file_format::{Direction, Row, ACCIDENTALS, BASS_NOTES, CC_ROWS, OMITTED_ROLES, PATTERN_ROWS, SCALE_CHORDS, TENSIONS};
use llamatron_model::schema::generated::limits::{MAX_GATE, MAX_PROBABILITY, MIN_PROBABILITY};
use llamatron_model::schema::generated::midi::{MAX_VELOCITY, MIN_VELOCITY};
use llamatron_model::values::generated::note::SHARP_NAMES;
use llamatron_model::values::generated::note::{MAX_OCTAVE, MIN_OCTAVE};
use llamatron_model::values::scale::Scale;
use llamatron_model::values::scale::ScaleType;
use llamatron_strings::{errors, named};
use std::cell::RefCell;
use std::rc::Rc;

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
    Row::TENSION,
    Row::OMIT,
    Row::INVERSION,
    Row::DOUBLE,
    Row::BASS,
    Row::BASS_OCTAVE,
    Row::CHORD_SCALE,
    Row::CC1,
    Row::CC2,
    Row::CC3,
    Row::CC4,
    Row::SLIDE,
    Row::GRAB,
];

/// A draw's rows, AD first: what a step adds of its value to its note and its velocity, and its Reset.
const NOTE_ROWS: [&str; 8] = [
    Row::AD_NOTE,
    Row::BD_NOTE,
    Row::CD_NOTE,
    Row::DD_NOTE,
    Row::ED_NOTE,
    Row::FD_NOTE,
    Row::GD_NOTE,
    Row::HD_NOTE,
];
const VELOCITY_ROWS: [&str; 8] = [
    Row::AD_VELOCITY,
    Row::BD_VELOCITY,
    Row::CD_VELOCITY,
    Row::DD_VELOCITY,
    Row::ED_VELOCITY,
    Row::FD_VELOCITY,
    Row::GD_VELOCITY,
    Row::HD_VELOCITY,
];
const RESET_ROWS: [&str; 8] = [
    Row::AD_RESET,
    Row::BD_RESET,
    Row::CD_RESET,
    Row::DD_RESET,
    Row::ED_RESET,
    Row::FD_RESET,
    Row::GD_RESET,
    Row::HD_RESET,
];
/// Each kind of statement's rows, its register first: Stop, Restart and Mute.
const STATEMENT_ROWS: [[&str; 5]; 3] = [
    [Row::STOP_C1, Row::STOP_C2, Row::STOP_C3, Row::STOP_C4, Row::STOP_C5],
    [Row::RESTART_C1, Row::RESTART_C2, Row::RESTART_C3, Row::RESTART_C4, Row::RESTART_C5],
    [Row::MUTE_C1, Row::MUTE_C2, Row::MUTE_C3, Row::MUTE_C4, Row::MUTE_C5],
];
const STOP: usize = 0;
const RESTART: usize = 1;
const MUTE: usize = 2;

/// Whether a row is one the draws' code reads, apart from the rows a step plays from.
fn is_draw_row(row: &str) -> bool {
    NOTE_ROWS.contains(&row) || VELOCITY_ROWS.contains(&row) || RESET_ROWS.contains(&row) || STATEMENT_ROWS.iter().any(|rows| rows.contains(&row))
}

/// What one step does to the song's draws, before its statements read the values: the draws it resets, then those it takes.
#[derive(Clone, Debug, Default)]
struct StepDraws {
    resets: Vec<usize>,
    drawn: Vec<usize>,
}

/// One pass through a pattern: its sounds, how long the ties at its start last, and how long the pass lasts.
#[derive(Clone, Debug)]
pub struct Pass {
    pub sounds: Vec<Sound>,
    pub tied_from_before: Rational,
    pub length: Rational,
    pub done: bool,
    pub controls: Vec<Control>,
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
    tension: Vec<String>,
    omit: Option<String>,
    inversion: Option<i64>,
    double: Option<String>,
    bass: Option<String>,
    bass_octave: bool,
    chord_scale: Option<String>,
    cc: [Option<i64>; 4],
    slide: bool,
    grab: bool,
    // What the step adds of each draw's value to its note and its velocity, which draws it resets, and its statements.
    note_adds: [i64; 8],
    velocity_adds: [i64; 8],
    resets: [bool; 8],
    statements: [Option<Statement>; 3],
}

impl StepValues {
    /// The draws the step's rows use, each once, in the draws' order.
    fn draws_used(&self) -> Vec<usize> {
        (0..8).filter(|name| self.note_adds[*name] != 0 || self.velocity_adds[*name] != 0).collect()
    }

    fn draws_reset(&self) -> Vec<usize> {
        (0..8).filter(|name| self.resets[*name]).collect()
    }
}

impl StepValues {
    /// Whether the step's chord rows voice its note or chord: tensions, an omission, an inversion, a doubling or a bass.
    fn is_voiced(&self) -> bool {
        !self.tension.is_empty()
            || self.omit.is_some()
            || self.inversion.is_some_and(|inversion| inversion != 0)
            || self.double.is_some()
            || self.bass.is_some()
    }
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
        if !PLAYED_ROWS.contains(row) && !is_draw_row(row) && pattern.row(row).is_some_and(|values| values.iter().any(truthy)) {
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
                Row::RATCHET_OFFSET => step.ratchet_offset = whole(value),
                Row::TENSION => step.tension = value.as_list().unwrap_or(&[]).iter().map(Data::python_str).collect(),
                Row::OMIT => step.omit = text(value).filter(|omit| !omit.is_empty()),
                Row::INVERSION => step.inversion = whole(value),
                Row::DOUBLE => step.double = text(value).filter(|double| !double.is_empty()),
                Row::BASS => step.bass = text(value).filter(|bass| !bass.is_empty()),
                Row::BASS_OCTAVE => step.bass_octave = truthy(value),
                Row::CHORD_SCALE => step.chord_scale = text(value).filter(|kind| !kind.is_empty()),
                Row::SLIDE => step.slide = truthy(value),
                Row::GRAB => step.grab = truthy(value),
                lane => step.cc[CC_ROWS.iter().position(|row| *row == lane).unwrap_or(0)] = whole(value),
            }
        }
    }
    for name in 0..8 {
        for (rows, kind) in [(&NOTE_ROWS, 0), (&VELOCITY_ROWS, 1), (&RESET_ROWS, 2)] {
            let Some(values) = pattern.row(rows[name]) else { continue };
            for (step, value) in steps.iter_mut().zip(values) {
                match kind {
                    0 => step.note_adds[name] = whole(value).unwrap_or(0),
                    1 => step.velocity_adds[name] = whole(value).unwrap_or(0),
                    _ => step.resets[name] = truthy(value),
                }
            }
        }
    }
    for (kind, rows) in STATEMENT_ROWS.iter().enumerate() {
        // A kind of statement is held where any step names its register.
        if !pattern.row(rows[0]).is_some_and(|values| values.iter().any(truthy)) {
            continue;
        }
        let columns: Vec<Option<&[Data]>> = rows.iter().map(|row| pattern.row(row)).collect();
        for (place, step) in steps.iter_mut().enumerate() {
            let parts: Vec<Option<&Data>> = columns
                .iter()
                .map(|column| column.and_then(|values| values.get(place)).filter(|value| !value.is_null()))
                .collect();
            step.statements[kind] = Statement::of(&parts);
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
    // The clip's scale, rooted at its octave, which a grabbed note moves along and builds its chord in.
    clip_scale: Option<Scale>,
    // What the clip's grab steps take notes from, or None for a clip that grabs nothing.
    grab: Option<GrabSource>,
    // The drifts the clip hears, or None, and what they do to the step being played.
    hearing: Option<Hearing>,
    effects: RefCell<StepEffects>,
    // Which of the song's draws a statement reading them draws from.
    redrawing: [bool; 8],
}

/// The drifts a clip hears: the song's play of them, the ones its chains name, where each one's clock starts, and where the
/// clip's scene starts from the song's top.
pub struct Hearing {
    pub drift: Rc<RefCell<DriftPlay>>,
    pub names: Vec<String>,
    pub origins: Vec<(String, Rational)>,
    pub scene_start: Rational,
}

impl<'a> PatternPlayer<'a> {
    pub fn new(setlist: &'a Setlist, song: &Song, track: &Track, scene_number: i64, scale_name: Option<String>) -> PatternPlayer<'a> {
        PatternPlayer {
            clip_scale: None,
            grab: None,
            hearing: None,
            effects: RefCell::new(StepEffects::default()),
            redrawing: [false; 8],
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

    /// The player with the clip's scale and what its grab steps take notes from.
    pub fn grabbing(self, clip_scale: Option<Scale>, grab: Option<GrabSource>) -> PatternPlayer<'a> {
        PatternPlayer { clip_scale, grab, ..self }
    }

    /// The player knowing which of the song's draws redraw in conditions.
    pub fn redrawing(self, redrawing: [bool; 8]) -> PatternPlayer<'a> {
        PatternPlayer { redrawing, ..self }
    }

    /// Whether any step's statement reads a draw that redraws in conditions.
    fn redraws_in_statements(&self, values: &[StepValues]) -> bool {
        values.iter().any(|step| {
            step.statements
                .iter()
                .flatten()
                .any(|statement| statement.draws_read().iter().any(|name| self.redrawing[*name]))
        })
    }

    /// The player hearing the drifts its clip's chains name.
    pub fn hearing(self, hearing: Option<Hearing>) -> PatternPlayer<'a> {
        PatternPlayer { hearing, ..self }
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
    /// start is where the pass starts in the clip, where a grab step looks; grabs says whether the pass's grab steps grab,
    /// which only the clip's own patterns do.
    #[allow(clippy::too_many_arguments)]
    pub fn play_pass(
        &self,
        pattern_name: &str,
        direction: Option<&str>,
        rolls: &mut DrawnWhenAsked,
        order: &mut StepOrder,
        start: Rational,
        grabs: bool,
        registers: &Registers,
        changes_registers: bool,
    ) -> Rendered<Pass> {
        let pattern = self.pattern(pattern_name)?;
        let step_length = self.setlist.get_pattern_step_size(pattern);
        let pass_length = self.pattern_length(pattern);
        let where_ = named(errors::ERR_WHERE_PATTERN, &[("name", pattern_name.into())]);
        let values = every_step_values(pattern)?;
        let drum = pattern.is_drum();
        let own_direction = pattern.get_direction().unwrap_or(Direction::FORWARD.to_string());
        let direction = direction.map(str::to_string).unwrap_or(own_direction);
        let steps = order.next_steps(&format!("steps/{pattern_name}"), values.len(), &direction);
        let uses_draws = values.iter().any(|step| !step.draws_used().is_empty() || !step.draws_reset().is_empty());
        let has_statements = values.iter().any(|step| step.statements.iter().any(Option::is_some));
        let draws = changes_registers && uses_draws;
        let uses_registers = has_statements || draws;
        let counting = registers.is_counting();
        // What each step draws: the draws its rows use and those its statements read that redraw in conditions.
        let step_draws: Option<Vec<StepDraws>> = (changes_registers && (uses_draws || self.redraws_in_statements(&values))).then(|| {
            values
                .iter()
                .map(|step| {
                    let mut drawn = step.draws_used();
                    for statement in step.statements.iter().flatten() {
                        drawn.extend(statement.draws_read().into_iter().filter(|name| self.redrawing[*name]));
                    }
                    drawn.sort();
                    drawn.dedup();
                    StepDraws {
                        resets: step.draws_reset(),
                        drawn,
                    }
                })
                .collect()
        });
        // Where a step's statement cut the pass short, if one did, and whether it ended the clip or only started the pattern over.
        let mut cut_at: Option<usize> = None;
        let mut done = false;
        // What each step that plays sounds: when it starts in the pass, and its pieces, a note or chord for each ratchet.
        let mut sounding: Vec<(Rational, Vec<Sound>)> = Vec::new();
        let mut controls = Vec::new();
        let mut tied_to: Option<usize> = None;
        let mut leading_ties = 0;
        for (slot, step) in steps.iter().enumerate() {
            let time = step_length * Rational::whole(slot as i128);
            let moment = start + time;
            let first = slot == 0;
            let values = &values[*step];
            // Every draw the step takes is taken before its statements read the values, the step's one draw from it.
            if let Some(drawing) = step_draws.as_ref().map(|steps| &steps[*step]) {
                if !drawing.drawn.is_empty() || !drawing.resets.is_empty() {
                    registers.before_statements(moment, &drawing.drawn, &drawing.resets, first);
                }
            }
            // A step's statements are read before it changes anything, in the order stop, restart, mute; a morph's target
            // is never cut short, and the first step played never starts the pattern over, which would take no time.
            let statement_holds = |kind: usize| {
                values.statements[kind]
                    .as_ref()
                    .is_some_and(|statement| holds(statement, registers.before_step(moment, first)))
            };
            if changes_registers && statement_holds(STOP) {
                cut_at = Some(slot);
                done = true;
                break;
            }
            if changes_registers && slot > 0 && statement_holds(RESTART) {
                cut_at = Some(slot);
                break;
            }
            let muted = !counting && statement_holds(MUTE);
            let current = if uses_registers { registers.at_step(moment) } else { [0; 8] };
            // A step with no note can send CC values too.
            for (lane, value) in values.cc.iter().enumerate() {
                if let Some(value) = value {
                    controls.push(Control {
                        time,
                        number: lane as i64,
                        value: *value,
                        slide: values.slide,
                    });
                }
            }
            if values.tie {
                if let Some(place) = tied_to {
                    sounding[place] = tied(&sounding[place], time + step_length);
                } else if slot == leading_ties {
                    leading_ties += 1;
                }
                continue;
            }
            let grabbed = match (&self.grab, grabs && values.grab) {
                (Some(source), true) => source.note_at(start + time),
                _ => None,
            };
            // A step with no note of its own can still grab one; with nothing to grab yet, it's silence, like an empty step.
            if values.degree.is_none() && grabbed.is_none() {
                tied_to = None;
                continue;
            }
            tied_to = Some(sounding.len());
            let mut velocity_added = if values.accent { self.accent } else { 0 };
            let mut note_moved = 0;
            if uses_registers && draws {
                if !drum {
                    note_moved += (0..8).map(|name| current[name] * values.note_adds[name]).sum::<i64>();
                }
                velocity_added += (0..8).map(|name| current[name] * values.velocity_adds[name]).sum::<i64>();
            }
            if let Some(hearing) = &self.hearing {
                let effects = hearing
                    .drift
                    .borrow_mut()
                    .effects(&hearing.names, hearing.scene_start + start + time, &hearing.origins);
                velocity_added += effects.velocity;
                *self.effects.borrow_mut() = effects;
            }
            let gate = gate_of(values, step_length).min(pass_length - time);
            let step_sound = self.step(values, gate, drum, &where_, (velocity_added, note_moved), rolls, grabbed, (!muted, counting))?;
            sounding.push((time, step_sound));
        }
        let sounds = in_sequence(&sounding, pass_length, step_length);
        let tied_from_before = step_length * Rational::whole(leading_ties as i128);
        let Some(cut_at) = cut_at else {
            return Ok(Pass {
                sounds,
                tied_from_before,
                length: pass_length,
                done: false,
                controls,
            });
        };
        // What the pass played before its statement cut it, a note still sounding cut there.
        let end = step_length * Rational::whole(cut_at as i128);
        if end <= Rational::ZERO {
            return Ok(Pass {
                sounds: Vec::new(),
                tied_from_before: Rational::ZERO,
                length: Rational::ZERO,
                done,
                controls: Vec::new(),
            });
        }
        let cut = crate::clip::Clip::of(sounds, None).section(Rational::ZERO, end)?;
        Ok(Pass {
            sounds: cut.sounds,
            tied_from_before: tied_from_before.min(end),
            length: end,
            done,
            controls: controls.into_iter().filter(|control| control.time < end).collect(),
        })
    }

    /// What one step plays, lasting its gate, as more than one sound if it ratchets.
    #[allow(clippy::too_many_arguments)]
    fn step(
        &self,
        values: &StepValues,
        length: Rational,
        drum: bool,
        where_: &str,
        (velocity_added, note_moved): (i64, i64),
        rolls: &mut DrawnWhenAsked,
        grabbed: Option<i64>,
        (heard, counting): (bool, bool),
    ) -> Rendered<Vec<Sound>> {
        let octave = values.octave.unwrap_or(if drum { self.default_drum_octave } else { self.default_octave });
        let velocity = (values.velocity.unwrap_or(self.default_velocity) + velocity_added).clamp(MIN_VELOCITY, MAX_VELOCITY);
        let ratchet = values.ratchet.filter(|ratchet| *ratchet != 0).unwrap_or(DEFAULT_RATCHET);
        let offset = values.ratchet_offset.unwrap_or(0);
        let transpose = if drum { 0 } else { self.transpose };
        let slice_length = length / Rational::whole(ratchet as i128);
        // A drift the clip hears moves its notes along the scale, but no drum's.
        let moved = note_moved + if drum { 0 } else { self.effects.borrow().degree };
        let mut slices = Vec::new();
        for place in 0..ratchet {
            let shift = transpose + moved + place * offset;
            // Only the last slice glides into what follows the step.
            let glide = values.glide && place == ratchet - 1;
            let mut sound = match grabbed {
                Some(number) => self.grabbed_sound(number, values.chord.as_deref(), slice_length, velocity, glide, shift, drum, where_)?,
                None => self.sound(values, drum, slice_length, velocity, glide, octave, shift, where_)?,
            };
            // Most steps play one note as it is, so only a step with chord rows is voiced.
            if values.is_voiced() {
                sound = self.voiced(sound, values, octave, shift)?;
            }
            slices.push(sound);
        }
        // A step whose statement mutes it isn't heard, so a ratchet sounds all its slices or none; counting plays every slice.
        if !heard {
            return Ok(slices.iter().map(|piece| Sound::Rest(piece.place())).collect());
        }
        if counting {
            return Ok(slices);
        }
        Ok(played_by_chance(slices, values.probability, self.effects.borrow().probability, rolls))
    }

    /// A grabbed note, moved along the clip's scale, or by half steps for drums, with the step's chord built on it; a note
    /// moved outside the MIDI range stays where it was grabbed, and a chord's note that would is left out.
    #[allow(clippy::too_many_arguments)]
    fn grabbed_sound(
        &self,
        number: i64,
        chord: Option<&str>,
        length: Rational,
        velocity: i64,
        glide: bool,
        shift: i64,
        drum: bool,
        where_: &str,
    ) -> Rendered<Sound> {
        let note = NoteSound {
            length: Some(length),
            midi: number,
            velocity: Some(velocity),
            glide,
            name: SHARP_NAMES[number.rem_euclid(12) as usize],
        };
        let scale = if drum { None } else { self.clip_scale.as_ref() };
        let root = along_scale(note, shift, scale).unwrap_or(note);
        let Some(symbol) = chord.filter(|_| !drum) else {
            return Ok(Sound::Note(root));
        };
        let (scale, moves): (Option<&Scale>, Vec<i64>) = match fixed_chord(symbol) {
            Some(shape) => (None, shape.to_vec()),
            None => {
                let Some(scale) = self.clip_scale.as_ref() else {
                    return Err(RenderError::Refused(named(
                        errors::ERR_NO_SCALE,
                        &[("where", where_.into()), ("scene", self.scene_number.into())],
                    )));
                };
                let above = SCALE_CHORDS
                    .iter()
                    .find(|(found, _)| *found == symbol)
                    .map(|(_, above)| above.to_vec())
                    .unwrap_or_default();
                (Some(scale), above.into_iter().filter(|above| *above != 0).collect())
            }
        };
        let mut notes = vec![root];
        for step in moves {
            if let Ok(moved) = along_scale(root, step, scale) {
                notes.push(moved);
            }
        }
        if notes.len() == 1 {
            return Ok(Sound::Note(root));
        }
        Ok(Sound::chord(notes))
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

    /// The clip's scale rooted at an octave, or the scale type a step borrows on the same root; the inner error is an octave
    /// a root cannot be in.
    /// The scale and root a drift the clip hears overrides it with take its place.
    fn scale_at(&self, scale_name: &str, octave: i64, kind: Option<&str>) -> Rendered<Result<Scale, llamatron_model::ValueError>> {
        let effects = self.effects.borrow();
        let scale_name = effects.scale.as_deref().unwrap_or(scale_name);
        let named = self.named_scale(scale_name)?;
        if let Some(root) = &effects.root {
            let root = match llamatron_model::values::note::Note::new(root, octave, None, None, false) {
                Ok(root) => root,
                Err(problem) => return Ok(Err(problem)),
            };
            let kind_name = kind.map(str::to_string).unwrap_or_else(|| named.get_kind().python_str());
            let kind = ScaleType::named(&kind_name.trim().to_uppercase().replace(' ', "_"))
                .ok_or_else(|| RenderError::Refused(format!("no scale type called {kind_name}")))?;
            return Ok(Ok(Scale::new(root, kind)));
        }
        let scale = match named.scale_at(octave) {
            Ok(scale) => scale,
            Err(problem) => return Ok(Err(problem)),
        };
        let Some(kind) = kind else { return Ok(Ok(scale)) };
        let borrowed =
            ScaleType::named(&kind.trim().to_uppercase().replace(' ', "_")).ok_or_else(|| RenderError::Refused(format!("no scale type called {kind}")))?;
        Ok(Ok(Scale::new(*scale.get_root(), borrowed)))
    }

    /// A step's note or chord as its chord rows voice it, in this order: its tensions added, the notes its Omit row names
    /// left out, its Inversion, its Double, and last its Bass under it all.
    fn voiced(&self, sound: Sound, values: &StepValues, octave: i64, shift: i64) -> Rendered<Sound> {
        let chord_tones = match &sound {
            Sound::Chord { notes, .. } => notes.len(),
            _ => 1,
        };
        let mut sound = sound;
        if !values.tension.is_empty() {
            sound = with_tensions(sound, &values.tension);
        }
        if let Some(omission) = &values.omit {
            sound = omitted(sound, chord_tones, omission);
        }
        sound = sound.inverted(values.inversion);
        if let Some(doubling) = &values.double {
            sound = doubled(sound, doubling);
        }
        if values.bass.is_some() && values.degree.is_some() && self.scale_name.is_some() {
            sound = self.with_bass(sound, values, octave, shift)?;
        }
        Ok(sound)
    }

    /// A step's note or chord with its Bass under it: the scale note some steps above the chord's root, off it by its sharp or
    /// flat, in the nearest octave below the lowest note, and with Bass Octave the octave below that too; a bass that would
    /// leave the MIDI range is left out.
    fn with_bass(&self, sound: Sound, values: &StepValues, octave: i64, shift: i64) -> Rendered<Sound> {
        let notes = match &sound {
            Sound::Note(note) => vec![*note],
            Sound::Chord { notes, .. } => notes.clone(),
            _ => return Ok(sound),
        };
        let bass_name = values.bass.as_deref().unwrap_or("");
        let Some((_, parts)) = BASS_NOTES.iter().find(|(name, _)| *name == bass_name) else {
            return Ok(sound);
        };
        let (steps, half_steps) = (parts[0], parts[1]);
        let scale_name = self.scale_name.as_deref().unwrap_or("");
        let scale = self
            .scale_at(scale_name, octave, values.chord_scale.as_deref())?
            .map_err(|problem| RenderError::Refused(problem.0))?;
        let first = notes[0];
        let degree = values.degree.as_ref().and_then(Data::as_whole).unwrap_or(0) as i64;
        let bass =
            scale_sound(&scale, degree + steps, shift, half_steps, first.length, first.velocity, false).map_err(|problem| RenderError::Refused(problem.0))?;
        let lowest = notes.iter().map(|note| note.midi).min().unwrap_or(bass.midi);
        let Some(bass) = bass.half_step((lowest - 1 - bass.midi).div_euclid(12) * 12) else {
            return Ok(sound);
        };
        let mut under = vec![bass];
        if values.bass_octave {
            let Some(below) = bass.half_step(-12) else { return Ok(sound) };
            under.insert(0, below);
        }
        under.extend(notes);
        Ok(Sound::chord(under))
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
        let scale: Scale = match self.scale_at(scale_name, octave, values.chord_scale.as_deref())? {
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
fn played_by_chance(slices: Vec<Sound>, probability: Option<i64>, added: i64, rolls: &mut DrawnWhenAsked) -> Vec<Sound> {
    let mut probability = probability.unwrap_or(DEFAULT_PROBABILITY);
    if added != 0 {
        probability = (probability + added).clamp(MIN_PROBABILITY, MAX_PROBABILITY);
    }
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

/// A chord with its tensions added, each its half steps above the chord's first note, the root; a single note has none, and
/// a tension the chord holds already or that would leave the MIDI range is left out.
fn with_tensions(sound: Sound, tensions: &[String]) -> Sound {
    let Sound::Chord { notes, .. } = &sound else { return sound };
    let root = notes[0];
    let held: Vec<i64> = notes.iter().map(|note| note.midi).collect();
    let mut notes = notes.clone();
    for tension in tensions {
        let Some((_, steps)) = TENSIONS.iter().find(|(name, _)| name == tension) else {
            continue;
        };
        if held.contains(&(root.midi + steps)) {
            continue;
        }
        if let Some(added) = root.half_step(*steps) {
            notes.push(added);
        }
    }
    Sound::chord(notes)
}

/// A chord with the notes its Omit row names left out by their role among its own first notes, built up from the root; a
/// tension is never left out, and a chord that would be left with nothing is as it is.
fn omitted(sound: Sound, chord_tones: usize, omission: &str) -> Sound {
    let Sound::Chord { notes, .. } = &sound else { return sound };
    let Some((_, roles)) = OMITTED_ROLES.iter().find(|(name, _)| *name == omission) else {
        return sound;
    };
    let root = notes[0].midi;
    let kept: Vec<NoteSound> = notes
        .iter()
        .enumerate()
        .filter(|(place, note)| *place >= chord_tones || role_of(note.midi - root).is_none_or(|role| !roles.contains(&role)))
        .map(|(_, note)| *note)
        .collect();
    match kept.len() {
        0 => sound,
        1 => Sound::Note(kept[0]),
        _ => Sound::chord(kept),
    }
}

/// A note or chord with the notes its Double row names played again an octave away; one the chord holds already, or that
/// would leave the MIDI range, is left out.
fn doubled(sound: Sound, doubling: &str) -> Sound {
    let mut notes = match &sound {
        Sound::Note(note) => vec![*note],
        Sound::Chord { notes, .. } => notes.clone(),
        _ => return sound,
    };
    let Some((first, last, octaves)) = doubled_notes(doubling) else {
        return sound;
    };
    let mut by_pitch = notes.clone();
    by_pitch.sort_by_key(|note| note.midi);
    let count = by_pitch.len() as isize;
    let place = |index: isize| (if index < 0 { (count + index).max(0) } else { index.min(count) }) as usize;
    let end = last.map(place).unwrap_or(by_pitch.len());
    let start = place(first);
    let copied: Vec<NoteSound> = if start < end { by_pitch[start..end].to_vec() } else { Vec::new() };
    let half_steps = octaves * 12;
    let mut held: Vec<i64> = notes.iter().map(|note| note.midi).collect();
    for note in copied {
        if held.contains(&(note.midi + half_steps)) {
            continue;
        }
        let Some(again) = note.half_step(half_steps) else { continue };
        notes.push(again);
        held.push(note.midi + half_steps);
    }
    Sound::chord(notes)
}
