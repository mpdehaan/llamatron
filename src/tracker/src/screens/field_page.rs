// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The settings page (the Python screens/shared/field_page.py, forms/navigator.py and renderers/settings_page.py): settings
//! in a column, a tab box among them, and buttons under them, where the keys depend on the setting under the cursor. A page
//! of settings says only its form and what its edits store; this draws it and moves its cursor.

use crate::app::App;
use crate::drawing::{cursor_mark, Style, INDENT};
use crate::forms::drawing::{box_lines, button_row, field_lines, spots_of, Looks};
use crate::forms::nodes::{Edit, Field, Kind};
use crate::forms::tab_box::{self, Spot, TabBox, ON_TAB_ROW};
use crate::keybindings::{FieldPage as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::page::{Duration, Page};
use crate::text::Text;
use crate::themes::Colour;
use llamatron_strings::{labels, marks, named};
use std::cell::Cell;

/// How wide a tab box is drawn before the page has been drawn at a width.
const BOX_WIDTH: usize = 80;

/// A part of a settings page's form: a field, or a tab box of fields.
pub enum Node {
    Field(Box<Field>),
    TabBox(TabBox),
}

/// What a page of settings says of itself: its form, and what its edits do.
pub trait Form {
    /// The kind of thing the page edits, where one page edits several kinds, as the plugin editor does each kind of
    /// generator, so that a walk of the program tells their fields apart; nothing where the page edits one kind.
    fn edited_kind(&self) -> String {
        String::new()
    }

    /// Keep showing the same thing after a step renamed it, and say whether the thing is still in the set (the page's own).
    fn follow_renames(&mut self, _renames: &crate::history::Renames) {}
    fn still_exists(&self, _app: &App) -> bool {
        true
    }

    /// The Python page's class name.
    fn name(&self) -> &'static str;
    fn class(&self) -> &'static KeyClass;
    fn crumbs(&self, app: &App) -> Vec<String>;
    fn theme(&self) -> Option<Colour>;
    fn form(&self, app: &App) -> Vec<Node>;

    fn duration(&self, _app: &App) -> Duration {
        Duration::Nothing
    }

    /// What the theme's stripe says, where that is more than the page's own crumb in capitals.
    /// The page's help, the F1 dialog's panel about it, a line each, where it is the page's own rather than its kind's.
    fn help(&self) -> Option<Vec<String>> {
        None
    }

    fn caption(&self, _app: &App) -> Option<String> {
        None
    }

    /// The lines under the settings and buttons.
    fn remarks(&self, _app: &App, _width: usize) -> Vec<Text> {
        Vec::new()
    }

    /// Store or act on what a key did to the field of an id.
    fn apply(&mut self, _app: &mut App, _id: usize, _edit: Edit) {}

    /// Ask for a new name for what the page shows, as ENTER on its Name field and F2 do; None where the page's Name is
    /// renamed some other way, which then reaches apply as ENTER on the Name field.
    fn rename(&self, _app: &mut App) -> Option<()> {
        None
    }

    /// The page's own keys besides its fields', where the cursor is on a row.
    fn page_keys(&self, _app: &App, _row: Option<&Field>) -> Vec<KeyItem> {
        Vec::new()
    }

    /// Act on one of the page's own keys, the cursor on a row.
    fn press_own(&mut self, _app: &mut App, _item: &KeyItem, _key: &str, _row: Option<&Field>) {}

    /// Whether a blank line comes before every section's heading rather than before the first alone.
    fn headings_apart(&self) -> bool {
        false
    }

    /// The page's keys that step the cell under the cursor in a row of cells that step, less then more, where it has such rows.
    fn slot_keys(&self) -> Option<(&'static crate::keybindings::Binding, &'static crate::keybindings::Binding)> {
        None
    }

    /// Whether every part of the page is ported, which a page made from declarations, as a generator's is, may not be yet.
    fn is_ported(&self, _app: &App) -> bool {
        true
    }

    /// Whether a field is the last row of a list among the settings, which leaves a blank line after it.
    fn ends_a_list(&self, _field: &Field) -> bool {
        false
    }
}

/// What a settings page keeps of its cursor and of how it was last drawn.
#[derive(Default)]
pub struct FormState {
    cursor: Cell<usize>,
    cell: Cell<usize>,
    box_width: Cell<usize>,
    stacked_buttons: Cell<bool>,
    first_line: Cell<usize>,
}

pub struct FieldPage<F: Form> {
    pub form: F,
    state: FormState,
    /// Whether the page was wholly ported when it last answered, which names it for the screen tour.
    ported: Cell<bool>,
    /// The field a dialog the page opened is asking for, by its id, and what its answer means.
    asking: Option<(usize, Asking)>,
}

/// What a dialog's answer means to the field that opened it: a place among its choices, a number between its bounds, or
/// its text.
enum Asking {
    Choice(Vec<String>),
    Number(Option<i64>, Option<i64>),
    Text,
}

/// What a settings page shows now: its fields, its box and its chosen tab.
struct Shown {
    nodes: Vec<Node>,
    fields: Vec<Field>,
    chosen: usize,
}

impl Shown {
    fn tab_box(&self) -> Option<&TabBox> {
        self.nodes.iter().find_map(|node| match node {
            Node::TabBox(tab_box) => Some(tab_box),
            Node::Field(_) => None,
        })
    }

    fn every_field(&self) -> impl Iterator<Item = &Field> {
        self.nodes.iter().filter_map(|node| match node {
            Node::Field(field) => Some(field.as_ref()),
            Node::TabBox(_) => None,
        })
    }

    fn box_place(&self) -> Option<usize> {
        self.fields.iter().position(Field::is_tab_row)
    }

    fn box_field_count(&self) -> usize {
        self.tab_box().map_or(0, |tab_box| tab_box.tabs[self.chosen].field_count())
    }

    /// Where the page's own buttons start: the run of buttons at the end, after the chosen tab's fields.
    fn first_button_place(&self) -> usize {
        let mut start = self.fields.len();
        while start > 0 && self.fields[start - 1].is_button() {
            start -= 1;
        }
        match self.box_place() {
            None => start,
            Some(row) => start.max(row + 1 + self.box_field_count()),
        }
    }
}

impl<F: Form> FieldPage<F> {
    pub fn new(form: F) -> FieldPage<F> {
        let state = FormState::default();
        state.box_width.set(BOX_WIDTH);
        FieldPage {
            form,
            state,
            ported: Cell::new(true),
            asking: None,
        }
    }

    /// Open the dialog an edit asks for, remembering which field asked, or apply the edit where it asks nothing.
    fn ask_or_apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        use crate::screens::dialogs::{ChoiceDialog, PromptDialog};
        match edit {
            Edit::AskChoice {
                title,
                options,
                current,
                choices,
            } => {
                self.asking = Some((id, Asking::Choice(choices)));
                app.show_page(Box::new(ChoiceDialog::new(&title, options, current)));
            }
            Edit::AskGrouped {
                title,
                options,
                current,
                choices,
                headings,
            } => {
                self.asking = Some((id, Asking::Choice(choices)));
                let mut dialog = ChoiceDialog::new(&title, options, current);
                dialog.headings = headings;
                app.show_page(Box::new(dialog));
            }
            Edit::AskGrid {
                title,
                options,
                current,
                choices,
                pages,
                details,
            } => {
                self.asking = Some((id, Asking::Choice(choices)));
                let dialog = crate::screens::dialogs::GridChoiceDialog::new(&title, options, pages, current, details);
                app.show_page(Box::new(dialog));
            }
            Edit::AskSound { title, top, groups, current } => {
                // The dialog answers with a sound's value, which stands for itself among the choices.
                let most = top
                    .iter()
                    .chain(groups.iter().flat_map(|(_, sounds)| sounds.iter()))
                    .map(|(_, value)| *value)
                    .max()
                    .unwrap_or(0);
                self.asking = Some((id, Asking::Choice((0..=most).map(|value| value.to_string()).collect())));
                app.show_page(Box::new(crate::screens::dialogs::SoundDialog::new(&title, top, groups, current)));
            }
            Edit::AskNumber { title, value, lowest, highest } => {
                self.asking = Some((id, Asking::Number(lowest, highest)));
                app.show_page(Box::new(PromptDialog::new(&title, &value.to_string())));
            }
            Edit::AskText { title, value } => {
                self.asking = Some((id, Asking::Text));
                app.show_page(Box::new(PromptDialog::new(&title, &value)));
            }
            edit => {
                self.form.apply(app, id, edit);
                // A form asks for a picker or a prompt of its own making by leaving the edit that would open it.
                if let Some(asked) = app.asking.take() {
                    self.ask_or_apply(app, id, asked);
                }
            }
        }
    }

    fn is_open(app: &App, field: &Field) -> bool {
        let starts_open = matches!(field.kind, Kind::Heading { starts_open: true });
        app.session.open_field_sections.contains(&field.label) != starts_open
    }

    fn chosen_tab(&self, app: &App, tab_box: &TabBox) -> usize {
        tab_box.tab_named(app.session.chosen_tabs.get(self.form.name()).map(String::as_str))
    }

    fn shown(&self, app: &App) -> Shown {
        let nodes = self.form.form(app);
        let mut fields = Vec::new();
        let mut chosen = 0;
        let mut open_now = true;
        for node in &nodes {
            match node {
                Node::TabBox(tab_box) => {
                    chosen = self.chosen_tab(app, tab_box);
                    fields.push(Field::tab_row(&tab_box.label));
                    fields.extend(tab_box.tabs[chosen].every_field().into_iter().cloned());
                }
                Node::Field(field) if field.is_heading() => {
                    fields.push(field.as_ref().clone());
                    open_now = Self::is_open(app, field);
                }
                Node::Field(field) => {
                    if open_now || field.is_button() {
                        fields.push(field.as_ref().clone());
                    }
                }
            }
        }
        Shown { nodes, fields, chosen }
    }

    /// The cursor's place, kept within the fields shown.
    fn place(&self, shown: &Shown) -> usize {
        let place = self.state.cursor.get().min(shown.fields.len().saturating_sub(1));
        self.state.cursor.set(place);
        place
    }

    fn cell_field<'a>(&self, shown: &'a Shown) -> Option<&'a Field> {
        let field = shown.fields.get(self.place(shown))?;
        if !field.is_cells() || field.cells.is_empty() {
            return Some(field);
        }
        let cell = self.state.cell.get().min(field.cells.len() - 1);
        self.state.cell.set(cell);
        Some(&field.cells[cell])
    }

    fn looks<'a>(&self, open: &'a dyn Fn(&Field) -> bool) -> Looks<'a> {
        Looks {
            cell: self.state.cell.get(),
            open,
        }
    }

    fn box_spots(&self, app: &App, shown: &Shown) -> Vec<Spot> {
        let Some(tab_box) = shown.tab_box() else { return Vec::new() };
        let open = |field: &Field| Self::is_open(app, field);
        spots_of(&self.looks(&open), &tab_box.tabs[shown.chosen], self.state.box_width.get())
    }

    fn in_box(&self, shown: &Shown) -> bool {
        let place = self.place(shown);
        shown.box_place().is_some_and(|row| row < place && place <= row + shown.box_field_count())
    }

    fn bind(&self, binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(self.form.class(), binding)
    }

    fn box_keys(&self, app: &App, shown: &Shown, row: Option<&Field>) -> Vec<KeyItem> {
        let place = self.place(shown);
        let box_place = shown.box_place().expect("a page with a tab box");
        if place == box_place {
            return vec![self.bind(&Keys::INTO_TAB)];
        }
        let mut keys = vec![self.bind(&Keys::TO_TABS)];
        if !self.in_box(shown) {
            return keys;
        }
        keys.push(self.bind(&Keys::TAB_PAGES));
        let here = place - box_place - 1;
        let spots = self.box_spots(app, shown);
        if !row.is_some_and(Field::is_cells) && tab_box::has_columns_beside(&spots, here) {
            keys.push(self.bind(&Keys::ACROSS));
        }
        keys
    }

    // The moves.

    fn move_cursor(&self, app: &App, shown: &Shown, name: &str) {
        if shown.fields.is_empty() {
            return;
        }
        self.state.cell.set(0);
        let Some(row) = shown.box_place() else {
            self.move_in_order(shown, name);
            return;
        };
        let count = shown.box_field_count();
        let place = self.place(shown);
        if row < place && place <= row + count {
            self.move_inside_box(app, shown, name, row, place - row - 1);
            return;
        }
        self.move_in_order(shown, name);
        if name == "up" && place > row + count && self.state.cursor.get() == row + count && count > 0 {
            let spots = self.box_spots(app, shown);
            self.state.cursor.set(row + 1 + tab_box::spot_from_below(&spots));
        }
    }

    fn move_inside_box(&self, app: &App, shown: &Shown, name: &str, row: usize, here: usize) {
        let spots = self.box_spots(app, shown);
        let there = if name == "down" {
            tab_box::spot_below(&spots, here)
        } else {
            tab_box::spot_above(&spots, here)
        };
        if there == ON_TAB_ROW {
            self.state.cursor.set(row);
        } else if there == tab_box::BELOW_BOX {
            let below = row + spots.len() + 1;
            if below < shown.fields.len() {
                self.state.cursor.set(below);
            }
        } else {
            self.state.cursor.set(row + 1 + there as usize);
        }
    }

    fn move_in_order(&self, shown: &Shown, name: &str) {
        let first_button = shown.first_button_place();
        let place = self.place(shown);
        let moved = |count: usize| {
            let step: i64 = if name == "up" || name == "left" { -1 } else { 1 };
            (place as i64 + step).clamp(0, count as i64 - 1) as usize
        };
        if self.state.stacked_buttons.get() {
            self.state.cursor.set(moved(shown.fields.len()));
            return;
        }
        if place >= first_button {
            if name == "up" && first_button > 0 {
                self.state.cursor.set(first_button - 1);
            }
            return;
        }
        self.state.cursor.set(moved((first_button + 1).min(shown.fields.len())));
    }

    fn move_across(&self, app: &App, shown: &Shown, direction: i64) {
        let row = shown.box_place().expect("a page with a tab box");
        let here = self.place(shown) - row - 1;
        let spots = self.box_spots(app, shown);
        self.state.cursor.set(row + 1 + tab_box::spot_beside(&spots, here, direction));
    }

    fn move_along_buttons(&self, shown: &Shown, name: &str) {
        let first_button = shown.first_button_place();
        let count = shown.fields.len() - first_button;
        let step: i64 = if name == "left" { -1 } else { 1 };
        let place = (self.place(shown) as i64 - first_button as i64 + step).clamp(0, count as i64 - 1);
        self.state.cursor.set(first_button + place as usize);
    }

    fn move_along_cells(&self, shown: &Shown, name: &str) {
        let count = shown.fields[self.place(shown)].cells.len();
        let step: i64 = if name == "left" { -1 } else { 1 };
        self.state.cell.set((self.state.cell.get() as i64 + step).clamp(0, count as i64 - 1) as usize);
    }

    fn step_tab(&self, app: &mut App, shown: &Shown, direction: i64) {
        let Some(tab_box) = shown.tab_box() else { return };
        let place = (shown.chosen as i64 + direction).clamp(0, tab_box.tabs.len() as i64 - 1) as usize;
        app.session.chosen_tabs.insert(self.form.name().to_string(), tab_box.tabs[place].label.clone());
    }

    fn page_through_tabs(&self, app: &mut App, shown: &Shown, direction: i64) {
        let row = shown.box_place().expect("a page with a tab box");
        let spots = self.box_spots(app, shown);
        let spot = spots[self.place(shown) - row - 1];
        self.step_tab(app, shown, direction);
        let after = self.shown(app);
        if after.box_field_count() == 0 {
            self.state.cursor.set(row);
            return;
        }
        let spots = self.box_spots(app, &after);
        self.state.cursor.set(row + 1 + tab_box::spot_like(&spots, spot));
    }

    fn jump_section(&self, shown: &Shown, direction: i64) {
        let place = self.place(shown);
        let headings: Vec<usize> = (0..shown.fields.len()).filter(|each| shown.fields[*each].is_heading()).collect();
        let found = if direction > 0 {
            headings.iter().find(|each| **each > place)
        } else {
            headings.iter().rfind(|each| **each < place)
        };
        if let Some(found) = found {
            self.state.cursor.set(*found);
        }
    }

    // The drawing.

    fn label_width(&self, app: &App, shown: &Shown) -> usize {
        shown
            .every_field()
            .filter(|field| !field.is_button())
            .map(|field| field.drawn_label(Self::is_open(app, field)).chars().count())
            .max()
            .unwrap_or(0)
            + 2
    }

    fn draw(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        let shown = self.shown(app);
        let cursor = self.place(&shown);
        self.cell_field(&shown);
        let open = |field: &Field| Self::is_open(app, field);
        let looks = self.looks(&open);
        let mut lines = vec![Text::default()];
        let mut selected = 0;
        let label_width = self.label_width(app, &shown);
        let first_button = shown.first_button_place();
        let mut seen_heading = false;
        let mut inside_box = 0;
        for (place, field) in shown.fields[..first_button].iter().enumerate() {
            if inside_box > 0 {
                inside_box -= 1;
                continue;
            }
            if field.is_tab_row() {
                // A tab box stands apart from the settings above it by a blank line, as a section does.
                if lines.last().is_some_and(|line| !line.text().is_empty()) {
                    lines.push(Text::default());
                }
                let tab_box = shown.tab_box().expect("a row of tabs has its box");
                let count = tab_box.tabs[shown.chosen].field_count();
                let inside = if cursor == place {
                    Some(ON_TAB_ROW)
                } else if place < cursor && cursor <= place + count {
                    Some((cursor - place - 1) as i64)
                } else {
                    None
                };
                self.state.box_width.set(width);
                let (drawn, box_selected) = box_lines(&looks, tab_box, shown.chosen, inside, width);
                if let Some(line) = box_selected {
                    selected = lines.len() + line;
                }
                lines.extend(drawn);
                lines.push(Text::default());
                inside_box = count;
                continue;
            }
            if field.is_heading() && (!seen_heading || self.form.headings_apart()) {
                seen_heading = true;
                if place > 0 {
                    lines.push(Text::default());
                }
            }
            if place == cursor {
                selected = lines.len() + field.selected_line();
            }
            lines.extend(field_lines(field, &looks, place == cursor, label_width, width));
            if field.may_leave_a_gap() && self.has_gap_after(place, field, &shown) {
                lines.push(Text::default());
            }
        }
        let buttons = &shown.fields[first_button..];
        if !buttons.is_empty() {
            let place = cursor as i64 - first_button as i64;
            lines.push(Text::default());
            let row = self.row_of_buttons(buttons, place, width);
            if place >= 0 {
                selected = lines.len() + if self.state.stacked_buttons.get() { place as usize } else { 1 };
            }
            lines.extend(row);
        }
        let remarks = self.form.remarks(app, width);
        if !remarks.is_empty() {
            lines.push(Text::default());
            lines.extend(remarks);
        }
        self.window_of_lines(lines, selected, height)
    }

    fn has_gap_after(&self, place: usize, field: &Field, shown: &Shown) -> bool {
        if place == 0 && field.label == labels::MSG_NAME_LABEL && shown.fields.len() > 1 && !shown.fields[1].is_button() {
            return true;
        }
        self.form.ends_a_list(field)
    }

    fn row_of_buttons(&self, buttons: &[Field], selected: i64, width: usize) -> Vec<Text> {
        let keys_and_names: Vec<(String, String)> = buttons.iter().map(|button| (button.key_name.clone(), button.label.clone())).collect();
        let selected_place = usize::try_from(selected).ok();
        let row: Vec<Text> = button_row(&keys_and_names, selected_place)
            .into_iter()
            .map(|line| {
                let mut indented = Text::plain(INDENT);
                indented.append_text(&line);
                indented
            })
            .collect();
        let stacked = row.iter().map(Text::cell_len).max().unwrap_or(0) > width;
        self.state.stacked_buttons.set(stacked);
        if !stacked {
            return row;
        }
        buttons
            .iter()
            .enumerate()
            .map(|(place, button)| {
                let here = selected_place == Some(place);
                let mut line = Text::plain(cursor_mark(here));
                line.append(
                    &named(marks::MSG_STACKED_BUTTON, &[("name", button.label.as_str().into())]),
                    if here { Style::BOLD } else { Style::PLAIN },
                );
                line
            })
            .collect()
    }

    fn window_of_lines(&self, lines: Vec<Text>, selected: usize, height: usize) -> Vec<Text> {
        if lines.len() <= height {
            self.state.first_line.set(0);
            return lines;
        }
        let first = self.state.first_line.get().max((selected + 1).saturating_sub(height)).min(selected);
        let first = first.min(lines.len() - height);
        self.state.first_line.set(first);
        lines[first..first + height].to_vec()
    }

    /// The edit a field's key makes, by the binding pressed.
    /// Rename what the page shows from its Name field, or hand the page ENTER on the field where it renames another way.
    fn rename_or_apply(&mut self, app: &mut App, id: usize) {
        if self.form.rename(app).is_none() {
            self.form.apply(app, id, Edit::Enter);
        }
    }

    fn edit_of(&self, field: &Field, item: &KeyItem) -> Option<Edit> {
        if let Some((less, more)) = self.form.slot_keys() {
            if item.is(more) {
                return Some(field.adjusted(1));
            }
            if item.is(less) {
                return Some(field.adjusted(-1));
            }
        }
        if item.is(&Keys::MORE) {
            return Some(field.adjusted(1));
        }
        if item.is(&Keys::LESS) {
            return Some(field.adjusted(-1));
        }
        if item.is(&Keys::TOGGLE) || item.is(&Keys::ENTER) {
            return Some(field.entered());
        }
        if item.is(&Keys::CLEAR) {
            return Some(field.cleared());
        }
        None
    }
}

impl<F: Form> Page for FieldPage<F> {
    /// The field or button the cursor is on, by its label, so that every field's keys are tried.
    fn place_kind(&self, app: &App) -> String {
        let shown = self.shown(app);
        let field = shown
            .fields
            .get(self.place(&shown))
            .map(|field| field.label.trim().to_string())
            .unwrap_or_default();
        format!("{} {field}", self.form.edited_kind())
    }

    fn follow_renames(&mut self, renames: &crate::history::Renames) {
        self.form.follow_renames(renames);
    }

    fn still_exists(&self, app: &App) -> bool {
        self.form.still_exists(app)
    }

    fn help(&self) -> Option<Vec<String>> {
        self.form.help()
    }

    fn answered(&mut self, app: &mut App, answer: crate::screens::dialogs::Answer) {
        use crate::screens::dialogs::Answer;
        let Some((id, asking)) = self.asking.take() else { return };
        let edit = match (asking, answer) {
            (Asking::Choice(choices), Answer::Chosen(place)) => match choices.get(place) {
                Some(chosen) => Edit::Choice(chosen.clone()),
                None => return,
            },
            (Asking::Number(lowest, highest), Answer::Typed(text)) => {
                let Ok(number) = text.trim().parse::<i64>() else {
                    app.refuse(&named(llamatron_strings::errors::ERR_TYPED_NOT_AN_INTEGER, &[("text", text.as_str().into())]));
                    return;
                };
                if lowest.is_some_and(|lowest| number < lowest) || highest.is_some_and(|highest| number > highest) {
                    let bound = |bound: Option<i64>| bound.map_or_else(|| "None".to_string(), |bound| bound.to_string());
                    let words = [
                        ("number", number.into()),
                        ("low", bound(lowest).as_str().into()),
                        ("high", bound(highest).as_str().into()),
                    ];
                    app.refuse(&named(llamatron_strings::errors::ERR_OUT_OF_RANGE, &words));
                    return;
                }
                Edit::Number(number)
            }
            (Asking::Text, Answer::Typed(text)) => Edit::Text(text),
            _ => return,
        };
        // An answer may ask again, as a picker's choice of a number to type does.
        self.ask_or_apply(app, id, edit);
    }

    fn name(&self) -> &'static str {
        if self.ported.get() {
            self.form.name()
        } else {
            crate::screens::not_ported::NOT_PORTED
        }
    }

    fn stack_name(&self) -> &str {
        self.form.name()
    }

    fn class(&self) -> &'static KeyClass {
        self.form.class()
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        let shown = self.shown(app);
        let mut result = vec![self.bind(&Keys::SELECT).wanting_key()];
        let place = self.place(&shown);
        let row = shown.fields.get(place);
        if let Some(row) = row {
            if row.is_tab_row() {
                result.push(self.bind(&Keys::ALONG_TABS));
            } else if row.is_cells() {
                result.push(self.bind(&Keys::ALONG_CELLS).wanting_key());
                let cell = row.cells.get(self.state.cell.get().min(row.cells.len().saturating_sub(1)));
                // The cell under the cursor steps by the page's own keys for a slot, or by [ and ] where it has none.
                if row.stepped_cells && cell.is_some_and(|cell| cell.adjusts) {
                    let (less, more) = self.form.slot_keys().unwrap_or((&Keys::LESS, &Keys::MORE));
                    result.push(self.bind(more));
                    result.push(self.bind(less));
                }
            } else if row.adjusts {
                result.push(self.bind(&Keys::MORE));
                result.push(self.bind(&Keys::LESS));
            }
        }
        let field = self.cell_field(&shown);
        if let Some(field) = field {
            if field.enters && field.is_toggle() {
                result.push(self.bind(&Keys::TOGGLE));
            } else if field.enters {
                result.push(self.bind(&Keys::ENTER).saying(&field.enter_what));
            }
            if field.clears {
                result.push(self.bind(&Keys::CLEAR).saying(&field.clear_what));
            }
        }
        if shown.every_field().any(|each| each.kind == Kind::Name) {
            result.push(self.bind(&Keys::RENAME));
        }
        if place >= shown.first_button_place() && field.is_some() && !self.state.stacked_buttons.get() {
            result.push(self.bind(&Keys::ALONG_BUTTONS).wanting_key());
        }
        if shown.tab_box().is_some() {
            result.extend(self.box_keys(app, &shown, row));
        }
        if shown.every_field().any(Field::is_heading) && !self.in_box(&shown) {
            result.push(self.bind(&Keys::SECTION));
        }
        result.extend(self.form.page_keys(app, row));
        let mut keys = vec![self.bind(&Keys::BACK)];
        keys.extend(result);
        keys
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        let shown = self.shown(app);
        let direction = item.step_of(key).unwrap_or(0);
        if item.is(&Keys::BACK) {
            app.go_back();
        } else if item.is(&Keys::SELECT) {
            self.move_cursor(app, &shown, key);
        } else if item.is(&Keys::ALONG_BUTTONS) {
            self.move_along_buttons(&shown, key);
        } else if item.is(&Keys::ALONG_CELLS) {
            self.move_along_cells(&shown, key);
        } else if item.is(&Keys::ALONG_TABS) {
            self.step_tab(app, &shown, direction);
        } else if item.is(&Keys::TO_TABS) {
            self.state.cursor.set(shown.box_place().unwrap_or(0));
        } else if item.is(&Keys::INTO_TAB) {
            if shown.box_field_count() > 0 {
                self.state.cursor.set(shown.box_place().unwrap_or(0) + 1);
            }
        } else if item.is(&Keys::TAB_PAGES) {
            self.page_through_tabs(app, &shown, direction);
        } else if item.is(&Keys::ACROSS) {
            self.move_across(app, &shown, direction);
        } else if item.is(&Keys::SECTION) {
            self.jump_section(&shown, direction);
        } else if item.is(&Keys::RENAME) {
            if let Some(name) = shown.every_field().find(|each| each.kind == Kind::Name) {
                let id = name.id;
                self.rename_or_apply(app, id);
            }
        } else if let Some(field) = self.cell_field(&shown).cloned() {
            match self.edit_of(&field, item) {
                Some(Edit::Enter) if field.kind == Kind::Name => self.rename_or_apply(app, field.id),
                Some(_) if field.is_heading() => {
                    let label = field.label.clone();
                    if !app.session.open_field_sections.remove(&label) {
                        app.session.open_field_sections.insert(label);
                    }
                }
                Some(edit) => self.ask_or_apply(app, field.id, edit),
                None => {
                    let row = shown.fields.get(self.place(&shown)).cloned();
                    self.form.press_own(app, item, key, row.as_ref())
                }
            }
        } else {
            let row = shown.fields.get(self.place(&shown)).cloned();
            self.form.press_own(app, item, key, row.as_ref());
        }
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        self.ported.set(self.form.is_ported(app));
        self.draw(app, width, height)
    }

    fn crumbs(&self, app: &App) -> Vec<String> {
        self.form.crumbs(app)
    }

    fn theme(&self) -> Option<Colour> {
        self.form.theme()
    }

    fn caption(&self, app: &App) -> String {
        self.form
            .caption(app)
            .unwrap_or_else(|| self.form.crumbs(app).last().map(|crumb| crumb.to_uppercase()).unwrap_or_default())
    }

    fn duration(&self, app: &App) -> Duration {
        self.form.duration(app)
    }
}
