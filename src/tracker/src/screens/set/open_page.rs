// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Open page (the Python screens/set/open_page.py and pages/folder_list.py): picks a set file to open, starting in the
//! examples folder, or the folder it was last in this session. Ctrl+O shows it from every page. A folder's rows are the
//! folder above, then its folders, then its set files, each sorted by name with capitals ignored.

use crate::app::App;
use crate::document::Document;
use crate::drawing::{Align, Style, INDENT};
use crate::keybindings::{KeyClass, OpenPage as Keys};
use crate::keys::KeyItem;
use crate::page::Duration;
use crate::screens::list_page::{ListColumn, ListPage, Listing, Row};
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_strings::{labels, marks, messages, named};
use std::path::{Path, PathBuf};

/// Where the picker starts: the examples folder where there is one, else the folder llamatron runs in.
const EXAMPLES_FOLDER: &str = "examples";
const HERE: &str = ".";
/// The row of the folder above, and what starts a hidden folder's name.
const PARENT: &str = "..";
const HIDDEN_PREFIX: char = '.';
/// The endings of the files a set is kept in, and of the MIDI files the import reads.
const SET_SUFFIXES: [&str; 2] = [".yml", ".yaml"];
const MIDI_SUFFIXES: [&str; 2] = [".mid", ".midi"];

static COLUMNS: [ListColumn; 1] = [ListColumn {
    heading: labels::Column::SELECT_FILE,
    width: None,
    align: Align::Left,
}];

/// The Open page: a folder's rows, and ENTER going into a folder, or opening a set file, or, as the MIDI import's picker,
/// reading a MIDI file and asking how to import it.
pub struct OpenPage {
    folder: PathBuf,
    /// Whether it picks a MIDI file to import rather than a set to open.
    midi: bool,
}

impl OpenPage {
    /// The Open page in the folder it was last in this session, or the examples folder, or here.
    pub fn new(app: &App) -> ListPage<OpenPage> {
        let folder = match &app.session.last_set_folder {
            Some(folder) if folder.is_dir() => folder.clone(),
            _ if Path::new(EXAMPLES_FOLDER).is_dir() => PathBuf::from(EXAMPLES_FOLDER),
            _ => PathBuf::from(HERE),
        };
        ListPage::new(OpenPage { folder, midi: false })
    }

    /// The MIDI import's picker, in the folder it was last in this session, or the home folder, since a MIDI file may be
    /// anywhere on the computer.
    pub fn for_midi(app: &App) -> ListPage<OpenPage> {
        let folder = match &app.session.last_midi_folder {
            Some(folder) if folder.is_dir() => folder.clone(),
            _ => std::env::var_os("HOME").map_or_else(|| PathBuf::from(HERE), PathBuf::from),
        };
        ListPage::new(OpenPage { folder, midi: true })
    }

    /// The endings of the files it lists.
    fn suffixes(&self) -> &'static [&'static str] {
        if self.midi {
            &MIDI_SUFFIXES
        } else {
            &SET_SUFFIXES
        }
    }

    /// Keep the folder shown for the session, so that the next picker of these files starts in it.
    fn remember_folder(&self, app: &mut App) {
        if self.midi {
            app.session.last_midi_folder = Some(self.folder.clone());
        } else {
            app.session.last_set_folder = Some(self.folder.clone());
        }
    }

    /// Read a MIDI file and ask how to import it, or say in a dialog why it cannot be read.
    fn offer_import(app: &mut App, path: &Path) {
        let file = path.file_name().map(|name| name.to_string_lossy().to_string()).unwrap_or_default();
        let read = std::fs::read(path)
            .map_err(|problem| problem.to_string())
            .and_then(|bytes| llamatron_importers::import::MidiImport::new(&bytes).map_err(|problem| problem.0));
        match read {
            Ok(import) => {
                let song = path.file_stem().map(|stem| stem.to_string_lossy().to_string()).unwrap_or_default();
                let dialog = crate::screens::import_dialog::ImportDialog::new(app, import, &song);
                app.show_page(Box::new(dialog));
            }
            Err(problem) => {
                let said = named(
                    llamatron_strings::errors::ERR_CANT_READ_MIDI,
                    &[("file", file.as_str().into()), ("problem", problem.as_str().into())],
                );
                let told = crate::screens::dialogs::MessageDialog::new(llamatron_strings::errors::ERR_CANT_IMPORT_TITLE, vec![said]);
                app.show_page(Box::new(told));
            }
        }
    }

    /// Whether a name in the folder is a folder the picker shows, hidden ones left out.
    fn is_folder(&self, name: &str) -> bool {
        self.folder.join(name).is_dir() && !name.starts_with(HIDDEN_PREFIX)
    }

    /// The path a row leads to, the folder above taken as its parent.
    fn path_of(&self, name: &str) -> PathBuf {
        let joined = self.folder.join(name);
        if name == PARENT {
            return std::path::absolute(&joined)
                .ok()
                .and_then(|path| path.parent().and_then(Path::parent).map(Path::to_path_buf))
                .unwrap_or(joined);
        }
        joined
    }

    /// The whole path of the folder, which the page shows over its rows.
    fn shown_path(&self) -> String {
        std::path::absolute(&self.folder).map_or_else(|_| self.folder.display().to_string(), |path| path.display().to_string())
    }

    /// Open a set file in place of the set open now, and say so; a file that cannot be opened is told in a dialog, saying
    /// why.
    fn open_file(app: &mut App, path: &Path) {
        match Document::open(path) {
            Ok(document) => {
                app.document = document;
                app.go_back();
                app.say(&named(messages::MSG_OPENED, &[("path", path.display().to_string().as_str().into())]));
            }
            Err(error) => {
                let told = crate::screens::dialogs::MessageDialog::new(llamatron_strings::errors::ERR_CANT_OPEN_TITLE, vec![error]);
                app.show_page(Box::new(told));
            }
        }
    }
}

impl Listing for OpenPage {
    fn name(&self) -> &'static str {
        "OpenPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        if self.midi {
            return vec![labels::Crumb::IMPORT_MIDI.to_string()];
        }
        vec![labels::Crumb::FILE.to_string(), labels::Crumb::OPEN.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::SET_FILE)
    }

    fn columns(&self) -> &[ListColumn] {
        &COLUMNS
    }

    fn duration(&self, _app: &App) -> Duration {
        Duration::Nothing
    }

    fn can_add(&self) -> bool {
        false
    }

    fn name_column_width(&self) -> Option<usize> {
        None
    }

    fn rows(&self, _app: &App) -> Vec<Row> {
        let mut names: Vec<String> = std::fs::read_dir(&self.folder)
            .map(|entries| {
                entries
                    .filter_map(Result::ok)
                    .map(|entry| entry.file_name().to_string_lossy().to_string())
                    .collect()
            })
            .unwrap_or_default();
        names.sort_by_key(|name| name.to_lowercase());
        let mut rows = vec![(PARENT.to_string(), vec![marks::MSG_PARENT_ROW.to_string()])];
        for name in names.iter().filter(|name| self.is_folder(name)) {
            rows.push((name.clone(), vec![named(marks::MSG_FOLDER_ROW, &[("name", name.as_str().into())])]));
        }
        for name in &names {
            let lowered = name.to_lowercase();
            if self.suffixes().iter().any(|suffix| lowered.ends_with(suffix)) {
                rows.push((name.clone(), vec![name.clone()]));
            }
        }
        rows
    }

    fn item_keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![KeyItem::of(&Keys::CLASS, &Keys::OPEN)]
    }

    fn lines_above(&self, _app: &App) -> Vec<Text> {
        vec![Text::styled(&format!("{INDENT}{}", self.shown_path()), Style::DIM), Text::default()]
    }

    fn press_row(&mut self, app: &mut App, item: &KeyItem, _key: &str, row: Option<&str>) -> Option<String> {
        let row = row?;
        if !item.is(&Keys::OPEN) {
            return None;
        }
        let path = self.path_of(row);
        if path.is_dir() {
            self.folder = path;
            self.remember_folder(app);
            return Some(PARENT.to_string());
        }
        self.remember_folder(app);
        if self.midi {
            Self::offer_import(app, &path);
        } else {
            Self::open_file(app, &path);
        }
        None
    }
}
