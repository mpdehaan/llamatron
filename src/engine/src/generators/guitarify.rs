// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Guitarify generator in Guitar mode (the Python engine/generators/guitarify/): a clip's chords and notes played as a
//! guitar plays them. Shape is the fretting hand: a chord voiced again as a hand can hold it, one note a string, within a few
//! frets of a position, above a capo; a single note stays, or becomes a power chord, a scale chord, an octave, a third or a
//! double stop. Strokes is the other hand: a bar of strokes, one a cell, following the song's bars. A strum's strings start
//! a few milliseconds apart, fading, each gap a little loose, all on an exact grid; with Let ring a string sounds until it
//! is struck again or its chord ends. A struck string is a held note, so that the strings of a strum overlap as on a guitar.

use crate::clip::Clip;
use crate::error::{RenderError, Rendered};
use crate::sound::{NoteSound, Sound};
use llamatron_math::{Number, PythonRandom, Rational, Seed};
use llamatron_model::file::data::Data;
use llamatron_model::schema::checking::{time_length, TimeLength};
use llamatron_model::schema::generated::file_format::{Approach, ChordColor, GuitarifySetting, SingleNotes, Stroke, Tuning, GENERATOR_ENABLED};
use llamatron_model::schema::generated::midi::{MAX_MIDI_NUMBER, MIN_MIDI_NUMBER};
use llamatron_model::values::scale::Scale;
use std::cell::RefCell;
use std::collections::HashMap;

const REACH: i64 = 4;
const POWER_CHORD: &[i64] = &[0, 7, 12];
const FIFTH: i64 = 7;
const MISSING_NOTE_COST: i64 = 1000;
const MISSING_ROOT_COST: i64 = 1500;
const MISSING_FIFTH_COST: i64 = 600;
const WRONG_BASS_COST: i64 = 400;
const INSIDE_MUTE_COST: i64 = 300;
const MUTED_STRING_COST: i64 = 40;
const SQUEAL_ABOVE: i64 = 24;
const FOURTH_BELOW: i64 = 5;
const NINTH_ABOVE: i64 = 14;
const FULL_VELOCITY: i64 = 127;
const PERCENT: i128 = 100;
const MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE: i128 = 240_000;
const TEMPO_DENOMINATOR: i128 = 1000;
const STRUM_TICKS: i128 = 19_200;
/// The folk strum, the bar a Guitarify plays unless its own is written: its cell, strokes and accents.
const DEFAULT_CELL: &str = "1/8";
const DEFAULT_BAR: &[&str] = &[
    Stroke::DOWN,
    Stroke::NOTHING,
    Stroke::DOWN,
    Stroke::UP,
    Stroke::NOTHING,
    Stroke::UP,
    Stroke::DOWN,
    Stroke::UP,
];
const DEFAULT_ACCENTS: &[bool] = &[true, false, false, false, false, false, true, false];

/// A chord as a hand is asked to hold it: the open strings, the hand's position, the chord's pitch classes and its root.
type ChordToHold = (Vec<i64>, i64, Vec<i64>, i64);

/// A way of holding a chord, a fret or none for each string, with how poor it is.
type ScoredHold = ((i64, Vec<i64>), Vec<Option<i64>>);

thread_local! {
    /// The best way to hold each chord, by the strings, the position, the chord's pitch classes and its root, since every
    /// clip of a song holds the same few chords.
    static VOICINGS: RefCell<HashMap<ChordToHold, Vec<i64>>> = RefCell::new(HashMap::new());
}

fn open_strings(tuning: &str) -> [i64; 6] {
    match tuning {
        Tuning::DROP_D => [38, 45, 50, 55, 59, 64],
        Tuning::OPEN_G => [38, 43, 50, 55, 59, 62],
        Tuning::OPEN_D => [38, 45, 50, 54, 57, 62],
        Tuning::DADGAD => [38, 45, 50, 55, 57, 62],
        _ => [40, 45, 50, 55, 59, 64],
    }
}

/// How long a short stroke rings, as a share of a cell.
fn short_stroke(stroke: &str) -> Option<Rational> {
    match stroke {
        Stroke::MUTE => Some(Rational::new(1, 4)),
        Stroke::STAB | Stroke::MUTED_BASS | Stroke::SQUEAL => Some(Rational::new(1, 2)),
        _ => None,
    }
}

/// What the strokes make of a clip, before the positions are laid out: a struck string, or a position passed on as it is.
#[derive(Clone)]
enum Event {
    Struck(NoteSound),
    PassedOn(Sound),
}

type Timed = (Rational, Event, Rational);

pub struct Guitarify {
    shape: bool,
    open: Vec<i64>,
    position: i64,
    single_notes: String,
    color: String,
    approach: String,
    strokes: bool,
    bar: Vec<String>,
    accents: Vec<bool>,
    cell: Rational,
    let_ring: bool,
    gap: Rational,
    fade: i64,
    loose_timing: i64,
    upstroke: Option<i64>,
    seed: Option<i128>,
    offset: Rational,
}

fn refused<T>(message: &str) -> Rendered<T> {
    Err(RenderError::Refused(message.to_string()))
}

/// A note at another pitch, spelled as a half step spells it, everything else kept.
fn moved(note: &NoteSound, midi: i64) -> Rendered<NoteSound> {
    note.half_step(midi - note.midi)
        .ok_or_else(|| RenderError::Refused("a guitar's note leaves the MIDI range".to_string()))
}

impl Guitarify {
    /// A Guitarify from its settings at a clip's place, or what is not ported yet.
    pub fn of(settings: &Data, bar_length: Rational, tempo: Number, seed: Option<i128>, offset: Rational) -> Rendered<Guitarify> {
        let written = |name: &str| settings.get(name).filter(|value| !value.is_null());
        let text = |name: &str, default: &str| {
            written(name)
                .map(Data::python_str)
                .filter(|value| !value.is_empty())
                .unwrap_or(default.to_string())
        };
        let whole = |name: &str, default: i64| written(name).and_then(Data::as_whole).map(|value| value as i64).unwrap_or(default);
        let _ = GENERATOR_ENABLED;
        let bar_written = written(GuitarifySetting::BAR).and_then(Data::as_list).filter(|bar| !bar.is_empty());
        let bar: Vec<String> = match bar_written {
            Some(bar) => bar.iter().map(Data::python_str).collect(),
            None => DEFAULT_BAR.iter().map(|stroke| stroke.to_string()).collect(),
        };
        let accents: Vec<bool> = if bar_written.is_none() && written(GuitarifySetting::ACCENTS).is_none() {
            DEFAULT_ACCENTS.to_vec()
        } else {
            let listed: Vec<bool> = written(GuitarifySetting::ACCENTS)
                .and_then(Data::as_list)
                .unwrap_or(&[])
                .iter()
                .map(|accent| *accent == Data::Bool(true))
                .collect();
            (0..bar.len()).map(|place| listed.get(place).copied().unwrap_or(false)).collect()
        };
        let cell_text = written(GuitarifySetting::CELL)
            .filter(|cell| cell.as_str() != Some(""))
            .cloned()
            .unwrap_or(Data::text(DEFAULT_CELL));
        let cell = match time_length(&cell_text).map_err(|problem| RenderError::Refused(problem.message))? {
            TimeLength::Bars(count) => bar_length * Rational::whole(count as i128),
            TimeLength::Length(length) => length,
        };
        let strings = whole(GuitarifySetting::STRINGS, 6) as usize;
        let capo = whole(GuitarifySetting::CAPO, 0);
        let tuned = open_strings(&text(GuitarifySetting::TUNING, Tuning::STANDARD));
        let open: Vec<i64> = tuned[6 - strings.min(6)..].iter().map(|pitch| pitch + capo).collect();
        let tempo = tempo.to_rational().limit_denominator(TEMPO_DENOMINATOR);
        let gap = Rational::whole(whole(GuitarifySetting::SPREAD, 8) as i128) * tempo / Rational::whole(MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE);
        let upstroke = whole(GuitarifySetting::UPSTROKE, 4);
        Ok(Guitarify {
            shape: written(GuitarifySetting::SHAPE) != Some(&Data::Bool(false)),
            open,
            position: whole(GuitarifySetting::POSITION, 0),
            single_notes: text(GuitarifySetting::SINGLE_NOTES, SingleNotes::LEAVE),
            color: text(GuitarifySetting::COLOR, ChordColor::AS_WRITTEN),
            approach: text(GuitarifySetting::APPROACH, Approach::OFF),
            strokes: written(GuitarifySetting::STROKES) != Some(&Data::Bool(false)) && !bar.is_empty(),
            bar,
            accents,
            cell,
            let_ring: written(GuitarifySetting::LET_RING) == Some(&Data::Bool(true)),
            gap,
            fade: whole(GuitarifySetting::FADE, 20),
            loose_timing: whole(GuitarifySetting::LOOSE_TIMING, 10),
            upstroke: (upstroke != 0).then_some(upstroke),
            seed,
            offset,
        })
    }

    pub fn generate(&self, clip: &Clip) -> Rendered<Clip> {
        let scale = clip.scale.as_ref();
        let mut sounds = Vec::new();
        for sound in clip.resolved_sounds()? {
            sounds.push(self.shaped_position(&sound, scale)?);
        }
        if self.strokes {
            sounds = self.struck(&sounds)?;
        }
        Ok(Clip {
            sounds,
            time_signature: None,
            looping: true,
            groove: None,
            ..clip.clone()
        })
    }

    fn shaped_position(&self, sound: &Sound, scale: Option<&Scale>) -> Rendered<Sound> {
        Ok(match sound {
            Sound::Held { length, sound } => Sound::Held {
                length: *length,
                sound: Box::new(self.shaped(sound, scale)?),
            },
            Sound::Note(_) | Sound::Chord { .. } | Sound::Degree { .. } => self.shaped(sound, scale)?,
            other => other.clone(),
        })
    }

    fn shaped(&self, sound: &Sound, scale: Option<&Scale>) -> Rendered<Sound> {
        let sound = match sound {
            Sound::Degree {
                length,
                number,
                octave,
                scale_notes,
                half_steps,
            } => match scale {
                None => return Ok(sound.clone()),
                Some(scale) => Sound::Note(
                    crate::sound::scale_sound(scale, *number, *scale_notes, octave * 12 + half_steps, *length, None, false)
                        .map_err(|problem| RenderError::Refused(problem.0))?,
                ),
            },
            other => other.clone(),
        };
        if !self.shape {
            return Ok(sound);
        }
        if let Sound::Chord { notes, .. } = &sound {
            if notes.len() > 1 {
                return self.voiced(&sound);
            }
        }
        let note = match &sound {
            Sound::Chord { notes, .. } => notes[0],
            Sound::Note(note) => *note,
            _ => return Ok(sound),
        };
        let chord_above = |above: &[i64]| Sound::chord_above(note, above).map_err(|problem| RenderError::Refused(problem.0));
        match self.single_notes.as_str() {
            SingleNotes::POWER_CHORD => return self.power_chord(&note),
            SingleNotes::SCALE_CHORD => {
                if let Some(above) = scale.and_then(|scale| triad_above(&note, scale)) {
                    return self.voiced(&chord_above(&above)?);
                }
            }
            SingleNotes::OCTAVE if note.midi + 12 <= MAX_MIDI_NUMBER => return chord_above(&[12]),
            SingleNotes::THIRD_ABOVE => {
                if let Some(above) = scale.and_then(|scale| triad_above(&note, scale)) {
                    if note.midi + above[0] <= MAX_MIDI_NUMBER {
                        return chord_above(&above[..1]);
                    }
                }
            }
            SingleNotes::DOUBLE_STOP if note.midi >= FOURTH_BELOW => return Ok(Sound::chord(vec![moved(&note, note.midi - FOURTH_BELOW)?, note])),
            _ => {}
        }
        Ok(sound)
    }

    /// A chord's notes, lowest first, as the color voices them: a ninth added, or the third moved or left out.
    fn colored(&self, notes: Vec<NoteSound>) -> Rendered<Vec<NoteSound>> {
        if self.color == ChordColor::AS_WRITTEN {
            return Ok(notes);
        }
        let root = notes[0];
        if self.color == ChordColor::ADD_9 {
            let ninth = root.midi + NINTH_ABOVE;
            if ninth > MAX_MIDI_NUMBER {
                return Ok(notes);
            }
            let mut colored = notes;
            colored.push(moved(&root, ninth)?);
            return Ok(colored);
        }
        let mut colored = Vec::new();
        for note in notes {
            let above = (note.midi - root.midi).rem_euclid(12);
            if above != 3 && above != 4 {
                colored.push(note);
            } else if self.color == ChordColor::SUS_2 {
                colored.push(moved(&note, note.midi - above + 2)?);
            } else if self.color == ChordColor::SUS_4 {
                colored.push(moved(&note, note.midi - above + 5)?);
            }
        }
        Ok(colored)
    }

    /// A single note as a power chord on the low strings: its root on the lowest string that can play it, the fifth and the
    /// octave above.
    fn power_chord(&self, note: &NoteSound) -> Rendered<Sound> {
        let lowest = self.open[0] + self.position;
        let root = lowest + (note.midi - lowest).rem_euclid(12);
        let mut notes = Vec::new();
        for above in POWER_CHORD {
            if root + above <= MAX_MIDI_NUMBER {
                notes.push(moved(note, root + above)?);
            }
        }
        Ok(Sound::chord(notes))
    }

    /// A chord as a hand holds it on the strings, from the lowest string up, each note the chord's own nearest of its class.
    fn voiced(&self, chord: &Sound) -> Rendered<Sound> {
        let Sound::Chord { notes, .. } = chord else { return Ok(chord.clone()) };
        let mut sorted = notes.clone();
        sorted.sort_by_key(|note| note.midi);
        let notes = self.colored(sorted)?;
        let mut classes: Vec<i64> = notes.iter().map(|note| note.midi.rem_euclid(12)).collect();
        classes.sort();
        classes.dedup();
        let root = notes[0].midi.rem_euclid(12);
        let pitches = best_voicing(&self.open, self.position, &classes, root);
        if pitches.is_empty() {
            return Ok(chord.clone());
        }
        let mut voiced = Vec::new();
        for pitch in pitches {
            let Some(note) = notes.iter().find(|note| note.midi.rem_euclid(12) == pitch.rem_euclid(12)) else {
                return refused("a voicing holds a note the chord has not");
            };
            voiced.push(moved(note, pitch)?);
        }
        Ok(Sound::chord(voiced))
    }

    /// The positions the bar of strokes makes of the shaped ones.
    fn struck(&self, sounds: &[Sound]) -> Rendered<Vec<Sound>> {
        let mut events: Vec<Timed> = Vec::new();
        let mut time = Rational::ZERO;
        let mut before: Option<Vec<i64>> = None;
        for (place, sound) in sounds.iter().enumerate() {
            let length = sound.place();
            let played = match sound {
                Sound::Held { sound, .. } => sound.as_ref(),
                other => other,
            };
            match played {
                Sound::Note(_) | Sound::Chord { .. } => {
                    let end = time + self.sounding_length(sound, played, length);
                    let mut strokes = self.strokes_on(played, time, end, place)?;
                    let pitches = pitches_of(played);
                    if self.approach != Approach::OFF && before.as_ref().is_some_and(|before| *before != pitches) {
                        strokes = self.approached(played, strokes, time, end)?;
                    }
                    before = Some(pitches);
                    events.extend(strokes);
                }
                Sound::Rest(_) => {}
                _ => events.push((time, Event::PassedOn(sound.clone()), time + length)),
            }
            time = time + length;
        }
        Ok(positions(events, time))
    }

    /// A new chord's strokes with the chord first played a fret away for a moment, whatever was struck then struck after.
    fn approached(&self, played: &Sound, strokes: Vec<Timed>, start: Rational, end: Rational) -> Rendered<Vec<Timed>> {
        let moment = Rational::new(1, 16).min((end - start) / Rational::whole(2));
        let lands = start + moment;
        let from_fret = if self.approach == Approach::FROM_BELOW { -1 } else { 1 };
        let strings = crate::positions::notes_of(played);
        if !strings
            .iter()
            .all(|note| (MIN_MIDI_NUMBER..=MAX_MIDI_NUMBER).contains(&(note.midi + from_fret)))
        {
            return Ok(strokes);
        }
        let mut events = Vec::new();
        for note in &strings {
            events.push((
                start,
                Event::Struck(NoteSound {
                    length: Some(moment),
                    ..moved(note, note.midi + from_fret)?
                }),
                lands,
            ));
        }
        for (begins, event, stops) in strokes {
            let (mut begins, mut event) = (begins, event);
            if begins < lands {
                begins = begins + moment;
                if stops <= begins {
                    continue;
                }
                if let Event::Struck(note) = event {
                    event = Event::Struck(NoteSound {
                        length: Some(stops - begins),
                        ..note
                    });
                }
            }
            events.push((begins, event, stops));
        }
        Ok(events)
    }

    fn sounding_length(&self, sound: &Sound, played: &Sound, length: Rational) -> Rational {
        match (sound, played.length()) {
            (Sound::Held { .. }, Some(own)) => own,
            _ => length,
        }
    }

    /// The events of the strokes that fall while one note or chord sounds, from start to end.
    fn strokes_on(&self, played: &Sound, start: Rational, end: Rational, place: usize) -> Rendered<Vec<Timed>> {
        let mut strings = crate::positions::notes_of(played);
        strings.sort_by_key(|note| note.midi);
        let mut struck: Vec<(Rational, &str, bool, Vec<NoteSound>)> = Vec::new();
        for (time, cell) in self.cells(start, end) {
            let stroke = self.bar[cell].as_str();
            if stroke != Stroke::NOTHING {
                struck.push((time, stroke, self.accents[cell], self.strings_of(stroke, &strings)?));
            }
        }
        let any_accent = self.accents.iter().any(|accent| *accent);
        let mut events = Vec::new();
        for (index, (time, stroke, accent, chosen)) in struck.iter().enumerate() {
            let following = struck.get(index + 1).map(|(time, ..)| *time).unwrap_or(end);
            let delays = self.delays(chosen.len(), following - *time, (place * self.bar.len() + index) as i128);
            for (string, (note, delay)) in chosen.iter().zip(delays).enumerate() {
                let mut stops = self.stops(note, index, &struck, end, following);
                if let Some(share) = short_stroke(stroke) {
                    stops = stops.min(*time + self.cell * share);
                }
                let begins = *time + delay;
                if stops <= begins {
                    continue;
                }
                let accented = any_accent.then_some(*accent);
                let share = stroke_share(stroke, accented, self.fade, string as i64, chosen.len() as i64);
                events.push((
                    begins,
                    Event::Struck(softened(
                        NoteSound {
                            length: Some(stops - begins),
                            ..*note
                        },
                        share,
                    )),
                    stops,
                ));
            }
        }
        Ok(events)
    }

    /// Where a sound starts and every cell that starts while it sounds, each with its cell of the bar.
    fn cells(&self, start: Rational, end: Rational) -> Vec<(Rational, usize)> {
        let whole = self.offset + start;
        let mut number = (whole / self.cell).floor();
        let count = self.bar.len() as i128;
        let mut found = Vec::new();
        let mut time = start;
        if self.cell * Rational::whole(number) != whole {
            found.push((start, number.rem_euclid(count) as usize));
            number += 1;
            time = self.cell * Rational::whole(number) - self.offset;
        }
        while time < end {
            found.push((time, number.rem_euclid(count) as usize));
            number += 1;
            time = time + self.cell;
        }
        found
    }

    /// The notes a stroke strikes, in the order it strikes them, from a chord's notes given lowest first.
    fn strings_of(&self, stroke: &str, strings: &[NoteSound]) -> Rendered<Vec<NoteSound>> {
        Ok(match stroke {
            Stroke::DOWN | Stroke::MUTE | Stroke::STAB => strings.to_vec(),
            Stroke::UP => {
                let top = match self.upstroke {
                    Some(count) => &strings[strings.len().saturating_sub(count as usize)..],
                    None => strings,
                };
                top.iter().rev().copied().collect()
            }
            Stroke::BASS | Stroke::MUTED_BASS => strings[..1].to_vec(),
            Stroke::SQUEAL => {
                let high = strings[0].midi + SQUEAL_ABOVE;
                if high > MAX_MIDI_NUMBER {
                    strings[strings.len() - 1..].to_vec()
                } else {
                    vec![moved(&strings[0], high)?]
                }
            }
            Stroke::ALT_BASS => {
                let fifth = (strings[0].midi + FIFTH).rem_euclid(12);
                match strings[1..].iter().find(|note| note.midi.rem_euclid(12) == fifth) {
                    Some(note) => vec![*note],
                    None => strings.get(1).or(strings.first()).map(|note| vec![*note]).unwrap_or_default(),
                }
            }
            other => {
                let counted: usize = other.trim_start_matches("string_").parse().unwrap_or(1);
                vec![strings[strings.len().saturating_sub(counted)]]
            }
        })
    }

    /// How much later than the stroke each of its strings starts: a gap more for each after the first, loose by the seed, all
    /// within the room the stroke has, on the grid.
    fn delays(&self, count: usize, room: Rational, seed_place: i128) -> Vec<Rational> {
        let mut delays = vec![Rational::ZERO];
        if count < 2 || self.gap <= Rational::ZERO {
            return vec![Rational::ZERO; count];
        }
        let mut chooser = match self.seed {
            Some(seed) => PythonRandom::new(Seed::Whole(seed + seed_place)),
            None => PythonRandom::unseeded(),
        };
        for _ in 0..count - 1 {
            let mut loose = Rational::ZERO;
            if self.loose_timing != 0 {
                let spread = self.loose_timing as f64;
                loose = Rational::new(chooser.uniform(-spread, spread).round_ties_even() as i128, PERCENT);
            }
            let last = delays[delays.len() - 1];
            delays.push(last + self.gap * (Rational::whole(1) + loose));
        }
        let widest = room * Rational::new(1, 2);
        let last = delays[delays.len() - 1];
        if last > widest {
            delays = delays.iter().map(|delay| *delay * widest / last).collect();
        }
        delays
            .iter()
            .map(|delay| Rational::new((*delay * Rational::whole(STRUM_TICKS)).round(), STRUM_TICKS))
            .collect()
    }

    /// When a struck string stops: with Let ring, when a later stroke strikes its pitch or the chord ends; else at the next.
    fn stops(&self, note: &NoteSound, index: usize, struck: &[(Rational, &str, bool, Vec<NoteSound>)], end: Rational, following: Rational) -> Rational {
        if !self.let_ring {
            return following;
        }
        for (time, _, _, chosen) in &struck[index + 1..] {
            if chosen.iter().any(|other| other.midi == note.midi) {
                return *time;
            }
        }
        end
    }
}

fn pitches_of(played: &Sound) -> Vec<i64> {
    let mut pitches: Vec<i64> = crate::positions::notes_of(played).iter().map(|note| note.midi).collect();
    pitches.sort();
    pitches
}

/// A note at a share of its loudness, never silent; a note with no velocity of its own is taken as full.
fn softened(note: NoteSound, share: Rational) -> NoteSound {
    if share == Rational::whole(1) {
        return note;
    }
    let velocity = note.velocity.unwrap_or(FULL_VELOCITY);
    let softer = (Rational::whole(velocity as i128) * share).round().max(1) as i64;
    NoteSound {
        velocity: Some(softer),
        ..note
    }
}

/// The share of its velocity a note of a stroke keeps: a mute and an unaccented muted bass quieter, an unaccented stroke
/// quieter in a bar with accents, and each string after the first faded by a further share of fade.
fn stroke_share(stroke: &str, accented: Option<bool>, fade: i64, string: i64, count: i64) -> Rational {
    let mut share = Rational::whole(1);
    if stroke == Stroke::MUTE {
        share = share * Rational::new(1, 2);
    }
    if stroke == Stroke::MUTED_BASS {
        if accented != Some(true) {
            share = share * Rational::new(4, 5);
        }
    } else if accented == Some(false) && stroke != Stroke::SQUEAL {
        share = share * Rational::new(4, 5);
    }
    if fade != 0 && count > 1 {
        share = share * (Rational::whole(1) - Rational::new((fade * string) as i128, PERCENT * (count as i128 - 1)));
    }
    share
}

/// The pitches of the best way to hold a chord, the lowest string first, or none where no string can play any of it.
fn best_voicing(strings: &[i64], position: i64, classes: &[i64], root: i64) -> Vec<i64> {
    let key = (strings.to_vec(), position, classes.to_vec(), root);
    if let Some(found) = VOICINGS.with(|voicings| voicings.borrow().get(&key).cloned()) {
        return found;
    }
    let frets: Vec<i64> = if position == 0 {
        (0..REACH).collect()
    } else {
        (position..position + REACH).collect()
    };
    let choices: Vec<Vec<Option<i64>>> = strings
        .iter()
        .map(|open| {
            let mut options = vec![None];
            options.extend(
                frets
                    .iter()
                    .filter(|fret| classes.contains(&(open + *fret).rem_euclid(12)) && open + *fret <= MAX_MIDI_NUMBER)
                    .map(|fret| Some(*fret)),
            );
            options
        })
        .collect();
    let mut ways: Vec<Vec<Option<i64>>> = vec![Vec::new()];
    for options in &choices {
        ways = ways
            .iter()
            .flat_map(|way| options.iter().map(move |option| [way.clone(), vec![*option]].concat()))
            .collect();
    }
    let mut best: Option<ScoredHold> = None;
    for held in ways {
        if held.iter().all(Option::is_none) {
            continue;
        }
        let score = cost(strings, &held, classes, root);
        if best.as_ref().is_none_or(|(found, _)| score < *found) {
            best = Some((score, held));
        }
    }
    let pitches: Vec<i64> = match best {
        None => Vec::new(),
        Some((_, held)) => strings.iter().zip(held).filter_map(|(open, fret)| fret.map(|fret| open + fret)).collect(),
    };
    VOICINGS.with(|voicings| voicings.borrow_mut().insert(key, pitches.clone()));
    pitches
}

/// How poor a way of holding a chord is, lower being better, with the way itself last so that two equal ways always choose
/// the same.
fn cost(strings: &[i64], held: &[Option<i64>], classes: &[i64], root: i64) -> (i64, Vec<i64>) {
    let sounding: Vec<usize> = (0..held.len()).filter(|place| held[*place].is_some()).collect();
    let pitches: Vec<i64> = sounding.iter().map(|place| strings[*place] + held[*place].unwrap_or(0)).collect();
    let played: Vec<i64> = pitches.iter().map(|pitch| pitch.rem_euclid(12)).collect();
    let mut total: i64 = classes
        .iter()
        .filter(|class| !played.contains(class))
        .map(|missing| missing_cost(*missing, root))
        .sum();
    if pitches[0].rem_euclid(12) != root {
        total += WRONG_BASS_COST;
    }
    total += INSIDE_MUTE_COST * (sounding[sounding.len() - 1] as i64 - sounding[0] as i64 + 1 - sounding.len() as i64);
    total += MUTED_STRING_COST * (held.len() - sounding.len()) as i64;
    total += sounding.iter().map(|place| held[*place].unwrap_or(0)).sum::<i64>();
    (total, held.iter().map(|fret| fret.unwrap_or(-1)).collect())
}

fn missing_cost(missing: i64, root: i64) -> i64 {
    if missing == root {
        return MISSING_ROOT_COST;
    }
    if missing == (root + FIFTH).rem_euclid(12) {
        return MISSING_FIFTH_COST;
    }
    MISSING_NOTE_COST
}

/// The half steps above a note to the third and fifth its place in the scale builds, or None for a note not in the scale.
fn triad_above(note: &NoteSound, scale: &Scale) -> Option<Vec<i64>> {
    let steps = scale.get_type().get_shape();
    let place = (note.midi - scale.get_root().get_midi_number()).rem_euclid(12);
    let index = steps.iter().position(|step| *step == place)? as i64;
    let size = steps.len() as i64;
    Some(
        [2, 4]
            .iter()
            .map(|along| (index + along).div_euclid(size) * 12 + steps[(index + along).rem_euclid(size) as usize] - place)
            .collect(),
    )
}

/// A clip's positions from timed events: notes struck at one moment are one chord, each place lasting until the next
/// starts, and a struck note sounding for its own length, as a held sound.
fn positions(events: Vec<Timed>, total: Rational) -> Vec<Sound> {
    let mut groups: Vec<(Rational, Vec<(Event, Rational)>)> = Vec::new();
    for (start, event, end) in events {
        match groups.iter_mut().find(|(found, _)| *found == start) {
            Some((_, group)) => group.push((event, end)),
            None => groups.push((start, vec![(event, end)])),
        }
    }
    groups.sort_by_key(|(start, _)| *start);
    let mut positions = Vec::new();
    let mut time = Rational::ZERO;
    for (place, (start, group)) in groups.iter().enumerate() {
        if *start > time {
            positions.push(Sound::Rest(*start - time));
        }
        let following = groups.get(place + 1).map(|(start, _)| *start).unwrap_or(total);
        if let Some((Event::PassedOn(sound), end)) = group.iter().find(|(event, _)| matches!(event, Event::PassedOn(_))) {
            let end = (*end).min(following);
            positions.push(sound.with_length(Some(end - *start)));
            time = end;
            continue;
        }
        let notes: Vec<NoteSound> = group
            .iter()
            .filter_map(|(event, _)| match event {
                Event::Struck(note) => Some(*note),
                Event::PassedOn(_) => None,
            })
            .collect();
        let played = if notes.len() > 1 { Sound::chord(notes) } else { Sound::Note(notes[0]) };
        positions.push(Sound::held(played, following - *start));
        time = following;
    }
    if total > time {
        positions.push(Sound::Rest(total - time));
    }
    positions
}

/// How a Guitarify in Strum mode strums a clip's chords: its direction, its spread in milliseconds, fade and loose timing, and
/// how many top strings an upstroke catches, None for every string; or None for one in Guitar mode.
pub fn strum_values(settings: &Data) -> Option<(String, i64, i64, i64, Option<i64>)> {
    let written = |name: &str| settings.get(name).filter(|value| !value.is_null());
    if written(GuitarifySetting::MODE).map(Data::python_str).as_deref() != Some("strum") {
        return None;
    }
    let whole = |name: &str, default: i64| written(name).and_then(Data::as_whole).map(|value| value as i64).unwrap_or(default);
    let direction = written(GuitarifySetting::DIRECTION)
        .map(Data::python_str)
        .filter(|direction| !direction.is_empty())
        .unwrap_or("by_the_beat".to_string());
    let upstroke = whole(GuitarifySetting::UPSTROKE, 4);
    Some((
        direction,
        whole(GuitarifySetting::SPREAD, 8),
        whole(GuitarifySetting::FADE, 20),
        whole(GuitarifySetting::LOOSE_TIMING, 10),
        (upstroke != 0).then_some(upstroke),
    ))
}
