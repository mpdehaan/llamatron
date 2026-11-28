// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The main screen (the Python screens/set/main_page.py): a button for every page and the file's actions, with a
//! double-lined box around what the cursor is on. Arrange is a bar across the top; under it three rows of three, in the order
//! a song is made; then a blank line and one bar with the file's six actions in two rows on the grid's own columns.

use crate::app::App;
use crate::drawing::{padded, BoxCharacters as Box, Canvas, Style};
use crate::keybindings::{Binding, KeyClass, MainPage as Keys, Page as PageKeys};
use crate::keys::KeyItem;
use crate::page::{Duration, Page};
use crate::screens::field_page::FieldPage;
use crate::screens::list_page::ListPage;
use crate::screens::set::file_page::FilePage;
use crate::screens::set::grooves_page::GroovesPage;
use crate::screens::set::scales_page::ScalesPage;
use crate::screens::set::songs_page::SongsPage;
use crate::style::Style as RichStyle;
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_engine::realizer::SongRealizer;
use llamatron_model::schema::generated::file_format::Section;
use llamatron_names::file_format;
use llamatron_names::words;
use llamatron_strings::{labels, messages};

const COLUMNS: usize = 3;
const GRID_WIDTH: usize = 80;
const CELL_GAP: usize = 1;
const EDGE_GAP: &str = " ";
const NAME_GAP: &str = " ";
const BORDERS: usize = 2;
const CELL_LINES: usize = 3;
const BUTTON_ROWS: usize = 3;
const BAR_ROWS: usize = 2;

/// The sections whose items a page's button counts, and the sections that hold generators.
const GENERATOR_SECTIONS: [&str; 10] = [
    words::ARPS,
    words::CHORDS,
    words::DRIFTS,
    words::GUITARIFIES,
    words::HOCKETS,
    words::MUSICIANS,
    words::PHRASINGS,
    words::SHAPES,
    words::TIMINGS,
    file_format::Section::CHAINS,
];

type Grid = [[&'static Binding; 3]; 6];

/// The cells by the geometry drawn, six rows of three.
fn rows() -> Grid {
    [
        [&Keys::ARRANGE, &Keys::ARRANGE, &Keys::ARRANGE],
        [&Keys::SONGS, &Keys::WIZARD, &Keys::PATTERNS],
        [&Keys::SCALES, &Keys::GENERATORS, &Keys::DRAWS],
        [&Keys::GROOVES, &Keys::INSTRUMENTS, &Keys::INSTRUMENTS],
        [&Keys::OPEN_SET_HERE, &Keys::IMPORT_HERE, &Keys::FILE],
        [&PageKeys::SAVE, &Keys::EXPORT_HERE, &Keys::QUIT],
    ]
}

/// What a cell is called: the page its key opens, or the name of the action.
fn cell_name(binding: &'static Binding) -> &'static str {
    let names: [(&'static Binding, &'static str); 5] = [
        (&PageKeys::SAVE, labels::PageName::SAVE),
        (&Keys::OPEN_SET_HERE, labels::PageName::OPEN),
        (&Keys::EXPORT_HERE, labels::PageName::EXPORT),
        (&Keys::IMPORT_HERE, labels::PageName::IMPORT),
        (&Keys::QUIT, labels::PageName::QUIT),
    ];
    names
        .iter()
        .find(|(found, _)| std::ptr::eq(*found, binding))
        .map(|(_, name)| *name)
        .unwrap_or(binding.what)
}

fn cell_theme(binding: &'static Binding) -> Option<Colour> {
    let found: [(&'static Binding, Colour); 9] = [
        (&Keys::SONGS, themes::SONGS),
        (&Keys::WIZARD, themes::WIZARD),
        (&Keys::PATTERNS, themes::PATTERNS),
        (&Keys::GENERATORS, themes::GENERATORS),
        (&Keys::SCALES, themes::SCALES),
        (&Keys::GROOVES, themes::GROOVES),
        (&Keys::INSTRUMENTS, themes::INSTRUMENTS),
        (&Keys::DRAWS, themes::DRAWS),
        (&Keys::FILE, themes::SET_FILE),
    ];
    found.iter().find(|(cell, _)| std::ptr::eq(*cell, binding)).map(|(_, theme)| *theme)
}

fn same(first: &'static Binding, second: &'static Binding) -> bool {
    std::ptr::eq(first, second)
}

/// Every row and column of the geometry a binding's cell covers, in reading order.
fn cell_positions(rows: &Grid, binding: &'static Binding) -> Vec<(usize, usize)> {
    let mut positions = Vec::new();
    for (row, cells) in rows.iter().enumerate() {
        for (column, cell) in cells.iter().enumerate() {
            if same(cell, binding) {
                positions.push((row, column));
            }
        }
    }
    positions
}

/// The row and column an arrow takes the cursor to, or None where it stops at an edge; a cell entered across the way it
/// stretches remembers where, and one entered along it is at its first row and column.
fn moved(rows: &Grid, position: (usize, usize), key: &str) -> Option<(usize, usize)> {
    let (row_step, column_step): (i64, i64) = match key {
        llamatron_names::keys::UP => (-1, 0),
        llamatron_names::keys::DOWN => (1, 0),
        llamatron_names::keys::LEFT => (0, -1),
        _ => (0, 1),
    };
    let here = rows[position.0][position.1];
    let (mut row, mut column) = (position.0 as i64, position.1 as i64);
    let there = loop {
        row += row_step;
        column += column_step;
        if row < 0 || column < 0 || row as usize >= rows.len() || column as usize >= COLUMNS {
            return None;
        }
        let there = rows[row as usize][column as usize];
        if !same(there, here) {
            break there;
        }
    };
    let places = cell_positions(rows, there);
    let tall = places.iter().any(|place| place.0 != places[0].0);
    let wide = places.iter().any(|place| place.1 != places[0].1);
    if (row_step != 0 && tall) || (column_step != 0 && wide) {
        return Some(places[0]);
    }
    Some((row as usize, column as usize))
}

pub struct MainPage {
    chosen: &'static Binding,
    position: Option<(usize, usize)>,
}

impl Default for MainPage {
    fn default() -> Self {
        MainPage::new()
    }
}

impl MainPage {
    pub fn new() -> MainPage {
        MainPage {
            chosen: &Keys::ARRANGE,
            position: None,
        }
    }

    fn cursor_keys(&self) -> Vec<KeyItem> {
        vec![KeyItem::of(&Keys::CLASS, &Keys::SELECT).wanting_key(), KeyItem::of(&Keys::CLASS, &Keys::OPEN)]
    }

    fn row_and_column(&self) -> (usize, usize) {
        let places = cell_positions(&rows(), self.chosen);
        match self.position {
            Some(position) if places.contains(&position) => position,
            _ => places[0],
        }
    }

    fn in_bar(&self) -> bool {
        rows()[4..].iter().any(|row| row.iter().any(|cell| same(cell, self.chosen)))
    }

    fn move_cursor(&mut self, key: &str) {
        let rows = rows();
        if let Some(there) = moved(&rows, self.row_and_column(), key) {
            self.chosen = rows[there.0][there.1];
            self.position = Some(there);
        }
    }

    /// Do what a cell's key does: open its page.
    fn act(&mut self, app: &mut App, binding: &'static Binding) {
        if same(binding, &Keys::FILE) {
            app.show_page(std::boxed::Box::new(FieldPage::new(FilePage)));
            return;
        }
        if same(binding, &Keys::GENERATORS) {
            let page = crate::screens::generators::generators_page::GeneratorsPage::new(app);
            app.show_page(std::boxed::Box::new(page));
            return;
        }
        if same(binding, &Keys::ARRANGE) {
            app.show_page(std::boxed::Box::new(crate::screens::arrange::arrange_page::ArrangePage::new()));
            return;
        }
        if same(binding, &Keys::PATTERNS) {
            let page = crate::screens::pattern::patterns_page::PatternsPage::new(app);
            app.show_page(std::boxed::Box::new(page));
            return;
        }
        if same(binding, &Keys::GROOVES) {
            app.show_page(std::boxed::Box::new(ListPage::new(GroovesPage)));
            return;
        }
        if same(binding, &Keys::SCALES) {
            app.show_page(std::boxed::Box::new(ListPage::new(ScalesPage)));
            return;
        }
        if same(binding, &Keys::DRAWS) {
            let page = crate::screens::field_page::FieldPage::new(crate::screens::set::draws_page::DrawsPage);
            app.show_page(std::boxed::Box::new(page));
            return;
        }
        if same(binding, &Keys::INSTRUMENTS) {
            let page = crate::screens::set::instruments_page::InstrumentsPage;
            app.show_page(std::boxed::Box::new(ListPage::new(page)));
            return;
        }
        if same(binding, &Keys::SONGS) {
            app.show_page(std::boxed::Box::new(ListPage::new(SongsPage)));
            return;
        }
        if same(binding, &Keys::QUIT) {
            crate::everywhere::quit_program(app);
            return;
        }
        if same(binding, &PageKeys::SAVE) {
            crate::everywhere::save(app, None);
            return;
        }
        if same(binding, &Keys::EXPORT_HERE) {
            crate::exporting::export(app);
            return;
        }
        if same(binding, &Keys::OPEN_SET_HERE) {
            app.open_set();
            return;
        }
        if same(binding, &Keys::IMPORT_HERE) {
            let picker = crate::screens::set::open_page::OpenPage::for_midi(app);
            app.show_page(std::boxed::Box::new(picker));
            return;
        }
        // The song wizard is not in this version: its key says so rather than opening a page.
        if same(binding, &Keys::WIZARD) {
            app.refuse(messages::MSG_WIZARD_NOT_YET);
        }
    }

    /// What a cell shows at its right: how many of its things the set has, or nothing.
    fn count(&self, app: &App, binding: &'static Binding) -> Option<String> {
        let setlist = app.document.get_setlist();
        if same(binding, &Keys::GENERATORS) {
            return Some(GENERATOR_SECTIONS.iter().map(|section| setlist.items(section).len()).sum::<usize>().to_string());
        }
        let section = [
            (&Keys::SONGS, Section::SONGS),
            (&Keys::PATTERNS, Section::PATTERNS),
            (&Keys::SCALES, Section::SCALES),
            (&Keys::INSTRUMENTS, Section::INSTRUMENTS),
            (&Keys::GROOVES, Section::GROOVES),
        ]
        .into_iter()
        .find(|(cell, _)| same(cell, binding))
        .map(|(_, section)| section)?;
        Some(setlist.items(section).len().to_string())
    }

    fn column_widths(&self) -> [usize; 3] {
        let room = GRID_WIDTH - CELL_GAP * (COLUMNS - 1);
        let other = room / COLUMNS;
        [room - other * (COLUMNS - 1), other, other]
    }

    fn column_lefts(&self, widths: &[usize; 3]) -> [usize; 3] {
        let mut lefts = [0; 3];
        let mut left = 0;
        for (place, width) in widths.iter().enumerate() {
            lefts[place] = left;
            left += width + CELL_GAP;
        }
        lefts
    }

    fn edge_style(&self, binding: &'static Binding) -> RichStyle {
        match cell_theme(binding) {
            None => RichStyle::parse(Style::DIM),
            Some(theme) => RichStyle::parse(&RichStyle::rgb(themes::balanced(theme))),
        }
    }

    fn draw_box(&self, canvases: &mut [Canvas], left: usize, width: usize, selected: bool, style: &RichStyle) {
        let (top_left, rule, top_right, bottom_left, bottom_right, bar) = if selected {
            (
                Box::DOUBLE_TOP_LEFT,
                Box::DOUBLE_RULE,
                Box::DOUBLE_TOP_RIGHT,
                Box::DOUBLE_BOTTOM_LEFT,
                Box::DOUBLE_BOTTOM_RIGHT,
                Box::DOUBLE_BAR,
            )
        } else {
            (Box::TOP_LEFT, Box::RULE, Box::TOP_RIGHT, Box::BOTTOM_LEFT, Box::BOTTOM_RIGHT, Box::BAR)
        };
        let inner = width - BORDERS;
        let left = left as i64;
        let last = canvases.len() - 1;
        canvases[0].write_style(left, &format!("{top_left}{}{top_right}", rule.repeat(inner)), style);
        canvases[last].write_style(left, &format!("{bottom_left}{}{bottom_right}", rule.repeat(inner)), style);
        for canvas in &mut canvases[1..last] {
            canvas.write_style(left, bar, style);
            canvas.write_style(left + width as i64 - 1, bar, style);
        }
    }

    fn draw_cell(&self, app: &App, canvases: &mut [Canvas], left: usize, binding: &'static Binding, selected: bool, width: usize) {
        let (edge, name_style) = if selected {
            (RichStyle::parse(Style::SELECTED_EDGE), Style::BOLD)
        } else {
            (self.edge_style(binding), Style::PLAIN)
        };
        self.draw_box(canvases, left, width, selected, &edge);
        let middle = &mut canvases[1];
        let right = (left + width - 1) as i64;
        let label = padded(binding.name);
        let name = cell_name(binding);
        let start = (left + 1 + EDGE_GAP.len()) as i64;
        let label_length = label.chars().count() as i64;
        middle.write(start, &label, Style::KEY);
        middle.write(start + label_length, &format!("{NAME_GAP}{name}"), name_style);
        if let Some(count) = self.count(app, binding) {
            let name_end = start + label_length + NAME_GAP.len() as i64 + name.chars().count() as i64;
            let length = count.chars().count() as i64;
            let column = (right - 1 - length).max((name_end + NAME_GAP.len() as i64).min(right - length));
            middle.write(column, &count, Style::PLAIN);
        }
    }

    fn draw_bar(&self, canvases: &mut [Canvas], rows: &[[&'static Binding; 3]], lefts: &[usize; 3], width: usize) {
        let in_bar = self.in_bar();
        let edge = RichStyle::parse(if in_bar { Style::SELECTED_EDGE } else { Style::DIM });
        self.draw_box(canvases, 0, width, in_bar, &edge);
        for (column, column_left) in lefts.iter().enumerate() {
            let labels: Vec<String> = rows.iter().map(|row| padded(row[column].name)).collect();
            let key_room = labels.iter().map(|label| label.chars().count()).max().unwrap_or(0) as i64;
            let start = (column_left + 1 + EDGE_GAP.len()) as i64;
            for (line, (row, label)) in rows.iter().zip(&labels).enumerate() {
                let binding = row[column];
                let canvas = &mut canvases[1 + line];
                canvas.write(start, label, Style::KEY);
                let mut text = format!("{NAME_GAP}{}", cell_name(binding));
                let mut style = Style::PLAIN;
                if same(binding, self.chosen) {
                    text.push(' ');
                    style = Style::REVERSE;
                }
                canvas.write(start + key_room, &text, style);
            }
        }
    }
}

impl Page for MainPage {
    fn name(&self) -> &'static str {
        "MainPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        let mut keys: Vec<KeyItem> = Keys::PAGES.iter().map(|binding| KeyItem::of(&Keys::CLASS, binding)).collect();
        for binding in [&Keys::OPEN_SET_HERE, &Keys::EXPORT_HERE, &Keys::IMPORT_HERE, &Keys::QUIT] {
            keys.push(KeyItem::of(&Keys::CLASS, binding));
        }
        keys.extend(self.cursor_keys());
        keys
    }

    fn shown_keys(&self, _app: &App) -> Vec<KeyItem> {
        let mut keys = self.cursor_keys();
        keys.push(KeyItem::of(&Keys::CLASS, &Keys::FOOTER_HELP));
        keys.push(KeyItem::of(&Keys::CLASS, &Keys::FOOTER_ABOUT));
        keys
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&Keys::SELECT) {
            self.move_cursor(key);
        } else if item.is(&Keys::OPEN) {
            let chosen = self.chosen;
            self.act(app, chosen);
        } else {
            self.act(app, item.binding);
        }
    }

    fn body(&self, app: &App, _width: usize, _height: usize) -> Vec<Text> {
        let rows = rows();
        let widths = self.column_widths();
        let lefts = self.column_lefts(&widths);
        let total = lefts[2] + widths[2];
        let mut grid: Vec<Canvas> = (0..(1 + BUTTON_ROWS) * CELL_LINES).map(|_| Canvas::new(total)).collect();
        self.draw_cell(app, &mut grid[..CELL_LINES], 0, &Keys::ARRANGE, same(self.chosen, &Keys::ARRANGE), total);
        for (number, row) in rows[1..1 + BUTTON_ROWS].iter().enumerate() {
            let number = number + 1;
            let lines = &mut grid[number * CELL_LINES..(number + 1) * CELL_LINES];
            // A cell that covers several places side by side is drawn once, as wide as all of them.
            let mut column = 0;
            while column < COLUMNS {
                let binding = row[column];
                let mut last = column;
                while last + 1 < COLUMNS && same(row[last + 1], binding) {
                    last += 1;
                }
                let width = lefts[last] + widths[last] - lefts[column];
                self.draw_cell(app, lines, lefts[column], binding, same(binding, self.chosen), width);
                column = last + 1;
            }
        }
        let mut bar: Vec<Canvas> = (0..BAR_ROWS + BORDERS).map(|_| Canvas::new(total)).collect();
        self.draw_bar(&mut bar, &rows[1 + BUTTON_ROWS..], &lefts, total);
        let mut lines = vec![Text::default()];
        lines.extend(grid.iter().map(Canvas::text));
        lines.push(Text::default());
        lines.extend(bar.iter().map(Canvas::text));
        lines
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::MAIN_SCREEN.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::MAIN_SCREEN)
    }

    fn caption(&self, _app: &App) -> String {
        String::new()
    }

    fn duration(&self, app: &App) -> Duration {
        if let Some(playing) = app.transport.playing_clock() {
            return Duration::Clock(playing);
        }
        let document = &app.document;
        Duration::Seconds(SongRealizer::new(document.get_setlist(), document.song(), None).song_seconds())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::preferences::TrackInstrumentDefault;

    /// The main screen as a person reads it: every page it opens is named in exactly one cell, at the smallest size and
    /// a large one, so that no cell is drawn twice and none is missing.
    #[test]
    fn the_main_screen_names_each_page_once() {
        let synth = |drum: bool| crate::track_instrument::new_track_instrument(TrackInstrumentDefault::BuiltIn, drum, false, None);
        let tracker = crate::app::Tracker::new(crate::document::Document::new_set(synth(false), synth(true)).expect("a new set"));
        let pages = [
            labels::PageName::ARRANGE,
            labels::PageName::SONGS,
            labels::PageName::PATTERNS,
            labels::PageName::SCALES,
            labels::PageName::GENERATORS,
            labels::PageName::DRAWS,
            labels::PageName::GROOVES,
            labels::PageName::INSTRUMENTS,
        ];
        for (width, height) in [(80, 24), (160, 50)] {
            let screen: String = tracker.screen(width, height).iter().map(|line| line.text() + "\n").collect();
            for page in pages {
                let cell = format!(" {page} ");
                let count = screen.lines().map(|line| line.matches(&cell).count()).sum::<usize>();
                assert_eq!(count, 1, "{page} at {width}x{height}:\n{screen}");
            }
        }
    }
}
