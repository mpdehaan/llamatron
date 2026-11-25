// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The screen tour (internal_tools/compare_screens.py's ScreenTour) played again: the keys the Python tour pressed between
//! its stops pressed into the tracker, and the screen at each stop recorded as Textual composes it, every line's pieces of
//! text with the style each is drawn in, so that the two programs' screens compare.

use crate::app::Tracker;
use crate::keys::pressed_key;
use crate::style::Style;

/// One stop: the page on top, and every line of the screen as pieces of text, each with its style as Rich writes it.
pub struct Stop {
    pub page: String,
    pub screen: Vec<Vec<(String, String)>>,
}

/// The screen as Textual composes a page's lines: each piece over the screen's own style, the room after a line's text in
/// the background alone.
pub fn composed(tracker: &Tracker, width: usize, height: usize) -> Vec<Vec<(String, String)>> {
    let base = Style::parse("default on default");
    let room = Style::parse("on default");
    let mut lines = Vec::new();
    for line in tracker.screen(width, height).into_iter().take(height) {
        let mut pieces = Vec::new();
        for segment in line.segments() {
            pieces.push((segment.text, base.and(&segment.style).written()));
        }
        let used = line.cell_len();
        if used < width {
            pieces.push((" ".repeat(width - used), room.written()));
        }
        lines.push(pieces);
    }
    while lines.len() < height {
        lines.push(vec![(" ".repeat(width), room.written())]);
    }
    lines
}

/// One stop of the Python's tour: the pages open there, from the main screen up, and the keys pressed since the stop before.
pub struct TourStop {
    pub stack: Vec<String>,
    /// The file the Python wrote its set to where the set changed by this stop, whether it then held unsaved changes, and
    /// its current song.
    pub set: Option<std::path::PathBuf>,
    pub dirty: bool,
    pub song: String,
    /// Each key pressed, with the pages open as the Python pressed it.
    pub keys: Vec<(String, Vec<String>)>,
}

/// Press each stop's keys and record the screen after them, then follow the Python's stack of pages where pages not ported
/// yet made the two part, so that the pages after them compare.
pub fn tour(tracker: &mut Tracker, width: usize, height: usize, stops: &[TourStop]) -> Vec<Stop> {
    // The tests that made the tour count FluidSynth as installed.
    tracker.app.fluidsynth_installed = true;
    let mut recorded = Vec::new();
    for stop in stops {
        let mut unported = false;
        for (key, stack) in &stop.keys {
            // A page not ported yet takes no keys: where the Python's pages went from it, the Rust follows them.
            if !tracker.top().is_ported() {
                unported = true;
                tracker.follow(stack);
            }
            tracker.press(&pressed_key(key));
        }
        // The screen is drawn first, since drawing a page may find a part of it not ported yet, which names it.
        let screen = composed(tracker, width, height);
        recorded.push(Stop {
            page: tracker.top().name().to_string(),
            screen,
        });
        tracker.follow(&stop.stack);
        // A page not ported yet that changed the set leaves the Rust's behind, so it takes up the Python's, and the pages after
        // it compare.
        if let (true, Some(file)) = (unported, &stop.set) {
            tracker.app.document.take_up(file, stop.dirty, &stop.song);
        }
    }
    recorded
}
