// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron, the tracker in Rust: `llamatron [set.yml]` opens a set's file, or a new set where none is named.

use std::process::ExitCode;

/// Run the tracker on the set named, saying why where it cannot start.
fn main() -> ExitCode {
    let path = std::env::args().nth(1).map(std::path::PathBuf::from);
    match llamatron_tracker::terminal::run(path.as_deref()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("llamatron: {error}");
            ExitCode::FAILURE
        }
    }
}
