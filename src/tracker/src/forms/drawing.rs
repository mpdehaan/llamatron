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
    named(marks::MSG_DRAW_STRIP_CELL, &[("value", value.into())])
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
    for (band_place, band) in bands_of(&widths, inner, &columns_under(tab)).into_iter().enumerate() {
        for (column_place, place) in band.into_iter().enumerate() {
            let column = &tab.columns[place];
            let mut line = usize::from(column.boxed) + usize::from(column.heading.is_some());
            for field in &column.fields {
                spots.push(Spot {
                    band: band_place as i64,
                    column: column_place as i64,
                    line: (line + field.selected_line()) as i64,
                });
                line += field_lines(field, looks, false, 0, inner).len();
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
    for band in bands_of(&widths, inner, &columns_under(tab)) {
        if !lines.is_empty() {
            lines.push(Text::default());
        }
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
        let count = column.fields.len() as i64;
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
        let mut line = Text::styled(&format!("{}{INSET}", Box::BAR), Style::DIM);
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

fn columns_under(tab: &Tab) -> Vec<usize> {
    (0..tab.columns.len()).filter(|place| tab.columns[*place].under).collect()
}

fn band_width(widths: &[usize]) -> usize {
    widths.iter().sum::<usize>() + COLUMN_GAP.len() * widths.len().saturating_sub(1)
}

fn bands_of(widths: &[usize], inner: usize, under: &[usize]) -> Vec<Vec<usize>> {
    let mut bands = Vec::new();
    let mut band: Vec<usize> = Vec::new();
    for (place, width) in widths.iter().enumerate() {
        let mut trial: Vec<usize> = band.iter().map(|each| widths[*each]).collect();
        trial.push(*width);
        if !band.is_empty() && (under.contains(&place) || band_width(&trial) > inner) {
            bands.push(std::mem::take(&mut band));
        }
        band.push(place);
    }
    if !band.is_empty() {
        bands.push(band);
    }
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
    for (place, field) in column.fields.iter().enumerate() {
        let here = cursor == Some(place);
        if here {
            selected = Some(lines.len() + field.selected_line());
        }
        lines.extend(field_lines(field, looks, here, label_width, inner));
    }
    (lines, selected)
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
