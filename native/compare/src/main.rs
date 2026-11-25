// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron-compare: what llamatron2 makes of a set, printed in a form the Python program prints the same way, so that
//! internal_tools/compare_llamatron2.py holds each layer of the port to the Python as it lands.
//!
//! `llamatron-compare load SET` prints the set file's data as JSON, as Python's json.dumps writes what PyYAML loaded;
//! `llamatron-compare layout SET` writes that data back as a set file, as the Python writer lays it out;
//! `llamatron-compare migrate SET` moves the data to today's layout, into the objects' layout and back, and writes it;
//! `llamatron-compare save SET` reads the set into objects and saves it, as the Python program saves a set.

use llamatron_model::file::data::{json_text, load, Data};
use std::process::ExitCode;

/// Data as Python's json.dumps writes it, with its default separators, keys in their order, every key made text.
fn json(data: &Data) -> String {
    match data {
        Data::Null => "null".into(),
        Data::Bool(flag) => if *flag { "true" } else { "false" }.into(),
        Data::Whole(whole) => whole.to_string(),
        Data::Float(float) if float.is_nan() => "NaN".into(),
        Data::Float(float) if float.is_infinite() => if *float > 0.0 { "Infinity" } else { "-Infinity" }.into(),
        Data::Float(float) => llamatron_math::number::python_float_text(*float),
        Data::Text(text) => json_text(text),
        Data::List(items) => format!("[{}]", items.iter().map(json).collect::<Vec<_>>().join(", ")),
        Data::Map(pairs) => format!(
            "{{{}}}",
            pairs
                .iter()
                .map(|(key, value)| format!("{}: {}", json_key(key), json(value)))
                .collect::<Vec<_>>()
                .join(", ")
        ),
    }
}

/// A mapping's key as json.dumps writes one: text as it is, a number or flag as its text.
fn json_key(key: &Data) -> String {
    match key {
        Data::Text(text) => json_text(text),
        Data::Null => "\"null\"".into(),
        Data::Bool(flag) => format!("\"{}\"", if *flag { "true" } else { "false" }),
        Data::Whole(whole) => format!("\"{whole}\""),
        Data::Float(float) => format!("\"{}\"", llamatron_math::number::python_float_text(*float)),
        other => json(other),
    }
}

fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    let (Some(command), Some(path)) = (arguments.first(), arguments.get(1)) else {
        eprintln!("usage: llamatron-compare load SET");
        return ExitCode::from(2);
    };
    // A MIDI file is read as bytes by the step that imports it.
    let read = if path.ends_with(".mid") {
        Ok(String::new())
    } else {
        std::fs::read_to_string(path)
    };
    let text = match read {
        Ok(text) => text,
        Err(problem) => {
            eprintln!("{path}: {problem}");
            return ExitCode::from(1);
        }
    };
    match command.as_str() {
        "load" => match load(&text) {
            Ok(data) => {
                println!("{}", json(&data));
                ExitCode::SUCCESS
            }
            Err(problem) => {
                eprintln!("{path}: {}", problem.0);
                ExitCode::from(1)
            }
        },
        "layout" => match load(&text) {
            Ok(data) => {
                print!("{}", llamatron_model::file::writing::dump_file_layout(&data));
                ExitCode::SUCCESS
            }
            Err(problem) => {
                eprintln!("{path}: {}", problem.0);
                ExitCode::from(1)
            }
        },
        "migrate" => match load(&text) {
            Ok(data) => {
                let stem = std::path::Path::new(path).file_stem().map(|stem| stem.to_string_lossy().to_string());
                let (moved, _) = llamatron_model::file::migrations::migrated(data, stem);
                match llamatron_model::file::layout::as_object_layout(&moved) {
                    Ok(objects) => {
                        let file = llamatron_model::file::layout::as_file_layout(&objects);
                        print!("{}", llamatron_model::file::writing::dump_file_layout(&file));
                        ExitCode::SUCCESS
                    }
                    Err(problem) => {
                        eprintln!("{path}: {}: {}", problem.section, problem.problem.message);
                        ExitCode::from(1)
                    }
                }
            }
            Err(problem) => {
                eprintln!("{path}: {}", problem.0);
                ExitCode::from(1)
            }
        },
        "save" => {
            let stem = std::path::Path::new(path).file_stem().map(|stem| stem.to_string_lossy().to_string());
            match llamatron_model::objects::setlist::Setlist::read_text(&text, stem) {
                Ok(setlist) => {
                    let file = llamatron_model::file::layout::as_file_layout(&setlist.to_data());
                    print!("{}", llamatron_model::file::writing::dump_file_layout(&file));
                    ExitCode::SUCCESS
                }
                Err(problem) => {
                    eprintln!("{path}: {}", problem.message);
                    ExitCode::from(1)
                }
            }
        }
        "import" => match imported(path, &text) {
            Ok(json) => {
                println!("{json}");
                ExitCode::SUCCESS
            }
            Err(problem) => {
                eprintln!("{path}: {problem}");
                ExitCode::from(1)
            }
        },
        "live" | "midi" => {
            let stem = std::path::Path::new(path)
                .file_stem()
                .map(|stem| stem.to_string_lossy().to_string())
                .unwrap_or_default();
            let setlist = match llamatron_model::objects::setlist::Setlist::read_text(&text, Some(stem.clone())) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    eprintln!("{path}: {}", problem.message);
                    return ExitCode::from(1);
                }
            };
            let exported = if command == "live" {
                exported_live(&setlist)
            } else {
                exported_midi(&setlist, &stem)
            };
            match exported {
                Ok(text) => {
                    println!("{text}");
                    ExitCode::SUCCESS
                }
                Err(llamatron_engine::error::RenderError::NotPorted(what)) => {
                    eprintln!("not ported yet: {what}");
                    ExitCode::from(NOT_PORTED)
                }
                Err(llamatron_engine::error::RenderError::Refused(problem)) => {
                    eprintln!("{path}: {problem}");
                    ExitCode::from(1)
                }
            }
        }
        "render" => {
            let stem = std::path::Path::new(path).file_stem().map(|stem| stem.to_string_lossy().to_string());
            let setlist = match llamatron_model::objects::setlist::Setlist::read_text(&text, stem) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    eprintln!("{path}: {}", problem.message);
                    return ExitCode::from(1);
                }
            };
            match rendered_songs(&setlist) {
                Ok(text) => {
                    println!("{text}");
                    ExitCode::SUCCESS
                }
                Err(llamatron_engine::error::RenderError::NotPorted(what)) => {
                    eprintln!("not ported yet: {what}");
                    ExitCode::from(NOT_PORTED)
                }
                Err(llamatron_engine::error::RenderError::Refused(problem)) => {
                    eprintln!("{path}: {problem}");
                    ExitCode::from(1)
                }
            }
        }
        "screens" => {
            let (Some(keys), Some(width), Some(height)) = (arguments.get(2), arguments.get(3), arguments.get(4)) else {
                eprintln!("usage: llamatron-compare screens SET KEYS WIDTH HEIGHT");
                return ExitCode::from(2);
            };
            match toured(path, keys, width.parse().unwrap_or(80), height.parse().unwrap_or(24)) {
                Ok(text) => {
                    println!("{text}");
                    ExitCode::SUCCESS
                }
                Err(problem) => {
                    eprintln!("{path}: {problem}");
                    ExitCode::from(1)
                }
            }
        }
        other => {
            eprintln!("llamatron-compare: a command it does not know: {other}");
            ExitCode::from(2)
        }
    }
}

/// What the tool exits with for a set using a part of the program not ported yet, which the harness counts apart.
const NOT_PORTED: u8 = 3;
/// The seed every comparison renders from, the harness's RENDER_SEED.
const RENDER_SEED: i64 = 1;

/// Every song of a set rendered from one seed, as the harness's rendered_text writes it: each scene, then each clip's length
/// and its notes, each start, end, MIDI number and velocity.
fn rendered_songs(setlist: &llamatron_model::objects::setlist::Setlist) -> llamatron_engine::error::Rendered<String> {
    let mut texts = Vec::new();
    for name in setlist.song_names() {
        let Some(song) = setlist.get_song(name) else { continue };
        texts.push(format!("song {name}"));
        let grid = llamatron_engine::realizer::SongRealizer::new(setlist, song, Some(RENDER_SEED)).render()?;
        let mut lines = Vec::new();
        for (place, row) in grid.rows.iter().enumerate() {
            let tempo = row.tempo.map(llamatron_math::number::python_float_text).unwrap_or("None".to_string());
            lines.push(format!("scene {place} tempo {tempo}"));
            for (time, tempo) in &row.tempo_changes {
                lines.push(format!("  tempo {time} {}", llamatron_math::number::python_float_text(*tempo)));
            }
            for track in &grid.tracks {
                let Some((_, clip)) = row.clips.iter().find(|(found, _)| found == track) else {
                    continue;
                };
                let (notes, length) = llamatron_engine::timing::timed_events(clip, clip.scale.as_ref())?;
                lines.push(format!("  {track} length {length}"));
                for note in notes {
                    lines.push(format!("    {} {} {} {}", note.start, note.end, note.midi_number, note.velocity));
                }
                for control in &clip.controls {
                    let slide = if control.slide { "True" } else { "False" };
                    lines.push(format!("    cc {} {} {} {slide}", control.time, control.number, control.value));
                }
            }
        }
        texts.push(lines.join("\n"));
    }
    Ok(texts.join("\n"))
}

/// Every MIDI file each song of a set exports from one seed, one line a file with its name and its SHA-512.
fn exported_midi(setlist: &llamatron_model::objects::setlist::Setlist, stem: &str) -> llamatron_engine::error::Rendered<String> {
    use llamatron_exporters::midi;
    let mut lines = Vec::new();
    for name in setlist.song_names() {
        let Some(song) = setlist.get_song(name) else { continue };
        let grid = llamatron_engine::realizer::SongRealizer::new(setlist, song, Some(RENDER_SEED)).render()?;
        let base = format!("{stem}_{name}");
        let mut files = midi::clip_tree(&grid, &base)?;
        files.push(midi::song_file(&grid, &base, false)?);
        files.extend(midi::stems(&grid, &base)?);
        files.push(midi::song_file(&grid, &base, true)?);
        for (filename, bytes) in files {
            let digest: String = llamatron_math::sha512::sha512(&bytes).iter().map(|byte| format!("{byte:02x}")).collect();
            lines.push(format!("{filename} {digest}"));
        }
    }
    Ok(lines.join("\n"))
}

/// Each song of a set as a Live set from one seed, the SHA-512 of its XML before it is zipped, or that it is refused.
fn exported_live(setlist: &llamatron_model::objects::setlist::Setlist) -> llamatron_engine::error::Rendered<String> {
    let mut lines = Vec::new();
    for name in setlist.song_names() {
        let Some(song) = setlist.get_song(name) else { continue };
        let grid = llamatron_engine::realizer::SongRealizer::new(setlist, song, Some(RENDER_SEED)).render()?;
        match llamatron_exporters::live::live_set(&grid, llamatron_exporters::live::DEFAULT_TEMPLATE) {
            Ok(xml) => {
                let digest: String = llamatron_math::sha512::sha512(&xml).iter().map(|byte| format!("{byte:02x}")).collect();
                lines.push(format!("{name} {digest}"));
            }
            Err(llamatron_engine::error::RenderError::Refused(_)) => lines.push(format!("{name} refused")),
            Err(other) => return Err(other),
        }
    }
    Ok(lines.join("\n"))
}

/// A new set, as the Python's Setlist.new() makes one.
const NEW_SET: &str = "step_size: 1/16\ndefault_octave: 5\ndefault_drum_octave: 3\noctave_labels: live\n\nscales:\n  - { name: scale-1, root: C, type: major }\n\npatterns:\n  - name: pattern-1\n    steps: 16\n    group: track-1\n    degree: [1, ~, ~, ~, 1, ~, ~, ~, 1, ~, ~, ~, 1, ~, ~, ~]\n\nsongs:\n  - name: untitled\n    tempo: 120\n    scale: scale-1\n\n    tracks:\n      - { name: track-1 }\n\n    scenes:\n      - name: scene-1\n        clips:\n          - { track: track-1, pattern: pattern-1 }\n";

/// Data as JSON, which the harness reads back as YAML.
fn json_written(data: &Data, out: &mut String) {
    match data {
        Data::Null => out.push_str("null"),
        Data::Bool(value) => out.push_str(if *value { "true" } else { "false" }),
        Data::Whole(value) => out.push_str(&value.to_string()),
        Data::Float(value) => out.push_str(&llamatron_math::number::python_float_text(*value)),
        Data::Text(text) => {
            out.push('"');
            for character in text.chars() {
                match character {
                    '"' => out.push_str("\\\""),
                    '\\' => out.push_str("\\\\"),
                    '\n' => out.push_str("\\n"),
                    character if (character as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", character as u32)),
                    character => out.push(character),
                }
            }
            out.push('"');
        }
        Data::List(items) => {
            out.push('[');
            for (place, item) in items.iter().enumerate() {
                if place > 0 {
                    out.push_str(", ");
                }
                json_written(item, out);
            }
            out.push(']');
        }
        Data::Map(pairs) => {
            out.push('{');
            for (place, (key, value)) in pairs.iter().enumerate() {
                if place > 0 {
                    out.push_str(", ");
                }
                json_written(&Data::text(&key.python_str()), out);
                out.push_str(": ");
                json_written(value, out);
            }
            out.push('}');
        }
    }
}

/// What importing each MIDI file a path stands for into a new set makes, as JSON: the file itself, or each song of a set
/// as its whole-song MIDI export.
fn imported(path: &str, text: &str) -> Result<String, String> {
    let file = std::path::Path::new(path);
    let stem = file.file_stem().map(|stem| stem.to_string_lossy().to_string()).unwrap_or_default();
    let mut inputs: Vec<(String, Vec<u8>)> = Vec::new();
    if path.ends_with(".mid") {
        inputs.push((stem, std::fs::read(file).map_err(|problem| problem.to_string())?));
    } else {
        let setlist = llamatron_model::objects::setlist::Setlist::read_text(text, Some(stem.clone())).map_err(|problem| problem.message)?;
        for name in setlist.song_names() {
            let Some(song) = setlist.get_song(name) else { continue };
            let grid = llamatron_engine::realizer::SongRealizer::new(&setlist, song, Some(RENDER_SEED))
                .render()
                .map_err(|problem| format!("{problem:?}"))?;
            let base = format!("{stem}_{name}");
            let (_, bytes) = llamatron_exporters::midi::song_file(&grid, &base, false).map_err(|problem| format!("{problem:?}"))?;
            inputs.push((base, bytes));
        }
    }
    let new_set = llamatron_model::objects::setlist::Setlist::read_text(NEW_SET, None).map_err(|problem| problem.message)?;
    let mut made = Vec::new();
    for (name, bytes) in inputs {
        let entry = match llamatron_importers::import::imported(&bytes, &new_set, &name) {
            Err(_) => Data::Map(vec![(Data::text("refused"), Data::text(&name))]),
            Ok(song) => Data::Map(vec![
                (Data::text("name"), Data::text(&song.name)),
                (Data::text("song"), song.song),
                (
                    Data::text("patterns"),
                    Data::Map(song.patterns.into_iter().map(|(name, data)| (Data::text(&name), data)).collect()),
                ),
                (
                    Data::text("scales"),
                    Data::Map(song.scales.into_iter().map(|(name, data)| (Data::text(&name), data)).collect()),
                ),
                (
                    Data::text("instruments"),
                    Data::Map(song.instruments.into_iter().map(|(name, data)| (Data::text(&name), data)).collect()),
                ),
            ]),
        };
        made.push(entry);
    }
    let mut out = String::new();
    json_written(&Data::List(made), &mut out);
    Ok(out)
}

fn folder_of(path: &str) -> std::path::PathBuf {
    std::path::Path::new(path).parent().map(std::path::Path::to_path_buf).unwrap_or_default()
}

/// The screen tour played on a set: the keys file holds a line for each stop, its keys between tabs; the answer is every
/// stop's page and screen as JSON, the set's folder written as FOLDER, as the Python capture writes it.
fn toured(path: &str, keys: &str, width: usize, height: usize) -> Result<String, String> {
    let document = llamatron_tracker::document::Document::open(std::path::Path::new(path))?;
    let text = std::fs::read_to_string(keys).map_err(|problem| problem.to_string())?;
    let stops: Vec<llamatron_tracker::tour::TourStop> = text
        .lines()
        .map(|line| {
            let mut parts = line.split('\t');
            let stack = parts
                .next()
                .unwrap_or("")
                .split(',')
                .filter(|name| !name.is_empty())
                .map(str::to_string)
                .collect();
            let set = parts.next().filter(|name| !name.is_empty()).map(|name| folder_of(path).join(name));
            let dirty = parts.next() == Some("True");
            let song = parts.next().unwrap_or("").to_string();
            let keys = parts
                .filter(|key| !key.is_empty())
                .map(|key| {
                    let (name, stack) = key.split_once('\x1f').unwrap_or((key, ""));
                    (name.to_string(), stack.split(',').filter(|page| !page.is_empty()).map(str::to_string).collect())
                })
                .collect();
            llamatron_tracker::tour::TourStop { stack, set, dirty, song, keys }
        })
        .collect();
    let mut tracker = llamatron_tracker::app::Tracker::new(document);
    let folder = std::path::Path::new(path)
        .parent()
        .map(|parent| parent.to_string_lossy().to_string())
        .unwrap_or_default();
    let mut out = String::from("[");
    for (number, stop) in llamatron_tracker::tour::tour(&mut tracker, width, height, &stops).into_iter().enumerate() {
        if number > 0 {
            out.push(',');
        }
        out.push_str("{\"page\":");
        json_written(&Data::Text(stop.page), &mut out);
        out.push_str(",\"screen\":[");
        for (line_number, line) in stop.screen.iter().enumerate() {
            if line_number > 0 {
                out.push(',');
            }
            out.push('[');
            for (piece_number, (text, style)) in line.iter().enumerate() {
                if piece_number > 0 {
                    out.push(',');
                }
                out.push('[');
                let shown = if folder.is_empty() { text.clone() } else { text.replace(&folder, "FOLDER") };
                json_written(&Data::Text(shown), &mut out);
                out.push(',');
                json_written(&Data::Text(style.clone()), &mut out);
                out.push(']');
            }
            out.push(']');
        }
        out.push_str("]}");
    }
    out.push(']');
    Ok(out)
}
