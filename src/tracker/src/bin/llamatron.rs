// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron: `llamatron [set.yml]` opens a set's file in the tracker, or a new set where none is named, and
//! `llamatron set.yml --to KIND` writes its songs without opening the tracker, as the Export dialog writes them.

use llamatron_strings::{cli, named};
use llamatron_tracker::launch::Launch;
use std::path::PathBuf;
use std::process::ExitCode;

/// What the command line asks for: a set to open or read, and where it asks for one, the export to write of it.
struct Asked {
    set: Option<PathBuf>,
    kind: Option<String>,
    song: Option<String>,
    out: Option<PathBuf>,
    replace: bool,
    /// Export a set holding values that cannot be used, each changed to the nearest allowed value.
    force: bool,
    /// The Ableton Live set to build an export from, in place of the one the program comes with.
    template: Option<PathBuf>,
    /// What the tracker does by itself once it opens.
    launch: Launch,
    /// List this computer's MIDI output ports, or the visualizer modes, one a line, and do nothing else: the recorder asks.
    lists_ports: bool,
    lists_visualizers: bool,
}

/// The options that only mean something when opening the tracker, and those only when exporting.
const LAUNCH_OPTIONS: [&str; 7] = [
    "--autoplay",
    "--autoplay-quit-when-finished",
    "--visualizer",
    "--details",
    "--max-seconds",
    "--launch-for-recording",
    "--interactive",
];
const EXPORT_OPTIONS: [&str; 5] = ["--song", "--out", "--replace", "--force", "--template"];
const OPTION_SEPARATOR: &str = ", ";

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
    if asked.lists_ports {
        for port in llamatron_tracker::realtime::backend::device_port_names() {
            println!("{port}");
        }
        return ExitCode::SUCCESS;
    }
    if asked.lists_visualizers {
        for mode in llamatron_tracker::visualizers::ported_modes() {
            println!("{mode}\t{}", llamatron_tracker::settings::mode_name(mode));
        }
        return ExitCode::SUCCESS;
    }
    let done = match &asked.kind {
        Some(kind) => export(&asked, kind),
        None => llamatron_tracker::terminal::run(asked.set.as_deref(), asked.launch.clone()),
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
        force: false,
        template: None,
        launch: Launch::default(),
        lists_ports: false,
        lists_visualizers: false,
    };
    let mut given: Vec<String> = Vec::new();
    let mut words = arguments.into_iter().peekable();
    while let Some(word) = words.next() {
        let value_after = |words: &mut std::iter::Peekable<std::vec::IntoIter<String>>| words.next_if(|next| !next.starts_with("--"));
        match word.as_str() {
            "--to" => asked.kind = Some(value_after(&mut words).unwrap_or_else(|| default_kind.to_string())),
            "--song" => asked.song = value_after(&mut words),
            "--out" => asked.out = value_after(&mut words).map(PathBuf::from),
            "--replace" => asked.replace = true,
            "--force" => asked.force = true,
            "--template" => asked.template = value_after(&mut words).map(PathBuf::from),
            "--autoplay" => asked.launch.autoplay = true,
            "--autoplay-quit-when-finished" => asked.launch.quit_when_finished = true,
            "--details" => asked.launch.details = true,
            "--launch-for-recording" => asked.launch.for_recording = true,
            "--list-midi-ports" => asked.lists_ports = true,
            "--list-visualizers" => asked.lists_visualizers = true,
            "--interactive" => {
                asked.launch.for_recording = true;
                asked.launch.interactive = true;
            }
            "--visualizer" => asked.launch.visualizer = Some(visualizer_named(value_after(&mut words))?),
            "--max-seconds" => asked.launch.max_seconds = Some(seconds_named(value_after(&mut words))?),
            option if option.starts_with("--") => {
                return Err(named(cli::ERR_CLI_UNKNOWN_OPTION, &[("option", option.into())]));
            }
            _ => {
                asked.set = Some(PathBuf::from(word));
                continue;
            }
        }
        given.push(word);
    }
    refuse_mixed(&asked, &given)?;
    Ok(asked)
}

/// Refuse launch options with --to, export options without it, and launch options with no set to play.
fn refuse_mixed(asked: &Asked, given: &[String]) -> Result<(), String> {
    let named_of = |options: &[&str]| -> String {
        let found: Vec<&str> = options.iter().copied().filter(|option| given.iter().any(|each| each == option)).collect();
        found.join(OPTION_SEPARATOR)
    };
    let launching = named_of(&LAUNCH_OPTIONS);
    let exporting = named_of(&EXPORT_OPTIONS);
    if asked.kind.is_some() && !launching.is_empty() {
        return Err(named(cli::ERR_CLI_NOT_WITH_TO, &[("options", launching.as_str().into())]));
    }
    if asked.kind.is_none() && !exporting.is_empty() {
        return Err(named(cli::ERR_CLI_ONLY_WITH_TO, &[("options", exporting.as_str().into())]));
    }
    if asked.launch.opens_arrange() && asked.set.is_none() {
        return Err(cli::ERR_CLI_LAUNCH_NEEDS_SET.to_string());
    }
    Ok(())
}

/// The visualizer mode --visualizer names, one that is built.
fn visualizer_named(value: Option<String>) -> Result<String, String> {
    let modes = llamatron_tracker::visualizers::ported_modes();
    let value = value.unwrap_or_default();
    if modes.contains(&value.as_str()) {
        return Ok(value);
    }
    let words = [("mode", value.as_str().into()), ("modes", modes.join(OPTION_SEPARATOR).as_str().into())];
    Err(named(cli::ERR_CLI_UNKNOWN_VISUALIZER, &words))
}

/// The seconds --max-seconds names.
fn seconds_named(value: Option<String>) -> Result<f64, String> {
    let value = value.unwrap_or_default();
    value
        .parse::<f64>()
        .ok()
        .filter(|seconds| seconds.is_finite() && *seconds >= 0.0)
        .ok_or_else(|| named(cli::ERR_CLI_NEEDS_SECONDS, &[("value", value.as_str().into())]))
}

/// The set a file holds for an export. A file holding values that cannot be used, each with an allowed value near it, is
/// read with those values in their place, each listed; without --force that is all, and the export is refused, saying to
/// pass it. The file is never changed.
fn corrected_for_export(path: &std::path::Path, force: bool) -> Result<llamatron_tracker::document::Document, String> {
    let opened = llamatron_tracker::document::Document::open_corrected(path)?;
    let (document, corrections) = (opened.document, opened.corrections);
    let line = if force { cli::MSG_CLI_CHANGED } else { cli::MSG_CLI_WOULD_CHANGE };
    for correction in &corrections {
        eprintln!("{}", named(line, &[("change", correction.described().as_str().into())]));
    }
    if !force && !corrections.is_empty() {
        let shown = path.display().to_string();
        return Err(named(llamatron_strings::errors::ERR_NEEDS_FORCE, &[("path", shown.as_str().into())]));
    }
    Ok(document)
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
    let mut document = corrected_for_export(path, asked.force)?;
    let template = match &asked.template {
        Some(template) => Some(std::fs::read(template).map_err(|problem| format!("{}: {problem}", template.display()))?),
        None => None,
    };
    let songs: Vec<String> = document.get_setlist().song_names().into_iter().map(str::to_string).collect();
    // A song is named without regard to case, as every name is.
    let chosen: Vec<String> = match &asked.song {
        Some(name) => match songs.iter().find(|song| song.to_lowercase() == name.to_lowercase()) {
            Some(song) => vec![song.clone()],
            None => {
                let shown = path.display().to_string();
                return Err(named(cli::ERR_CLI_NO_SONG, &[("name", name.as_str().into()), ("path", shown.as_str().into())]));
            }
        },
        None => songs,
    };
    let directory = match &asked.out {
        Some(out) => out.clone(),
        None => document.export_directory().unwrap_or_default(),
    };
    // A folder named with --out is made when it doesn't exist yet, as a person naming one expects.
    std::fs::create_dir_all(&directory).map_err(|problem| format!("{}: {problem}", directory.display()))?;
    for song in chosen {
        document.select_song(&song);
        if !asked.replace && llamatron_tracker::exporting::has_earlier_export(&document, kind, &directory) {
            let earlier = directory.join(document.export_name()).display().to_string();
            return Err(named(llamatron_strings::errors::ERR_FILE_EXISTS, &[("path", earlier.as_str().into())]));
        }
        let written = llamatron_tracker::exporting::export_song(&document, kind, &directory, template.as_deref())?;
        let shown = written.display().to_string();
        let words = [("target", kind.into()), ("song", song.as_str().into()), ("path", shown.as_str().into())];
        println!("{}", named(cli::MSG_CLI_WROTE, &words));
    }
    Ok(())
}
