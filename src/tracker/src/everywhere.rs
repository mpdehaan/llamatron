// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What the everywhere keys do (the Python screens/shared/everywhere.py): saving, saving as, opening a set and quitting, each
//! asking first where the set or its file says to.

use crate::app::App;
use crate::screens::dialogs::{Answer, ConfirmDialog, MessageDialog, PromptDialog, QuitDialog, SAVE_THEN_QUIT};
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_strings::{errors, messages, named};
use std::path::{Path, PathBuf};

/// Where Save as offers to save a set that has no file yet.
const DEFAULT_SAVE_FOLDER: &str = file_format::Section::SONGS;
const DEFAULT_SAVE_NAME: &str = "untitled.yml";
/// The ending a set's file is given where its name has none, and the endings a set's file may have.
const SET_SUFFIX: &str = ".yml";
const SET_SUFFIXES: [&str; 2] = [".yml", ".yaml"];

/// What runs once the set is saved, such as quitting.
pub type AfterSaving = Box<dyn FnOnce(&mut App)>;

/// Save the set where it came from, or ask where. A file that already holds the set is left alone, saying so; a file
/// something else changed is written over only after asking; a protected set's file is never written over, and saving
/// offers to save a copy under another name instead.
pub fn save(app: &mut App, then: Option<AfterSaving>) {
    let Some(path) = app.document.get_path().map(Path::to_path_buf) else {
        save_as(app, then);
        return;
    };
    let shown = path.display().to_string();
    if app.document.file_is_protected(None) {
        let lines = vec![
            named(messages::MSG_PROTECTED_EXPLAINED, &[(fill::PATH, shown.as_str().into())]),
            messages::MSG_PROTECTED_SAVE_COPY_QUESTION.to_string(),
        ];
        confirm(app, messages::MSG_PROTECTED_TITLE, lines, Box::new(move |app: &mut App| save_as(app, then)));
        return;
    }
    if app.document.file_holds_this_set() {
        app.say(&named(messages::MSG_FILE_UNCHANGED, &[(fill::PATH, shown.as_str().into())]));
        if let Some(then) = then {
            then(app);
        }
    } else if app.document.file_changed_elsewhere() {
        let lines = vec![named(messages::MSG_FILE_CHANGED_ELSEWHERE_QUESTION, &[(fill::PATH, shown.as_str().into())])];
        confirm(
            app,
            messages::MSG_FILE_CHANGED_ELSEWHERE_TITLE,
            lines,
            Box::new(move |app: &mut App| write(app, &path, then, false)),
        );
    } else {
        write(app, &path, then, false);
    }
}

/// Ask for a file to save the set as, adding .yml where the name has no ending, and asking before replacing another file.
pub fn save_as(app: &mut App, then: Option<AfterSaving>) {
    let default = app
        .document
        .get_path()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| Path::new(DEFAULT_SAVE_FOLDER).join(DEFAULT_SAVE_NAME));
    let mut then = Some(then);
    let prompt = PromptDialog::new(messages::MSG_SAVE_AS_PROMPT, &default.display().to_string()).then(Box::new(move |app: &mut App, answer: &Answer| {
        let Answer::Typed(typed) = answer else { return };
        if let Some(then) = then.take() {
            chosen(app, typed, then);
        }
    }));
    app.show_page(Box::new(prompt));
}

/// Save as the path typed, a path from the home folder, ~/songs/a.yml, meaning the home folder as it does in a terminal.
fn chosen(app: &mut App, typed: &str, then: Option<AfterSaving>) {
    let typed = typed.trim();
    if typed.is_empty() {
        return;
    }
    let mut path = expanded(typed);
    let lowered = path.to_lowercase();
    if !SET_SUFFIXES.iter().any(|suffix| lowered.ends_with(suffix)) {
        path.push_str(SET_SUFFIX);
    }
    let path = PathBuf::from(path);
    let shown = path.display().to_string();
    if app.document.file_is_protected(Some(&path)) {
        let lines = vec![
            named(messages::MSG_PROTECTED_EXPLAINED, &[(fill::PATH, shown.as_str().into())]),
            messages::MSG_PROTECTED_CHOOSE_ANOTHER_NAME.to_string(),
        ];
        app.show_page(Box::new(MessageDialog::new(messages::MSG_PROTECTED_TITLE, lines)));
    } else if Some(path.as_path()) != app.document.get_path() && path.exists() {
        let lines = vec![named(messages::MSG_REPLACE_FILE_QUESTION, &[(fill::PATH, shown.as_str().into())])];
        confirm(
            app,
            messages::MSG_REPLACE_FILE_TITLE,
            lines,
            Box::new(move |app: &mut App| write(app, &path, then, true)),
        );
    } else {
        write(app, &path, then, true);
    }
}

/// Write the set to a path, as the person's own copy where they chose the name, saying where it went or why it could not.
fn write(app: &mut App, path: &Path, then: Option<AfterSaving>, as_copy: bool) {
    let written = if as_copy { app.document.save_as(path) } else { app.document.save(path) };
    let shown = path.display().to_string();
    if let Err(error) = written {
        let lines = vec![named(
            errors::ERR_CANT_SAVE,
            &[(fill::PATH, shown.as_str().into()), (fill::ERROR, error.as_str().into())],
        )];
        app.show_page(Box::new(MessageDialog::new(errors::ERR_CANT_SAVE_TITLE, lines)));
        return;
    }
    app.say(&named(messages::MSG_SAVED, &[(fill::PATH, shown.as_str().into())]));
    if let Some(then) = then {
        then(app);
    }
}

/// Quit, or with unsaved changes offer to quit without saving, first since quitting is never an accident, or to save first.
pub fn quit_program(app: &mut App) {
    if !app.document.is_dirty() {
        app.quitting = true;
        return;
    }
    let question = QuitDialog::new(Box::new(|app: &mut App, answer: &Answer| {
        if *answer == Answer::Chosen(SAVE_THEN_QUIT) {
            save(app, Some(Box::new(|app: &mut App| app.quitting = true)));
        } else {
            app.quitting = true;
        }
    }));
    app.show_page(Box::new(question));
}

/// Ask a YES or NO question, running what is given on YES.
fn confirm(app: &mut App, title: &str, lines: Vec<String>, then: AfterSaving) {
    let mut then = Some(then);
    let question = ConfirmDialog::new(title, lines, false, false).then(Box::new(move |app: &mut App, _answer: &Answer| {
        if let Some(then) = then.take() {
            then(app);
        }
    }));
    app.show_page(Box::new(question));
}

/// A path typed with ~ for the home folder, as a terminal reads it.
fn expanded(typed: &str) -> String {
    match (typed.strip_prefix('~'), std::env::var("HOME")) {
        (Some(rest), Ok(home)) if rest.is_empty() || rest.starts_with('/') => format!("{home}{rest}"),
        _ => typed.to_string(),
    }
}
