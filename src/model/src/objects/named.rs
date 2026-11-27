// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The small things a set names: a scale (model/objects/named_scale.py), a groove (groove.py), a chain of generators
//! (chain.py), and a generator's settings, kept as the file writes them (engine/generators/settings_base.py).

use crate::file::data::Data;
use crate::objects::holder::{in_table, passed_over};
use crate::schema::checking::{check, InvalidValue};
use crate::schema::generated::file_format::{ChainSetting, GrooveSetting, ScaleSetting};
use crate::schema::generated::settings::{self as tables, Setting};
use llamatron_strings::errors;
use llamatron_strings::named;

/// A scale the set names: a root and a kind.
#[derive(Clone, Debug, PartialEq)]
pub struct NamedScale {
    root: Data,
    kind: Data,
}

impl NamedScale {
    pub fn from_data(data: &Data) -> Result<NamedScale, InvalidValue> {
        let pairs = data.as_map().unwrap_or(&[]);
        let names: Vec<&str> = pairs.iter().filter_map(|(key, _)| key.as_str()).collect();
        let exact = names.len() == 2 && names.contains(&ScaleSetting::ROOT) && names.contains(&ScaleSetting::TYPE);
        if !exact {
            return Err(InvalidValue::new(named(errors::ERR_EXPECTED_ROOT_AND_TYPE, &[("data", data.into())])));
        }
        for setting in tables::NAMED_SCALE {
            if let Some(value) = data.get(setting.name) {
                check(setting, value, None)?;
            }
        }
        Ok(NamedScale {
            root: data.get(ScaleSetting::ROOT).cloned().unwrap_or(Data::Null),
            kind: data.get(ScaleSetting::TYPE).cloned().unwrap_or(Data::Null),
        })
    }

    pub fn get_root(&self) -> &Data {
        &self.root
    }

    pub fn get_kind(&self) -> &Data {
        &self.kind
    }

    pub fn set_root(&mut self, root: &str) {
        self.root = Data::text(root);
    }

    pub fn set_kind(&mut self, kind: &str) {
        self.kind = Data::text(kind);
    }

    pub fn to_data(&self) -> Data {
        Data::Map(vec![
            (Data::text(ScaleSetting::ROOT), self.root.clone()),
            (Data::text(ScaleSetting::TYPE), self.kind.clone()),
        ])
    }
}

/// A groove: its cells, and how long each is, or nothing for the default.
#[derive(Clone, Debug, PartialEq)]
pub struct Groove {
    cells: Data,
    cell_length: Option<Data>,
}

impl Groove {
    pub fn from_data(data: &Data) -> Result<Groove, InvalidValue> {
        if !matches!(data, Data::Map(_)) {
            return Err(InvalidValue::new(named(errors::ERR_GROOVE_EXPECTED_SETTINGS, &[("data", data.into())])));
        }
        let data = passed_over(data, &|name| in_table(tables::GROOVE, name));
        let cells = data.get(GrooveSetting::CELLS).cloned().unwrap_or(Data::Null);
        for setting in tables::GROOVE {
            let value = data.get(setting.name);
            if setting.name == GrooveSetting::CELLS || value.is_some() {
                check(setting, value.unwrap_or(&Data::Null), None)?;
            }
        }
        Ok(Groove {
            cells,
            cell_length: data.get(GrooveSetting::CELL_LENGTH).cloned(),
        })
    }

    pub fn get_cells(&self) -> &Data {
        &self.cells
    }

    pub fn get_cell_length(&self) -> Option<&Data> {
        self.cell_length.as_ref()
    }

    /// Set how long a cell is, as the file writes it, such as 1/8; the default length is left out of the file.
    pub fn set_cell_length(&mut self, length: &str) {
        self.cell_length = (length != crate::schema::generated::defaults::DEFAULT_GROOVE_CELL_LENGTH).then(|| Data::text(length));
    }

    pub fn to_data(&self) -> Data {
        let mut pairs = vec![(Data::text(GrooveSetting::CELLS), self.cells.clone())];
        if let Some(length) = &self.cell_length {
            pairs.push((Data::text(GrooveSetting::CELL_LENGTH), length.clone()));
        }
        Data::Map(pairs)
    }
}

/// A chain: its steps, each a generator's kind and name.
#[derive(Clone, Debug, PartialEq)]
pub struct Chain {
    steps: Vec<(String, String)>,
}

impl Chain {
    pub fn from_data(data: &Data) -> Result<Chain, InvalidValue> {
        // A chain written as a mapping holds its steps under steps; an older file's other settings there are passed over.
        let steps_data = match data {
            Data::Map(_) => data.get(ChainSetting::STEPS).unwrap_or(&Data::Null),
            _ => data,
        };
        let Some(listed) = steps_data.as_list() else {
            return Err(InvalidValue::new(errors::ERR_EXPECTED_LIST.to_string()));
        };
        let mut steps = Vec::new();
        for step in listed {
            match step.as_map() {
                Some([(Data::Text(kind), Data::Text(name))]) => steps.push((kind.clone(), name.clone())),
                _ => return Err(InvalidValue::new(named(errors::ERR_ONE_GENERATOR_PER_STEP, &[("step", step.into())]))),
            }
        }
        Ok(Chain { steps })
    }

    pub fn get_steps(&self) -> &[(String, String)] {
        &self.steps
    }

    /// Add a step at the end: a generator of a kind, by its name.
    pub fn add_step(&mut self, kind: &str, name: &str) {
        self.steps.push((kind.to_string(), name.to_string()));
    }

    /// Make the step at a place another generator, where there is a step there.
    pub fn set_step(&mut self, place: usize, kind: &str, name: &str) {
        if let Some(step) = self.steps.get_mut(place) {
            *step = (kind.to_string(), name.to_string());
        }
    }

    /// Put the same generator again right after the step at a place.
    pub fn copy_step(&mut self, place: usize) {
        if let Some(step) = self.steps.get(place).cloned() {
            self.steps.insert(place + 1, step);
        }
    }

    /// Take out the step at a place.
    pub fn remove_step(&mut self, place: usize) {
        if place < self.steps.len() {
            self.steps.remove(place);
        }
    }

    /// Move the step at a place up or down the chain, and say whether it moved: it stops at either end.
    pub fn move_step(&mut self, place: usize, offset: i64) -> bool {
        let target = place as i64 + offset;
        if place >= self.steps.len() || !(0..self.steps.len() as i64).contains(&target) {
            return false;
        }
        let step = self.steps.remove(place);
        self.steps.insert(target as usize, step);
        true
    }

    pub fn to_data(&self) -> Data {
        Data::List(
            self.steps
                .iter()
                .map(|(kind, name)| Data::Map(vec![(Data::text(kind), Data::text(name))]))
                .collect(),
        )
    }
}

/// A generator's settings, kept as the file writes them, its unknown names passed over.
#[derive(Clone, Debug, PartialEq)]
pub struct GeneratorSettings {
    table: &'static [Setting],
    data: Data,
}

/// A plugin's table of settings by its name.
pub fn plugin_table(plugin: &str) -> Option<&'static [Setting]> {
    Some(match plugin {
        "arp" => tables::ARP_PLUGIN,
        "chords" => tables::CHORDS_PLUGIN,
        "drift" => tables::DRIFT_PLUGIN,
        "guitarify" => tables::GUITARIFY_PLUGIN,
        "hocket" => tables::HOCKET_PLUGIN,
        "musician" => tables::MUSICIAN_PLUGIN,
        "phrasing" => tables::PHRASING_PLUGIN,
        "shapes" => tables::SHAPES_PLUGIN,
        "timing" => tables::TIMING_PLUGIN,
        _ => return None,
    })
}

/// The octaves the Chords generator voices its chords between unless its settings say: from 4 to 6.
pub const DEFAULT_VOICING_LOWEST_OCTAVE: i64 = 4;
pub const DEFAULT_VOICING_HIGHEST_OCTAVE: i64 = 6;
/// The Chords generator's settings of the octaves it voices between.
const VOICING_LOWEST_OCTAVE: &str = "lowest_octave";
const VOICING_HIGHEST_OCTAVE: &str = "highest_octave";

/// Refuse a Chords generator voicing from an octave above the one it voices up to, once each is checked on its own.
fn checked_voicing_range(data: &Data) -> Result<(), InvalidValue> {
    let octave = |name: &str, default: i64| data.get(name).and_then(Data::as_whole).map_or(default, |octave| octave as i64);
    let lowest = octave(VOICING_LOWEST_OCTAVE, DEFAULT_VOICING_LOWEST_OCTAVE);
    let highest = octave(VOICING_HIGHEST_OCTAVE, DEFAULT_VOICING_HIGHEST_OCTAVE);
    if lowest > highest {
        return Err(InvalidValue::new(named(
            errors::ERR_VOICE_LEADING_RANGE,
            &[("lowest", lowest.into()), ("highest", highest.into())],
        )));
    }
    Ok(())
}

impl GeneratorSettings {
    pub fn from_data(table: &'static [Setting], data: &Data) -> Result<GeneratorSettings, InvalidValue> {
        let data = if data.is_null() { Data::Map(Vec::new()) } else { data.clone() };
        if !matches!(data, Data::Map(_)) {
            return Err(InvalidValue::new(named(errors::ERR_NOT_SETTINGS, &[("value", (&data).into())])));
        }
        let data = passed_over(&data, &|name| in_table(table, name));
        for (key, value) in data.as_map().unwrap_or(&[]) {
            if let Some(setting) = table.iter().find(|setting| Some(setting.name) == key.as_str()) {
                check(setting, value, None)?;
            }
        }
        if std::ptr::eq(table, tables::CHORDS_PLUGIN) {
            checked_voicing_range(&data)?;
        }
        Ok(GeneratorSettings { table, data })
    }

    pub fn get_written(&self, name: &str) -> Option<&Data> {
        self.data.get(name)
    }

    pub fn get_table(&self) -> &'static [Setting] {
        self.table
    }

    /// Its settings as written, a mapping by name.
    pub fn written_data(&self) -> &Data {
        &self.data
    }

    /// Set one setting, or leave it out with None, at its place where it is written and at the end where it is not.
    pub fn set_written(&mut self, name: &str, value: Option<Data>) {
        match value {
            Some(value) => self.data.set(name, value),
            None => {
                if let Data::Map(pairs) = &mut self.data {
                    pairs.retain(|(key, _)| key.as_str() != Some(name));
                }
            }
        }
    }

    pub fn to_data(&self) -> Data {
        self.data.clone()
    }
}
