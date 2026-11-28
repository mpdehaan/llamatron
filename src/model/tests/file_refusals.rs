// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What a set file refuses as it opens: each small set in `tests/data/refused/` holds one thing the file format does not
//! allow, and opening it fails with the message saying what.

use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::MIN_MORPH_REPEAT;
use llamatron_model::schema::generated::{limits, midi};

/// The step of tie_on_a_note.yml that both plays and ties, numbered from 1.
const TIED_STEP: i64 = 2;
use llamatron_strings::{errors, named};

/// Each refused set, and the message its refusal holds.
fn refusals() -> Vec<(&'static str, String)> {
    vec![
        (
            "morph_with_one_repeat.yml",
            named(errors::ERR_MORPH_TOO_FEW_REPEATS, &[("lowest", MIN_MORPH_REPEAT.into())]),
        ),
        ("morph_without_its_style.yml", errors::ERR_MORPH_NEEDS_BOTH.to_string()),
        (
            "degree_not_a_degree.yml",
            named(errors::ERR_NOT_DEGREE, &[("lowest", limits::MIN_DEGREE.into())]),
        ),
        (
            "velocity_out_of_range.yml",
            named(
                errors::ERR_NOT_IN_RANGE,
                &[("lowest", midi::MIN_VELOCITY.into()), ("highest", midi::MAX_VELOCITY.into())],
            ),
        ),
        ("chord_on_a_drum_pattern.yml", errors::ERR_CHORD_ON_DRUMS.to_string()),
        ("tie_on_a_note.yml", named(errors::ERR_TIE_ON_A_NOTE, &[("step", TIED_STEP.into())])),
        (
            "track_octaves_backwards.yml",
            named(errors::ERR_OCTAVE_RANGE_BACKWARDS, &[("lowest", 6.into()), ("highest", 3.into())]),
        ),
        (
            "chords_octaves_backwards.yml",
            named(errors::ERR_VOICE_LEADING_RANGE, &[("lowest", 7.into()), ("highest", 5.into())]),
        ),
        (
            "draw_slot_out_of_range.yml",
            named(
                errors::ERR_DRAW_SLOT_OUT_OF_RANGE,
                &[("lowest", 0.into()), ("highest", 11.into()), ("value", 12.into())],
            ),
        ),
        ("groove_named_as_a_factory_groove.yml", "(swing 54)".to_string()),
    ]
}

/// Every refused set fails to open, saying why.
#[test]
fn each_refused_set_says_why_it_does_not_open() {
    let folder = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/refused");
    for (file, message) in refusals() {
        let text = std::fs::read_to_string(folder.join(file)).expect("the refused set is there");
        match Setlist::read_text(&text) {
            Ok(_) => panic!("{file} opened"),
            Err(problem) => assert!(problem.message.contains(&message), "{file}: {}", problem.message),
        }
    }
}

/// A set refused only for values that have an allowed value near them opens corrected, each correction listed: a row's
/// steps brought within its limits at once, counted.
#[test]
fn a_set_with_values_out_of_range_opens_corrected() {
    let folder = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/refused");
    let text = std::fs::read_to_string(folder.join("velocity_out_of_range.yml")).expect("the set is there");
    let read = Setlist::read_text_corrected(&text).expect("the set opens corrected");
    let (setlist, corrections) = (read.setlist, read.corrections);
    let pattern = setlist.get_pattern("tune").expect("the pattern");
    let loudest = llamatron_model::file::data::Data::Whole(midi::MAX_VELOCITY as i128);
    assert_eq!(pattern.row("velocity").and_then(|steps| steps.first()), Some(&loudest));
    let changed_steps = 1;
    assert_eq!(corrections.len(), 1);
    assert_eq!(corrections[0].count, Some(changed_steps));
    let unfixable = std::fs::read_to_string(folder.join("degree_not_a_degree.yml")).expect("the set is there");
    assert!(Setlist::read_text_corrected(&unfixable).is_err());
}
