// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! How a settings page's fields are drawn (the Python renderers/fields.py, tab_box.py and components/button_row.py): a
//! setting as its label and value on one line with the cursor's mark before it, a button boxed, a heading, a row of cells,
//! and a tab box with its row of tabs over the chosen tab's settings.

use crate::drawing::{cursor_mark, padded, BoxCharacters as Box, Style, INDENT, SPACE};
use crate::forms::nodes::{Drawn, Field};
use crate::forms::tab_box::{Spot, Tab, TabBox, ON_TAB_ROW, TOP_BAND};
use crate::text::Text;
#[cfg(test)]
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_strings::{labels, legends, marks, named};

const CELL_GAP: &str = "  ";
const COLUMN_GAP: &str = INDENT;
const MOST_REMARKS: usize = 3;
const SIDES: usize = 2;
const INSET: &str = SPACE;
const TAB_ROW_LINES: usize = 3;
const NAME_LINE: usize = 1;
const SPACE_UNDER: usize = 1;
const STRIP_PAD: &str = "    ";
const STRIP_LABEL_WIDTH: usize = 7;
const STRIP_CELL_WIDTH: usize = 5;

/// What drawing a field asks of its page: the cell the cursor is on in a row of cells, and whether a heading is open.
pub struct Looks<'a> {
    pub cell: usize,
    pub open: &'a dyn Fn(&Field) -> bool,
}

fn ljust(text: &str, width: usize) -> String {
    format!("{text:<width$}")
}

/// The lines a field is drawn as, the cursor on it where here is true, its label as wide as label_width.
pub fn field_lines(field: &Field, looks: &Looks, here: bool, label_width: usize, width: usize) -> Vec<Text> {
    match &field.drawn {
        Drawn::Button => {
            let row = button_row(&[(field.key_name.clone(), field.label.clone())], if here { Some(0) } else { None });
            row.into_iter().map(|line| indented(&line)).collect()
        }
        Drawn::Heading => {
            let mut line = Text::default();
            line.append(cursor_mark(here), Style::PLAIN);
            line.append(&ljust(&field.drawn_label((looks.open)(field)), label_width), Style::BOLD);
            line.append(&padded(&field.heading_value()), Style::DIM);
            vec![line]
        }
        Drawn::Cells => vec![cells_line(field, looks, here, label_width)],
        Drawn::TableRow { widths } => vec![table_row_line(field, looks, here, label_width, widths)],
        Drawn::CaptionedTableRow { widths, caption, headings } => {
            let mut line = Text::default();
            line.append(cursor_mark(false), Style::PLAIN);
            line.append(&ljust(caption, label_width), Style::BOLD);
            for (place, heading) in headings.iter().enumerate() {
                line.append(&ljust(&padded(heading), widths[place] + 2), Style::BOLD);
                line.append(CELL_GAP, Style::PLAIN);
            }
            vec![line, table_row_line(field, looks, here, label_width, widths)]
        }
        Drawn::Strip { lit } => strip_lines(field, looks, here, width, *lit),
        Drawn::StatementRow { first, last } => statement_row_lines(field, looks, here, *first, *last),
        Drawn::SettingLine | Drawn::TabRow => {
            let mut line = Text::default();
            line.append(cursor_mark(here), Style::PLAIN);
            line.append(&ljust(&field.drawn_label(false), label_width), if here { Style::BOLD } else { Style::PLAIN });
            line.append(&padded(field.value()), Style::PLAIN);
            if field.enter_what == legends::What::CHOOSE {
                line.append(marks::MSG_PICKER_MARK, Style::DIM);
            }
            vec![line]
        }
    }
}

/// Each column's width in a table of statements: its widest value, padded, with room for the picker's mark.
fn statement_cell_widths() -> Vec<usize> {
    let room = padded("").chars().count() + padded(marks::MSG_PICKER_MARK).chars().count() - 1;
    crate::forms::statements::part_widths().iter().map(|width| room + width).collect()
}

fn statement_rule(left: &str, joint: &str, right: &str) -> Text {
    let widths = statement_cell_widths();
    let parts: Vec<String> = widths.iter().map(|width| Box::RULE.repeat(*width)).collect();
    Text::plain(&format!("{INDENT}{left}{}{right}", parts.join(joint)))
}

fn statement_row_lines(row: &Field, looks: &Looks, here: bool, first: bool, last: bool) -> Vec<Text> {
    let mut line = Text::default();
    line.append(cursor_mark(here), Style::PLAIN);
    line.append(Box::BAR, Style::PLAIN);
    for (place, cell_width) in statement_cell_widths().into_iter().enumerate() {
        let mut cell = Text::default();
        if let Some(field) = row.cells.get(place) {
            let on_cell = here && place == looks.cell.min(row.cells.len() - 1);
            cell.append(&padded(field.value().trim_end()), if on_cell { Style::REVERSE } else { Style::PLAIN });
            if field.enter_what == legends::What::CHOOSE {
                cell.append(marks::MSG_PICKER_MARK, Style::DIM);
            }
        }
        let filled = cell.cell_len();
        line.append_text(&cell);
        line.append(&" ".repeat(cell_width.saturating_sub(filled)), Style::PLAIN);
        line.append(Box::BAR, Style::PLAIN);
    }
    let under = if last {
        statement_rule(Box::BOTTOM_LEFT, Box::BOTTOM_TEE, Box::BOTTOM_RIGHT)
    } else {
        statement_rule(Box::LEFT_TEE, Box::CROSS, Box::RIGHT_TEE)
    };
    if first {
        vec![statement_rule(Box::TOP_LEFT, Box::TOP_TEE, Box::TOP_RIGHT), line, under]
    } else {
        vec![line, under]
    }
}

fn indented(line: &Text) -> Text {
    let mut result = Text::plain(INDENT);
    result.append_text(line);
    result
}

fn cells_line(row: &Field, looks: &Looks, here: bool, label_width: usize) -> Text {
    let mut line = Text::default();
    line.append(cursor_mark(here), Style::PLAIN);
    line.append(&ljust(&row.drawn_label(false), label_width), if here { Style::BOLD } else { Style::PLAIN });
    for (place, cell) in row.cells.iter().enumerate() {
        let on_cell = here && place == looks.cell.min(row.cells.len() - 1);
        line.append(&padded(cell.value()), if on_cell { Style::REVERSE } else { Style::PLAIN });
        if cell.enter_what == legends::What::CHOOSE {
            line.append(marks::MSG_PICKER_MARK, Style::DIM);
        }
        line.append(CELL_GAP, Style::PLAIN);
    }
    line
}

fn table_row_line(row: &Field, looks: &Looks, here: bool, label_width: usize, widths: &[usize]) -> Text {
    let mut line = Text::default();
    line.append(cursor_mark(here), Style::PLAIN);
    line.append(&ljust(&row.drawn_label(false), label_width), if here { Style::BOLD } else { Style::PLAIN });
    for (place, cell) in row.cells.iter().enumerate() {
        let on_cell = here && place == looks.cell.min(row.cells.len() - 1);
        line.append(
            &ljust(&padded(cell.value()), widths[place] + 2),
            if on_cell { Style::REVERSE } else { Style::PLAIN },
        );
        line.append(CELL_GAP, Style::PLAIN);
    }
    line
}

fn slot_text(value: &str) -> String {
    named(marks::MSG_DRAW_STRIP_CELL, &[(fill::VALUE, value.into())])
}

fn strip_lines(strip: &Field, looks: &Looks, here: bool, width: usize, lit: Option<usize>) -> Vec<Text> {
    let count = strip.cells.len();
    let room = width.saturating_sub(STRIP_PAD.len() + STRIP_LABEL_WIDTH + 2) / (STRIP_CELL_WIDTH + 1);
    let shown = room.min(count).max(1);
    let cell = looks.cell.min(count.saturating_sub(1));
    let first = if here {
        (cell as i64 - (shown / 2) as i64).min(count as i64 - shown as i64).max(0) as usize
    } else {
        0
    };
    let cells = Box::RULE.repeat(STRIP_CELL_WIDTH);
    let edge = |left: &str, tee: &str, right: &str| {
        let joined = vec![cells.clone(); shown].join(tee);
        Text::styled(
            &format!("{STRIP_PAD}{left}{}{tee}{joined}{right}", Box::RULE.repeat(STRIP_LABEL_WIDTH)),
            Style::DIM,
        )
    };
    let top = edge(Box::TOP_LEFT, Box::TOP_TEE, Box::TOP_RIGHT);
    let rule = edge(Box::LEFT_TEE, Box::CROSS, Box::RIGHT_TEE);
    let bottom = edge(Box::BOTTOM_LEFT, Box::BOTTOM_TEE, Box::BOTTOM_RIGHT);
    let mut numbers = Text::plain(STRIP_PAD);
    numbers.append(
        &format!("{}{}", Box::BAR, ljust(&padded(labels::MSG_DRAW_STRIP_SLOT_ROW), STRIP_LABEL_WIDTH)),
        Style::DIM,
    );
    let mark = cursor_mark(here);
    let mut values = Text::plain(&format!("{mark}{}", &STRIP_PAD[mark.chars().count().min(STRIP_PAD.len())..]));
    values.append(
        &format!("{}{}", Box::BAR, ljust(&padded(labels::MSG_DRAW_STRIP_VALUE_ROW), STRIP_LABEL_WIDTH)),
        Style::DIM,
    );
    for (place, slot) in strip.cells.iter().enumerate().skip(first).take(shown) {
        numbers.append(Box::BAR, Style::DIM);
        numbers.append(&slot_text(&(place + 1).to_string()), Style::DIM);
        values.append(Box::BAR, Style::DIM);
        let on_cursor = here && place == cell;
        let is_lit = Some(place) == lit;
        let style = match (on_cursor, is_lit) {
            (true, true) => Style::DRAW_LIGHT_REVERSED,
            (true, false) => Style::REVERSE,
            (false, true) => Style::DRAW_LIGHT,
            _ => Style::PLAIN,
        };
        values.append(&slot_text(slot.value()), style);
    }
    numbers.append(Box::BAR, Style::DIM);
    values.append(Box::BAR, Style::DIM);
    vec![Text::default(), top, numbers, rule, values, bottom]
}

/// The three lines of a row of boxed buttons, each its key's name and its name, the one at selected double-lined.
pub fn button_row(buttons: &[(String, String)], selected: Option<usize>) -> Vec<Text> {
    let mut lines = vec![Text::default(), Text::default(), Text::default()];
    for (place, (key_name, label)) in buttons.iter().enumerate() {
        let double = Some(place) == selected;
        let (top_left, top_right, bottom_left, bottom_right, rule, bar) = if double {
            (
                Box::DOUBLE_TOP_LEFT,
                Box::DOUBLE_TOP_RIGHT,
                Box::DOUBLE_BOTTOM_LEFT,
                Box::DOUBLE_BOTTOM_RIGHT,
                Box::DOUBLE_RULE,
                Box::DOUBLE_BAR,
            )
        } else {
            (Box::TOP_LEFT, Box::TOP_RIGHT, Box::BOTTOM_LEFT, Box::BOTTOM_RIGHT, Box::RULE, Box::BAR)
        };
        let key = if key_name.is_empty() { String::new() } else { padded(key_name) };
        let key_length = key.chars().count();
        let inner = 1 + key_length + usize::from(!key.is_empty()) + label.chars().count() + 1;
        if place > 0 {
            for line in &mut lines {
                line.append(SPACE, Style::PLAIN);
            }
        }
        lines[0].append(&format!("{top_left}{}{top_right}", rule.repeat(inner)), Style::PLAIN);
        lines[1].append(&format!("{bar} "), Style::PLAIN);
        if !key.is_empty() {
            lines[1].append(&key, Style::REVERSE);
            lines[1].append(SPACE, Style::PLAIN);
        }
        lines[1].append(label, if double { Style::BOLD } else { Style::PLAIN });
        lines[1].append(&format!(" {bar}"), Style::PLAIN);
        lines[2].append(&format!("{bottom_left}{}{bottom_right}", rule.repeat(inner)), Style::PLAIN);
    }
    lines
}

pub fn inner_width(width: usize) -> usize {
    width.saturating_sub(SIDES + INSET.len() * SIDES)
}

/// The box's lines, and the place among them of the line the cursor is on; cursor is ON_TAB_ROW, the place of the field it
/// is on among the chosen tab's, or None outside the box.
pub fn box_lines(looks: &Looks, tab_box: &TabBox, chosen: usize, cursor: Option<i64>, width: usize) -> (Vec<Text>, Option<usize>) {
    let inner = inner_width(width);
    let height = tab_box.tabs.iter().map(|tab| tab_contents(looks, tab, inner, None).0.len()).max().unwrap_or(0) + SPACE_UNDER;
    let (mut lines, selected) = tab_contents(looks, &tab_box.tabs[chosen], inner, cursor);
    if tab_box.tabs[chosen].not_ready {
        // A tab that does nothing now, such as the MIDI tab of a built-in instrument, is dim inside as well as by its name.
        for line in &mut lines {
            let end = line.len();
            line.stylize(Style::DIM, 0, end);
        }
    }
    while lines.len() < height {
        lines.push(Text::default());
    }
    let result = boxed_tabs(&tab_box.tabs, chosen, width, cursor == Some(ON_TAB_ROW), &lines);
    if cursor == Some(ON_TAB_ROW) {
        return (result, Some(NAME_LINE));
    }
    (result, selected.map(|line| TAB_ROW_LINES + line))
}

/// A row of tabs over a box of a width holding lines, the chosen tab open into the box.
pub fn boxed_tabs(tabs: &[Tab], chosen: usize, width: usize, here: bool, lines: &[Text]) -> Vec<Text> {
    let inner = inner_width(width);
    let mut result = tab_row(tabs, chosen, width, here);
    for line in lines {
        let mut boxed = Text::plain(&format!("{}{INSET}", Box::BAR));
        let shown = line.slice_cells(inner);
        let used = shown.cell_len();
        boxed.append_text(&shown);
        boxed.append(&format!("{}{INSET}{}", SPACE.repeat(inner - used), Box::BAR), Style::PLAIN);
        result.push(boxed);
    }
    result.push(Text::plain(&format!(
        "{}{}{}",
        Box::BOTTOM_LEFT,
        Box::RULE.repeat(width - SIDES),
        Box::BOTTOM_RIGHT
    )));
    result
}

/// Where each of a tab's fields is drawn in a box of a width.
pub fn spots_of(looks: &Looks, tab: &Tab, width: usize) -> Vec<Spot> {
    let inner = inner_width(width);
    let mut spots: Vec<Spot> = (0..tab.top.len())
        .map(|place| Spot {
            band: TOP_BAND,
            column: 0,
            line: place as i64,
        })
        .collect();
    let drawn = drawn_columns(looks, tab, inner, None);
    let widths: Vec<usize> = drawn.iter().map(|(lines, _)| column_width(lines)).collect();
    for (band_place, band) in bands_of(&widths, &footer_columns(tab)).into_iter().enumerate() {
        // A column with fields beside its own takes two places in its band, so that Left and Right reach them.
        let mut column_place = 0i64;
        for place in band {
            let column = &tab.columns[place];
            let mut line = usize::from(column.boxed) + usize::from(column.heading.is_some());
            let mut lines = Vec::new();
            for field in &column.fields {
                lines.push(line);
                spots.push(Spot {
                    band: band_place as i64,
                    column: column_place,
                    line: (line + field.selected_line()) as i64,
                });
                line += field_lines(field, looks, false, 0, inner).len();
            }
            column_place += 1;
            if column.fields_beside().next().is_some() {
                for beside in column.beside.iter().filter(|beside| beside.field.is_some()) {
                    spots.push(Spot {
                        band: band_place as i64,
                        column: column_place,
                        line: lines.get(beside.of).copied().unwrap_or(line) as i64,
                    });
                }
                column_place += 1;
            }
        }
    }
    spots
}

fn tab_contents(looks: &Looks, tab: &Tab, inner: usize, cursor: Option<i64>) -> (Vec<Text>, Option<usize>) {
    let mut lines = vec![Text::default()];
    let mut selected = None;
    let top_width = tab
        .top
        .iter()
        .map(|field| field.drawn_label((looks.open)(field)).chars().count())
        .max()
        .unwrap_or(0)
        + COLUMN_GAP.len();
    for (place, field) in tab.top.iter().enumerate() {
        let here = cursor == Some(place as i64);
        if here {
            selected = Some(lines.len() + field.selected_line());
        }
        lines.extend(field_lines(field, looks, here, top_width, inner));
    }
    if !tab.top.is_empty() && !tab.columns.is_empty() {
        lines.push(Text::default());
    }
    let after_top = cursor.filter(|place| *place >= tab.top.len() as i64).map(|place| place - tab.top.len() as i64);
    let (bands, band_selected) = bands(looks, tab, inner, after_top);
    if let Some(line) = band_selected {
        selected = Some(lines.len() + line);
    }
    lines.extend(bands);
    if !tab.remarks.is_empty() {
        lines.push(Text::default());
        for remark in tab.remarks.iter().take(MOST_REMARKS) {
            lines.push(Text::styled(remark, Style::DIM));
        }
    }
    (lines, selected)
}

fn bands(looks: &Looks, tab: &Tab, inner: usize, cursor: Option<i64>) -> (Vec<Text>, Option<usize>) {
    let drawn = drawn_columns(looks, tab, inner, cursor);
    let widths: Vec<usize> = drawn.iter().map(|(lines, _)| column_width(lines)).collect();
    let mut lines: Vec<Text> = Vec::new();
    let mut selected = None;
    for (band_place, band) in bands_of(&widths, &footer_columns(tab)).into_iter().enumerate() {
        if !lines.is_empty() {
            lines.push(Text::default());
        }
        // The row of columns shows as many as fit, always the cursor's, with a line saying how many are hidden each side.
        let band = if band_place == 0 {
            let cursor_place = band.iter().position(|place| drawn[*place].1.is_some());
            let (start, end) = shown_window(&band.iter().map(|place| widths[*place]).collect::<Vec<_>>(), inner, cursor_place);
            if start > 0 || end + 1 < band.len() {
                lines.push(hidden_line(start, band.len() - 1 - end, inner));
            }
            band[start..=end].to_vec()
        } else {
            band
        };
        let parts: Vec<&(Vec<Text>, Option<usize>)> = band.iter().map(|place| &drawn[*place]).collect();
        let widths: Vec<usize> = parts.iter().map(|(column, _)| column_width(column)).collect();
        let height = parts.iter().map(|(column, _)| column.len()).max().unwrap_or(0);
        let start = lines.len();
        for row in 0..height {
            let mut line = Text::default();
            for (place, (column, _)) in parts.iter().enumerate() {
                if place > 0 {
                    line.append(COLUMN_GAP, Style::PLAIN);
                }
                let part = column.get(row).cloned().unwrap_or_default();
                let used = part.cell_len();
                line.append_text(&part);
                line.append(&SPACE.repeat(widths[place] - used), Style::PLAIN);
            }
            lines.push(line);
        }
        for (_, column_selected) in &parts {
            if let Some(line) = column_selected {
                selected = Some(start + line);
            }
        }
    }
    (lines, selected)
}

fn drawn_columns(looks: &Looks, tab: &Tab, inner: usize, cursor: Option<i64>) -> Vec<(Vec<Text>, Option<usize>)> {
    let mut drawn = Vec::new();
    let mut first = 0i64;
    for column in &tab.columns {
        let count = column.field_count() as i64;
        let within = cursor
            .filter(|place| first <= *place && *place < first + count)
            .map(|place| (place - first) as usize);
        drawn.push(column_lines(looks, column, inner, within));
        first += count;
    }
    let boxed: Vec<usize> = (0..tab.columns.len()).filter(|place| tab.columns[*place].boxed).collect();
    if boxed.is_empty() {
        return drawn;
    }
    let width = boxed.iter().map(|place| column_width(&drawn[*place].0)).max().unwrap_or(0);
    let height = boxed.iter().map(|place| drawn[*place].0.len()).max().unwrap_or(0);
    for place in boxed {
        let (lines, selected) = drawn[place].clone();
        drawn[place] = in_a_box(&lines, selected, width, height);
    }
    drawn
}

fn in_a_box(lines: &[Text], selected: Option<usize>, width: usize, height: usize) -> (Vec<Text>, Option<usize>) {
    let edge = Box::RULE.repeat(width + INSET.len() * SIDES);
    let mut boxed = vec![Text::styled(&format!("{}{edge}{}", Box::TOP_LEFT, Box::TOP_RIGHT), Style::DIM)];
    for row in 0..height {
        // The bar alone is dim: a line made styled would dim everything appended to it, the fields in the box too.
        let mut line = Text::default();
        line.append(&format!("{}{INSET}", Box::BAR), Style::DIM);
        let part = lines.get(row).cloned().unwrap_or_default();
        let used = part.cell_len();
        line.append_text(&part);
        line.append(&format!("{}{INSET}", SPACE.repeat(width - used)), Style::PLAIN);
        line.append(Box::BAR, Style::DIM);
        boxed.push(line);
    }
    boxed.push(Text::styled(&format!("{}{edge}{}", Box::BOTTOM_LEFT, Box::BOTTOM_RIGHT), Style::DIM));
    (boxed, selected.map(|line| line + 1))
}

fn footer_columns(tab: &Tab) -> Vec<usize> {
    (0..tab.columns.len()).filter(|place| tab.columns[*place].footer).collect()
}

/// The first and last of a row of columns of widths to show in a box's inner width: every one where all fit; otherwise
/// from the first as far as fit where the cursor's column is among them, else ending on the cursor's column, reaching
/// back as far as fit, then on to the right as far as fit.
fn shown_window(widths: &[usize], inner: usize, cursor: Option<usize>) -> (usize, usize) {
    if widths.is_empty() {
        return (0, 0);
    }
    let fits = |start: usize, end: usize| band_width(&widths[start..=end]) <= inner;
    let target = cursor.unwrap_or(0);
    let mut start = 0;
    if !fits(0, target) {
        start = target;
        while start > 0 && fits(start - 1, target) {
            start -= 1;
        }
    }
    let mut end = target.max(start);
    while end + 1 < widths.len() && fits(start, end + 1) {
        end += 1;
    }
    (start, end)
}

/// The dim line over a row of columns that scrolls: how many are hidden at the left and at the right, each only where
/// some are.
fn hidden_line(left: usize, right: usize, inner: usize) -> Text {
    let left_text = if left > 0 {
        named(marks::MSG_HIDDEN_LEFT, &[(fill::COUNT, left.into())])
    } else {
        String::new()
    };
    let right_text = if right > 0 {
        named(marks::MSG_HIDDEN_RIGHT, &[(fill::COUNT, right.into())])
    } else {
        String::new()
    };
    let gap = inner.saturating_sub(left_text.chars().count() + right_text.chars().count());
    Text::styled(&format!("{left_text}{}{right_text}", SPACE.repeat(gap)), Style::DIM)
}

fn band_width(widths: &[usize]) -> usize {
    widths.iter().sum::<usize>() + COLUMN_GAP.len() * widths.len().saturating_sub(1)
}

/// The bands a tab's columns stand in: every column in one row, then each footer in a row of its own under it.
fn bands_of(widths: &[usize], footers: &[usize]) -> Vec<Vec<usize>> {
    let row: Vec<usize> = (0..widths.len()).filter(|place| !footers.contains(place)).collect();
    let mut bands = Vec::new();
    if !row.is_empty() {
        bands.push(row);
    }
    bands.extend(footers.iter().map(|footer| vec![*footer]));
    bands
}

fn column_lines(looks: &Looks, column: &crate::forms::tab_box::TabColumn, inner: usize, cursor: Option<usize>) -> (Vec<Text>, Option<usize>) {
    let label_width = column
        .fields
        .iter()
        .map(|field| field.drawn_label((looks.open)(field)).chars().count())
        .max()
        .unwrap_or(0)
        + COLUMN_GAP.len();
    let mut lines = Vec::new();
    if let Some(heading) = &column.heading {
        lines.push(Text::styled(&format!("{INDENT}{heading}"), Style::BOLD));
    }
    let mut selected = None;
    let mut starts = Vec::new();
    for (place, field) in column.fields.iter().enumerate() {
        let here = cursor == Some(place);
        if here {
            selected = Some(lines.len() + field.selected_line());
        }
        starts.push(lines.len());
        lines.extend(field_lines(field, looks, here, label_width, inner));
    }
    if !column.beside.is_empty() {
        let beside_cursor = cursor.and_then(|place| place.checked_sub(column.fields.len()));
        if let Some(line) = beside_lines(column, &mut lines, &starts, label_width, beside_cursor) {
            selected = Some(line);
        }
    }
    (lines, selected)
}

/// The widest value a field can show, every choice included, with the picker's mark where it has one, so that what
/// stands beside it never moves as the value changes.
fn widest_value(field: &Field) -> usize {
    let shown = match &field.kind {
        crate::forms::nodes::Kind::Choice { names: Some(names), .. } => names.iter().map(|name| name.chars().count()).max(),
        _ => None,
    };
    let mark = if field.enter_what == legends::What::CHOOSE {
        marks::MSG_PICKER_MARK.chars().count()
    } else {
        0
    };
    padded("").chars().count() + shown.unwrap_or(0).max(field.value().chars().count()) + mark
}

/// The fields beside a column's own drawn onto the lines of the fields they stand beside, in a column of their own past
/// the widest the fields they stand beside can be: each its label and value, or its label over a dash where it has no field.
/// Gives the line the cursor is on where it is on one of them.
fn beside_lines(column: &crate::forms::tab_box::TabColumn, lines: &mut [Text], starts: &[usize], label_width: usize, cursor: Option<usize>) -> Option<usize> {
    // Past the widest the fields with something beside them can be; a field with nothing beside it may run under.
    let main_width = column
        .beside
        .iter()
        .filter_map(|beside| column.fields.get(beside.of).map(|field| (beside.of, field)))
        .map(|(of, field)| {
            let drawn = starts.get(of).and_then(|start| lines.get(*start)).map_or(0, Text::cell_len);
            drawn.max(cursor_mark(false).chars().count() + label_width + widest_value(field))
        })
        .max()
        .unwrap_or(0);
    let beside_label = column.beside.iter().map(|beside| beside.label.chars().count()).max().unwrap_or(0) + COLUMN_GAP.len();
    let value_width = column
        .beside
        .iter()
        .filter_map(|beside| beside.field.as_ref())
        .map(widest_value)
        .max()
        .unwrap_or(0)
        .max(padded(marks::MSG_NOTHING_BESIDE).chars().count());
    let mut selected = None;
    let mut stopping = 0;
    for beside in &column.beside {
        let Some(line) = starts.get(beside.of).and_then(|start| lines.get_mut(*start)) else {
            continue;
        };
        let here = beside.field.is_some() && cursor == Some(stopping);
        let used = line.cell_len();
        line.append(&SPACE.repeat(main_width.saturating_sub(used)), Style::PLAIN);
        line.append(cursor_mark(here), Style::PLAIN);
        let label_style = if here { Style::BOLD } else { Style::PLAIN };
        match &beside.field {
            Some(field) => {
                line.append(&ljust(&beside.label, beside_label), label_style);
                line.append(&padded(field.value()), Style::PLAIN);
                if here {
                    selected = Some(starts[beside.of]);
                }
                stopping += 1;
            }
            None => {
                line.append(&ljust(&beside.label, beside_label), Style::DIM);
                line.append(&format!("{:^value_width$}", marks::MSG_NOTHING_BESIDE), Style::DIM);
            }
        }
    }
    selected
}

fn column_width(lines: &[Text]) -> usize {
    lines.iter().map(Text::cell_len).max().unwrap_or(0)
}

fn tab_row(tabs: &[Tab], chosen: usize, width: usize, here: bool) -> Vec<Text> {
    let (names, shown_chosen) = tabs_shown(tabs, chosen, width);
    let widths: Vec<usize> = names.iter().map(|(name, _)| padded(name).chars().count()).collect();
    let tops = format!(
        "{}{}{}",
        Box::TOP_LEFT,
        widths.iter().map(|each| Box::RULE.repeat(*each)).collect::<Vec<_>>().join(Box::TOP_TEE),
        Box::TOP_RIGHT
    );
    let mut middle = Text::plain(Box::BAR);
    for (place, (name, dim)) in names.iter().enumerate() {
        let mut style = Style::PLAIN.to_string();
        if place == shown_chosen {
            style = if here { Style::REVERSE } else { Style::BOLD }.to_string();
        }
        if *dim {
            style = format!("{style} {}", Style::DIM).trim().to_string();
        }
        middle.append(&padded(name), &style);
        middle.append(Box::BAR, Style::PLAIN);
    }
    vec![Text::plain(&tops), middle, Text::plain(&top_edge(&widths, shown_chosen, width))]
}

fn top_edge(widths: &[usize], chosen: usize, width: usize) -> String {
    let mut edges = vec![0usize];
    for each in widths {
        edges.push(edges.last().expect("edges start at 0") + each + 1);
    }
    let mut cells: Vec<&str> = vec![Box::RULE; width.max(edges.last().copied().unwrap_or(0) + 1)];
    for (place, each) in widths.iter().enumerate() {
        if place == chosen {
            for cell in cells.iter_mut().skip(edges[place] + 1).take(*each) {
                *cell = SPACE;
            }
        }
    }
    let last = edges.len() - 1;
    for (place, column) in edges.iter().enumerate() {
        cells[*column] = joint(place, chosen, last, *column + 1 == width);
    }
    if *edges.last().expect("edges start at 0") + 1 < width {
        cells[width - 1] = Box::TOP_RIGHT;
    }
    cells.concat()
}

fn joint(place: usize, chosen: usize, last: usize, at_right: bool) -> &'static str {
    if place == 0 {
        return if chosen == 0 { Box::BAR } else { Box::LEFT_TEE };
    }
    if place == last && at_right {
        return if chosen + 1 == last { Box::BAR } else { Box::RIGHT_TEE };
    }
    if chosen + 1 == place {
        return Box::BOTTOM_LEFT;
    }
    if chosen == place {
        return Box::BOTTOM_RIGHT;
    }
    Box::BOTTOM_TEE
}

fn tabs_shown(tabs: &[Tab], chosen: usize, width: usize) -> (Vec<(String, bool)>, usize) {
    let names: Vec<(String, bool)> = tabs.iter().map(|tab| (tab.shown_name(), tab.is_dim())).collect();
    let row_width = |first: usize, last: usize| {
        let mut total = 1 + names[first..=last].iter().map(|(name, _)| padded(name).chars().count() + 1).sum::<usize>();
        if first > 0 {
            total += padded(marks::MSG_TABS_HIDDEN_BEFORE).chars().count() + 1;
        }
        if last + 1 < names.len() {
            total += padded(marks::MSG_TABS_HIDDEN_AFTER).chars().count() + 1;
        }
        total
    };
    let (mut first, mut last) = (chosen, chosen);
    loop {
        let mut grown = false;
        if last + 1 < names.len() && row_width(first, last + 1) <= width {
            last += 1;
            grown = true;
        }
        if first > 0 && row_width(first - 1, last) <= width {
            first -= 1;
            grown = true;
        }
        if !grown {
            break;
        }
    }
    let mut shown: Vec<(String, bool)> = names[first..=last].to_vec();
    let mut shown_chosen = chosen - first;
    if first > 0 {
        shown.insert(0, (marks::MSG_TABS_HIDDEN_BEFORE.to_string(), false));
        shown_chosen += 1;
    }
    if last + 1 < names.len() {
        shown.push((marks::MSG_TABS_HIDDEN_AFTER.to_string(), false));
    }
    (shown, shown_chosen)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::forms::tab_box::TabColumn;

    /// A boxed column dims its box alone: the fields inside are drawn as any field is, never greyed out with the edges.
    #[test]
    fn a_boxed_column_dims_its_edges_but_not_its_fields() {
        let label = "LFO 1";
        let mut column = TabColumn::new(None, vec![Field::toggle(1, label, false)]);
        column.boxed = true;
        let tab = Tab::new("LFOs", vec![column]);
        let looks = Looks { cell: 0, open: &|_| false };
        let wide = 80;
        let drawn = drawn_columns(&looks, &tab, wide, None);
        let line = drawn[0].0.iter().find(|line| line.text().contains(label)).expect("the field's line");
        let dimmed = |segment: &crate::text::Segment| segment.style.is_on(file_format::ChordSymbol::DIMINISHED);
        let segments = line.segments();
        assert!(
            segments.iter().filter(|segment| segment.text.contains(label)).all(|segment| !dimmed(segment)),
            "the label is not dim"
        );
        assert!(
            segments.iter().any(|segment| segment.text.contains(Box::BAR) && dimmed(segment)),
            "the box's bar is"
        );
    }
}
