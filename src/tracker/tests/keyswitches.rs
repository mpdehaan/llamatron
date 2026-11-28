// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Keyswitches as a person hears them: a pattern's Keyswitch row sends each slot's note from its instrument's Keyswitch
//! Map for as long as the step's note is written, held on by a tie, early by the instrument's Keyswitch lead but never
//! before the clip; none from a slot with no note or an instrument through FluidSynth; carried by the MIDI file and real
//! time to a MIDI port, and left out of the General MIDI file.

use llamatron_engine::realizer::{Grid, SongRealizer};
use llamatron_engine::timing::keyswitch_events;
use llamatron_exporters::midi::song_file;
use llamatron_importers::reading::read_midi;
use llamatron_math::rational::Rational;
use llamatron_model::objects::setlist::Setlist;
use llamatron_names::scenario;
use llamatron_names::spec;
use llamatron_tracker::realtime::timeline::{song_timeline, Route};

/// The slots' notes in the scenario's Keyswitch Map: sustain and staccato; legato has none.
const SUSTAIN_NOTE: i64 = 24;
const STACCATO_NOTE: i64 = 25;
const SEED: i64 = 7;

/// The scenario's song, rendered.
fn keyswitched() -> Grid {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/keyswitched.yml");
    let text = std::fs::read_to_string(path).expect("the scenario's set is there");
    let setlist = Setlist::read_text(&text).expect("the scenario's set is valid");
    let song = setlist.get_song(spec::SONG).expect("the song");
    SongRealizer::new(&setlist, song, Some(SEED)).render().expect("the song renders")
}

/// The keyswitch notes a track's clip sends: start, end and note.
fn switches(grid: &Grid, track: &str) -> Vec<(Rational, Rational, i64)> {
    let clip = &grid.rows[0].clips.iter().find(|(name, _)| name == track).expect("the track's clip").1;
    let length = Rational::whole(1);
    keyswitch_events(clip, length)
        .iter()
        .map(|note| (note.start, note.end, note.midi_number))
        .collect()
}

fn quarter(count: i128) -> Rational {
    Rational::new(count, 4)
}

/// Sustain sounds under the tied first note, staccato under the third, legato's slot sends nothing; the lead sends each
/// early but never before the clip; FluidSynth is sent none.
#[test]
fn each_slot_sends_its_note_as_long_as_the_note_is_written() {
    let grid = keyswitched();
    // Ten milliseconds at 120 beats a minute, in whole notes: a whole note lasts two seconds.
    let lead = Rational::new(1, 200);
    let sustain = (Rational::ZERO, quarter(2), SUSTAIN_NOTE);
    let staccato = (quarter(2), quarter(3), STACCATO_NOTE);
    assert_eq!(switches(&grid, scenario::LEAD), [sustain, staccato]);
    assert_eq!(switches(&grid, scenario::EARLY), [sustain, (staccato.0 - lead, staccato.1, STACCATO_NOTE)]);
    assert!(switches(&grid, scenario::SAMPLED).is_empty());
}

/// The MIDI file carries the keyswitch notes beside the tune's, and the General MIDI file, which a player would sound
/// them in, leaves them out.
#[test]
fn the_midi_file_carries_keyswitches_and_the_general_midi_file_leaves_them_out() {
    let grid = keyswitched();
    let pitches = |general_midi: bool| -> Vec<i64> {
        let (_, bytes) = song_file(&grid, spec::SONG, general_midi).expect("the file writes");
        let contents = read_midi(&bytes).expect("the file reads back");
        let lead = contents.parts.iter().find(|part| part.name == scenario::LEAD).expect("the lead's part");
        lead.notes.iter().map(|note| note.pitch).collect()
    };
    let midi = pitches(false);
    assert!(midi.contains(&SUSTAIN_NOTE) && midi.contains(&STACCATO_NOTE), "{midi:?}");
    let general = pitches(true);
    assert!(!general.contains(&SUSTAIN_NOTE) && !general.contains(&STACCATO_NOTE), "{general:?}");
}

/// Real time sends a MIDI port the keyswitch, marked as one, before the note it changes at the same instant, and a route
/// that takes none is sent none.
#[test]
fn real_time_sends_a_port_the_keyswitch_before_its_note() {
    let grid = keyswitched();
    let route = |keyswitches: bool| Route {
        port: "a port".to_string(),
        channel: 0,
        program: None,
        pan: None,
        keyswitches,
        sound: None,
        early: 0.0,
    };
    let events = song_timeline(
        &grid,
        &[(scenario::LEAD.to_string(), route(true)), (scenario::SAMPLED.to_string(), route(false))],
    )
    .expect("a timeline");
    let lead: Vec<_> = events.iter().filter(|event| event.tag.track == scenario::LEAD).collect();
    let first_on = lead.iter().find(|event| event.value > 0).expect("a note on");
    assert!(first_on.switch && first_on.number == SUSTAIN_NOTE);
    let sampled_switches = events.iter().filter(|event| event.tag.track == scenario::SAMPLED && event.switch).count();
    assert_eq!(sampled_switches, 0);
}

/// The Ableton Live set holds each keyswitch note in its clip, beside the notes it changes.
#[test]
fn the_live_set_holds_keyswitches_in_its_clips() {
    let grid = keyswitched();
    let xml = llamatron_exporters::live::live_set(&grid, llamatron_exporters::live::DEFAULT_TEMPLATE).expect("the set writes");
    let text = String::from_utf8(xml).expect("the set is text");
    let set = llamatron_exporters::xml::parse(&text).expect("the set reads back");
    let mut found = Vec::new();
    set.each(&mut found);
    let keys: Vec<i64> = found
        .iter()
        .filter(|element| element.tag == "MidiKey")
        .filter_map(|element| element.get("Value")?.parse().ok())
        .collect();
    assert!(keys.contains(&SUSTAIN_NOTE) && keys.contains(&STACCATO_NOTE), "{keys:?}");
}
