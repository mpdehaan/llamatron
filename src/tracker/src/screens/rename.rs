// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Renaming a named thing of the set (the Python shared/page.py's ask_name and shows_named_item.py's rename): a prompt for a
//! new name, which cannot be empty or another thing's, the rename followed through every reference by name and by every
//! open page that shows the thing.

use crate::app::App;
use crate::screens::dialogs::{Answer, PromptDialog};
use llamatron_model::objects::naming::is_taken;
use llamatron_model::schema::generated::limits::MAX_NAME_LENGTH;
use llamatron_strings::{errors, named};

/// What stores a new name once it is accepted.
pub type StoreName = Box<dyn Fn(&mut App, &str)>;

/// Ask for a new name for a thing of the current song that is no section's, a scene or a clip: a prompt titled by a
/// template taking the old name, refusing an empty name or one the taken names hold, and storing the new one.
pub fn ask_song_name(app: &mut App, prompt: &str, name: &str, most: usize, taken: Vec<String>, store: StoreName) {
    let old = name.to_string();
    let title = named(prompt, &[("name", name.into())]);
    let mut dialog = PromptDialog::new(&title, name);
    dialog.max_length = Some(most);
    let dialog = dialog.then(Box::new(move |app: &mut App, answer: &Answer| {
        let Answer::Typed(typed) = answer else { return };
        let text = typed.trim();
        if text.is_empty() {
            app.refuse(errors::ERR_EMPTY_NAME);
        } else if text != old && is_taken(text, &taken) {
            app.refuse(&named(errors::ERR_NAME_IN_USE, &[("name", text.into())]));
        } else if text != old {
            store(app, text);
        }
    }));
    app.show_page(Box::new(dialog));
}

/// Ask for a new name for a thing of a section, titled by a prompt template that takes the old name.
pub fn ask_rename(app: &mut App, section: &'static str, name: &str, prompt: &str) {
    let old = name.to_string();
    let taken: Vec<String> = app.document.names_taken(section).into_iter().filter(|each| *each != old).collect();
    let title = named(prompt, &[("name", name.into())]);
    let mut dialog = PromptDialog::new(&title, name);
    dialog.max_length = Some(MAX_NAME_LENGTH as usize);
    let dialog = dialog.then(Box::new(move |app: &mut App, answer: &Answer| {
        let Answer::Typed(typed) = answer else { return };
        let text = typed.trim();
        if text.is_empty() {
            app.refuse(errors::ERR_EMPTY_NAME);
        } else if text != old && is_taken(text, &taken) {
            app.refuse(&named(errors::ERR_NAME_IN_USE, &[("name", text.into())]));
        } else if text != old {
            match app.document.rename_named(section, &old, text) {
                Ok(()) => app.renamed(section, &old, text),
                Err(problem) => app.refuse(&problem),
            }
        }
    }));
    app.show_page(Box::new(dialog));
}
