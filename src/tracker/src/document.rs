// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The set being edited (the Python interface/tracker/document.py): the set, the file it came from, whether it changed since,
//! and the current song.

use crate::history::{describe_change, History, Snapshot};
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::Song;
use std::path::{Path, PathBuf};

pub struct Document {
    setlist: Setlist,
    path: Option<PathBuf>,
    dirty: bool,
    current: String,
    /// The set as each key left it, for undo and redo, and the set as its file holds it, which says whether it needs saving.
    history: History,
    clean: Data,
    /// The set as its file held it when opened or last saved here, the version aside, which says whether something else has
    /// changed the file since.
    saved: Option<Data>,
    /// Whether the next change continues the step before rather than making one of its own.
    continuing: bool,
    /// A count moved by every change to the set or to the current song, which real-time playback follows to hear an edit
    /// made while playing.
    revision: u64,
}

impl Document {
    /// A set held, saved at a path if it has one; its first song current.
    pub fn new(setlist: Setlist, path: Option<PathBuf>) -> Document {
        let current = setlist.song_names().first().map(|name| name.to_string()).unwrap_or_default();
        let clean = setlist.to_data();
        let saved = path.as_ref().map(|_| without_version(&clean));
        let history = History::new(Snapshot {
            data: clean.clone(),
            song: current.clone(),
        });
        Document {
            setlist,
            path,
            dirty: false,
            current,
            history,
            clean,
            saved,
            continuing: false,
            revision: 0,
        }
    }

    /// A new set, as the tracker opens on when no file is named: one empty song and a C Major scale, saved nowhere yet.
    pub fn new_set() -> Result<Document, String> {
        let setlist = Setlist::read_text(crate::generated::tables::NEW_SET, None).map_err(|error| error.message)?;
        Ok(Document::new(setlist, None))
    }

    /// The text saving writes: the set with the program's version.
    pub fn file_text(&self) -> String {
        use llamatron_model::schema::generated::file_format::SetlistSetting;
        let mut data = self.setlist.to_data();
        if let Data::Map(pairs) = &mut data {
            let version = Data::text(SetlistSetting::VERSION);
            match pairs.iter_mut().find(|(key, _)| *key == version) {
                Some(pair) => pair.1 = Data::text(crate::version::PROGRAM_VERSION),
                None => pairs.insert(0, (version, Data::text(crate::version::PROGRAM_VERSION))),
            }
        }
        let file = llamatron_model::file::layout::as_file_layout(&data);
        llamatron_model::file::writing::dump_file_layout(&file)
    }

    /// Write the set to a file, making any folders it needs; a protected set's own file is never written over.
    pub fn save(&mut self, path: &Path) -> Result<(), String> {
        if self.file_is_protected(Some(path)) {
            let words = [("path", path.display().to_string().as_str().into())];
            return Err(llamatron_strings::named(llamatron_strings::errors::ERR_FILE_PROTECTED, &words));
        }
        if let Some(folder) = path.parent().filter(|folder| !folder.as_os_str().is_empty()) {
            std::fs::create_dir_all(folder).map_err(|error| error.to_string())?;
        }
        std::fs::write(path, self.file_text()).map_err(|error| error.to_string())?;
        self.path = Some(path.to_path_buf());
        self.dirty = false;
        self.clean = self.setlist.to_data();
        self.saved = Some(without_version(&self.clean));
        Ok(())
    }

    /// Save the set under a name chosen for it: a copy of a protected set is the person's own, so the copy isn't protected.
    pub fn save_as(&mut self, path: &Path) -> Result<(), String> {
        use llamatron_model::schema::generated::file_format::SetlistSetting;
        if self.is_protected() && self.path.as_deref().is_some_and(|own| own != path) {
            self.setlist.set_written(SetlistSetting::PROTECTED, None);
        }
        self.save(path)
    }

    /// Whether the set is protected, as the demos are.
    fn is_protected(&self) -> bool {
        use llamatron_model::schema::generated::file_format::SetlistSetting;
        matches!(self.setlist.get_written(SetlistSetting::PROTECTED), Some(Data::Bool(true)))
    }

    /// Whether saving to a path, or where the set came from, would write over a protected set's own file.
    pub fn file_is_protected(&self, path: Option<&Path>) -> bool {
        let path = path.or(self.path.as_deref());
        self.is_protected() && path.is_some() && path == self.path.as_deref() && path.is_some_and(Path::exists)
    }

    /// What the set's file holds now, the version aside, or None with no file or one that can't be read.
    fn file_now(&self) -> Option<Data> {
        let path = self.path.as_ref()?;
        let text = std::fs::read_to_string(path).ok()?;
        let stem = path.file_stem().map(|stem| stem.to_string_lossy().to_string());
        let setlist = Setlist::read_text(&text, stem).ok()?;
        Some(without_version(&setlist.to_data()))
    }

    /// Whether the set's file already holds exactly what saving would write, in order, so that saving would change nothing;
    /// a set whose file holds it has nothing unsaved.
    pub fn file_holds_this_set(&mut self) -> bool {
        let holds = self.file_now().is_some_and(|held| held == without_version(&self.setlist.to_data()));
        if holds {
            self.dirty = false;
        }
        holds
    }

    /// Whether something else has changed the set's file since it was opened or saved here; a file that can no longer be
    /// read counts as changed, so that saving asks before writing over it.
    pub fn file_changed_elsewhere(&self) -> bool {
        let Some(path) = self.path.as_ref() else { return false };
        if !path.exists() {
            return false;
        }
        self.file_now() != self.saved
    }

    /// The set a file holds, opened as the tracker opens it.
    pub fn open(path: &Path) -> Result<Document, String> {
        let text = std::fs::read_to_string(path).map_err(|error| error.to_string())?;
        let stem = path.file_stem().map(|stem| stem.to_string_lossy().to_string());
        let setlist = Setlist::read_text(&text, stem).map_err(|error| error.message)?;
        Ok(Document::new(setlist, Some(path.to_path_buf())))
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
            self.revision += 1;
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
    pub fn take_up(&mut self, file: &Path, dirty: bool, song: &str) -> Result<(), String> {
        let text = std::fs::read_to_string(file).map_err(|error| format!("{}: {error}", file.display()))?;
        let stem = self
            .path
            .as_ref()
            .and_then(|path| path.file_stem())
            .map(|stem| stem.to_string_lossy().to_string());
        let setlist = Setlist::read_text(&text, stem).map_err(|error| format!("{}: {}", file.display(), error.message))?;
        self.setlist = setlist;
        self.dirty = dirty;
        self.current = song.to_string();
        self.record_edit();
        Ok(())
    }

    /// The count every change to the set or the current song moves.
    pub fn get_revision(&self) -> u64 {
        self.revision
    }

    /// Make one change to the set, and note that it needs saving.
    pub fn change_set(&mut self, change: impl FnOnce(&mut Setlist)) {
        change(&mut self.setlist);
        self.dirty = true;
        self.revision += 1;
    }

    fn snapshot(&self) -> Snapshot {
        Snapshot {
            data: self.setlist.to_data(),
            song: self.current.clone(),
        }
    }

    /// Note the set as a key left it, a step to undo where it changed.
    pub fn record_edit(&mut self) -> bool {
        let snapshot = self.snapshot();
        if std::mem::take(&mut self.continuing) {
            let recorded = self.history.record_continuing(snapshot);
            // A step taken back to where it began may leave the set as its file holds it.
            self.dirty = self.setlist.to_data() != self.clean;
            return recorded;
        }
        self.history.record(snapshot)
    }

    /// Have the next change continue the step before, as the carries of one move do, so that undo takes them back at once.
    pub fn continue_edit(&mut self) {
        self.continuing = true;
    }

    /// Go a step back in the history, or forward, and say what the step changed, or None where there is no step.
    /// Take the last step back, and say what it changed and what it renamed, or None when there is nothing to undo.
    pub fn undo(&mut self) -> Option<(String, crate::history::Renames)> {
        let leaving = self.snapshot();
        let arriving = self.history.undo()?;
        Some(self.restore(&leaving, arriving))
    }

    /// Make again the last step undone, and say what it changed and what it renamed, or None when there is nothing to redo.
    pub fn redo(&mut self) -> Option<(String, crate::history::Renames)> {
        let leaving = self.snapshot();
        let arriving = self.history.redo()?;
        Some(self.restore(&leaving, arriving))
    }

    fn restore(&mut self, leaving: &Snapshot, arriving: Snapshot) -> (String, crate::history::Renames) {
        let words = describe_change(leaving, &arriving);
        let renames = crate::history::renamed_items(leaving, &arriving);
        if let Ok(setlist) = Setlist::from_data(&arriving.data) {
            self.setlist = setlist;
        }
        self.revision += 1;
        self.current = if self.setlist.get_song(&arriving.song).is_some() {
            arriving.song
        } else {
            self.setlist.song_names().first().map(|name| name.to_string()).unwrap_or_default()
        };
        self.dirty = self.setlist.to_data() != self.clean;
        (words, renames)
    }

    /// Where the set's data differs from the data it opened or was last saved with, by its top-level names, for the screen
    /// tour to say why a stop's unsaved mark differs.
    pub fn differences_from_clean(&self) -> Vec<String> {
        let now = self.setlist.to_data();
        let names = |data: &Data| -> Vec<String> {
            data.as_map().map_or(Vec::new(), |pairs| {
                pairs.iter().filter_map(|(key, _)| key.as_str().map(str::to_string)).collect()
            })
        };
        let mut keys = names(&now);
        keys.extend(names(&self.clean).into_iter().filter(|key| !names(&now).contains(key)));
        keys.into_iter().filter(|key| now.get(key) != self.clean.get(key)).collect()
    }

    /// Note that the set changed, so that it needs saving.
    pub fn changed(&mut self) {
        self.dirty = true;
    }
}

/// A set's data without the version that wrote it, which saving always brings up to date, for comparing.
fn without_version(data: &Data) -> Data {
    use llamatron_model::schema::generated::file_format::SetlistSetting;
    match data {
        Data::Map(pairs) => Data::Map(pairs.iter().filter(|(key, _)| key.as_str() != Some(SetlistSetting::VERSION)).cloned().collect()),
        other => other.clone(),
    }
}

/// The set's name for its exports: its file's name without the ending, or untitled until it is saved.
const UNTITLED: &str = "untitled";

impl Document {
    /// The set's name, its file's name without the ending, or untitled until it is saved.
    pub fn get_name(&self) -> String {
        self.path
            .as_ref()
            .and_then(|path| path.file_stem())
            .map_or(UNTITLED.to_string(), |stem| stem.to_string_lossy().to_string())
    }

    /// The folder the current song's exports go in, the set's file's, or None until the set is saved.
    pub fn export_directory(&self) -> Option<PathBuf> {
        let path = self.path.as_ref()?;
        let folder = path.parent().map(Path::to_path_buf).unwrap_or_default();
        Some(if folder.as_os_str().is_empty() { PathBuf::from(".") } else { folder })
    }

    /// What the current song's exports are named after: <set>_<song>.
    pub fn export_name(&self) -> String {
        format!("{}_{}", self.get_name(), self.current)
    }

    /// The current song played into its clips, from its own seed, as an export plays it.
    pub fn rendered(&self) -> Result<llamatron_engine::realizer::Grid, String> {
        llamatron_engine::realizer::SongRealizer::new(&self.setlist, self.song(), None)
            .render()
            .map_err(|error| match error {
                llamatron_engine::error::RenderError::Refused(problem) => problem,
                llamatron_engine::error::RenderError::NotPorted(what) => format!("not ported yet: {what}"),
            })
    }
}
