// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron: `llamatron [set.yml]` opens a set's file in the tracker, or a new set where none is named, and
//! `llamatron set.yml --to KIND` writes its songs without opening the tracker, as the Export dialog writes them.

use llamatron_strings::{cli, named};
use std::path::PathBuf;
use std::process::ExitCode;

/// What the command line asks for: a set to open or read, and where it asks for one, the export to write of it.
struct Asked {
    set: Option<PathBuf>,
    kind: Option<String>,
    song: Option<String>,
    out: Option<PathBuf>,
    replace: bool,
}

/// Open the tracker on the set named, or write the exports asked for, saying why where neither can be done.
fn main() -> ExitCode {
    let asked = match asked(std::env::args().skip(1).collect()) {
        Ok(asked) => asked,
        Err(problem) => {
            eprintln!("llamatron: {problem}");
            eprintln!("{}", cli::MSG_CLI_USAGE);
            return ExitCode::FAILURE;
        }
    };
    let done = match &asked.kind {
        Some(kind) => export(&asked, kind),
        None => llamatron_tracker::terminal::run(asked.set.as_deref()),
    };
    match done {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("llamatron: {error}");
            ExitCode::FAILURE
        }
    }
}

/// The command line read: a set's path, then any of --to, --song, --out and --replace.
fn asked(arguments: Vec<String>) -> Result<Asked, String> {
    // --to without a kind writes the Ableton Live set, its default, as it did.
    let default_kind = llamatron_tracker::exporting::EXPORT_KINDS[0];
    let mut asked = Asked {
        set: None,
        kind: None,
        song: None,
        out: None,
        replace: false,
    };
    let mut words = arguments.into_iter().peekable();
    while let Some(word) = words.next() {
        let value_after = |words: &mut std::iter::Peekable<std::vec::IntoIter<String>>| words.next_if(|next| !next.starts_with("--"));
        match word.as_str() {
            "--to" => asked.kind = Some(value_after(&mut words).unwrap_or_else(|| default_kind.to_string())),
            "--song" => asked.song = value_after(&mut words),
            "--out" => asked.out = value_after(&mut words).map(PathBuf::from),
            "--replace" => asked.replace = true,
            option if option.starts_with("--") => {
                return Err(named(cli::ERR_CLI_UNKNOWN_OPTION, &[("option", option.into())]));
            }
            _ => asked.set = Some(PathBuf::from(word)),
        }
    }
    Ok(asked)
}

/// Write the songs of the set asked for, or the one song named, as a kind of export, each beside the set or in the
/// directory asked for, saying where each went; an earlier export is replaced only when asked to.
fn export(asked: &Asked, kind: &str) -> Result<(), String> {
    let kinds = llamatron_tracker::exporting::EXPORT_KINDS;
    if !kinds.contains(&kind) {
        return Err(named(
            cli::ERR_CLI_UNKNOWN_KIND,
            &[("kind", kind.into()), ("kinds", kinds.join(", ").as_str().into())],
        ));
    }
    let path = asked.set.as_ref().ok_or_else(|| cli::ERR_CLI_NEEDS_A_SET.to_string())?;
    let mut document = llamatron_tracker::document::Document::open(path)?;
    let songs: Vec<String> = document.get_setlist().song_names().into_iter().map(str::to_string).collect();
    let chosen: Vec<String> = match &asked.song {
        Some(name) if songs.contains(name) => vec![name.clone()],
        Some(name) => {
            let shown = path.display().to_string();
            return Err(named(cli::ERR_CLI_NO_SONG, &[("name", name.as_str().into()), ("path", shown.as_str().into())]));
        }
        None => songs,
    };
    let directory = match &asked.out {
        Some(out) => out.clone(),
        None => document.export_directory().unwrap_or_default(),
    };
    for song in chosen {
        document.select_song(&song);
        if !asked.replace && llamatron_tracker::exporting::has_earlier_export(&document, kind, &directory) {
            let earlier = directory.join(document.export_name()).display().to_string();
            return Err(named(llamatron_strings::errors::ERR_FILE_EXISTS, &[("path", earlier.as_str().into())]));
        }
        let written = llamatron_tracker::exporting::export_song(&document, kind, &directory)?;
        let shown = written.display().to_string();
        let words = [("target", kind.into()), ("song", song.as_str().into()), ("path", shown.as_str().into())];
        println!("{}", named(cli::MSG_CLI_WROTE, &words));
    }
    Ok(())
}
