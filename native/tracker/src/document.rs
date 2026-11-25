// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The set being edited (the Python interface/tracker/document.py): the set, the file it came from, whether it changed since,
//! and the current song.

use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::Song;
use std::path::{Path, PathBuf};

pub struct Document {
    setlist: Setlist,
    path: Option<PathBuf>,
    dirty: bool,
    current: String,
    /// The kinds of generator the Generators page shows open, which the set's file remembers and nothing undoes.
    open_generator_types: Vec<String>,
}

/// The kinds of generator a file's data says the Generators page shows open, only the plugins' kinds.
fn open_types_of(text: &str) -> Vec<String> {
    let Ok(data) = llamatron_model::file::data::load(text) else {
        return Vec::new();
    };
    let listed = data
        .get(llamatron_model::schema::generated::file_format::OPEN_GENERATOR_TYPES)
        .and_then(|types| types.as_list().map(<[_]>::to_vec))
        .unwrap_or_default();
    listed
        .iter()
        .filter_map(|kind| kind.as_str())
        .filter(|kind| llamatron_model::schema::generated::plugins::PLUGINS.iter().any(|plugin| plugin.name == *kind))
        .map(str::to_string)
        .collect()
}

impl Document {
    /// A set held, saved at a path if it has one; its first song current.
    pub fn new(setlist: Setlist, path: Option<PathBuf>) -> Document {
        let current = setlist.song_names().first().map(|name| name.to_string()).unwrap_or_default();
        Document {
            setlist,
            path,
            dirty: false,
            current,
            open_generator_types: Vec::new(),
        }
    }

    /// The set a file holds, opened as the tracker opens it.
    pub fn open(path: &Path) -> Result<Document, String> {
        let text = std::fs::read_to_string(path).map_err(|error| error.to_string())?;
        let stem = path.file_stem().map(|stem| stem.to_string_lossy().to_string());
        let setlist = Setlist::read_text(&text, stem).map_err(|error| error.message)?;
        let mut document = Document::new(setlist, Some(path.to_path_buf()));
        document.open_generator_types = open_types_of(&text);
        Ok(document)
    }

    pub fn get_setlist(&self) -> &Setlist {
        &self.setlist
    }

    pub fn song(&self) -> &Song {
        self.setlist.get_song(&self.current).expect("the current song is always in the set")
    }

    pub fn get_current_song_name(&self) -> &str {
        &self.current
    }

    /// Make another of the set's songs current, which changes nothing in the file.
    pub fn select_song(&mut self, name: &str) {
        if self.setlist.get_song(name).is_some() {
            self.current = name.to_string();
        }
    }

    pub fn get_path(&self) -> Option<&Path> {
        self.path.as_deref()
    }

    pub fn is_dirty(&self) -> bool {
        self.dirty
    }

    /// The file's name without its folders, for the header's crumb, or None before the set is saved.
    pub fn get_file_name(&self) -> Option<String> {
        self.path
            .as_ref()
            .and_then(|path| path.file_name())
            .map(|name| name.to_string_lossy().to_string())
    }

    /// Take up the set another program's file holds in place of this one's, keeping this one's own file, as the screen tour
    /// does where a page not ported yet changed the set.
    pub fn take_up(&mut self, file: &Path, dirty: bool, song: &str) {
        let Ok(text) = std::fs::read_to_string(file) else { return };
        let stem = self
            .path
            .as_ref()
            .and_then(|path| path.file_stem())
            .map(|stem| stem.to_string_lossy().to_string());
        if let Ok(setlist) = Setlist::read_text(&text, stem) {
            self.setlist = setlist;
            self.dirty = dirty;
            self.current = song.to_string();
        }
    }

    pub fn is_generator_type_open(&self, kind: &str) -> bool {
        self.open_generator_types.iter().any(|open| open == kind)
    }

    /// Show a kind of generator open or closed on the Generators page, which is no edit of the set.
    pub fn show_generator_type(&mut self, kind: &str, opened: bool) {
        self.open_generator_types.retain(|open| open != kind);
        if opened {
            self.open_generator_types.push(kind.to_string());
        }
    }

    /// Make one change to the set, and note that it needs saving.
    pub fn change_set(&mut self, change: impl FnOnce(&mut Setlist)) {
        change(&mut self.setlist);
        self.dirty = true;
    }

    /// Note that the set changed, so that it needs saving.
    pub fn changed(&mut self) {
        self.dirty = true;
    }
}
