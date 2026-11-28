// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The MIDI import (the Python importers/midi_import.py): a MIDI file made into a song for a set, with the import dialog's
//! choices left as they first stand, every note played by the song for as long as the file plays it.

use crate::cutting::Cut;
use crate::cutting::{auto_step_sizes, bar_lines, finest_step_size, grid_for, snapped, step_size_for, Cutter, Longest};
use crate::keys::{key_of_notes, key_of_signature, MusicalKey};
use crate::reading::{read_midi, Change, MidiContents, MidiPart, PartNote};
use crate::voices::{voices_of, Voice};
use crate::writing::{ImportedSong, SongWriter};
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::values::time_signature::TimeSignature;
use llamatron_names::fill;

const DEFAULT_LONGEST_PATTERN: i64 = 32;

/// What is wrong with a MIDI file the import can't make a song of.
#[derive(Debug)]
pub struct ImportProblem(pub String);

/// The song's keys in time order: the file's key signatures, or the key its notes are in where it has none from the start.
fn keys(contents: &MidiContents) -> Vec<Change<MusicalKey>> {
    let mut keys: Vec<Change<MusicalKey>> = Vec::new();
    for change in &contents.keys {
        let key = key_of_signature(&change.value);
        match keys.last_mut() {
            Some(last) if last.time == change.time => *last = Change { time: change.time, value: key },
            Some(last) if last.value == key => {}
            _ => keys.push(Change { time: change.time, value: key }),
        }
    }
    if keys.first().is_none_or(|first| first.time != Rational::ZERO) {
        let first = match keys.first() {
            Some(first) => first.value.clone(),
            None => {
                let notes: Vec<PartNote> = contents.parts.iter().flat_map(|part| part.notes.iter().copied()).collect();
                key_of_notes(&notes)
            }
        };
        keys.insert(
            0,
            Change {
                time: Rational::ZERO,
                value: first,
            },
        );
    }
    keys
}

fn time_signature_text((beats, unit): (i64, i64)) -> Option<String> {
    TimeSignature::new(beats, unit).ok().map(|signature| signature.to_text())
}

/// The longest pattern the import may make, in steps, as the import dialog offers it, and how large a share of the notes
/// moved to a step says they were swung.
pub const LONGEST_PATTERN_CHOICES: [i64; 5] = [8, 16, 32, 64, 128];
const SWING_SHARE: f64 = 0.1;

/// What the import dialog asks: the song's name, the longest pattern, whether every pattern gets a name of its own, chords
/// as chords, whether CCs come in, and the step size, or None to work it out.
#[derive(Clone, Debug, PartialEq)]
pub struct ImportChoices {
    pub song_name: String,
    pub longest_pattern: i64,
    pub unique_names: bool,
    pub chords: bool,
    pub controls: bool,
    pub step_size: Option<Rational>,
}

impl ImportChoices {
    /// The choices the dialog starts on, for a song of a name.
    pub fn named(song_name: &str) -> ImportChoices {
        ImportChoices {
            song_name: song_name.to_string(),
            longest_pattern: DEFAULT_LONGEST_PATTERN,
            unique_names: true,
            chords: true,
            controls: true,
            step_size: None,
        }
    }
}

/// What a MIDI file holds, as the import dialog says it: its tracks that play notes, its bars, its first time signature and
/// tempo, and its keys in order.
pub struct Found {
    pub tracks: usize,
    pub bars: usize,
    pub time_signature: Option<String>,
    pub tempo: Data,
    pub keys: Vec<MusicalKey>,
}

/// A song made from a MIDI file, ready to add to the set, and what it holds and what changed, for the dialog to say.
pub struct Imported {
    pub song: ImportedSong,
    pub step_size: Rational,
    pub tracks: usize,
    pub patterns: usize,
    pub scenes: usize,
    pub long_patterns: i64,
    pub warnings: Vec<String>,
}

/// One MIDI file read for importing.
pub struct MidiImport {
    contents: MidiContents,
}

impl MidiImport {
    /// A MIDI file's bytes read for importing, or why they cannot be.
    pub fn new(midi: &[u8]) -> Result<MidiImport, ImportProblem> {
        let contents = read_midi(midi).map_err(|problem| ImportProblem(problem.0))?;
        if contents.note_count() == 0 {
            return Err(ImportProblem(llamatron_strings::errors::ERR_MIDI_NO_NOTES.to_string()));
        }
        Ok(MidiImport { contents })
    }

    /// What the file holds: its MIDI tracks that play notes, its bars, its first time signature and tempo, and its keys.
    pub fn found(&self) -> Found {
        let contents = &self.contents;
        let end = contents
            .parts
            .iter()
            .flat_map(|part| part.notes.iter().map(|note| note.end))
            .max()
            .unwrap_or(Rational::ZERO);
        let bars = bar_lines(&contents.time_signatures, end, None);
        let mut names: Vec<&str> = contents.parts.iter().map(|part| part.name.as_str()).collect();
        names.sort_unstable();
        names.dedup();
        Found {
            tracks: names.len(),
            bars: bars.len().saturating_sub(1),
            time_signature: time_signature_text(contents.time_signatures[0].value),
            tempo: crate::writing::tempo_of(contents.tempos[0].value),
            keys: keys(contents).into_iter().map(|change| change.value).collect(),
        }
    }

    /// The song this file makes for a set, with the choices given, leaving the set as it is.
    pub fn imported(&self, setlist: &Setlist, choices: &ImportChoices) -> Imported {
        let contents = &self.contents;
        let (found_size, _) = step_size_for(&contents.parts, finest_step_size());
        let step_size = choices.step_size.unwrap_or(found_size);
        let clip_step_sizes = match choices.step_size {
            Some(size) => vec![size],
            None => auto_step_sizes(),
        };
        let (parts, moved) = snapped(&contents.parts, step_size);
        let keys = keys(contents);
        let in_key = keys[0].value.places();
        let mut voices = Vec::new();
        let mut firsts = Vec::new();
        for part in &parts {
            firsts.push(voices.len());
            voices.extend(voices_of(part, choices.chords, choices.controls, Some(in_key.clone())));
        }
        let end = parts
            .iter()
            .flat_map(|part| part.notes.iter().map(|note| note.end))
            .max()
            .unwrap_or(Rational::ZERO);
        let holding = voices.iter().flat_map(|voice| voice.controls.iter().map(|control| control.time)).max();
        let bars = bar_lines(&contents.time_signatures, end, holding);
        let grid = match choices.step_size {
            Some(size) => size,
            None => grid_for(&voices, step_size),
        };
        let longest = Longest {
            steps: choices.longest_pattern,
            bars: None,
            bar: bars[1] - bars[0],
        };
        let cutter = Cutter::new(&voices, grid, &clip_step_sizes, bars.clone(), keys, contents.tempos.clone(), longest);
        let cut = cutter.best_cut();
        let writer = SongWriter {
            setlist,
            voices: &voices,
            cut: &cut,
            bars: &bars,
            step_size: grid,
            share: !choices.unique_names,
        };
        let song = writer.written(&choices.song_name, time_signature_text(contents.time_signatures[0].value));
        let warnings = self.warnings(&voices, &parts, &firsts, &cut, grid, moved, choices.controls);
        Imported {
            patterns: song.patterns.len(),
            song,
            step_size,
            tracks: voices.len(),
            scenes: cut.scenes.len(),
            long_patterns: cut.long_patterns,
            warnings,
        }
    }

    /// What the import had to change, each a sentence with its count, in the order the dialog says them.
    #[allow(clippy::too_many_arguments)]
    fn warnings(&self, voices: &[Voice], parts: &[MidiPart], firsts: &[usize], cut: &Cut, grid: Rational, moved: i64, controls: bool) -> Vec<String> {
        use llamatron_strings::texts::importing;
        let contents = &self.contents;
        let mut left_out = Vec::new();
        for (part, first) in parts.iter().zip(firsts) {
            let lanes: &[i64] = voices.get(*first).map_or(&[], |voice| voice.lanes.as_slice());
            left_out.extend(
                part.controls
                    .iter()
                    .filter(|control| !lanes.contains(&control.number))
                    .map(|control| control.number),
            );
        }
        let mut numbers = left_out.clone();
        numbers.sort_unstable();
        numbers.dedup();
        let numbers: Vec<String> = numbers.iter().map(i64::to_string).collect();
        let numbers = numbers.join(importing::MSG_WARN_NUMBERS_JOIN);
        let tempos_moved = contents
            .tempos
            .iter()
            .filter(|change| scene_tempo_at(cut, change.time, grid) != change.value)
            .count() as i64;
        let glided = voices.iter().flat_map(|voice| voice.played.iter()).filter(|played| played.glide).count() as i64;
        let swung = moved as f64 >= SWING_SHARE * contents.note_count() as f64;
        let counted = [
            (moved, if swung { importing::MSG_WARN_SWUNG } else { importing::MSG_WARN_MOVED }),
            (cut.lengths_changed, importing::MSG_WARN_LENGTHS_CHANGED),
            (cut.too_low, importing::MSG_WARN_TOO_LOW),
            (glided, importing::MSG_WARN_GLIDED),
            (cut.controls_moved, importing::MSG_WARN_CONTROLS_MOVED),
            (tempos_moved, importing::MSG_WARN_TEMPOS_MOVED),
            (contents.unended, importing::MSG_WARN_UNENDED),
            (
                left_out.len() as i64,
                if controls {
                    importing::MSG_WARN_CONTROLS_LEFT_OUT
                } else {
                    importing::MSG_WARN_CONTROLS_OFF
                },
            ),
            (contents.controls_without_notes, importing::MSG_WARN_CONTROLS_NO_NOTES),
            (contents.left_out, importing::MSG_WARN_LEFT_OUT),
        ];
        counted
            .iter()
            .filter(|(count, _)| *count != 0)
            .map(|(count, message)| llamatron_strings::named(message, &[(fill::COUNT, (*count).into()), (fill::NUMBERS, numbers.as_str().into())]))
            .collect()
    }
}

/// The tempo of the scene that plays at a time, in microseconds a quarter note, which differs from a tempo change at that
/// time where the change could not start a scene.
fn scene_tempo_at(cut: &Cut, time: Rational, step_size: Rational) -> i64 {
    let mut tempo = cut.scenes[0].tempo;
    for scene in &cut.scenes {
        if Rational::whole(scene.start as i128) * step_size > time {
            break;
        }
        tempo = scene.tempo;
    }
    tempo
}

/// The song a MIDI file's bytes make for a set, named song_name, with the import dialog's first choices, leaving the set
/// as it is.
pub fn imported(midi: &[u8], setlist: &Setlist, song_name: &str) -> Result<ImportedSong, ImportProblem> {
    let import = MidiImport::new(midi)?;
    Ok(import.imported(setlist, &ImportChoices::named(song_name)).song)
}
