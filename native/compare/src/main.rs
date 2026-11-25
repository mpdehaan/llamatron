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
    let text = match std::fs::read_to_string(path) {
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
        other => {
            eprintln!("llamatron-compare: a command it does not know: {other}");
            ExitCode::from(2)
        }
    }
}
