// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Chords generator (the Python engine/generators/chords/): a clip's notes moved through a progression, or along the chords
//! another track plays, then voiced nearest the chord before where voice leading is on.
//!
//! A progression takes the clip's pattern as written over chord I. Each chord lasts every, a bar unless set, counted from the
//! clip's start, or from its run's where it carries on, and the progression loops. A plain degree moves every note that many
//! scale steps up, less one; a degree with a sharp or flat moves every note by exact half steps. A chord may borrow a scale
//! type on the clip's root, or name a quality or tensions, which set the figure's third, fifth, seventh and the notes between.

use crate::chord_source::{ChordSource, HeardChord};
use crate::clip::Clip;
use crate::error::{RenderError, Rendered};
use crate::sound::{along_scale, scale_place, scale_sound, NoteSound, OutOfRange, Sound};
use crate::tables::fixed_chord;
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::fundamentals::voice_leading;
use llamatron_model::schema::checking::{time_length, TimeLength};
use llamatron_model::schema::generated::file_format::{ACCIDENTALS, GENERATOR_ENABLED, GENERATOR_RESTART, ONE_BAR_WRITTEN, TENSIONS};
use llamatron_model::schema::generated::midi::{MAX_MIDI_NUMBER, MIN_MIDI_NUMBER};
use llamatron_model::values::scale::{Scale, ScaleType};

pub const MODE: &str = "mode";
pub const CHORDS_FROM: &str = "chords_from";
const VOICING: &str = "voicing";
const PROGRESSION: &str = "progression";
const FOLLOW_PROGRESSION: &str = "follow_progression";
const EVERY: &str = "every";
const CHORDS: &str = "chords";
const ACCIDENTAL_ROW: &str = "accidentals";
const INVERSIONS: &str = "inversions";
const SCALES: &str = "scales";
const QUALITIES: &str = "qualities";
const TENSION_ROW: &str = "tensions";
const VOICE_LEADING: &str = "voice_leading";
const LOWEST_OCTAVE: &str = "lowest_octave";
const HIGHEST_OCTAVE: &str = "highest_octave";
const ROOT_IN_BASS: &str = "root_in_bass";
const DEFAULT_LOWEST_OCTAVE: i64 = 4;
const DEFAULT_HIGHEST_OCTAVE: i64 = 6;
/// The settings the port reads; a Chords generator with any other written is not ported yet.
const PORTED: &[&str] = &[
    GENERATOR_ENABLED,
    GENERATOR_RESTART,
    MODE,
    EVERY,
    CHORDS,
    ACCIDENTAL_ROW,
    INVERSIONS,
    SCALES,
    QUALITIES,
    TENSION_ROW,
    CHORDS_FROM,
    VOICE_LEADING,
    LOWEST_OCTAVE,
    HIGHEST_OCTAVE,
    ROOT_IN_BASS,
];
/// A chord's places above its root, in a scale of seven notes: the 9th, 3rd, 11th, 5th, 13th and 7th.
const ROOT_PLACE: i64 = 0;
const NINTH_PLACE: i64 = 1;
const THIRD_PLACE: i64 = 2;
const ELEVENTH_PLACE: i64 = 3;
const FIFTH_PLACE: i64 = 4;
const THIRTEENTH_PLACE: i64 = 5;
const SEVENTH_PLACE: i64 = 6;
const PLACED_SCALE_SIZE: usize = 7;
const MAJOR_SHAPE: &[i64] = &[0, 2, 4, 5, 7, 9, 11];
/// The octaves away a voicing is tried at, either way.
const OCTAVES_TRIED: i64 = 4;

/// Where a generator carries on from: how far into its run the clip starts, and the state the same track's clip before left
/// it in, a voicing's last chord.
#[derive(Clone, Debug, Default)]
pub struct Continuation {
    pub offset: Rational,
    pub state: Option<super::GeneratorState>,
}

/// A Chords generator's settings as a clip or a chain holds them.
pub struct ChordsSettings<'a> {
    data: &'a Data,
}

fn row<'a>(data: &'a Data, name: &str, count: usize) -> Vec<Option<&'a Data>> {
    let values = data.get(name).and_then(Data::as_list).unwrap_or(&[]);
    (0..count).map(|place| values.get(place).filter(|value| !value.is_null())).collect()
}

impl<'a> ChordsSettings<'a> {
    pub fn of(data: &'a Data) -> Rendered<ChordsSettings<'a>> {
        for (key, value) in data.as_map().unwrap_or(&[]) {
            let name = key.python_str();
            if !PORTED.contains(&name.as_str()) && !value.is_null() {
                return Err(RenderError::NotPorted(format!("the Chords generator's {name} setting")));
            }
        }
        Ok(ChordsSettings { data })
    }

    fn written(&self, name: &str) -> Option<&'a Data> {
        self.data.get(name).filter(|value| !value.is_null())
    }

    pub fn get_mode(&self) -> String {
        self.written(MODE).map(Data::python_str).unwrap_or(VOICING.to_string())
    }

    pub fn get_restart(&self) -> Option<String> {
        self.written(GENERATOR_RESTART).map(Data::python_str).filter(|restart| !restart.is_empty())
    }

    pub fn get_chords_from(&self) -> Option<String> {
        self.written(CHORDS_FROM).map(Data::python_str)
    }

    /// Whether it voices each chord nearest the one before: as set, else in Voicing mode alone.
    fn voices(&self) -> bool {
        match self.written(VOICE_LEADING) {
            Some(Data::Bool(on)) => *on,
            Some(_) => true,
            None => self.get_mode() == VOICING,
        }
    }

    fn whole_or(&self, name: &str, default: i64) -> i64 {
        self.written(name).and_then(Data::as_whole).map(|value| value as i64).unwrap_or(default)
    }

    fn chords(&self) -> Vec<i64> {
        let chords: Vec<i64> = self
            .written(CHORDS)
            .and_then(Data::as_list)
            .unwrap_or(&[])
            .iter()
            .filter_map(Data::as_whole)
            .map(|chord| chord as i64)
            .collect();
        if chords.is_empty() {
            return vec![1];
        }
        chords
    }

    fn progression(&self, bar: Rational, continuation: &Continuation) -> Rendered<Progression> {
        let written = self
            .written(EVERY)
            .filter(|every| every.as_str() != Some(""))
            .cloned()
            .unwrap_or(Data::text(ONE_BAR_WRITTEN));
        let every = match time_length(&written).map_err(|problem| RenderError::Refused(problem.message))? {
            TimeLength::Bars(count) => bar * Rational::whole(count as i128),
            TimeLength::Length(length) => length,
        };
        let chords = self.chords();
        let count = chords.len();
        let accidentals = row(self.data, ACCIDENTAL_ROW, count)
            .into_iter()
            .map(|value| {
                value
                    .and_then(|value| ACCIDENTALS.iter().find(|(found, _)| Some(*found) == value.as_str()))
                    .map(|(_, steps)| *steps)
            })
            .collect();
        let inversions = row(self.data, INVERSIONS, count)
            .into_iter()
            .map(|value| value.and_then(Data::as_whole).map(|value| value as i64))
            .collect();
        let scales = row(self.data, SCALES, count)
            .into_iter()
            .map(|value| value.and_then(|kind| ScaleType::named(&kind.python_str().trim().to_uppercase().replace(' ', "_"))))
            .collect();
        let tensions: Vec<Option<Vec<i64>>> = row(self.data, TENSION_ROW, count)
            .into_iter()
            .map(|value| value.map(tensions_in_order))
            .collect();
        let qualities = row(self.data, QUALITIES, count);
        let replaced: Vec<Vec<(i64, i64)>> = qualities
            .iter()
            .zip(row(self.data, TENSION_ROW, count))
            .map(|(quality, added)| replaced_places(quality.map(Data::python_str).as_deref(), added))
            .collect();
        let plain = scales_are_plain(&row(self.data, SCALES, count)) && replaced.iter().all(Vec::is_empty);
        Ok(Progression {
            chords,
            accidentals,
            inversions,
            scales,
            tensions,
            replaced,
            plain,
            every,
            offset: continuation.offset,
        })
    }

    fn voicing(&self, continuation: &Continuation) -> VoiceLeading {
        VoiceLeading {
            lowest_octave: self.whole_or(LOWEST_OCTAVE, DEFAULT_LOWEST_OCTAVE),
            highest_octave: self.whole_or(HIGHEST_OCTAVE, DEFAULT_HIGHEST_OCTAVE),
            root_in_bass: self.written(ROOT_IN_BASS).is_some_and(|value| *value == Data::Bool(true)),
            before: match &continuation.state {
                Some(super::GeneratorState::Voicing(before)) => Some(before.clone()),
                _ => None,
            },
        }
    }

    /// The generator its settings make at a clip's place: what its Mode does to the notes, then its voicing.
    pub fn make_generator(&self, bar: Rational, continuation: &Continuation, followed: Option<ChordSource>) -> Rendered<ChordsGenerator> {
        let moving = match self.get_mode().as_str() {
            PROGRESSION => Some(Moving::Progression(self.progression(bar, continuation)?)),
            FOLLOW_PROGRESSION => Some(Moving::Follow(followed)),
            VOICING => None,
            other => return Err(RenderError::NotPorted(format!("the Chords generator's {other} mode"))),
        };
        let voicing = self.voices().then(|| self.voicing(continuation));
        Ok(ChordsGenerator { moving, voicing })
    }
}

fn scales_are_plain(scales: &[Option<&Data>]) -> bool {
    scales.iter().all(Option::is_none)
}

/// The tensions a chord's value holds, in the order the tensions come, as half steps above the root.
fn tensions_in_order(value: &Data) -> Vec<i64> {
    let held: Vec<String> = value.as_list().unwrap_or(&[]).iter().map(Data::python_str).collect();
    TENSIONS
        .iter()
        .filter(|(name, _)| held.iter().any(|found| found == name))
        .map(|(_, steps)| *steps)
        .collect()
}

/// For a progression's chord, the half steps above its root that a figure's notes take at each place of the scale above the
/// root: a named quality sets its third, fifth and seventh, and each tension the note between.
fn replaced_places(symbol: Option<&str>, tensions: Option<&Data>) -> Vec<(i64, i64)> {
    let mut places: Vec<(i64, i64)> = Vec::new();
    let mut put = |place: i64, half_steps: i64| match places.iter_mut().find(|(found, _)| *found == place) {
        Some(entry) => entry.1 = half_steps,
        None => places.push((place, half_steps)),
    };
    if let Some(shape) = symbol.and_then(fixed_chord) {
        for half_steps in shape {
            let within = half_steps.rem_euclid(12);
            if *half_steps > 12 {
                let place = match within {
                    2 => NINTH_PLACE,
                    5 => ELEVENTH_PLACE,
                    _ => THIRTEENTH_PLACE,
                };
                put(place, within);
            } else if (2..6).contains(&within) {
                put(THIRD_PLACE, within);
            } else if (6..9).contains(&within) {
                put(FIFTH_PLACE, within);
            } else if (9..12).contains(&within) {
                put(SEVENTH_PLACE, within);
            }
        }
    }
    for tension in tensions.and_then(Data::as_list).unwrap_or(&[]) {
        let name = tension.python_str();
        let Some((_, steps)) = TENSIONS.iter().find(|(found, _)| *found == name) else {
            continue;
        };
        let place = match name.as_str() {
            "b9" | "9" | "#9" => NINTH_PLACE,
            "11" | "#11" => ELEVENTH_PLACE,
            _ => THIRTEENTH_PLACE,
        };
        put(place, steps.rem_euclid(12));
    }
    places
}

pub enum Moving {
    Progression(Progression),
    Follow(Option<ChordSource>),
}

/// Runs a Chords generator's parts in order on a clip: what its Mode makes of the notes, then its voicing.
pub struct ChordsGenerator {
    moving: Option<Moving>,
    voicing: Option<VoiceLeading>,
}

impl ChordsGenerator {
    pub fn generate(&mut self, clip: &Clip) -> Rendered<Clip> {
        let mut clip = clip.clone();
        clip.sounds = clip.resolved_sounds()?;
        if let Some(moving) = &self.moving {
            clip = match moving {
                Moving::Progression(progression) => progression.generate(&clip)?,
                Moving::Follow(chords) => follow(&clip, chords.as_ref())?,
            };
        }
        if let Some(voicing) = &mut self.voicing {
            clip = voicing.generate(&clip)?;
        }
        Ok(clip)
    }

    /// The state the next clip carries on from: its voicing's last chord.
    pub fn end_state(&self) -> Option<Vec<i64>> {
        self.voicing.as_ref().and_then(|voicing| voicing.before.clone())
    }
}

/// A clip made from another with new sounds, keeping its name, scale, length and note length.
fn remade(clip: &Clip, sounds: Vec<Sound>) -> Clip {
    Clip {
        sounds,
        time_signature: None,
        looping: true,
        ..clip.clone()
    }
}

pub struct Progression {
    chords: Vec<i64>,
    accidentals: Vec<Option<i64>>,
    inversions: Vec<Option<i64>>,
    scales: Vec<Option<ScaleType>>,
    tensions: Vec<Option<Vec<i64>>>,
    replaced: Vec<Vec<(i64, i64)>>,
    plain: bool,
    every: Rational,
    offset: Rational,
}

impl Progression {
    /// Which chord of the progression plays at a time from the clip's start, counted from 0.
    fn chord_at(&self, time: Rational) -> usize {
        ((time + self.offset) / self.every).floor().rem_euclid(self.chords.len() as i128) as usize
    }

    fn generate(&self, clip: &Clip) -> Rendered<Clip> {
        let scale = clip.scale.as_ref();
        let mut now = Rational::ZERO;
        let mut result = Vec::new();
        for sound in clip.resolved_sounds()? {
            result.push(self.moved(&sound, self.chord_at(now), scale)?);
            now = now + sound.place();
        }
        Ok(remade(clip, result))
    }

    fn moved(&self, sound: &Sound, place: usize, scale: Option<&Scale>) -> Rendered<Sound> {
        Ok(match sound {
            Sound::Degree { .. } if scale.is_some() => self.moved(&settled(sound, scale)?, place, scale)?,
            Sound::Note(note) => Sound::Note(self.moved_note(*note, place, scale)),
            Sound::Chord { notes, .. } => {
                let mut moved: Vec<NoteSound> = notes.iter().map(|note| self.moved_note(*note, place, scale)).collect();
                if let Some(tensions) = self.tensions[place].as_ref().filter(|tensions| !tensions.is_empty()) {
                    moved = with_tensions(moved, tensions);
                }
                Sound::chord(moved).inverted(self.inversions[place])
            }
            Sound::Held { length, sound } => Sound::Held {
                length: *length,
                sound: Box::new(self.moved(sound, place, scale)?),
            },
            Sound::Phrase { length, parts } => Sound::Phrase {
                length: *length,
                parts: parts.iter().map(|part| self.moved(part, place, scale)).collect::<Rendered<_>>()?,
            },
            other => other.clone(),
        })
    }

    /// A note moved to a chord, or as it was where moving it would leave the MIDI range.
    fn moved_note(&self, note: NoteSound, place: usize, scale: Option<&Scale>) -> NoteSound {
        let moved = match scale.filter(|_| !self.plain) {
            None => self.to_chord(note, place, scale),
            Some(scale) => self.to_changed_chord(note, place, scale),
        };
        moved.unwrap_or(note)
    }

    fn to_chord(&self, note: NoteSound, place: usize, scale: Option<&Scale>) -> Result<NoteSound, OutOfRange> {
        match self.accidentals[place] {
            None => along_scale(note, self.chords[place] - 1, scale),
            Some(accidental) => {
                let steps = half_steps_to(self.chords[place], scale) + accidental;
                note.half_step(steps)
                    .ok_or_else(|| OutOfRange("a chord's note leaves the MIDI range".to_string()))
            }
        }
    }

    /// A note moved to a chord that borrows a scale or names its quality or tensions: carried first to the same place in the
    /// chord's scale, then, where the chord names the note at its place above the root, made that many half steps.
    fn to_changed_chord(&self, note: NoteSound, place: usize, scale: &Scale) -> Result<NoteSound, OutOfRange> {
        let borrowed = self.scales[place].map(|kind| Scale::new(*scale.get_root(), kind));
        let drawn_from = borrowed.as_ref().unwrap_or(scale);
        let (above, extra) = place_in(note.midi, scale);
        let note = match &borrowed {
            Some(borrowed) => carried(note, scale, borrowed)?,
            None => note,
        };
        let size = drawn_from.get_type().get_shape().len();
        let half_steps = self.replaced[place].iter().find(|(found, _)| *found == above).map(|(_, steps)| *steps);
        let Some(half_steps) = half_steps.filter(|_| extra == 0 && size == PLACED_SCALE_SIZE && above != ROOT_PLACE) else {
            return self.to_chord(note, place, Some(drawn_from));
        };
        let root = self.to_chord(along_scale(note, -above, Some(drawn_from))?, place, Some(drawn_from))?;
        root.half_step(half_steps)
            .ok_or_else(|| OutOfRange("a chord's note leaves the MIDI range".to_string()))
    }
}

fn settled(sound: &Sound, scale: Option<&Scale>) -> Rendered<Sound> {
    let (
        Sound::Degree {
            length,
            number,
            octave,
            scale_notes,
            half_steps,
        },
        Some(scale),
    ) = (sound, scale)
    else {
        return Ok(sound.clone());
    };
    scale_sound(scale, *number, *scale_notes, octave * 12 + half_steps, *length, None, false)
        .map(Sound::Note)
        .map_err(|problem| RenderError::Refused(problem.0))
}

/// Which note of a scale's octave, counted from 0, a MIDI number is at or just above, and how many half steps above it.
fn place_in(midi: i64, scale: &Scale) -> (i64, i64) {
    let shape = scale.get_type().get_shape();
    let within = (midi - scale.get_root().get_midi_number()).rem_euclid(12);
    let place = scale_place(shape, within);
    (place as i64, within - shape[place])
}

/// A note of one scale as the note at the same place of another on the same root, keeping its distance above a scale note.
fn carried(note: NoteSound, scale: &Scale, drawn_from: &Scale) -> Result<NoteSound, OutOfRange> {
    let (place, _) = place_in(note.midi, scale);
    let shape = scale.get_type().get_shape();
    let other = drawn_from.get_type().get_shape();
    let steps = other[place as usize % other.len()] - shape[place as usize];
    note.half_step(steps)
        .ok_or_else(|| OutOfRange("a borrowed note leaves the MIDI range".to_string()))
}

/// A chord's notes with its tensions added above its lowest note, each left out where the chord has its pitch already.
fn with_tensions(notes: Vec<NoteSound>, tensions: &[i64]) -> Vec<NoteSound> {
    let Some(lowest) = notes.iter().min_by_key(|note| note.midi).copied() else {
        return notes;
    };
    let held: Vec<i64> = notes.iter().map(|note| note.midi.rem_euclid(12)).collect();
    let mut result = notes;
    for tension in tensions {
        if held.contains(&(lowest.midi + tension).rem_euclid(12)) {
            continue;
        }
        if let Some(added) = lowest.half_step(*tension) {
            result.push(added);
        }
    }
    result
}

/// How many half steps a degree of a scale is above its root, the major scale's without one.
fn half_steps_to(degree: i64, scale: Option<&Scale>) -> i64 {
    let shape = scale.map(|scale| scale.get_type().get_shape()).unwrap_or(MAJOR_SHAPE);
    let size = shape.len() as i64;
    (degree - 1).div_euclid(size) * 12 + shape[(degree - 1).rem_euclid(size) as usize]
}

/// A clip's notes moved to the chord sounding on another track as each starts; before the first chord, or with no track to
/// follow, nothing moves.
fn follow(clip: &Clip, chords: Option<&ChordSource>) -> Rendered<Clip> {
    let sounds = clip.resolved_sounds()?;
    let (Some(chords), Some(scale)) = (chords, clip.scale.as_ref()) else {
        return Ok(remade(clip, sounds));
    };
    let mut result = Vec::new();
    let mut now = Rational::ZERO;
    for sound in &sounds {
        result.push(followed(sound, now, scale, chords)?);
        now = now + sound.place();
    }
    Ok(remade(clip, result))
}

fn followed(sound: &Sound, start: Rational, scale: &Scale, chords: &ChordSource) -> Rendered<Sound> {
    Ok(match sound {
        Sound::Degree { .. } => followed(&settled(sound, Some(scale))?, start, scale, chords)?,
        Sound::Held { length, sound } => Sound::Held {
            length: *length,
            sound: Box::new(followed(sound, start, scale, chords)?),
        },
        Sound::Phrase { length, parts } => {
            let mut moved = Vec::new();
            let mut start = start;
            for part in parts {
                moved.push(followed(part, start, scale, chords)?);
                start = start + part.place();
            }
            Sound::Phrase { length: *length, parts: moved }
        }
        other => match (chords.chord_at(start), other) {
            (None, _) => other.clone(),
            (Some(chord), Sound::Note(note)) => Sound::Note(to_followed_chord(*note, chord, scale)),
            (Some(chord), Sound::Chord { notes, .. }) => Sound::chord(notes.iter().map(|note| to_followed_chord(*note, chord, scale)).collect()),
            _ => other.clone(),
        },
    })
}

/// A note moved to a chord heard on another track: along the scale for a root on a note of the scale, by exact half steps for
/// one between, then made the chord's own third, fifth or seventh; or as it was where that would leave the MIDI range.
fn to_followed_chord(note: NoteSound, chord: &HeardChord, scale: &Scale) -> NoteSound {
    let (root, _) = chord;
    let (steps, extra) = place_in(*root, scale);
    let moved = if extra != 0 {
        note.half_step((root - scale.get_root().get_midi_number()).rem_euclid(12))
            .ok_or_else(|| OutOfRange(String::new()))
    } else {
        along_scale(note, steps, Some(scale))
    };
    match moved.and_then(|moved| as_the_chord_has_it(note, moved, chord, scale)) {
        Ok(moved) => moved,
        Err(_) => note,
    }
}

fn as_the_chord_has_it(note: NoteSound, moved: NoteSound, chord: &HeardChord, scale: &Scale) -> Result<NoteSound, OutOfRange> {
    let (root, held) = chord;
    let (above, extra) = place_in(note.midi, scale);
    let kind: &[i64] = match above {
        2 => &[3, 4],
        4 => &[6, 7, 8],
        6 => &[9, 10, 11],
        _ => return Ok(moved),
    };
    if extra != 0 || scale.get_type().get_shape().len() != PLACED_SCALE_SIZE {
        return Ok(moved);
    }
    let own = (moved.midi - root).rem_euclid(12);
    let has: Vec<i64> = kind
        .iter()
        .copied()
        .filter(|interval| held.contains(&(root + interval).rem_euclid(12)))
        .collect();
    if !kind.contains(&own) || has.contains(&own) || has.len() != 1 {
        return Ok(moved);
    }
    moved.half_step(has[0] - own).ok_or_else(|| OutOfRange(String::new()))
}

/// Each chord of a clip voiced as near as it can be to the chord before, within its octaves.
pub struct VoiceLeading {
    lowest_octave: i64,
    highest_octave: i64,
    root_in_bass: bool,
    before: Option<Vec<i64>>,
}

impl VoiceLeading {
    fn generate(&mut self, clip: &Clip) -> Rendered<Clip> {
        let mut before = self.before.clone();
        let mut result = Vec::new();
        for sound in clip.resolved_sounds()? {
            let (chord, held) = match &sound {
                Sound::Held { length, sound } => (sound.as_ref().clone(), Some(*length)),
                other => (other.clone(), None),
            };
            let Sound::Chord { .. } = chord else {
                result.push(sound);
                continue;
            };
            let voiced = match &before {
                Some(before) => self.voiced(&chord, before),
                None => chord,
            };
            if let Sound::Chord { notes, .. } = &voiced {
                let mut pitches: Vec<i64> = notes.iter().map(|note| note.midi).collect();
                pitches.sort();
                before = Some(pitches);
            }
            result.push(match held {
                Some(length) => Sound::held(voiced, length),
                None => voiced,
            });
        }
        self.before = before;
        Ok(remade(clip, result))
    }

    fn fits(&self, pitches: &[i64]) -> bool {
        let lowest = (self.lowest_octave * 12).max(MIN_MIDI_NUMBER);
        let highest = ((self.highest_octave + 1) * 12 - 1).min(MAX_MIDI_NUMBER);
        pitches.iter().all(|pitch| (lowest..=highest).contains(pitch))
    }

    /// A chord voiced nearest the pitches before it, its notes kept in the order it was built.
    fn voiced(&self, chord: &Sound, before: &[i64]) -> Sound {
        let Sound::Chord { notes, .. } = chord else { return chord.clone() };
        let mut by_pitch: Vec<usize> = (0..notes.len()).collect();
        by_pitch.sort_by_key(|place| notes[*place].midi);
        let (fixed, moving): (&[usize], &[usize]) = if self.root_in_bass {
            by_pitch.split_at(1.min(by_pitch.len()))
        } else {
            (&[], &by_pitch[..])
        };
        let target = if self.root_in_bass && before.len() > 1 { &before[1..] } else { before };
        let floor = fixed.first().map(|place| notes[*place].midi);
        let pitches: Vec<i64> = moving.iter().map(|place| notes[*place].midi).collect();
        let mut best: Option<((i64, i64), Vec<i64>)> = None;
        for shape in voice_leading::inversions(&pitches) {
            for octaves in -OCTAVES_TRIED..=OCTAVES_TRIED {
                let tried: Vec<i64> = shape.iter().map(|pitch| pitch + octaves * 12).collect();
                if !self.fits(&tried) || floor.is_some_and(|floor| tried.iter().min().is_some_and(|lowest| *lowest <= floor)) {
                    continue;
                }
                let score = (voice_leading::movement(&tried, target), octaves.abs());
                if best.as_ref().is_none_or(|(found, _)| score < *found) {
                    best = Some((score, tried));
                }
            }
        }
        let Some((_, best)) = best else { return chord.clone() };
        let mut voiced = notes.clone();
        for (place, pitch) in moving.iter().zip(best) {
            if let Some(moved) = notes[*place].half_step(pitch - notes[*place].midi) {
                voiced[*place] = moved;
            }
        }
        Sound::chord(voiced)
    }
}
