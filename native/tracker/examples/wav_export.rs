// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Export a set's current song as a WAV file, as Ctrl+X's WAV does: `cargo run --release --example wav_export SET OUT.wav`.

use std::process::ExitCode;

/// Write the WAV file of the set's first song, saying why where it cannot.
fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().collect();
    let (Some(set), Some(out)) = (arguments.get(1), arguments.get(2)) else {
        eprintln!("usage: wav_export SET OUT.wav");
        return ExitCode::FAILURE;
    };
    let exported = llamatron_tracker::document::Document::open(std::path::Path::new(set))
        .and_then(|document| document.rendered().map(|grid| (document, grid)))
        .and_then(|(document, grid)| llamatron_tracker::wav::export(&document, &grid, std::path::Path::new(out)));
    match exported {
        Ok(()) => ExitCode::SUCCESS,
        Err(problem) => {
            eprintln!("{problem}");
            ExitCode::FAILURE
        }
    }
}
