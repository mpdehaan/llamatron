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
    /// The types of generator the Python's Generators page showed open before the stop's keys, which its set files do not
    /// keep.
    pub open_types: Vec<String>,
    /// Each key pressed, with the pages open as the Python pressed it.
    pub keys: Vec<TourKey>,
}

/// A key the Python pressed: its name, the pages and dialogs open as it pressed it, and, where the key before changed the
/// set, the file it wrote the set to then, whether the set held unsaved changes and its current song.
pub struct TourKey {
    pub key: String,
    pub stack: Vec<String>,
    pub set: Option<(std::path::PathBuf, bool, String)>,
}

/// Press each stop's keys and record the screen after them, then follow the Python's stack of pages where pages not ported
/// yet made the two part, so that the pages after them compare.
pub fn tour(tracker: &mut Tracker, width: usize, height: usize, stops: &[TourStop]) -> Result<Vec<Stop>, String> {
    // The tests that made the tour count FluidSynth as installed.
    tracker.app.fluidsynth_installed = true;
    // A tour never makes a sound or opens a MIDI port, whatever its keys launch.
    crate::realtime::backend::SENDING_ALLOWED.store(false, std::sync::atomic::Ordering::SeqCst);
    let mut recorded = Vec::new();
    // The Python opened types on its Generators page before the stops compared begin, and pages not ported yet may open or
    // close them, so the Rust takes the Python's up at the start and after those.
    let mut take_up_open_types = true;
    for stop in stops {
        if take_up_open_types {
            tracker.app.document.set_open_generator_types(stop.open_types.clone());
        }
        let mut unported = false;
        let mut last_unported = false;
        for key in &stop.keys {
            // A key pressed on a page or dialog not ported yet that changed the set leaves the Rust's behind, so it takes
            // up the Python's.
            if let (true, Some((file, dirty, song))) = (last_unported, &key.set) {
                tracker.app.document.take_up(file, *dirty, song)?;
            }
            // A page not ported yet takes no keys: where the Python's pages went from it, or where the Python opened a page
            // or dialog the Rust has not ported, the Rust follows them.
            if !tracker.top().is_ported() || key.stack.len() > tracker.depth() {
                tracker.follow(&key.stack);
            }
            last_unported = !tracker.top().is_ported();
            unported |= last_unported;
            tracker.press(&pressed_key(&key.key));
            // The terminal draws after every key, and a page may keep its scrolling as it draws, such as Arrange's window
            // over the tracks, so the tour draws after every key too.
            composed(tracker, width, height);
        }
        // Where the Python opened a page or a dialog the Rust did not, the Rust follows it before drawing, so that the stop
        // counts as waiting on what is not ported yet rather than differing.
        if stop.stack.len() > tracker.depth() {
            tracker.follow(&stop.stack);
        }
        // The screen is drawn first, since drawing a page may find a part of it not ported yet, which names it.
        let screen = composed(tracker, width, height);
        if std::env::var("TOUR_STOP").ok().and_then(|stop| stop.parse::<usize>().ok()) == Some(recorded.len()) {
            eprintln!(
                "stop {}: dirty {}, differs from clean in {:?}",
                recorded.len(),
                tracker.app.document.is_dirty(),
                tracker.app.document.differences_from_clean()
            );
        }
        recorded.push(Stop {
            page: tracker.top().name().to_string(),
            screen,
        });
        tracker.follow(&stop.stack);
        // A page not ported yet that changed the set leaves the Rust's behind, so it takes up the Python's, and the pages after
        // it compare.
        if let (true, Some(file)) = (unported, &stop.set) {
            tracker.app.document.take_up(file, stop.dirty, &stop.song)?;
        }
        take_up_open_types = unported;
    }
    Ok(recorded)
}

/// One place a walk of the program reached: the keys that reach it from the main screen, the page on top, its screen, and,
/// where a key there panicked, what the panic said.
pub struct Explored {
    pub keys: Vec<String>,
    pub page: String,
    /// What the cursor was on there, as the page says it.
    pub kind: String,
    /// The keys the page offered there, each the name its legend shows and what it does, where this place was the first of
    /// its kind; none for the places after.
    pub offered: Vec<(String, String)>,
    pub screen: Vec<Vec<(String, String)>>,
    pub panic: Option<String>,
}

/// The keys that work on every page, which a page's own table leaves to the tracker.
const EVERYWHERE_KEYS: [&str; 9] = ["ctrl+s", "ctrl+o", "ctrl+x", "ctrl+t", "ctrl+z", "ctrl+y", "f1", "f2", "f3"];
/// A binding of this many keys or fewer has each pressed, such as the four arrows; one of more, such as every letter a search
/// takes, has its first alone.
const KEYS_EACH_PRESSED: usize = 4;
/// How many places a walk reaches at most, so that a page that opens pages without end cannot hold it up.
const MOST_PLACES: usize = 100_000;

/// Walk the program from the main screen on a set's text: at each kind of place reached, every key the page offers there is
/// pressed, and the place after it recorded; each place is rebuilt from the set afresh by pressing the keys that reach it, so
/// that no place sees what another did. The places a step deeper are reached side by side, a thread for each core, each
/// with a copy of the set of its own. A key that panics is recorded, not followed.
pub fn explore(set: &std::path::Path, folder: &std::path::Path, width: usize, height: usize) -> Result<Vec<Explored>, String> {
    let text = std::fs::read_to_string(set).map_err(|problem| format!("{}: {problem}", set.display()))?;
    let name = set.file_name().unwrap_or_default().to_os_string();
    crate::realtime::backend::SENDING_ALLOWED.store(false, std::sync::atomic::Ordering::SeqCst);
    let threads = std::thread::available_parallelism().map_or(1, |count| count.get());
    let mut seen: std::collections::HashSet<Vec<String>> = std::collections::HashSet::new();
    let mut level: Vec<Vec<String>> = vec![Vec::new()];
    let mut explored = Vec::new();
    while !level.is_empty() && explored.len() < MOST_PLACES {
        let chunk = level.len().div_ceil(threads);
        let reached: Vec<(Vec<String>, Reached)> = std::thread::scope(|scope| {
            let workers: Vec<_> = level
                .chunks(chunk)
                .enumerate()
                .map(|(place, paths)| {
                    let copy = folder.join(format!("walker_{place}")).join(&name);
                    let text = &text;
                    scope.spawn(move || {
                        let _ = std::fs::create_dir_all(copy.parent().unwrap_or(std::path::Path::new(".")));
                        paths
                            .iter()
                            .map(|path| (path.clone(), reach(text, &copy, path, width, height)))
                            .collect::<Vec<_>>()
                    })
                })
                .collect();
            workers.into_iter().flat_map(|worker| worker.join().unwrap_or_default()).collect()
        });
        let mut next = Vec::new();
        for (path, place) in reached {
            match place {
                Reached::Place {
                    page,
                    screen,
                    kind,
                    offered,
                    shown,
                } => {
                    let shown = if seen.contains(&kind) { Vec::new() } else { shown };
                    explored.push(Explored {
                        keys: path.clone(),
                        page,
                        kind: kind[1].clone(),
                        offered: shown,
                        screen,
                        panic: None,
                    });
                    if seen.insert(kind) {
                        for key in offered {
                            let mut deeper = path.clone();
                            deeper.push(key);
                            next.push(deeper);
                        }
                    }
                }
                Reached::Refused(problem) => return Err(problem),
                Reached::Panicked(said) => explored.push(Explored {
                    keys: path,
                    page: String::new(),
                    kind: String::new(),
                    offered: Vec::new(),
                    screen: Vec::new(),
                    panic: Some(said),
                }),
            }
        }
        level = next;
    }
    Ok(explored)
}

/// What pressing a place's keys from the main screen came to: the place, with its page, screen, kind and the keys it offers;
/// the set refused; or a panic, with what it said.
enum Reached {
    Place {
        page: String,
        screen: Vec<Vec<(String, String)>>,
        kind: Vec<String>,
        offered: Vec<String>,
        shown: Vec<(String, String)>,
    },
    Refused(String),
    Panicked(String),
}

/// Rebuild a place: the set written afresh to its copy, opened, and the keys pressed from the main screen.
fn reach(text: &str, copy: &std::path::Path, path: &[String], width: usize, height: usize) -> Reached {
    let reached = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| -> Result<Reached, String> {
        std::fs::write(copy, text).map_err(|problem| problem.to_string())?;
        let document = crate::document::Document::open(copy)?;
        let mut tracker = crate::app::Tracker::new(document);
        tracker.app.fluidsynth_installed = true;
        // The terminal draws after every key, and a page may settle its cursor as it draws, so the walk draws too.
        for key in path {
            tracker.press(key);
            composed(&tracker, width, height);
        }
        let screen = composed(&tracker, width, height);
        let offered = if tracker.app.quitting { Vec::new() } else { keys_to_press(&tracker) };
        // A kind of place is its top page or dialog and what the cursor is on there: each has its keys tried once, wherever
        // it was opened from.
        let kind = vec![tracker.top().name().to_string(), tracker.top().place_kind(&tracker.app)];
        let mut shown: Vec<(String, String)> = Vec::new();
        for item in tracker.offered_keys() {
            let key = (item.label.clone(), item.what.clone());
            if !shown.contains(&key) {
                shown.push(key);
            }
        }
        Ok(Reached::Place {
            page: tracker.top().name().to_string(),
            screen,
            kind,
            offered,
            shown,
        })
    }));
    match reached {
        Ok(Ok(place)) => place,
        Ok(Err(problem)) => Reached::Refused(problem),
        Err(panic) => Reached::Panicked(
            panic
                .downcast_ref::<String>()
                .cloned()
                .or_else(|| panic.downcast_ref::<&str>().map(|text| text.to_string()))
                .unwrap_or_default(),
        ),
    }
}

/// The keys to try where the tracker is now: each key of each binding the top page offers, or the first of a binding of many,
/// and on a page, not a dialog, the keys that work everywhere.
fn keys_to_press(tracker: &crate::app::Tracker) -> Vec<String> {
    let mut keys: Vec<String> = Vec::new();
    for item in tracker.offered_keys() {
        let pressed: Vec<&str> = if item.keys.len() <= KEYS_EACH_PRESSED {
            item.keys.clone()
        } else {
            item.keys.iter().take(1).copied().collect()
        };
        for key in pressed {
            if !keys.iter().any(|known| known == key) {
                keys.push(key.to_string());
            }
        }
    }
    if !tracker.top().is_dialog() {
        for key in EVERYWHERE_KEYS {
            if !keys.iter().any(|known| known == key) {
                keys.push(key.to_string());
            }
        }
    }
    keys
}
