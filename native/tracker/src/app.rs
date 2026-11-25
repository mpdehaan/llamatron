// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The tracker (the Python interface/tracker/app.py): the set being edited, the status line every page shares, what the
//! session remembers, and the stack of pages, the top one taking the keys.

use crate::document::Document;
use crate::keybindings::Page as PageKeys;
use crate::keys::KeyItem;
use crate::page::{page_lines, Page};
use crate::screens::main_page::MainPage;
use crate::text::Text;

/// The dim line above the legend: what the last key did, or why it did nothing, in amber.
#[derive(Default)]
pub struct StatusLine {
    text: String,
    refusal: bool,
}

impl StatusLine {
    pub fn say(&mut self, text: &str) {
        self.text = text.to_string();
        self.refusal = false;
    }

    pub fn refuse(&mut self, text: &str) {
        self.text = text.to_string();
        self.refusal = true;
    }

    pub fn clear(&mut self) {
        self.text.clear();
        self.refusal = false;
    }

    pub fn text(&self) -> &str {
        &self.text
    }

    pub fn is_refusal(&self) -> bool {
        self.refusal
    }
}

/// What the session remembers of how the pages were left, which no file keeps.
pub struct Session {
    /// The settings pages' sections open now, by name.
    pub open_field_sections: std::collections::HashSet<String>,
    /// The tab each kind of page with a tab box last showed, by the page's name.
    pub chosen_tabs: std::collections::HashMap<String, String>,
    /// Whether the pattern editor shows the piano roll rather than the rows, kept as you move between patterns.
    pub on_roll: bool,
    /// The pattern editor's open sections, by name, kept for the session.
    pub open_sections: std::collections::HashSet<String>,
    /// Whether Arrange shows its details view, kept for the session.
    pub shows_arrange_details: bool,
    /// The folder the Open page was last in, where the next one starts.
    pub last_set_folder: Option<std::path::PathBuf>,
    /// The Live sets the person has said this session may be written over, asked about only the first time.
    pub confirmed_overwrites: Vec<std::path::PathBuf>,
}

impl Default for Session {
    fn default() -> Session {
        Session {
            open_field_sections: Default::default(),
            chosen_tabs: Default::default(),
            on_roll: true,
            open_sections: crate::screens::pattern::rows_view::OPEN_AT_START
                .iter()
                .map(|section| section.to_string())
                .collect(),
            shows_arrange_details: false,
            last_set_folder: None,
            confirmed_overwrites: Vec::new(),
        }
    }
}

/// What a page asks of the stack, done once its key is handled.
pub enum Request {
    Open(Box<dyn Page>),
    Back,
    /// A dialog's answer, for the page that is on top once the dialog has closed.
    Answer(crate::screens::dialogs::Answer),
}

/// What every page reaches: the set, the status line, what the session remembers, and the requests of the key in hand.
pub struct App {
    pub document: Document,
    pub status: StatusLine,
    pub session: Session,
    /// Whether FluidSynth is installed to play General MIDI, which offers Listen on a pattern whose song names no Preview
    /// instrument.
    pub fluidsynth_installed: bool,
    /// The screen's height as last drawn, which a page that fits itself to the whole screen reads.
    pub screen_height: std::cell::Cell<usize>,
    requests: Vec<Request>,
    /// What a settings page's form asked the page to ask in a dialog, for the field whose key the form was handling.
    pub asking: Option<crate::forms::nodes::Edit>,
    /// Whether the tracker is to close, once the key that said so is handled.
    pub quitting: bool,
}

impl App {
    pub fn new(document: Document) -> App {
        App {
            document,
            status: StatusLine::default(),
            session: Session::default(),
            fluidsynth_installed: false,
            screen_height: std::cell::Cell::new(24),
            requests: Vec::new(),
            quitting: false,
            asking: None,
        }
    }

    pub fn show_page(&mut self, page: Box<dyn Page>) {
        self.requests.push(Request::Open(page));
    }

    /// Show the Open page to pick a set file, which Ctrl+O and the File page's Open do; a set with unsaved changes asks
    /// first.
    pub fn open_set(&mut self) {
        let show_open = |app: &mut App| {
            let page = crate::screens::set::open_page::OpenPage::new(app);
            app.show_page(Box::new(page));
        };
        if !self.document.is_dirty() {
            show_open(self);
            return;
        }
        let messages = vec![llamatron_strings::messages::MSG_UNSAVED_CONTINUE.to_string()];
        let question = crate::screens::dialogs::ConfirmDialog::new(llamatron_strings::messages::MSG_UNSAVED_TITLE, messages, false, false);
        let question = question.then(Box::new(move |app: &mut App, _answer: &crate::screens::dialogs::Answer| show_open(app)));
        self.show_page(Box::new(question));
    }

    pub fn go_back(&mut self) {
        self.requests.push(Request::Back);
    }

    /// Hand a dialog's answer to the page that opened it, once the dialog has closed.
    pub fn answer(&mut self, answer: crate::screens::dialogs::Answer) {
        self.requests.push(Request::Answer(answer));
    }

    pub fn say(&mut self, text: &str) {
        self.status.say(text);
    }

    pub fn refuse(&mut self, text: &str) {
        self.status.refuse(text);
    }
}

/// The tracker: the app and its stack of pages.
pub struct Tracker {
    pub app: App,
    pages: Vec<Box<dyn Page>>,
}

impl Tracker {
    /// The tracker on a set, on the main screen.
    pub fn new(document: Document) -> Tracker {
        Tracker {
            app: App::new(document),
            pages: vec![Box::new(MainPage::new())],
        }
    }

    /// How many pages are open, the main screen among them.
    pub fn depth(&self) -> usize {
        self.pages.len()
    }

    pub fn top(&self) -> &dyn Page {
        self.pages.last().expect("the main screen is never closed").as_ref()
    }

    /// The keys that work on every page, before the page's own.
    /// The F1 dialog of the page on top: where it is, the everywhere keys but F1 itself, the page's own keys, and its help.
    fn help_of_top(&self) -> crate::screens::dialogs::HelpDialog {
        let page = self.top();
        let place = page.crumbs(&self.app).join(llamatron_strings::marks::MSG_CRUMB_SEPARATOR);
        // F1 isn't listed in its own dialog: it closes the dialog, and leaving it out puts Undo and Redo in one column.
        let everywhere: Vec<KeyItem> = self.everywhere_keys().into_iter().filter(|item| !item.is(&PageKeys::HELP)).collect();
        let about = page.help().unwrap_or_else(|| {
            crate::generated::tables::HELP_OF_PAGE
                .iter()
                .find(|(name, _)| *name == page.name())
                .map_or(Vec::new(), |(_, lines)| lines.iter().map(|line| line.to_string()).collect())
        });
        crate::screens::dialogs::HelpDialog::new(&place, everywhere, page.page_key_table(&self.app), about)
    }

    fn everywhere_keys(&self) -> Vec<KeyItem> {
        PageKeys::EVERYWHERE.iter().map(|binding| KeyItem::of(&PageKeys::CLASS, binding)).collect()
    }

    /// Press a key into the page on top: an everywhere key first, then the page's own.
    pub fn press(&mut self, key: &str) {
        let page = self.pages.last_mut().expect("the main screen is never closed");
        if page.takes_text() {
            if let Some(character) = typed_character(key) {
                self.app.status.clear();
                page.type_text(&mut self.app, character);
                return;
            }
        }
        // A dialog keeps to its own keys: the everywhere keys work on pages, so that F1 closes the help rather than opening it.
        let mut table: Vec<KeyItem> = Vec::new();
        if !page.is_dialog() {
            table.extend(PageKeys::EVERYWHERE.iter().map(|binding| KeyItem::of(&PageKeys::CLASS, binding)));
        }
        table.extend(page.page_key_table(&self.app));
        let Some(item) = table.into_iter().find(|item| item.keys.contains(&key)) else {
            return;
        };
        self.app.status.clear();
        if std::ptr::eq(item.binding, &PageKeys::UNDO) || std::ptr::eq(item.binding, &PageKeys::REDO) {
            self.step_history(std::ptr::eq(item.binding, &PageKeys::UNDO));
            return;
        }
        if std::ptr::eq(item.binding, &PageKeys::OPEN_SET) {
            self.app.open_set();
        } else if std::ptr::eq(item.binding, &PageKeys::EXPORT) {
            crate::exporting::export(&mut self.app);
        } else if std::ptr::eq(item.binding, &PageKeys::SAVE) {
            crate::everywhere::save(&mut self.app, None);
        } else if std::ptr::eq(item.binding, &PageKeys::QUIT_NOW) {
            self.app.quitting = true;
        } else if std::ptr::eq(item.binding, &PageKeys::HELP) {
            let help = self.help_of_top();
            self.app.show_page(Box::new(help));
        } else if PageKeys::EVERYWHERE.iter().any(|binding| std::ptr::eq(*binding, item.binding)) {
            // The other everywhere keys are not ported yet; they do nothing.
            return;
        } else {
            page.press(&mut self.app, &item, key);
        }
        self.app.document.record_edit();
        let requests = std::mem::take(&mut self.app.requests);
        for request in requests {
            match request {
                Request::Open(page) => self.pages.push(page),
                Request::Back => {
                    if self.pages.len() > 1 {
                        self.pages.pop();
                    }
                }
                Request::Answer(answer) => {
                    if let Some(page) = self.pages.last_mut() {
                        page.answered(&mut self.app, answer);
                    }
                    let more = std::mem::take(&mut self.app.requests);
                    for request in more {
                        if let Request::Open(page) = request {
                            self.pages.push(page);
                        }
                    }
                }
            }
        }
    }

    /// Undo or redo a step, saying on the status line what it changed, or that there is none.
    fn step_history(&mut self, back: bool) {
        use llamatron_strings::{messages, named};
        let (step, done, nothing) = if back {
            (self.app.document.undo(), messages::MSG_UNDONE, messages::MSG_NOTHING_TO_UNDO)
        } else {
            (self.app.document.redo(), messages::MSG_RESTORED, messages::MSG_NOTHING_TO_REDO)
        };
        match step {
            Some(words) => self.app.say(&named(done, &[("what", words.as_str().into())])),
            None => self.app.say(nothing),
        }
    }

    /// Bring the stack of pages in line with another program's, by their names from the main screen up, where pages not
    /// ported yet made the two part: the pages both hold are kept, and each the other has past them stands as not ported.
    pub fn follow(&mut self, names: &[String]) {
        let mut kept = 0;
        while kept < self.pages.len() && kept < names.len() && self.pages[kept].stack_name() == names[kept] {
            kept += 1;
        }
        if kept == self.pages.len() && kept == names.len() {
            return;
        }
        self.pages.truncate(kept.max(1));
        for name in &names[self.pages.len()..] {
            self.pages.push(Box::new(crate::screens::not_ported::NotPorted { name: name.clone() }));
        }
    }

    /// The screen as shown at a size.
    pub fn screen(&self, width: usize, height: usize) -> Vec<Text> {
        self.app.screen_height.set(height);
        let under = self.pages.iter().rposition(|page| !page.is_dialog()).unwrap_or(0);
        let mut lines = page_lines(self.pages[under].as_ref(), &self.app, width, height);
        while lines.len() < height {
            lines.push(Text::default());
        }
        if under + 1 < self.pages.len() {
            // Under a dialog the page's lines reach across the screen in the plain style, as a modal screen lays them.
            for line in lines.iter_mut() {
                let short = width.saturating_sub(line.cell_len());
                let mut padded = Text::default();
                padded.append_text(line);
                padded.append(&" ".repeat(short), crate::drawing::Style::PLAIN);
                *line = padded;
            }
        }
        for dialog in &self.pages[under + 1..] {
            crate::screens::dialogs::laid_over(&mut lines, &dialog.dialog_lines(&self.app, width), width, dialog.dialog_shift());
        }
        lines
    }

    pub fn everywhere(&self) -> Vec<KeyItem> {
        self.everywhere_keys()
    }
}

/// The character a key types, where it types one: a printable letter, mark or space.
fn typed_character(key: &str) -> Option<char> {
    if key == "space" {
        return Some(' ');
    }
    let mut characters = key.chars();
    match (characters.next(), characters.next()) {
        (Some(character), None) if !character.is_control() => Some(character),
        _ => None,
    }
}
