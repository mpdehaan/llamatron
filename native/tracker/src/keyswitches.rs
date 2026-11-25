// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! An instrument's keyswitches as the pattern editor names them (the Python keyswitch_text.py and the pattern editor's
//! keyswitch_instrument): the ten slots of an instrument's Keyswitch Map, each a name and a MIDI note or neither, and the
//! instrument a pattern's steps are named by, where one is known for certain.

use crate::app::App;
use crate::settings::shown_octave;
use crate::uses::clip_slots_naming;
use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::file_format::{Section, KEYSWITCH_SLOT_COUNT};
use llamatron_model::values::generated::note::SHARP_NAMES;
use llamatron_strings::{marks, messages, named};

/// How wide a slot's note is written, such as C0 (24).
pub const KEYSWITCH_NOTE_WIDTH: usize = 12;
/// The names of the rows the Keyswitch section has, one a slot, each reading and writing the one Keyswitch row.
pub const SLOT_ROWS: [&str; 10] = [
    "keyswitch slot 0",
    "keyswitch slot 1",
    "keyswitch slot 2",
    "keyswitch slot 3",
    "keyswitch slot 4",
    "keyswitch slot 5",
    "keyswitch slot 6",
    "keyswitch slot 7",
    "keyswitch slot 8",
    "keyswitch slot 9",
];

/// One keyswitch slot as an instrument answers it: its name and its MIDI note, each None where the slot has none.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Keyswitch {
    pub name: Option<String>,
    pub note: Option<i64>,
}

/// The slot a row of the Keyswitch section stands for, or None for any other row.
pub fn slot_of_row(row: &str) -> Option<usize> {
    SLOT_ROWS.iter().position(|each| *each == row)
}

/// An instrument's ten slots, or ten empty ones where there is no instrument to ask.
pub fn keyswitches_of(app: &App, instrument: Option<&str>) -> Vec<Keyswitch> {
    let empty = vec![Keyswitch::default(); KEYSWITCH_SLOT_COUNT as usize];
    let Some(name) = instrument else { return empty };
    let Some(llamatron_model::objects::setlist::Item::Instrument(held)) = app.document.get_setlist().get_item(Section::INSTRUMENTS, name) else {
        return empty;
    };
    let Some(slots) = held.get_written("keyswitches").and_then(Data::as_list) else {
        return empty;
    };
    let mut keyswitches: Vec<Keyswitch> = slots
        .iter()
        .map(|slot| Keyswitch {
            name: slot.get("name").and_then(Data::as_str).map(str::to_string),
            note: slot.get("note").and_then(Data::as_whole).map(|note| note as i64),
        })
        .collect();
    keyswitches.resize(KEYSWITCH_SLOT_COUNT as usize, Keyswitch::default());
    keyswitches
}

/// What a slot is called: its name where the instrument gives it one, and its number otherwise.
pub fn slot_name(keyswitches: &[Keyswitch], slot: usize) -> String {
    match keyswitches.get(slot).and_then(|keyswitch| keyswitch.name.clone()) {
        Some(name) => name,
        None => named(marks::MSG_KEYSWITCH_SLOT_NAMED, &[("slot", slot.into())]),
    }
}

/// A keyswitch's MIDI note as the tracker writes it: its name in the set's octave labels and its number, such as C0 (24).
pub fn note_text(app: &App, note: i64) -> String {
    let octave = shown_octave(app.document.get_setlist(), note.div_euclid(12));
    let name = format!("{}{octave}", SHARP_NAMES[note.rem_euclid(12) as usize]);
    named(marks::MSG_KEYSWITCH_NOTE, &[("name", name.as_str().into()), ("number", note.into())])
}

/// The instrument whose keyswitches a pattern's steps are named by, and what the keyswitch dialog says over its slots:
/// the instrument's name, or why none is named. The instrument is known when a clip opened the editor, whose track plays
/// it, or when every track that plays the pattern has the one instrument; otherwise the slots go by their numbers alone.
pub fn keyswitch_instrument(app: &App, pattern: &str, opened_track: Option<&str>) -> (Option<String>, String) {
    let song = app.document.song();
    let names: Vec<Option<String>> = match opened_track.and_then(|track| song.get_track(track)) {
        Some(track) => vec![track.get_instrument_name()],
        None => {
            let setlist = app.document.get_setlist();
            let mut names = Vec::new();
            for (song_name, _, _, track) in clip_slots_naming(setlist, Section::PATTERNS, pattern) {
                let instrument = setlist
                    .get_song(&song_name)
                    .and_then(|held| held.get_track(&track))
                    .and_then(|held| held.get_instrument_name());
                if !names.contains(&instrument) {
                    names.push(instrument);
                }
            }
            names
        }
    };
    let known: Vec<&String> = names.iter().flatten().collect();
    if names.len() == 1 && !known.is_empty() {
        return (Some(known[0].clone()), known[0].clone());
    }
    if names.len() > 1 {
        return (None, messages::MSG_KEYSWITCH_SEVERAL_INSTRUMENTS.to_string());
    }
    (None, messages::MSG_KEYSWITCH_NO_INSTRUMENT.to_string())
}

/// The slots the Keyswitch section has a row for, and the hint over them: where one instrument is known, the slots its
/// Keyswitch Map gives a name or a note and any other slot a step uses; otherwise only the slots the steps use.
pub fn slot_rows(app: &App, pattern: &str, opened_track: Option<&str>) -> (Vec<usize>, String) {
    let (instrument, said) = keyswitch_instrument(app, pattern, opened_track);
    let mut used: Vec<usize> = Vec::new();
    if let Some(held) = app.document.get_setlist().get_pattern(pattern) {
        for step in 0..held.get_steps().max(0) as usize {
            for slot in crate::patterns::value(held, "keyswitch", step).and_then(Data::as_list).unwrap_or(&[]) {
                if let Some(slot) = slot.as_whole() {
                    used.push(slot as usize);
                }
            }
        }
    }
    let Some(instrument) = instrument else {
        used.sort_unstable();
        used.dedup();
        return (used, said);
    };
    let mapped = keyswitches_of(app, Some(&instrument))
        .iter()
        .enumerate()
        .filter(|(_, keyswitch)| **keyswitch != Keyswitch::default())
        .map(|(slot, _)| slot)
        .collect::<Vec<_>>();
    used.extend(mapped);
    used.sort_unstable();
    used.dedup();
    (used, named(messages::MSG_KEYSWITCH_SECTION_HINT, &[("instrument", said.as_str().into())]))
}
