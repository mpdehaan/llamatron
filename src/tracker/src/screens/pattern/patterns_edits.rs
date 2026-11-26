// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Patterns page's edits (the Python screens/pattern/patterns_page.py's): A makes a pattern in the cursor's group,
//! asking its kind and its name, and opens it; N renames a pattern, C copies it, G moves it to another group or a new one
//! and Bksp deletes it once nothing uses it; on the row of tabs N renames the group, C copies all of it and Bksp takes
//! every pattern out of it; the + New tab makes a group, which shows with only its + (New) row until a pattern is made in
//! it. A dialog's answer puts the cursor through the cursor request, as a pattern's name or a group's + (New) row.

use super::{Listed, PatternTab, PatternsPage};
use crate::app::App;
use crate::keybindings::PatternsPage as Keys;
use crate::keys::KeyItem;
use crate::screens::dialogs::{Answer, ChoiceDialog, ConfirmDialog, PromptDialog};
use crate::screens::new_pattern_dialog::NewPatternDialog;
use llamatron_model::objects::naming::{copy_name, is_taken, new_name};
use llamatron_model::schema::generated::file_format::Section;
use llamatron_model::schema::generated::limits::MAX_NAME_LENGTH;
use llamatron_strings::{errors, labels, legends, messages, named, names};

/// How the cursor request names a pattern's row, and a group's + (New) row.
const PATTERN_ROW: &str = "pattern:";
const NEW_PATTERN_ROW: &str = "new:";
/// The key the page's chosen tab is kept under for the session.
const PAGE: &str = "PatternsPage";
/// How many steps a new pattern has where a bar of the song is not whole steps.
const NEW_PATTERN_STEPS: i64 = 16;

/// Choose the tab a pattern is in: its group's, or Ungrouped.
fn choose_tab_of(app: &mut App, name: &str) {
    let group = app
        .document
        .get_setlist()
        .get_pattern(name)
        .and_then(|pattern| pattern.get_written("group"))
        .and_then(|group| group.as_str())
        .map(str::to_string);
    let label = group.unwrap_or_else(|| labels::MSG_UNGROUPED.to_string());
    app.session.chosen_tabs.insert(PAGE.to_string(), label);
}

/// Choose a tab by the label it shows.
fn choose_tab(app: &mut App, label: &str) {
    app.session.chosen_tabs.insert(PAGE.to_string(), label.to_string());
}

/// Put the cursor on a pattern's row, choosing its group's tab.
fn cursor_on_pattern(app: &mut App, name: &str) {
    choose_tab_of(app, name);
    app.cursor_to(&format!("{PATTERN_ROW}{name}"));
}

/// Ask for a name no other thing of a list has, starting from a value, and hand it on.
fn ask_unused_name(app: &mut App, title: &str, value: &str, taken: Vec<String>, then: impl Fn(&mut App, &str) + 'static) {
    let mut dialog = PromptDialog::new(title, value);
    dialog.max_length = Some(MAX_NAME_LENGTH as usize);
    let dialog = dialog.then(Box::new(move |app: &mut App, answer: &Answer| {
        let Answer::Typed(text) = answer else { return };
        let text = text.trim();
        if text.is_empty() || is_taken(text, &taken) {
            app.refuse(errors::ERR_NAME_EMPTY_OR_IN_USE);
            return;
        }
        then(app, text);
    }));
    app.show_page(Box::new(dialog));
}

/// How many steps a new pattern has: one bar of the current song, or 16 where a bar is not whole steps.
fn new_pattern_steps(app: &App) -> i64 {
    let bar = app.document.song().get_time_signature().bar_length() / app.document.get_setlist().get_step_size();
    if bar.denominator() == 1 {
        bar.numerator() as i64
    } else {
        NEW_PATTERN_STEPS
    }
}

impl PatternsPage {
    /// The groups made on the page that hold no pattern yet, shown beside the groups patterns are in.
    pub(super) fn groups_made_here(&self) -> Vec<String> {
        self.new_groups.borrow().clone()
    }

    /// Put the cursor where a dialog's answer said: a pattern's row, or a group's + (New) row.
    pub(super) fn put_cursor_at(&mut self, app: &App, row: &str) {
        let wanted = if let Some(name) = row.strip_prefix(PATTERN_ROW) {
            Listed::Pattern(name.to_string())
        } else if let Some(group) = row.strip_prefix(NEW_PATTERN_ROW) {
            Listed::NewPattern(group.to_string())
        } else {
            return;
        };
        self.on_tabs = false;
        if let Some(found) = self.rows(app).iter().position(|(listed, _)| *listed == wanted) {
            self.cursor.set(found);
        }
    }

    /// After a key changed what a search looks for, keep the cursor among the rows it finds, and show what was typed.
    pub(super) fn settle_search(&mut self, app: &mut App) {
        let matches = self.matches(app);
        if !matches.is_empty() && !matches.contains(&self.cursor.get()) {
            self.cursor.set(matches[0]);
        }
        app.say(&named(messages::MSG_SEARCH_STATUS, &[("text", self.typed.as_str().into())]));
    }

    /// ENTER at the end of a search: the cursor stays on the pattern found, its group's tab chosen.
    pub(super) fn keep_found(&mut self, app: &mut App) {
        let found = self.listed(app);
        self.searching = false;
        if let Listed::Pattern(name) = found {
            choose_tab_of(app, &name);
            self.put_cursor_at(app, &format!("{PATTERN_ROW}{name}"));
        }
    }

    /// Do what a key that edits the patterns or their groups does, and say whether the key was one.
    pub(super) fn press_edit(&mut self, app: &mut App, item: &KeyItem) -> bool {
        let chosen = self.chosen(app);
        if self.on_tabs {
            match (&chosen, item) {
                (PatternTab::Group(group), item) if item.is(&Keys::RENAME) => self.rename_group(app, group),
                (PatternTab::Group(group), item) if item.is(&Keys::COPY) => self.copy_group(app, group),
                (PatternTab::Group(group), item) if item.is(&Keys::UNGROUP) => self.ungroup(app, group),
                (PatternTab::Group(_), item) if item.is(&Keys::ADD) => self.add(app),
                (PatternTab::New, item) if item.is(&Keys::NEW_GROUP) => self.new_group(app),
                _ => return false,
            }
            return true;
        }
        match self.listed(app) {
            Listed::Pattern(name) if item.is(&Keys::RENAME) => {
                crate::screens::rename::ask_rename(app, Section::PATTERNS, &name, messages::MSG_RENAME_PATTERN_PROMPT);
            }
            Listed::Pattern(name) if item.is(&Keys::COPY) => match app.document.copy_named(Section::PATTERNS, &name) {
                Ok(new) => {
                    app.say(&named(messages::MSG_COPIED_TO, &[("name", new.as_str().into())]));
                    if let Some(found) = self.rows(app).iter().position(|(listed, _)| *listed == Listed::Pattern(new.clone())) {
                        self.cursor.set(found);
                    }
                }
                Err(problem) => app.refuse(&problem),
            },
            Listed::Pattern(name) if item.is(&Keys::DELETE) => {
                crate::screens::list_page::delete_after_checks(app, Section::PATTERNS, legends::MSG_PATTERN_WHAT, &name);
            }
            Listed::Pattern(name) if item.is(&Keys::GROUP) => self.choose_group(app, &name),
            Listed::Pattern(_) if item.is(&Keys::ADD) => self.add(app),
            Listed::NewPattern(_) if item.is(&Keys::NEW_PATTERN) || item.is(&Keys::ADD) => self.add(app),
            Listed::NewGroup if item.is(&Keys::NEW_GROUP) => self.new_group(app),
            _ => return false,
        }
        true
    }

    /// Ask what kind of pattern to make, a drum pattern or one written for a scale of so many notes, then its name, make it
    /// in the cursor's group and open it.
    fn add(&self, app: &mut App) {
        let group = match self.chosen(app) {
            PatternTab::Group(group) => Some(group),
            _ => None,
        };
        let made_here = self.new_groups.clone();
        let then = Box::new(move |app: &mut App, drum: bool, scale_length: Option<i64>| {
            let taken = app.document.names_of(Section::PATTERNS);
            let value = app.document.new_name(Section::PATTERNS, names::MSG_NEW_PATTERN_WORD);
            let (group, made_here) = (group.clone(), made_here.clone());
            ask_unused_name(app, messages::MSG_NEW_PATTERN_PROMPT, &value, taken, move |app, text| {
                let steps = new_pattern_steps(app);
                if let Err(problem) = app.document.add_blank_pattern(text, steps, group.as_deref(), drum, scale_length) {
                    app.refuse(&problem);
                    return;
                }
                made_here.borrow_mut().retain(|made| Some(made) != group.as_ref());
                cursor_on_pattern(app, text);
                app.show_page(crate::screens::pattern::open_pattern(text));
            });
        });
        app.show_page(Box::new(NewPatternDialog::new(then)));
    }

    /// Move a pattern to another group, picked from the groups, or to a new one, the picker's last entry.
    fn choose_group(&self, app: &mut App, name: &str) {
        let groups = self.groups(app);
        let current = app
            .document
            .get_setlist()
            .get_pattern(name)
            .and_then(|pattern| pattern.get_written("group"))
            .and_then(|group| group.as_str())
            .map(str::to_string);
        let place = current.and_then(|current| groups.iter().position(|group| *group == current)).unwrap_or(0);
        let mut options = groups.clone();
        options.push(labels::MSG_NEW_GROUP_BUTTON.to_string());
        let (name, made_here) = (name.to_string(), self.new_groups.clone());
        let moved = std::rc::Rc::new(move |app: &mut App, group: &str| {
            let (pattern, group) = (name.clone(), group.to_string());
            app.document.change_set(|setlist| {
                if let Some(llamatron_model::objects::setlist::Item::Pattern(held)) = setlist.get_item_mut(Section::PATTERNS, &pattern) {
                    held.set_group(Some(&group));
                }
            });
            made_here.borrow_mut().retain(|made| *made != group);
            cursor_on_pattern(app, &name);
        });
        let mut dialog = ChoiceDialog::new(messages::MSG_GROUP_TITLE, options, place);
        let all = groups.clone();
        dialog.then = Some(Box::new(move |app: &mut App, answer: &Answer| {
            let Answer::Chosen(chosen) = answer else { return };
            if *chosen < groups.len() {
                moved(app, &groups[*chosen]);
                return;
            }
            let moved = moved.clone();
            let value = new_name(names::MSG_NEW_GROUP_WORD, &all);
            ask_unused_name(app, messages::MSG_NEW_GROUP_PROMPT, &value, all.clone(), move |app, text| moved(app, text));
        }));
        app.show_page(Box::new(dialog));
    }

    /// Make a group, whose tab shows with only its + (New) row until a pattern is made in it.
    fn new_group(&self, app: &mut App) {
        let groups = self.groups(app);
        let value = new_name(names::MSG_NEW_GROUP_WORD, &groups);
        let made_here = self.new_groups.clone();
        ask_unused_name(app, messages::MSG_NEW_GROUP_PROMPT, &value, groups, move |app, text| {
            made_here.borrow_mut().push(text.to_string());
            choose_tab(app, text);
            app.cursor_to(&format!("{NEW_PATTERN_ROW}{text}"));
        });
    }

    /// Ask for the group's new name, one no group has, for every pattern in it.
    fn rename_group(&self, app: &mut App, group: &str) {
        let taken: Vec<String> = self.groups(app).into_iter().filter(|each| each != group).collect();
        let title = named(messages::MSG_RENAME_GROUP_PROMPT, &[("name", group.into())]);
        let (old, made_here) = (group.to_string(), self.new_groups.clone());
        ask_unused_name(app, &title, group, taken, move |app, text| {
            if text == old {
                return;
            }
            for made in made_here.borrow_mut().iter_mut().filter(|made| **made == old) {
                *made = text.to_string();
            }
            app.document.rename_pattern_group(&old, text);
            choose_tab(app, text);
        });
    }

    /// Take every pattern out of the group after asking, deleting none; a group made here that holds none is simply gone.
    fn ungroup(&self, app: &mut App, group: &str) {
        let title = named(messages::MSG_UNGROUP_TITLE, &[("name", group.into())]);
        let lines = vec![messages::MSG_UNGROUP_QUESTION.to_string()];
        let (group, made_here) = (group.to_string(), self.new_groups.clone());
        let dialog = ConfirmDialog::new(&title, lines, false, false).then(Box::new(move |app: &mut App, _: &Answer| {
            made_here.borrow_mut().retain(|made| *made != group);
            app.document.ungroup_patterns(&group);
            choose_tab(app, labels::MSG_UNGROUPED);
        }));
        app.show_page(Box::new(dialog));
    }

    /// Copy the whole group under a new name, asked for in a prompt that starts from the group's name counted up.
    fn copy_group(&self, app: &mut App, group: &str) {
        let groups = self.groups(app);
        let title = named(messages::MSG_COPY_GROUP_TITLE, &[("name", group.into())]);
        let value = copy_name(group, &groups);
        let (group, made_here) = (group.to_string(), self.new_groups.clone());
        ask_unused_name(app, &title, &value, groups, move |app, text| {
            let copies = match app.document.copy_pattern_group(&group, text) {
                Ok(copies) => copies,
                Err(problem) => return app.refuse(&problem),
            };
            if copies.is_empty() {
                made_here.borrow_mut().push(text.to_string());
            }
            app.say(&named(messages::MSG_GROUP_COPIED, &[("name", text.into())]));
            choose_tab(app, text);
        });
    }
}
