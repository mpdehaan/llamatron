// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The MIDI import (the Python importers/midi_import.py): a MIDI file made into a song for a set, with the import dialog's
//! choices left as they first stand, every note played by the song for as long as the file plays it.

use crate::cutting::{auto_step_sizes, bar_lines, finest_step_size, grid_for, snapped, step_size_for, Cutter, Longest};
use crate::keys::{key_of_notes, key_of_signature, MusicalKey};
use crate::reading::{read_midi, Change, MidiContents, PartNote};
use crate::voices::voices_of;
use crate::writing::{ImportedSong, SongWriter};
use llamatron_math::Rational;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::values::time_signature::TimeSignature;

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

/// The song a MIDI file's bytes make for a set, named song_name, leaving the set as it is.
pub fn imported(midi: &[u8], setlist: &Setlist, song_name: &str) -> Result<ImportedSong, ImportProblem> {
    let contents = read_midi(midi).map_err(|problem| ImportProblem(problem.0))?;
    if contents.note_count() == 0 {
        return Err(ImportProblem("the MIDI file plays no notes".to_string()));
    }
    let (step_size, _) = step_size_for(&contents.parts, finest_step_size());
    let (parts, _) = snapped(&contents.parts, step_size);
    let keys = keys(&contents);
    let in_key = keys[0].value.places();
    let mut voices = Vec::new();
    for part in &parts {
        voices.extend(voices_of(part, true, true, Some(in_key.clone())));
    }
    let end = parts
        .iter()
        .flat_map(|part| part.notes.iter().map(|note| note.end))
        .max()
        .unwrap_or(Rational::ZERO);
    let holding = voices.iter().flat_map(|voice| voice.controls.iter().map(|control| control.time)).max();
    let bars = bar_lines(&contents.time_signatures, end, holding);
    let grid = grid_for(&voices, step_size);
    let longest = Longest {
        steps: DEFAULT_LONGEST_PATTERN,
        bars: None,
        bar: bars[1] - bars[0],
    };
    let cutter = Cutter::new(&voices, grid, &auto_step_sizes(), bars.clone(), keys, contents.tempos.clone(), longest);
    let cut = cutter.best_cut();
    let writer = SongWriter {
        setlist,
        voices: &voices,
        cut: &cut,
        bars: &bars,
        step_size: grid,
    };
    Ok(writer.written(song_name, time_signature_text(contents.time_signatures[0].value)))
}
