// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Arrange's edits of the current song (the Python arrange_page.py's): adding, inserting, copying and deleting scenes and
//! tracks, and adding, pasting and deleting clips, a blank pattern made for an empty cell.

use super::{ArrangePage, FIRST_TRACK_COLUMN, HEADER_ROW, SCENE_COLUMN};
use crate::app::App;
use crate::keybindings::ArrangePage as Keys;
use crate::keys::KeyItem;
use crate::page::Page;
use crate::screens::dialogs::{Answer, ChoiceDialog, ConfirmDialog, MessageDialog};
use crate::settings::sorted_names;
use llamatron_model::file::data::Data;
use llamatron_model::objects::naming::new_name;
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, Section};
use llamatron_model::schema::generated::limits::{MAX_SCALE_LENGTH, MIN_SCALE_LENGTH};
use llamatron_strings::{errors, labels, messages, named, names};

/// How many steps a new pattern has where a bar of the song is not whole steps.
const NEW_PATTERN_STEPS: i64 = 16;
/// Where the picker of a clip's pattern offers a new blank pattern.
const NEW_PATTERN_PLACE: usize = 0;
/// What the picker of how a copy's patterns go answers: sharing them, or copies of them.
const OWN_PATTERNS: usize = 1;

/// Where Arrange's cursor goes once a dialog has answered: a scene's place, or the row of track names, and a column.
pub fn cursor_row(row: i64, column: usize) -> String {
    format!("{row}:{column}")
}

impl ArrangePage {
    /// Do what a key that edits the song does, and say whether the key was one.
    pub(super) fn press_edit(&mut self, app: &mut App, item: &KeyItem) -> bool {
        if item.is(&Keys::ADD_SCENE) || item.is(&Keys::ADD_SCENE_HERE) {
            self.add_scene(app);
        } else if item.is(&Keys::INSERT_SCENE) {
            let index = self.row.get().max(0) as usize;
            let name = Self::new_scene_name(app);
            Self::edited(app, |document| document.add_scene(index, &name));
        } else if item.is(&Keys::COPY_SCENE) {
            self.copy_scene(app);
        } else if item.is(&Keys::DELETE_SCENE) {
            self.delete_scene(app);
        } else if item.is(&Keys::ADD_TRACK) || item.is(&Keys::ADD_TRACK_HERE) {
            // On a + column, a track of that column's kind; on a track, one of that track's kind, at the end of its group.
            let drum = self
                .plus_here(app)
                .unwrap_or_else(|| self.cursor_track(app).is_some_and(|track| Self::is_drum_track(app, &track)));
            let name = Self::new_track_name(app);
            if Self::edited(app, |document| document.add_track(&name, None, drum)) {
                self.row.set(HEADER_ROW);
                if let Some(place) = Self::place_of(app, &name) {
                    self.column.set(place + FIRST_TRACK_COLUMN);
                }
            }
        } else if item.is(&Keys::INSERT_TRACK) {
            // A track of the cursor's track's kind, just before it.
            let Some(track) = self.cursor_track(app) else { return true };
            let drum = Self::is_drum_track(app, &track);
            let place = app.document.song().tracks().iter().position(|(name, _)| *name == track);
            let name = Self::new_track_name(app);
            Self::edited(app, |document| document.add_track(&name, place, drum));
        } else if item.is(&Keys::COPY_TRACK) {
            self.copy_track(app);
        } else if item.is(&Keys::DELETE_TRACK) {
            self.delete_track(app);
        } else if item.is(&Keys::ADD_CLIP) {
            self.add_clip(app);
        } else if item.is(&Keys::BLANK_PATTERN) {
            let Some(track) = self.cursor_track(app) else { return true };
            let row = self.row.get().max(0) as usize;
            let crumbs = self.crumbs(app);
            blank_pattern(app, row, &track, crumbs);
        } else if item.is(&Keys::PASTE) {
            self.paste_clip(app);
        } else if item.is(&Keys::DELETE_CLIP) {
            self.delete_clip(app);
        } else if item.is(&Keys::FRACTURE) {
            let dialog = ConfirmDialog::new(messages::MSG_FRACTURE_TITLE, Vec::new(), false, false).then(Box::new(|app: &mut App, _: &Answer| {
                match app.document.fracture() {
                    Ok(copies) if copies.is_empty() => app.say(messages::MSG_NOTHING_TO_FRACTURE),
                    Ok(copies) => app.say(&named(messages::MSG_FRACTURED, &[("count", copies.len().into())])),
                    Err(problem) => app.refuse(&problem),
                }
            }));
            app.show_page(Box::new(dialog));
        } else {
            return false;
        }
        true
    }

    /// Put the cursor where a dialog's answer said, as cursor_row wrote it.
    pub(super) fn put_cursor_at(&self, row: &str) {
        let Some((scene, column)) = row.split_once(':') else { return };
        if let (Ok(scene), Ok(column)) = (scene.parse(), column.parse()) {
            self.row.set(scene);
            self.column.set(column);
        }
    }

    /// Make an edit of the set, refusing with why where it could not be made, and say whether it was made.
    fn edited(app: &mut App, edit: impl FnOnce(&mut crate::document::Document) -> Result<(), String>) -> bool {
        match edit(&mut app.document) {
            Ok(()) => true,
            Err(problem) => {
                app.refuse(&problem);
                false
            }
        }
    }

    /// The name for a new scene: the scene word and one more than the highest number in use.
    fn new_scene_name(app: &App) -> String {
        let taken: Vec<String> = app
            .document
            .song()
            .scenes()
            .iter()
            .filter_map(|scene| scene.get_written("name").and_then(Data::as_str).map(str::to_string))
            .collect();
        new_name(names::MSG_NEW_SCENE_WORD, &taken)
    }

    /// The name for a new track, numbered as a new scene is, which its settings page renames.
    fn new_track_name(app: &App) -> String {
        new_name(names::MSG_NEW_TRACK_WORD, &Self::tracks(app))
    }

    /// Add a scene after the cursor's, or at the end from the + row, and move onto its name.
    fn add_scene(&mut self, app: &mut App) {
        let index = if self.on_plus_row(app) {
            Self::scene_count(app) as usize
        } else {
            (self.row.get() + 1).max(0) as usize
        };
        let name = Self::new_scene_name(app);
        if Self::edited(app, |document| document.add_scene(index, &name)) {
            self.row.set(index as i64);
            self.column.set(SCENE_COLUMN);
        }
    }

    /// Ask whether a copy of the cursor's scene shares its patterns or gets copies of them, then put the copy right below
    /// it and move onto it.
    fn copy_scene(&self, app: &mut App) {
        let row = self.row.get().max(0) as usize;
        let name = super::scene_name(&app.document.song().scenes()[row], row);
        let title = named(messages::MSG_COPY_SCENE_TITLE, &[("name", name.as_str().into())]);
        let column = self.column.get();
        ask_how_patterns_copy(
            app,
            &title,
            Box::new(move |app: &mut App, own: bool| {
                if !ArrangePage::edited(app, |document| document.copy_scene(row)) {
                    return;
                }
                if own {
                    let tracks: Vec<(usize, String)> = app.document.song().scenes()[row + 1]
                        .clip_slots()
                        .iter()
                        .map(|(track, _)| (row + 1, track.clone()))
                        .collect();
                    ArrangePage::edited(app, |document| document.give_own_patterns(&tracks));
                }
                app.cursor_to(&cursor_row(row as i64 + 1, column));
            }),
        );
    }

    /// Delete the cursor's scene after asking, never the song's last.
    fn delete_scene(&self, app: &mut App) {
        if Self::scene_count(app) <= 1 {
            let lines = vec![errors::ERR_LAST_SCENE_SHOWN.to_string()];
            app.show_page(Box::new(MessageDialog::new(errors::ERR_CANT_DELETE_TITLE, lines)));
            return;
        }
        let row = self.row.get().max(0) as usize;
        let scene = &app.document.song().scenes()[row];
        let count = scene.clip_slots().len();
        let question = named(messages::MSG_DELETE_SCENE_QUESTION, &[("name", super::scene_name(scene, row).as_str().into())]);
        let mut lines = Vec::new();
        if count > 0 {
            lines.push(named(messages::MSG_ALSO_DELETES_CLIPS, &[("count", count.into())]));
        }
        confirm_delete(
            app,
            &question,
            lines,
            Box::new(move |app: &mut App| ArrangePage::edited(app, |document| document.remove_scene(row))),
        );
    }

    /// Ask whether a copy of the cursor's track shares its patterns or gets copies of them, then put the copy to its right
    /// with its clips and move onto it.
    fn copy_track(&self, app: &mut App) {
        let Some(name) = self.cursor_track(app) else { return };
        let title = named(messages::MSG_COPY_TRACK_TITLE, &[("name", name.as_str().into())]);
        let (row, column) = (self.row.get(), self.column.get());
        ask_how_patterns_copy(
            app,
            &title,
            Box::new(move |app: &mut App, own: bool| {
                let copy = match app.document.copy_named(Section::TRACKS, &name) {
                    Ok(copy) => copy,
                    Err(problem) => return app.refuse(&problem),
                };
                if own {
                    let clips: Vec<(usize, String)> = app
                        .document
                        .song()
                        .scenes()
                        .iter()
                        .enumerate()
                        .filter(|(_, scene)| scene.get_clip_slot(&copy).is_some())
                        .map(|(index, _)| (index, copy.clone()))
                        .collect();
                    ArrangePage::edited(app, |document| document.give_own_patterns(&clips));
                }
                app.cursor_to(&cursor_row(row, column + 1));
            }),
        );
    }

    /// Delete the cursor's track after asking, saying how many clips go with it and how many clips grabbing from it stop,
    /// never the song's last.
    fn delete_track(&self, app: &mut App) {
        let tracks = Self::tracks(app);
        if tracks.len() <= 1 {
            let lines = vec![errors::ERR_LAST_TRACK_SHOWN.to_string()];
            app.show_page(Box::new(MessageDialog::new(errors::ERR_CANT_DELETE_TITLE, lines)));
            return;
        }
        let Some(name) = self.cursor_track(app) else { return };
        let song = app.document.song();
        let clips = song.scenes().iter().filter(|scene| scene.get_clip_slot(&name).is_some()).count();
        let grabbing = song
            .scenes()
            .iter()
            .flat_map(|scene| scene.clip_slots())
            .filter(|(_, clip)| clip.get_written(ClipSlotSetting::GRAB_TRACK).and_then(Data::as_str) == Some(name.as_str()))
            .count();
        let question = named(messages::MSG_DELETE_TRACK_QUESTION, &[("name", name.as_str().into())]);
        let mut lines = Vec::new();
        if clips > 0 {
            lines.push(named(messages::MSG_ALSO_DELETES_CLIPS, &[("count", clips.into())]));
        }
        if grabbing > 0 {
            lines.push(named(messages::MSG_GRABBERS_STOP, &[("count", grabbing.into())]));
        }
        confirm_delete(
            app,
            &question,
            lines,
            Box::new(move |app: &mut App| ArrangePage::edited(app, |document| document.delete_named(Section::TRACKS, &name))),
        );
    }

    /// Ask what the empty cell's clip plays: a new blank pattern first, or one of the set's patterns.
    fn add_clip(&self, app: &mut App) {
        let row = self.row.get().max(0) as usize;
        let Some(track) = self.cursor_track(app) else { return };
        // A clip holds only a pattern of its track's kind.
        let drum = Self::is_drum_track(app, &track);
        let patterns = sorted_names(
            &app.document
                .get_setlist()
                .items(Section::PATTERNS)
                .iter()
                .filter(|(_, item)| matches!(item, llamatron_model::objects::setlist::Item::Pattern(pattern) if pattern.is_drum() == drum))
                .map(|(name, _)| name.clone())
                .collect::<Vec<_>>(),
        );
        let mut options = vec![messages::MSG_NEW_PATTERN_CHOICE.to_string()];
        options.extend(patterns.iter().cloned());
        let crumbs = self.crumbs(app);
        let mut dialog = ChoiceDialog::new(messages::MSG_PATTERN_FOR_CLIP_TITLE, options, NEW_PATTERN_PLACE);
        dialog.then = Some(Box::new(move |app: &mut App, answer: &Answer| {
            let Answer::Chosen(place) = answer else { return };
            if *place == NEW_PATTERN_PLACE {
                blank_pattern(app, row, &track, crumbs.clone());
                return;
            }
            let clip = llamatron_model::objects::edits::new_clip(&patterns[place - 1]);
            ArrangePage::edited(app, |document| document.put_clip(row, &track, &clip));
        }));
        app.show_page(Box::new(dialog));
    }

    /// Put the clip copied with C on the cursor's cell; one that would grab from its own track or round in a circle keeps
    /// its own notes, and says so.
    fn paste_clip(&self, app: &mut App) {
        let Some(copied) = &self.copied else { return };
        let row = self.row.get().max(0) as usize;
        let Some(track) = self.cursor_track(app) else { return };
        let copied_drum = app.document.get_setlist().get_item(Section::PATTERNS, &copied.get_pattern_name());
        let fits = match copied_drum {
            Some(llamatron_model::objects::setlist::Item::Pattern(pattern)) => pattern.is_drum() == Self::is_drum_track(app, &track),
            _ => true,
        };
        if !fits {
            app.refuse(messages::MSG_PASTE_CLIP_AMONG_ITS_KIND);
            return;
        }
        let mut clip = copied.clone();
        let grab = clip.get_written(ClipSlotSetting::GRAB_TRACK).and_then(Data::as_str).map(str::to_string);
        let dropped = grab.filter(|other| *other == track || Self::grab_circles(app, row, &track, other));
        if dropped.is_some() {
            clip.set_written(ClipSlotSetting::GRAB_TRACK, None);
        }
        if Self::edited(app, |document| document.put_clip(row, &track, &clip.to_data())) {
            if let Some(other) = dropped {
                app.say(&named(messages::MSG_PASTED_WITHOUT_GRAB, &[("track", other.as_str().into())]));
            }
        }
    }

    /// Delete the cursor's clip after asking.
    fn delete_clip(&self, app: &mut App) {
        let row = self.row.get().max(0) as usize;
        let Some(track) = self.cursor_track(app) else { return };
        let question = named(messages::MSG_DELETE_CLIP_QUESTION, &[("track", track.as_str().into())]);
        confirm_delete(
            app,
            &question,
            Vec::new(),
            Box::new(move |app: &mut App| ArrangePage::edited(app, |document| document.remove_clip(row, &track))),
        );
    }
}

/// What takes whether a copy gets copies of its patterns.
type PatternsChosen = dyn Fn(&mut App, bool);

/// Ask whether a copy shares the patterns its clips play or gets copies of them, and hand on whether it gets copies.
fn ask_how_patterns_copy(app: &mut App, title: &str, then: Box<PatternsChosen>) {
    let options = labels::MSG_COPY_PATTERNS_CHOICES.iter().map(|choice| choice.to_string()).collect();
    let mut dialog = ChoiceDialog::new(title, options, 0);
    dialog.then = Some(Box::new(move |app: &mut App, answer: &Answer| {
        if let Answer::Chosen(place) = answer {
            then(app, *place == OWN_PATTERNS);
        }
    }));
    app.show_page(Box::new(dialog));
}

/// Ask whether to delete something, the question as the title in red and what else goes with it under it, and delete it on
/// YES alone.
fn confirm_delete(app: &mut App, question: &str, lines: Vec<String>, then: Box<dyn Fn(&mut App) -> bool>) {
    let dialog = ConfirmDialog::new(question, lines, false, true).then(Box::new(move |app: &mut App, _: &Answer| {
        then(app);
    }));
    app.show_page(Box::new(dialog));
}

/// Make a blank pattern named after a track, a drum pattern on a drum track, put a clip of it in a scene's empty cell, and
/// open it in the pattern editor with Arrange's crumbs before its own.
fn blank_pattern(app: &mut App, row: usize, track: &str, crumbs: Vec<String>) {
    let name = app.document.new_name(Section::PATTERNS, track);
    let song = app.document.song();
    let drum = song.get_track(track).is_some_and(|held| held.is_drum());
    let bar = song.get_time_signature().bar_length() / app.document.get_setlist().get_step_size();
    let steps = if bar.denominator() == 1 { bar.numerator() as i64 } else { NEW_PATTERN_STEPS };
    if !ArrangePage::edited(app, |document| document.add_blank_pattern(&name, steps, Some(track), drum, None)) {
        return;
    }
    if !ArrangePage::edited(app, |document| document.put_clip(row, track, &llamatron_model::objects::edits::new_clip(&name))) {
        return;
    }
    if !drum {
        // The pattern is written for a scale as large as the one its clip plays under.
        let setlist = app.document.get_setlist();
        let length = crate::patterns::pattern_scale(setlist, app.document.song(), &name)
            .map(|scale| crate::patterns::scale_half_steps(setlist, &scale).len() as i64)
            .filter(|size| (MIN_SCALE_LENGTH..=MAX_SCALE_LENGTH).contains(size));
        if let Some(length) = length {
            let pattern = name.clone();
            app.document.change_set(|setlist| {
                if let Some(llamatron_model::objects::setlist::Item::Pattern(held)) = setlist.get_item_mut(Section::PATTERNS, &pattern) {
                    held.set_written("scale_length", Some(Data::Whole(length as i128)));
                }
            });
        }
    }
    app.show_page(crate::screens::pattern::open_clip_pattern(&name, crumbs, track));
}
