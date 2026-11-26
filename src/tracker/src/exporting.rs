// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Exporting the current song (the Python everywhere.py's export and the document's): Ctrl+X asks which kind, and the
//! export is written beside the set's file, named <set>_<song> plus what the file is, replacing an earlier one of its kind.
//! A set with no file is saved first; a scene in which every clip loops blocks every export, since it would never end.

use crate::app::App;
use crate::screens::dialogs::{Answer, ConfirmDialog, ExportDialog, MessageDialog, EXPORT_CHOICES};
use crate::uses::scene_label;
use llamatron_strings::{errors, messages, named, names};
use std::path::{Path, PathBuf};

/// The kinds of export, as their files name them.
const ABLETON: &str = "ableton";
const STEMS: &str = "stems";
const MIDI_FILE: &str = "midi";
const CLIP_TREE: &str = "cliptree";
const GENERAL_MIDI: &str = "gm";
const WAV: &str = "wav";
/// How many never-ending scenes the loop errors dialog lists, the rest counted.
const LOOP_ERRORS_SHOWN: usize = 10;
/// The row that holds a step's statement that stops its clip.
const STOP_ROW: &str = "stop_c1";

/// Ask which kind of export to write for the current song, and write it; a set with no file is saved first.
pub fn export(app: &mut App) {
    let lines = loop_error_lines(app);
    if !lines.is_empty() {
        app.show_page(Box::new(MessageDialog::new(errors::ERR_LOOP_SCENES_TITLE, lines)));
        return;
    }
    if app.document.get_path().is_none() {
        let lines = vec![messages::MSG_SAVE_BEFORE_EXPORT.to_string()];
        let mut asked = Some(());
        let question = ConfirmDialog::new(messages::MSG_SAVE_BEFORE_EXPORT_TITLE, lines, false, false).then(Box::new(move |app: &mut App, _: &Answer| {
            if asked.take().is_some() {
                crate::everywhere::save_as(app, Some(Box::new(choose_export)));
            }
        }));
        app.show_page(Box::new(question));
        return;
    }
    choose_export(app);
}

/// Ask which kind of export to write, and write it.
fn choose_export(app: &mut App) {
    let title = named(messages::MSG_EXPORT_TITLE, &[("name", app.document.get_current_song_name().into())]);
    let dialog = ExportDialog::new(
        &title,
        Box::new(|app: &mut App, answer: &Answer| {
            if let Answer::Chosen(place) = answer {
                export_chosen(app, EXPORT_CHOICES[*place]);
            }
        }),
    );
    app.show_page(Box::new(dialog));
}

/// Write the kind of export chosen; the WAV export says first which tracks are in it.
fn export_chosen(app: &mut App, kind: &'static str) {
    if kind != WAV {
        export_as(app, kind);
    } else if !crate::wav::fluidsynth_installed() {
        let lines = vec![errors::ERR_WAV_NEEDS_FLUIDSYNTH.to_string()];
        app.show_page(Box::new(MessageDialog::new(errors::ERR_CANT_EXPORT_TITLE, lines)));
    } else {
        let lines = vec![messages::MSG_WAV_EXPORT_NOTE.to_string()];
        let question =
            ConfirmDialog::new(messages::MSG_WAV_EXPORT_TITLE, lines, false, false).then(Box::new(move |app: &mut App, _: &Answer| export_as(app, kind)));
        app.show_page(Box::new(question));
    }
}

/// Write a kind of export, asking first the first time this session a Live set would be written over, since work done in
/// Live may be in it.
fn export_as(app: &mut App, kind: &'static str) {
    let Some(directory) = app.document.export_directory() else { return };
    let name = app.document.export_name();
    let path = shown_path(kind, &directory, &name);
    let earlier = !earlier_files(kind, &directory, &name).is_empty();
    if kind == ABLETON && earlier && !app.session.confirmed_overwrites.contains(&path) {
        let shown = path.display().to_string();
        let lines = vec![
            named(messages::MSG_REPLACE_EXPORT_QUESTION, &[("path", shown.as_str().into())]),
            messages::MSG_EXPORT_REPLACES_LIVE_WORK.to_string(),
        ];
        let question = ConfirmDialog::new(messages::MSG_REPLACE_EXPORT_TITLE, lines, false, false).then(Box::new(move |app: &mut App, _: &Answer| {
            app.session.confirmed_overwrites.push(path.clone());
            write_export(app, kind);
        }));
        app.show_page(Box::new(question));
        return;
    }
    write_export(app, kind);
}

/// Write the export, saying where it went, or in a dialog why it could not be written.
fn write_export(app: &mut App, kind: &'static str) {
    match exported(app, kind) {
        Ok(path) => {
            let words = [("name", label_of(kind).into()), ("path", path.display().to_string().as_str().into())];
            app.say(&named(messages::MSG_EXPORTED, &words));
        }
        Err(problem) => app.show_page(Box::new(MessageDialog::new(errors::ERR_CANT_EXPORT_TITLE, vec![problem]))),
    }
}

/// Export the current song beside the set's file, replacing an earlier export of its kind, and return where it went.
fn exported(app: &App, kind: &str) -> Result<PathBuf, String> {
    let document = &app.document;
    let directory = document.export_directory().ok_or_else(|| errors::ERR_SAVE_BEFORE_EXPORT.to_string())?;
    let song = document.song();
    if song.get_track_names().is_empty() || song.scenes().is_empty() {
        return Err(errors::ERR_NOTHING_TO_EXPORT.to_string());
    }
    let grid = document.rendered()?;
    let name = document.export_name();
    for earlier in earlier_files(kind, &directory, &name) {
        std::fs::remove_file(&earlier).map_err(|error| format!("{}: {error}", earlier.display()))?;
    }
    let refused = |error: llamatron_engine::error::RenderError| match error {
        llamatron_engine::error::RenderError::Refused(problem) => problem,
        llamatron_engine::error::RenderError::NotPorted(what) => format!("not ported yet: {what}"),
    };
    let files: Vec<(String, Vec<u8>)> = match kind {
        ABLETON => {
            let xml = llamatron_exporters::live::live_set(&grid, llamatron_exporters::live::DEFAULT_TEMPLATE).map_err(refused)?;
            vec![(format!("{name}.als"), llamatron_exporters::live::zipped(&xml))]
        }
        STEMS => llamatron_exporters::midi::stems(&grid, &name).map_err(refused)?,
        MIDI_FILE => vec![llamatron_exporters::midi::song_file(&grid, &name, false).map_err(refused)?],
        CLIP_TREE => llamatron_exporters::midi::clip_tree(&grid, &name).map_err(refused)?,
        GENERAL_MIDI => vec![llamatron_exporters::midi::song_file(&grid, &name, true).map_err(refused)?],
        _ => {
            crate::wav::export(document, &grid, &directory.join(format!("{name}.wav")))?;
            Vec::new()
        }
    };
    for (file, bytes) in files {
        let path = directory.join(file);
        std::fs::write(&path, bytes).map_err(|error| format!("{}: {error}", path.display()))?;
    }
    Ok(shown_path(kind, &directory, &name))
}

/// Where a kind of export goes, as people are shown it: the file, or the files' pattern for the kinds that write several.
fn shown_path(kind: &str, directory: &Path, name: &str) -> PathBuf {
    let file = match kind {
        ABLETON => format!("{name}.als"),
        STEMS => format!("{name}_stem_*.mid"),
        CLIP_TREE => format!("{name}_clip_*.mid"),
        GENERAL_MIDI => format!("{name}_gm.mid"),
        WAV => format!("{name}.wav"),
        _ => format!("{name}.mid"),
    };
    normalized(&directory.join(file))
}

/// A path without its ./ parts, as Python's normpath writes one.
fn normalized(path: &Path) -> PathBuf {
    path.components().filter(|part| !matches!(part, std::path::Component::CurDir)).collect()
}

/// The files an earlier export of a kind left in a directory, and nothing else that is there: the stems' and the clips'
/// files numbered as each export numbers them, so that one never takes the other's.
fn earlier_files(kind: &str, directory: &Path, name: &str) -> Vec<PathBuf> {
    let numbered = |prefix: String, digits: usize| -> Vec<PathBuf> {
        let mut found: Vec<PathBuf> = std::fs::read_dir(directory)
            .map(|entries| {
                entries
                    .filter_map(Result::ok)
                    .map(|entry| entry.file_name().to_string_lossy().to_string())
                    .filter(|file| {
                        let Some(rest) = file.strip_prefix(&prefix) else { return false };
                        rest.ends_with(".mid") && rest.chars().take(digits).filter(char::is_ascii_digit).count() == digits
                    })
                    .map(|file| directory.join(file))
                    .collect()
            })
            .unwrap_or_default();
        found.sort();
        found
    };
    match kind {
        STEMS => numbered(format!("{name}_stem_"), 3),
        CLIP_TREE => numbered(format!("{name}_clip_s_"), 1),
        _ => {
            let path = shown_path(kind, directory, name);
            if path.exists() {
                vec![path]
            } else {
                Vec::new()
            }
        }
    }
}

/// What people are shown for a kind of export.
fn label_of(kind: &str) -> &'static str {
    match kind {
        ABLETON => names::MSG_ABLETON_EXPORT_LABEL,
        STEMS => names::MSG_STEMS_EXPORT_LABEL,
        CLIP_TREE => names::MSG_CLIP_TREE_EXPORT_LABEL,
        GENERAL_MIDI => names::MSG_GENERAL_MIDI_EXPORT_LABEL,
        WAV => names::MSG_WAV_EXPORT_LABEL,
        _ => names::MSG_MIDI_FILE_EXPORT_LABEL,
    }
}

/// The lines of the loop errors dialog: each scene in which every clip loops and no step can stop its clip, so that the
/// scene would never end, or nothing when every scene can end.
pub fn loop_error_lines(app: &App) -> Vec<String> {
    let setlist = app.document.get_setlist();
    let song = app.document.song();
    let can_stop = |pattern: &str| {
        setlist
            .get_pattern(pattern)
            .and_then(|pattern| pattern.row(STOP_ROW))
            .is_some_and(|steps| steps.iter().any(|step| !step.is_null()))
    };
    let mut scenes = Vec::new();
    for (place, scene) in song.scenes().iter().enumerate() {
        if !scene.every_clip_loops() {
            continue;
        }
        let stops = scene.get_track_names().iter().any(|track| {
            scene
                .get_clip_slot(track)
                .is_some_and(|clip| clip.get_pattern_names().iter().any(|pattern| can_stop(pattern)))
        });
        if !stops {
            scenes.push(scene_label(place + 1, scene));
        }
    }
    if scenes.is_empty() {
        return scenes;
    }
    let mut lines = vec![errors::ERR_LOOP_SCENES_INTRO.to_string()];
    lines.extend(scenes.iter().take(LOOP_ERRORS_SHOWN).cloned());
    if scenes.len() > LOOP_ERRORS_SHOWN {
        lines.push(named(errors::ERR_AND_MORE, &[("count", (scenes.len() - LOOP_ERRORS_SHOWN).into())]));
    }
    lines
}
