// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Shapes as a clip plays (the Python engine/realizer/shapes.py, model/objects/shapes.py and velocity_ramps.py): Density
//! thins a finished clip's notes, the strongest places in the bar kept longest; Swell scales their velocity; Articulate
//! their length, each by a percentage ramping from its start to its end over its span, then holding, repeating or bouncing.
//! A dropped note becomes a rest of its length, and a lengthened one is held past its place but never past the track's next
//! note. How loud the clip plays, its velocity stacked on its scene's, track's and instrument's, with a ramp in and out,
//! scales every note besides.

use crate::sound::{NoteSound, Sound};
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::schema::checking::{time_length, TimeLength};
use llamatron_model::schema::generated::defaults::DEFAULT_VELOCITY;
use llamatron_model::schema::generated::midi::{MAX_VELOCITY, MIN_VELOCITY};
use llamatron_names::file_format;

const FULL: i128 = 100;
const UNCHANGED: i128 = 100;
const BAR_START: i64 = 0;
const BAR_MIDDLE: i64 = 1;
const ON_A_BEAT: i64 = 2;
const ON_AN_EIGHTH: i64 = 3;
const ON_A_SIXTEENTH: i64 = 4;
const FINER: i64 = 5;
const ACCENTED: i64 = ON_A_BEAT;
pub const DENSITY: &str = "density";
pub const SWELL: &str = "swell";
pub const ARTICULATE: &str = "articulate";
/// The shapes, in the order a file and a reshaping take them; Density and Articulate a clip or scene may set itself.
pub const SHAPES: &[&str] = &[DENSITY, SWELL, ARTICULATE];
pub const PLACED_SHAPES: &[&str] = &[DENSITY, ARTICULATE];
const REPEAT: &str = "repeat";
const BOUNCE: &str = "bounce";

/// One shape as set somewhere: its start and end percentages, its over in whole notes or None for the whole span, its then,
/// and a Swell's accent.
#[derive(Clone, Debug)]
pub struct ShapeValues {
    pub start: Rational,
    pub end: Rational,
    pub over: Option<Rational>,
    pub then: String,
    pub accent: i64,
}

/// A shape where it runs: its values, the span its whole ramp covers, and how far into that span the clip starts.
pub type PlacedShape = (ShapeValues, Rational, Rational);

fn percent(value: Option<&Data>) -> Option<Rational> {
    match value? {
        Data::Whole(number) => Some(Rational::whole(*number)),
        Data::Float(number) => Some(Rational::from_float(*number)),
        _ => None,
    }
}

/// A shape's values from an object's settings, the over a length in whole notes of a bar, or None where both its start and
/// end are blank.
pub fn shape_values(written: &dyn Fn(&str) -> Option<Data>, shape: &str, accent: i64, bar: Rational) -> Option<ShapeValues> {
    let part = |name: &str| written(&format!("{shape}_{name}")).filter(|value| !value.is_null());
    let start = part(file_format::RampPart::START);
    let end = part(file_format::RampPart::END);
    if start.is_none() && end.is_none() {
        return None;
    }
    let over = part(file_format::RampPart::OVER).and_then(|over| match time_length(&over).ok()? {
        TimeLength::Bars(count) => Some(bar * Rational::whole(count as i128)),
        TimeLength::Length(length) => Some(length),
    });
    Some(ShapeValues {
        start: percent(start.as_ref()).unwrap_or(Rational::whole(UNCHANGED)),
        end: percent(end.as_ref()).unwrap_or(Rational::whole(UNCHANGED)),
        over,
        then: part(file_format::ShapePart::THEN)
            .map(|then| then.python_str())
            .filter(|then| !then.is_empty())
            .unwrap_or(file_format::PartSetting::HOLD.to_string()),
        accent,
    })
}

/// A shape's percentage at a time from its start, ramping from start to end over its over, or the whole span, then holding,
/// repeating or bouncing.
fn percent_at(values: &ShapeValues, time: Rational, span: Rational) -> Rational {
    let length = values.over.unwrap_or(span);
    if length == Rational::ZERO {
        return values.end;
    }
    let place = time / length;
    let share = match values.then.as_str() {
        REPEAT => place - Rational::whole(place.floor()),
        BOUNCE => {
            let lap = place - Rational::whole(2 * (place / Rational::whole(2)).floor());
            if lap > Rational::whole(1) {
                Rational::whole(2) - lap
            } else {
                lap
            }
        }
        _ => place.min(Rational::whole(1)),
    };
    values.start + (values.end - values.start) * share
}

/// A velocity ramp placed on a clip: the percentages it starts from and reaches, how long it lasts and when it begins, from
/// the clip's start.
#[derive(Clone, Debug)]
pub struct PlacedRamp {
    pub start: Rational,
    pub end: Rational,
    pub span: Rational,
    pub begins: Rational,
}

/// How loud a clip plays over its time: the percentage that holds, and its ramps in and out.
#[derive(Clone, Debug)]
pub struct PlacedVelocity {
    pub level: Rational,
    pub ramp_in: Option<PlacedRamp>,
    pub ramp_out: Option<PlacedRamp>,
}

/// One ramp as written, before it is placed: its ends as percentages of the written velocity, its bars, and whether the bars
/// are the clip's own.
pub struct VelocityRamp {
    pub start: Rational,
    pub end: Rational,
    pub over: Rational,
    pub of_clip: bool,
}

/// How loud a clip plays: its level, and its ramps in and out.
pub struct Velocity {
    pub level: Rational,
    pub ramp_in: Option<VelocityRamp>,
    pub ramp_out: Option<VelocityRamp>,
}

impl Velocity {
    /// How loud a clip plays from its scene's settings, its own, and the outer levels of its instrument and track: the levels
    /// stacking, each a percentage of the others, and a clip's ramp fields winning over its scene's, field by field.
    pub fn of(scene: &dyn Fn(&str) -> Option<Data>, clip: &dyn Fn(&str) -> Option<Data>, outer: &[Option<Rational>]) -> Velocity {
        let mut level = Rational::whole(UNCHANGED);
        let scaled = |level: Rational, percent: Option<Rational>| match percent {
            None => level,
            Some(percent) => level * percent / Rational::whole(UNCHANGED),
        };
        for share in outer.iter().copied().chain([
            percent(scene(file_format::TrackSetting::VELOCITY).as_ref()),
            percent(clip(file_format::TrackSetting::VELOCITY).as_ref()),
        ]) {
            level = scaled(level, share);
        }
        let ramp = |way: &str| {
            let taken = |part: &str| {
                let name = format!("velocity_{way}_{part}");
                clip(&name)
                    .filter(|value| !value.is_null())
                    .or_else(|| scene(&name).filter(|value| !value.is_null()))
            };
            let start = percent(taken(file_format::RampPart::START).as_ref());
            let end = percent(taken(file_format::RampPart::END).as_ref());
            let over = percent(taken(file_format::RampPart::OVER).as_ref())?;
            if start.is_none() && end.is_none() {
                return None;
            }
            let of_clip = clip(&format!("velocity_{way}_over")).is_some_and(|value| !value.is_null());
            Some(VelocityRamp {
                start: scaled(level, start),
                end: scaled(level, end),
                over,
                of_clip,
            })
        };
        Velocity {
            level,
            ramp_in: ramp(file_format::RampWay::IN),
            ramp_out: ramp(file_format::RampWay::OUT),
        }
    }

    pub fn changes_nothing(&self) -> bool {
        self.level == Rational::whole(UNCHANGED) && self.ramp_in.is_none() && self.ramp_out.is_none()
    }
}

/// The percentage of its written velocity a note plays at, at a time from its clip's start.
fn velocity_percent_at(velocity: &PlacedVelocity, time: Rational) -> Rational {
    if let Some(ramp) = &velocity.ramp_in {
        let place = time - ramp.begins;
        if place < ramp.span {
            return ramp.start + (ramp.end - ramp.start) * place / ramp.span;
        }
    }
    if let Some(ramp) = &velocity.ramp_out {
        let place = time - ramp.begins;
        if place >= Rational::ZERO {
            return ramp.start + (ramp.end - ramp.start) * (place / ramp.span).min(Rational::whole(1));
        }
    }
    velocity.level
}

/// How strong a start's place in the bar is, the bar's start the strongest.
fn strength(start: Rational, bar: Rational, beat: Rational) -> i64 {
    let within = start - bar * Rational::whole((start / bar).floor());
    if within == Rational::ZERO {
        return BAR_START;
    }
    if within == bar / Rational::whole(2) {
        return BAR_MIDDLE;
    }
    for (level, unit) in [
        (ON_A_BEAT, beat),
        (ON_AN_EIGHTH, beat / Rational::whole(2)),
        (ON_A_SIXTEENTH, beat / Rational::whole(4)),
    ] {
        if (within / unit).is_whole() {
            return level;
        }
    }
    FINER
}

/// Whether a note at a place of a strength plays at a density: the strongest places keep playing longest.
fn plays_at(density: Rational, level: i64) -> bool {
    let above = match level {
        BAR_START => Rational::ZERO,
        BAR_MIDDLE => Rational::new(25, 4),
        ON_A_BEAT => Rational::new(25, 2),
        ON_AN_EIGHTH => Rational::whole(25),
        ON_A_SIXTEENTH => Rational::whole(50),
        _ => return density >= Rational::whole(FULL),
    };
    density >= Rational::whole(FULL) || density > above
}

/// What shapes a clip's sounds, each shape where it runs or None, with its velocity, over the clip's span.
pub struct Reshaping {
    pub density: Option<PlacedShape>,
    pub swell: Option<PlacedShape>,
    pub articulate: Option<PlacedShape>,
    pub velocity: Option<PlacedVelocity>,
    pub span: Rational,
    pub bar: Rational,
    pub beat: Rational,
}

impl Reshaping {
    /// A clip's sounds reshaped, each keeping its place.
    pub fn reshaped(&self, sounds: &[Sound]) -> Vec<Sound> {
        let mut starts = Vec::new();
        let mut now = Rational::ZERO;
        for sound in sounds {
            starts.push(now);
            now = now + sound.place();
        }
        // Where the next sound that is no rest starts, for each sound, or the span's end after the last.
        let mut following = vec![self.span; sounds.len()];
        let mut upcoming = self.span;
        for place in (0..sounds.len()).rev() {
            following[place] = upcoming;
            if !sounds[place].is_rest() {
                upcoming = starts[place];
            }
        }
        let mut result = Vec::new();
        for (place, sound) in sounds.iter().enumerate() {
            if sound.is_rest() {
                result.push(sound.clone());
                continue;
            }
            let time = starts[place];
            let level = strength(time, self.bar, self.beat);
            if let Some((values, span, offset)) = &self.density {
                if !plays_at(percent_at(values, time + *offset, *span), level) {
                    result.push(Sound::Rest(sound.place()));
                    continue;
                }
            }
            let mut sound = sound.clone();
            if let Some((values, span, offset)) = &self.swell {
                let mut scale = percent_at(values, time + *offset, *span);
                if level <= ACCENTED {
                    scale = scale + Rational::whole(values.accent as i128) * scale / Rational::whole(FULL);
                }
                sound = with_velocity(&sound, scale);
            }
            if let Some(velocity) = &self.velocity {
                sound = with_velocity(&sound, velocity_percent_at(velocity, time));
            }
            if let Some((values, span, offset)) = &self.articulate {
                let room = following[place] - starts[place];
                result.extend(with_length(&sound, percent_at(values, time + *offset, *span), room));
                continue;
            }
            result.push(sound);
        }
        result
    }
}

fn scaled_note(note: &NoteSound, scale: Rational) -> NoteSound {
    let velocity = note.velocity.unwrap_or(DEFAULT_VELOCITY);
    let scaled = (Rational::whole(velocity as i128) * scale / Rational::whole(FULL))
        .round()
        .clamp(MIN_VELOCITY as i128, MAX_VELOCITY as i128) as i64;
    NoteSound {
        velocity: Some(scaled),
        ..*note
    }
}

/// A sound with every note's velocity scaled by a percentage, held to the velocities MIDI allows.
fn with_velocity(sound: &Sound, scale: Rational) -> Sound {
    match sound {
        Sound::Note(note) => Sound::Note(scaled_note(note, scale)),
        Sound::Chord { length, notes } => Sound::Chord {
            length: *length,
            notes: notes.iter().map(|note| scaled_note(note, scale)).collect(),
        },
        Sound::Held { length, sound } => Sound::Held {
            length: *length,
            sound: Box::new(with_velocity(sound, scale)),
        },
        Sound::Phrase { length, parts } => Sound::Phrase {
            length: *length,
            parts: parts.iter().map(|part| with_velocity(part, scale)).collect(),
        },
        other => other.clone(),
    }
}

/// The positions a sound becomes when it sounds for a share of its written length, held past its place where longer but
/// never past room, the time until the track's next note.
fn with_length(sound: &Sound, share: Rational, room: Rational) -> Vec<Sound> {
    if let Sound::Phrase { .. } = sound {
        return vec![sound.clone()];
    }
    let played = match sound {
        Sound::Held { sound, .. } => sound.as_ref(),
        other => other,
    };
    let written = match played {
        Sound::Chord { notes, .. } => notes.iter().filter_map(|note| note.length).max().unwrap_or(Rational::ZERO),
        other => other.place(),
    };
    let place = sound.place();
    let wanted = written * (share / Rational::whole(FULL));
    let lasting = if room > Rational::ZERO { wanted.min(room) } else { wanted };
    if lasting == place {
        return vec![played.lasting(Some(lasting))];
    }
    if lasting < place {
        return vec![played.lasting(Some(lasting)), Sound::Rest(place - lasting)];
    }
    vec![Sound::held(played.lasting(Some(lasting)), place)]
}
