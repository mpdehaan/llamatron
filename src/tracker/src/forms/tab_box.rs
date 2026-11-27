// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A settings page's tab box as plain nodes (the Python forms/tab_box.py): its tabs, each with fields across its top and
//! columns under headings, and where the cursor goes from a field among the spots the tracker drew them at.

use crate::forms::nodes::Field;
use llamatron_strings::{marks, named};

/// Where the cursor is on the row of tabs, or past the box's foot.
pub const ON_TAB_ROW: i64 = -1;
pub const BELOW_BOX: i64 = -2;
/// The band of the fields across a tab's top.
pub const TOP_BAND: i64 = -1;

#[derive(Clone, Debug)]
pub struct TabColumn {
    pub heading: Option<String>,
    pub fields: Vec<Field>,
    /// The fields drawn beside some of its fields, in a narrow column of their own inside the same box.
    pub beside: Vec<Beside>,
    /// Whether it stands in a row of its own under the row of columns, as a button for the whole tab does; every other
    /// column keeps to the one row, which scrolls sideways where it does not fit.
    pub footer: bool,
    pub boxed: bool,
}

/// A field drawn beside one of a column's fields, on its line, such as a Mod Matrix slot's CC number beside its Source;
/// where the field would mean nothing, its label stands over a dash and the cursor passes it by.
#[derive(Clone, Debug)]
pub struct Beside {
    /// The place among the column's fields of the field it stands beside.
    pub of: usize,
    pub label: String,
    pub field: Option<Field>,
}

impl TabColumn {
    /// The fields beside its own that the cursor stops on, in order, after its own fields.
    pub fn fields_beside(&self) -> impl Iterator<Item = &Field> {
        self.beside.iter().filter_map(|beside| beside.field.as_ref())
    }

    /// How many fields the cursor stops on in it, its own and those beside.
    pub fn field_count(&self) -> usize {
        self.fields.len() + self.fields_beside().count()
    }

    pub fn new(heading: Option<&str>, fields: Vec<Field>) -> TabColumn {
        TabColumn {
            heading: heading.map(str::to_string),
            fields,
            beside: Vec::new(),
            footer: false,
            boxed: false,
        }
    }
}

/// Where a field of a tab is drawn: its band of columns, its column among the band's, and the line its cursor stands on.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Spot {
    pub band: i64,
    pub column: i64,
    pub line: i64,
}

#[derive(Clone, Debug, Default)]
pub struct Tab {
    pub label: String,
    pub top: Vec<Field>,
    pub columns: Vec<TabColumn>,
    /// Whether the built-in generator it shows is on, or None for a tab that shows none.
    pub on: Option<bool>,
    pub remarks: Vec<String>,
    pub not_ready: bool,
}

impl Tab {
    pub fn new(label: &str, columns: Vec<TabColumn>) -> Tab {
        Tab {
            label: label.to_string(),
            columns,
            ..Tab::default()
        }
    }

    /// The tab's fields in the order the cursor goes through them: across the top, then column by column.
    pub fn every_field(&self) -> Vec<&Field> {
        let mut fields: Vec<&Field> = self.top.iter().collect();
        for column in &self.columns {
            fields.extend(column.fields.iter());
            fields.extend(column.fields_beside());
        }
        fields
    }

    pub fn field_count(&self) -> usize {
        self.top.len() + self.columns.iter().map(TabColumn::field_count).sum::<usize>()
    }

    pub fn is_dim(&self) -> bool {
        self.on == Some(false) || self.not_ready
    }

    /// The tab's name as its tab shows it, with the mark of its generator being on or off where it shows one.
    pub fn shown_name(&self) -> String {
        match self.on {
            None => self.label.clone(),
            Some(on) => {
                let mark = if on { marks::MSG_TOGGLE_ON } else { marks::MSG_FIELD_TOGGLE_OFF };
                named(marks::MSG_TAB_WITH_MARK, &[("name", self.label.as_str().into()), ("mark", mark.into())])
            }
        }
    }
}

#[derive(Clone, Debug)]
pub struct TabBox {
    pub label: String,
    pub tabs: Vec<Tab>,
}

impl TabBox {
    /// The place of the tab of a name, or the first's where none has it.
    pub fn tab_named(&self, name: Option<&str>) -> usize {
        self.tabs.iter().position(|tab| Some(tab.label.as_str()) == name).unwrap_or(0)
    }
}

/// The columns of a run of sections, each heading's fields a column under the heading's name.
pub fn columns_of_sections(fields: Vec<Field>) -> Vec<TabColumn> {
    let mut columns = Vec::new();
    let mut current = TabColumn::new(None, Vec::new());
    for field in fields {
        if field.is_heading() {
            if !current.fields.is_empty() {
                columns.push(current);
            }
            current = TabColumn::new(Some(&field.label), Vec::new());
        } else {
            current.fields.push(field);
        }
    }
    if !current.fields.is_empty() {
        columns.push(current);
    }
    columns
}

fn column_places(spots: &[Spot], band: i64, column: i64) -> Vec<usize> {
    (0..spots.len())
        .filter(|place| spots[*place].band == band && spots[*place].column == column)
        .collect()
}

fn bands_in(spots: &[Spot]) -> Vec<i64> {
    let mut bands: Vec<i64> = spots.iter().map(|spot| spot.band).collect();
    bands.sort();
    bands.dedup();
    bands
}

fn column_near(spots: &[Spot], band: i64, column: i64) -> i64 {
    let mut columns: Vec<i64> = spots.iter().filter(|spot| spot.band == band).map(|spot| spot.column).collect();
    columns.sort();
    columns.dedup();
    if columns.contains(&column) {
        column
    } else {
        *columns.last().unwrap_or(&0)
    }
}

/// Where Down leads from the field at a place.
pub fn spot_below(spots: &[Spot], here: usize) -> i64 {
    let spot = spots[here];
    if let Some(later) = column_places(spots, spot.band, spot.column).into_iter().find(|place| *place > here) {
        return later as i64;
    }
    let Some(band) = bands_in(spots).into_iter().find(|band| *band > spot.band) else {
        return BELOW_BOX;
    };
    column_places(spots, band, column_near(spots, band, spot.column))[0] as i64
}

/// Where Up leads from the field at a place.
pub fn spot_above(spots: &[Spot], here: usize) -> i64 {
    let spot = spots[here];
    if let Some(earlier) = column_places(spots, spot.band, spot.column).into_iter().rfind(|place| *place < here) {
        return earlier as i64;
    }
    let Some(band) = bands_in(spots).into_iter().rfind(|band| *band < spot.band) else {
        return ON_TAB_ROW;
    };
    *column_places(spots, band, column_near(spots, band, spot.column))
        .last()
        .expect("a band has fields") as i64
}

fn nearest(spots: &[Spot], places: Vec<usize>, line: i64) -> usize {
    places
        .into_iter()
        .min_by_key(|place| ((spots[*place].line - line).abs(), spots[*place].line))
        .expect("places to choose from")
}

/// Where Left or Right leads from the field at a place: the nearest field of the column beside, or the same place.
pub fn spot_beside(spots: &[Spot], here: usize, direction: i64) -> usize {
    let spot = spots[here];
    let places = column_places(spots, spot.band, spot.column + direction);
    if places.is_empty() {
        return here;
    }
    nearest(spots, places, spot.line)
}

/// The place of the field standing where a spot of another tab stood.
pub fn spot_like(spots: &[Spot], spot: Spot) -> usize {
    let mut bands = bands_in(spots);
    bands.sort_by_key(|band| (band - spot.band).abs());
    for band in bands {
        let same = column_places(spots, band, spot.column);
        if !same.is_empty() {
            return nearest(spots, same, spot.line);
        }
    }
    0
}

pub fn has_columns_beside(spots: &[Spot], here: usize) -> bool {
    let spot = spots[here];
    spots.iter().any(|other| other.band == spot.band && other.column != spot.column)
}

/// Where Up from under the box leads: the last field of the first column of the last band.
pub fn spot_from_below(spots: &[Spot]) -> usize {
    let band = *bands_in(spots).last().expect("a tab with fields");
    *column_places(spots, band, 0).last().expect("a band's first column")
}
