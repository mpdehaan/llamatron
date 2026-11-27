// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Instruments page (the Python screens/set/instruments_page.py and pages/instrument_list.py): each instrument, what it
//! plays through, its MIDI channel and how often the set uses it.

use crate::app::App;
use crate::drawing::Align;
use crate::keybindings::{InstrumentsPage as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::list_page::{named_item_keys, ListColumn, Listing, NamedWords, Row};
use crate::settings::named_in;
use crate::themes::{self, Colour};
use crate::uses::uses_of;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::{Instrument, Item};
use llamatron_model::schema::generated::defaults::DEFAULT_CHANNEL;
use llamatron_model::schema::generated::file_format::{InstrumentSetting, Section, SoundSetting};
use llamatron_strings::{labels, marks, named};

const COLUMNS: [ListColumn; 4] = [
    ListColumn {
        heading: labels::Column::SELECT_INSTRUMENT,
        width: None,
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::DEVICE,
        width: Some(36),
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::CHANNEL,
        width: Some(3),
        align: Align::Right,
    },
    ListColumn {
        heading: labels::Column::USED,
        width: Some(4),
        align: Align::Right,
    },
];
const MIDI: &str = "midi";
const OFF: &str = "off";
const BUILT_IN: &str = "built_in";
const FIRST_ENGINE: &str = "basic";

/// What an instrument is: off, a MIDI device and channel, or a sound llamatron makes; a file that leaves it out means MIDI.
fn kind_of(instrument: &Instrument) -> &str {
    instrument.get_written(InstrumentSetting::KIND).and_then(Data::as_str).unwrap_or(MIDI)
}

/// What an instrument plays through: its synth, nothing, or its MIDI device.
pub fn plays_through(instrument: &Instrument) -> String {
    match kind_of(instrument) {
        BUILT_IN => {
            let engine = instrument
                .get_written(InstrumentSetting::SOUND)
                .and_then(|sound| sound.get(SoundSetting::ENGINE))
                .and_then(Data::as_str)
                .unwrap_or(FIRST_ENGINE);
            named(
                labels::MSG_BUILT_IN_SHOWN,
                &[("engine", named_in(labels::MSG_ENGINE_NAMES, engine).as_str().into())],
            )
        }
        OFF => marks::MSG_INSTRUMENT_OFF_SHOWN.to_string(),
        _ => instrument
            .get_written(InstrumentSetting::DEVICE)
            .and_then(Data::as_str)
            .unwrap_or(marks::MSG_NO_DEVICE_SHOWN)
            .to_string(),
    }
}

fn channel_shown(instrument: &Instrument) -> String {
    if kind_of(instrument) != MIDI {
        return marks::MSG_NO_CHANNEL_SHOWN.to_string();
    }
    let channel = instrument
        .get_written(InstrumentSetting::CHANNEL)
        .and_then(Data::as_whole)
        .map_or(DEFAULT_CHANNEL, |whole| whole as i64);
    channel.to_string()
}

pub struct InstrumentsPage;

impl Listing for InstrumentsPage {
    fn name(&self) -> &'static str {
        "InstrumentsPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::INSTRUMENTS.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::INSTRUMENTS)
    }

    fn columns(&self) -> &[ListColumn] {
        &COLUMNS
    }

    fn rows(&self, app: &App) -> Vec<Row> {
        let setlist = app.document.get_setlist();
        let mut rows = Vec::new();
        for (name, item) in setlist.items(Section::INSTRUMENTS) {
            let Item::Instrument(instrument) = item else { continue };
            let uses = uses_of(setlist, Section::INSTRUMENTS, name).len();
            rows.push((
                name.clone(),
                vec![name.clone(), plays_through(instrument), channel_shown(instrument), uses.to_string()],
            ));
        }
        rows
    }

    fn item_keys(&self, _app: &App) -> Vec<KeyItem> {
        named_item_keys(&Keys::CLASS, &Keys::EDIT)
    }

    /// ENTER opens the instrument's page; adding asks its role, then makes it, off, and opens its page.
    fn named(&self) -> Option<NamedWords> {
        Some(NamedWords {
            section: "instruments",
            rename_prompt: llamatron_strings::messages::MSG_RENAME_INSTRUMENT_PROMPT,
            what: llamatron_strings::legends::MSG_INSTRUMENT_WHAT,
        })
    }

    fn press_row(&mut self, app: &mut App, item: &KeyItem, _key: &str, row: Option<&str>) -> Option<String> {
        if item.is(&Keys::ADD) || item.is(&Keys::ADD_HERE) {
            use llamatron_model::schema::generated::file_format::INSTRUMENT_ROLES;
            let options = INSTRUMENT_ROLES.iter().map(|role| named_in(labels::MSG_ROLE_NAMES, role)).collect();
            let then = Box::new(|app: &mut App, answer: &crate::screens::dialogs::Answer| {
                let crate::screens::dialogs::Answer::Chosen(place) = answer else { return };
                let place = *place;
                let role = INSTRUMENT_ROLES[place];
                let setlist = app.document.get_setlist();
                let taken: Vec<String> = setlist.items(Section::INSTRUMENTS).iter().map(|(name, _)| name.clone()).collect();
                let name = llamatron_model::objects::naming::new_name(llamatron_strings::names::MSG_NEW_INSTRUMENT_WORD, &taken);
                let data = Data::Map(vec![
                    (Data::text(InstrumentSetting::KIND), Data::text("off")),
                    (Data::text(InstrumentSetting::ROLE), Data::text(role)),
                ]);
                let Ok(instrument) = Instrument::from_data(&data) else { return };
                app.document
                    .change_set(|setlist| setlist.add_item(Section::INSTRUMENTS, &name, Item::Instrument(instrument)));
                let page = crate::screens::set::instrument_editor::InstrumentEditor { name };
                app.show_page(Box::new(crate::screens::field_page::FieldPage::new(page)));
            });
            let mut dialog = crate::screens::dialogs::ChoiceDialog::new(llamatron_strings::messages::MSG_NEW_INSTRUMENT_TITLE, options, 0);
            dialog.then = Some(then);
            app.show_page(Box::new(dialog));
            return None;
        }
        if let (true, Some(name)) = (item.is(&Keys::EDIT), row) {
            let page = crate::screens::set::instrument_editor::InstrumentEditor { name: name.to_string() };
            app.show_page(Box::new(crate::screens::field_page::FieldPage::new(page)));
        }
        None
    }
}
