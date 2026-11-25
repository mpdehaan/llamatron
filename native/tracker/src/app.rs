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
#[derive(Default)]
pub struct Session {
    /// The settings pages' sections open now, by name.
    pub open_field_sections: std::collections::HashSet<String>,
    /// The tab each kind of page with a tab box last showed, by the page's name.
    pub chosen_tabs: std::collections::HashMap<String, String>,
}

/// What a page asks of the stack, done once its key is handled.
pub enum Request {
    Open(Box<dyn Page>),
    Back,
}

/// What every page reaches: the set, the status line, what the session remembers, and the requests of the key in hand.
pub struct App {
    pub document: Document,
    pub status: StatusLine,
    pub session: Session,
    /// Whether FluidSynth is installed to play General MIDI, which offers Listen on a pattern whose song names no Preview
    /// instrument.
    pub fluidsynth_installed: bool,
    requests: Vec<Request>,
}

impl App {
    pub fn new(document: Document) -> App {
        App {
            document,
            status: StatusLine::default(),
            session: Session::default(),
            fluidsynth_installed: false,
            requests: Vec::new(),
        }
    }

    pub fn show_page(&mut self, page: Box<dyn Page>) {
        self.requests.push(Request::Open(page));
    }

    pub fn go_back(&mut self) {
        self.requests.push(Request::Back);
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

    pub fn top(&self) -> &dyn Page {
        self.pages.last().expect("the main screen is never closed").as_ref()
    }

    /// The keys that work on every page, before the page's own.
    fn everywhere_keys(&self) -> Vec<KeyItem> {
        PageKeys::EVERYWHERE.iter().map(|binding| KeyItem::of(&PageKeys::CLASS, binding)).collect()
    }

    /// Press a key into the page on top: an everywhere key first, then the page's own.
    pub fn press(&mut self, key: &str) {
        let page = self.pages.last_mut().expect("the main screen is never closed");
        let everywhere = PageKeys::EVERYWHERE.iter().map(|binding| KeyItem::of(&PageKeys::CLASS, binding));
        let table: Vec<KeyItem> = everywhere.chain(page.page_key_table(&self.app)).collect();
        let Some(item) = table.into_iter().find(|item| item.keys.contains(&key)) else {
            return;
        };
        self.app.status.clear();
        if PageKeys::EVERYWHERE.iter().any(|binding| std::ptr::eq(*binding, item.binding)) {
            // The everywhere keys are not ported yet; they do nothing.
            return;
        }
        page.press(&mut self.app, &item, key);
        let requests = std::mem::take(&mut self.app.requests);
        for request in requests {
            match request {
                Request::Open(page) => self.pages.push(page),
                Request::Back => {
                    if self.pages.len() > 1 {
                        self.pages.pop();
                    }
                }
            }
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
        page_lines(self.top(), &self.app, width, height)
    }

    pub fn everywhere(&self) -> Vec<KeyItem> {
        self.everywhere_keys()
    }
}
