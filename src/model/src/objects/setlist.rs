// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A whole set as it is stored (the Python model/objects/setlist.py, instrument.py): its settings, then its sections in the
//! order a file writes them, each a list of named items or left out: scales, patterns, every generator plugin's section in
//! the order of the plugins' names, the chains, grooves, instruments, and the songs last. Each section is read in that
//! order, so that each can name what the ones before it hold.

use crate::file::corrections::{corrected, Correction};
use crate::file::data::Data;
use crate::file::layout::{as_object_layout, GENERATORS_WITHOUT_PLUGIN};
use crate::file::migrations::migrated;
use crate::objects::holder::{in_table, passed_over, Holder, SongFileError};
use crate::objects::named::{plugin_table, Chain, GeneratorSettings, Groove, NamedScale};
use crate::objects::pattern::Pattern;
use crate::objects::song::{sensible_visualizer, Song};
use crate::schema::checking::{Context, InvalidValue};
use crate::schema::generated::file_format::{InstrumentSetting, Section, SetlistSetting, OPEN_GENERATOR_TYPES, VISUALIZER_NAMES};
use crate::schema::generated::plugins::PLUGINS;
use crate::schema::generated::settings::{INSTRUMENT, SETLIST};
use crate::values::generated::lists::FACTORY_GROOVE_NAMES;
use llamatron_strings::errors;
use llamatron_strings::named;

/// An instrument's settings, and its preview pattern, or none.
#[derive(Clone, Debug, PartialEq)]
pub struct Instrument {
    settings: Holder,
    preview: Option<Pattern>,
}

impl Instrument {
    pub fn from_data(data: &Data) -> Result<Instrument, InvalidValue> {
        if !matches!(data, Data::Map(_)) {
            return Err(InvalidValue::new(named(errors::ERR_INSTRUMENT_EXPECTED_SETTINGS, &[("data", data.into())])));
        }
        let data = passed_over(data, &|name| in_table(INSTRUMENT, name));
        let settings = Holder::read(INSTRUMENT, &data, None, &[InstrumentSetting::PREVIEW])?;
        let preview = match data.get(InstrumentSetting::PREVIEW).filter(|preview| !preview.is_null()) {
            Some(preview) => Some(Pattern::from_data(preview)?),
            None => None,
        };
        Ok(Instrument { settings, preview })
    }

    pub fn get_written(&self, name: &str) -> Option<&Data> {
        self.settings.get(name)
    }

    /// Write one of its settings as a file holds it, or take it out with None.
    pub fn set_written(&mut self, name: &str, value: Option<Data>) {
        self.settings.put(name, value);
    }

    pub fn get_preview(&self) -> Option<&Pattern> {
        self.preview.as_ref()
    }

    /// The preview pattern, to change, or None until one is made.
    pub fn get_preview_mut(&mut self) -> Option<&mut Pattern> {
        self.preview.as_mut()
    }

    /// Give the instrument its starting preview pattern, a drum's for a percussion instrument, unless it has one.
    pub fn make_preview(&mut self, drum: bool) {
        if self.preview.is_none() {
            let data = crate::objects::instrument_previews::starting_preview(drum);
            self.preview = Some(Pattern::from_data(&data).expect("a starting preview is a pattern"));
        }
    }

    /// The settings the file writes, and the preview pattern's data under preview where it has one, last.
    pub fn to_data(&self) -> Data {
        let mut pairs: Vec<(Data, Data)> = self
            .settings
            .written()
            .into_iter()
            .filter(|(key, _)| key.as_str() != Some(InstrumentSetting::PREVIEW))
            .collect();
        if let Some(preview) = &self.preview {
            pairs.push((Data::text(InstrumentSetting::PREVIEW), preview.to_data()));
        }
        Data::Map(pairs)
    }
}

/// An item of one of the set's sections.
#[derive(Clone, Debug, PartialEq)]
pub enum Item {
    Scale(NamedScale),
    Pattern(Pattern),
    Generator(GeneratorSettings),
    Chain(Chain),
    Groove(Groove),
    Instrument(Instrument),
    Song(Box<Song>),
}

impl Item {
    fn to_data(&self) -> Data {
        match self {
            Item::Scale(scale) => scale.to_data(),
            Item::Pattern(pattern) => pattern.to_data(),
            Item::Generator(settings) => settings.to_data(),
            Item::Chain(chain) => chain.to_data(),
            Item::Groove(groove) => groove.to_data(),
            Item::Instrument(instrument) => instrument.to_data(),
            Item::Song(song) => song.to_data(),
        }
    }
}

/// A section: its name, and its items by name in order, or None where the file leaves it out.
#[derive(Clone, Debug, PartialEq)]
pub struct NamedItems {
    pub section: &'static str,
    pub items: Option<Vec<(String, Item)>>,
}

impl NamedItems {
    fn has(&self, name: &str) -> bool {
        self.items.as_ref().is_some_and(|items| items.iter().any(|(found, _)| found == name))
    }

    fn get(&self, name: &str) -> Option<&Item> {
        self.items.as_ref()?.iter().find(|(found, _)| found == name).map(|(_, item)| item)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Setlist {
    settings: Holder,
    sections: Vec<NamedItems>,
}

/// The set's sections, in the order a file writes them.
pub fn setlist_sections() -> Vec<&'static str> {
    let mut sections = vec![Section::SCALES, Section::PATTERNS];
    sections.extend(PLUGINS.iter().map(|plugin| plugin.section));
    sections.extend([Section::CHAINS, Section::GROOVES, Section::INSTRUMENTS, Section::SONGS]);
    sections
}

fn plugin_of_section(section: &str) -> Option<&'static str> {
    PLUGINS.iter().find(|plugin| plugin.section == section).map(|plugin| plugin.name)
}

/// Hidden visualizers made sensible: the modes named, in the modes' order, or nothing for none.
fn sensible_hidden_visualizers(value: Option<Data>) -> Option<Data> {
    let names = value.as_ref().and_then(Data::as_list).unwrap_or(&[]).to_vec();
    let kept: Vec<Data> = VISUALIZER_NAMES
        .iter()
        .map(|name| Data::text(name))
        .filter(|name| names.contains(name))
        .collect();
    (!kept.is_empty()).then_some(Data::List(kept))
}

/// A generator order made sensible: each entry a one-key map of a generator's kind to its name, anything else left out.
fn sensible_generator_order(value: Option<Data>) -> Option<Data> {
    let entries = value.as_ref().and_then(Data::as_list).unwrap_or(&[]).to_vec();
    let kept: Vec<Data> = entries
        .into_iter()
        .filter(|entry| match entry.as_map() {
            Some([(Data::Text(kind), Data::Text(_))]) => kind == "chain" || PLUGINS.iter().any(|plugin| plugin.name == kind),
            _ => false,
        })
        .collect();
    (!kept.is_empty()).then_some(Data::List(kept))
}

impl Setlist {
    /// The set a file's text holds, read as the Python reads it: loaded, migrated, laid out as the objects read it, and every
    /// part checked in the order the file is read.
    pub fn read_text(text: &str, file_stem: Option<String>) -> Result<Setlist, SongFileError> {
        let data = crate::file::data::load(text).map_err(|problem| SongFileError::plain(problem.0))?;
        Setlist::read_data(data, file_stem)
    }

    /// A set from data laid out as a set file is, as a file's text reads to: migrated, then laid out as the objects are.
    pub fn read_data(data: Data, file_stem: Option<String>) -> Result<Setlist, SongFileError> {
        let (moved, _) = migrated(data, file_stem);
        let laid_out = as_object_layout(&moved).map_err(|problem| SongFileError::at(&problem.section, problem.problem))?;
        Setlist::from_data(&laid_out)
    }

    /// A set from a file's text, with each value that cannot be used but has an allowed value near it changed to that value,
    /// and the corrections made: none where the file reads as it is. A problem with no allowed value near it still refuses
    /// the file. The file itself is not changed.
    pub fn read_text_corrected(text: &str, file_stem: Option<String>) -> Result<(Setlist, Vec<Correction>), SongFileError> {
        let data = crate::file::data::load(text).map_err(|problem| SongFileError::plain(problem.0))?;
        let (moved, _) = migrated(data, file_stem);
        let laid_out = as_object_layout(&moved).map_err(|problem| SongFileError::at(&problem.section, problem.problem))?;
        let refusal = match Setlist::from_data(&laid_out) {
            Ok(setlist) => return Ok((setlist, Vec::new())),
            Err(refusal) => refusal,
        };
        let (fixed, corrections) = corrected(&laid_out);
        if corrections.is_empty() {
            return Err(refusal);
        }
        Ok((Setlist::from_data(&fixed)?, corrections))
    }

    pub fn from_data(data: &Data) -> Result<Setlist, SongFileError> {
        let data = if data.is_null() { Data::Map(Vec::new()) } else { data.clone() };
        if !matches!(data, Data::Map(_)) {
            return Err(SongFileError::plain(errors::ERR_NOT_A_SETLIST.to_string()));
        }
        let sections = setlist_sections();
        let data = passed_over(&data, &|name| {
            in_table(SETLIST, name) || sections.contains(&name) || name == OPEN_GENERATOR_TYPES || name == GENERATORS_WITHOUT_PLUGIN
        });
        let mut settings = Holder::read(SETLIST, &data, None, &[]).map_err(|problem| SongFileError::plain(problem.message))?;
        settings.put(
            SetlistSetting::VISUALIZER,
            sensible_visualizer(settings.get(SetlistSetting::VISUALIZER).cloned()),
        );
        settings.put(
            SetlistSetting::HIDDEN_VISUALIZERS,
            sensible_hidden_visualizers(settings.get(SetlistSetting::HIDDEN_VISUALIZERS).cloned()),
        );
        settings.put(
            SetlistSetting::GENERATOR_ORDER,
            sensible_generator_order(settings.get(SetlistSetting::GENERATOR_ORDER).cloned()),
        );
        let mut setlist = Setlist {
            settings,
            sections: sections.iter().map(|section| NamedItems { section, items: None }).collect(),
        };
        for place in 0..sections.len() {
            let section = sections[place];
            let Some(held) = data.get(section) else { continue };
            if section == Section::GROOVES {
                checked_groove_names(held).map_err(|(name, problem)| SongFileError::at(&setlist.place(section, &name), problem))?;
            }
            let mut items = Vec::new();
            for (name, item) in held.as_map().unwrap_or(&[]) {
                let name = name.python_str();
                let read = setlist
                    .read_item(section, item)
                    .map_err(|problem| SongFileError::at(&setlist.place(section, &name), problem))?;
                items.push((name, read));
            }
            setlist.sections[place].items = Some(items);
        }
        Ok(setlist)
    }

    fn place(&self, section: &str, name: &str) -> String {
        format!("{section} ({name})")
    }

    fn read_item(&self, section: &str, data: &Data) -> Result<Item, InvalidValue> {
        Ok(match section {
            Section::SCALES => Item::Scale(NamedScale::from_data(data)?),
            Section::PATTERNS => Item::Pattern(Pattern::from_data(data)?),
            Section::CHAINS => Item::Chain(Chain::from_data(data)?),
            Section::GROOVES => Item::Groove(Groove::from_data(data)?),
            Section::INSTRUMENTS => Item::Instrument(Instrument::from_data(data)?),
            Section::SONGS => Item::Song(Box::new(Song::from_data(data, self)?)),
            other => {
                let table = plugin_of_section(other).and_then(plugin_table).unwrap_or(&[]);
                Item::Generator(GeneratorSettings::from_data(table, data)?)
            }
        })
    }

    fn section(&self, section: &str) -> Option<&NamedItems> {
        self.sections.iter().find(|items| items.section == section)
    }

    pub fn get_written(&self, name: &str) -> Option<&Data> {
        self.settings.get(name)
    }

    /// A section's items by name, in order; none for a section the file left out.
    pub fn items(&self, section: &str) -> &[(String, Item)] {
        self.section(section).and_then(|items| items.items.as_deref()).unwrap_or(&[])
    }

    pub fn get_item(&self, section: &str, name: &str) -> Option<&Item> {
        self.section(section)?.get(name)
    }

    /// The pattern of a name, or an instrument's preview pattern by its key, to change.
    pub fn get_pattern_mut(&mut self, name: &str) -> Option<&mut Pattern> {
        if let Some(instrument) = crate::objects::instrument_previews::preview_instrument(name) {
            return match self.get_item_mut(Section::INSTRUMENTS, instrument)? {
                Item::Instrument(instrument) => instrument.get_preview_mut(),
                _ => None,
            };
        }
        match self.get_item_mut(Section::PATTERNS, name)? {
            Item::Pattern(pattern) => Some(pattern),
            _ => None,
        }
    }

    pub fn get_item_mut(&mut self, section: &str, name: &str) -> Option<&mut Item> {
        let held = self.sections.iter_mut().find(|held| held.section == section)?;
        held.items.as_mut()?.iter_mut().find(|(found, _)| found == name).map(|(_, item)| item)
    }

    /// Add an item at the end of its section, which the set then holds even where its file left the section out.
    pub fn add_item(&mut self, section: &str, name: &str, item: Item) {
        if let Some(held) = self.sections.iter_mut().find(|held| held.section == section) {
            held.items.get_or_insert_with(Vec::new).push((name.to_string(), item));
        }
    }

    /// Set one of the set's own settings, or leave it out with None.
    pub fn set_written(&mut self, name: &str, value: Option<Data>) {
        self.settings.put(name, value);
    }

    /// The set's data as the objects write it: its settings, then each section the file had.
    pub fn to_data(&self) -> Data {
        let mut pairs = self.settings.written();
        for section in &self.sections {
            if let Some(items) = &section.items {
                pairs.push((
                    Data::text(section.section),
                    Data::Map(items.iter().map(|(name, item)| (Data::text(name), item.to_data())).collect()),
                ));
            }
        }
        Data::Map(pairs)
    }
}

/// Refuse a groove of the set's own named as a factory groove is, before any groove is read, with the name refused.
fn checked_groove_names(grooves: &Data) -> Result<(), (String, InvalidValue)> {
    for (name, _) in grooves.as_map().unwrap_or(&[]) {
        let name = name.python_str();
        if FACTORY_GROOVE_NAMES.contains(&name.as_str()) {
            let names = crate::schema::checking::listed(FACTORY_GROOVE_NAMES);
            let problem = named(errors::ERR_FACTORY_GROOVE_NAME, &[("name", name.as_str().into()), ("names", names.into())]);
            return Err((name, InvalidValue::new(problem)));
        }
    }
    Ok(())
}

impl Context for Setlist {
    fn has_scale(&self, name: &str) -> bool {
        self.section(Section::SCALES).is_some_and(|items| items.has(name))
    }
    fn has_pattern(&self, name: &str) -> bool {
        self.section(Section::PATTERNS).is_some_and(|items| items.has(name))
    }
    fn is_drum_pattern(&self, name: &str) -> bool {
        matches!(self.get_item(Section::PATTERNS, name), Some(Item::Pattern(pattern)) if pattern.is_drum())
    }
    fn has_track(&self, _: &str) -> bool {
        false
    }
    fn has_instrument(&self, name: &str) -> bool {
        self.section(Section::INSTRUMENTS).is_some_and(|items| items.has(name))
    }
    fn has_groove(&self, name: &str) -> bool {
        FACTORY_GROOVE_NAMES.contains(&name) || self.section(Section::GROOVES).is_some_and(|items| items.has(name))
    }
    fn has_generator_named(&self, name: &str) -> bool {
        PLUGINS
            .iter()
            .map(|plugin| plugin.section)
            .chain([Section::CHAINS])
            .any(|section| self.section(section).is_some_and(|items| items.has(name)))
    }
}
