// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The fields a settings page is made of (the Python forms/nodes.py): a Field is a label, the text of its value, and what
//! [ and ], ENTER and Bksp do there. A field's kind says what most settings are, and works out what a key makes of it: a page
//! is handed that as an Edit to store, by the field's id, so that a setting's behaviour is said once, in its kind.

use llamatron_strings::{labels, legends, marks, named};

/// How the tracker draws a field.
#[derive(Clone, Debug, PartialEq)]
pub enum Drawn {
    SettingLine,
    Button,
    Heading,
    Cells,
    TableRow {
        widths: Vec<usize>,
    },
    CaptionedTableRow {
        widths: Vec<usize>,
        caption: String,
        headings: Vec<String>,
    },
    Strip {
        lit: Option<usize>,
    },
    TabRow,
    /// A line of a table of statements, the first drawing the grid's top edge and the last its bottom edge.
    StatementRow {
        first: bool,
        last: bool,
    },
}

/// What a field's value is, which says what its keys do.
#[derive(Clone, Debug, PartialEq)]
pub enum Kind {
    /// What the page says of each key, its own actions by the field's id.
    Custom,
    Toggle {
        on: bool,
    },
    Name,
    Number {
        number: Option<i64>,
        lowest: Option<i64>,
        highest: Option<i64>,
        start: i64,
    },
    Choice {
        choices: Vec<String>,
        current: String,
        names: Option<Vec<String>>,
        picked: Option<String>,
    },
    Text {
        current: String,
        blank: String,
    },
    Button,
    Heading {
        starts_open: bool,
    },
}

/// What a key did to a field, for its page to store or act on.
#[derive(Clone, Debug, PartialEq)]
pub enum Edit {
    Toggle(bool),
    Number(i64),
    Choice(String),
    Text(String),
    /// The setting left out, Bksp's.
    Clear,
    /// A custom field's [ or ] , by its direction.
    Adjust(i64),
    /// A custom field's or a button's ENTER, or a name's rename.
    Enter,
    /// A number to type, a choice to pick or text to type, which a dialog asks.
    AskNumber {
        title: String,
        value: i64,
        lowest: Option<i64>,
        highest: Option<i64>,
    },
    AskChoice {
        title: String,
        options: Vec<String>,
        current: usize,
        choices: Vec<String>,
    },
    AskText {
        title: String,
        value: String,
    },
}

#[derive(Clone, Debug)]
pub struct Field {
    pub id: usize,
    pub label: String,
    pub shown_label: Option<String>,
    value: String,
    pub kind: Kind,
    pub drawn: Drawn,
    pub adjusts: bool,
    pub enters: bool,
    pub enter_what: String,
    pub clears: bool,
    pub clear_what: String,
    pub key_name: String,
    /// A heading's mark of something set inside, or what it says in its place.
    pub said: Option<String>,
    pub is_set: bool,
    pub cells: Vec<Field>,
    /// Whether the cells step with [ and ], as a drift's two versions do.
    pub stepped_cells: bool,
}

/// The next value in a list, starting from the middle where the current one isn't there, stopping at both ends.
pub fn stepped(values: &[String], current: &str, offset: i64) -> String {
    let place = values.iter().position(|value| value == current).unwrap_or(values.len() / 2) as i64;
    values[(place + offset).clamp(0, values.len() as i64 - 1) as usize].clone()
}

pub fn within(number: i64, lowest: Option<i64>, highest: Option<i64>) -> i64 {
    let number = lowest.map_or(number, |low| number.max(low));
    highest.map_or(number, |high| number.min(high))
}

impl Field {
    fn plain(id: usize, label: &str, value: &str, kind: Kind) -> Field {
        Field {
            id,
            label: label.to_string(),
            shown_label: None,
            value: value.to_string(),
            kind,
            drawn: Drawn::SettingLine,
            adjusts: false,
            enters: false,
            enter_what: legends::What::EDIT.to_string(),
            clears: false,
            clear_what: legends::What::CLEAR.to_string(),
            key_name: String::new(),
            said: None,
            is_set: false,
            cells: Vec::new(),
            stepped_cells: false,
        }
    }

    /// A field whose keys the page says itself, by its id.
    pub fn custom(id: usize, label: &str, value: &str) -> Field {
        Field::plain(id, label, value, Kind::Custom)
    }

    pub fn toggle(id: usize, label: &str, on: bool) -> Field {
        let mut field = Field::plain(
            id,
            label,
            if on { marks::MSG_TOGGLE_ON } else { marks::MSG_FIELD_TOGGLE_OFF },
            Kind::Toggle { on },
        );
        field.enters = true;
        field.enter_what = legends::What::TOGGLE.to_string();
        field
    }

    pub fn name(id: usize, value: &str) -> Field {
        let mut field = Field::plain(id, labels::MSG_NAME_LABEL, value, Kind::Name);
        field.enters = true;
        field.enter_what = legends::What::RENAME.to_string();
        field
    }

    /// A whole number between two ends, either of which may be None; shown is its text where that isn't the number.
    pub fn number(id: usize, label: &str, number: Option<i64>, lowest: Option<i64>, highest: Option<i64>, start: i64, shown: Option<String>) -> Field {
        let value = shown.unwrap_or_else(|| number.unwrap_or(start).to_string());
        let mut field = Field::plain(
            id,
            label,
            &value,
            Kind::Number {
                number,
                lowest,
                highest,
                start,
            },
        );
        field.adjusts = true;
        field.enters = true;
        field
    }

    /// One of a fixed list of choices, shown as its text where given.
    pub fn choice(id: usize, label: &str, choices: Vec<String>, current: &str, shown: Option<String>) -> Field {
        let value = shown.unwrap_or_else(|| current.to_string());
        let mut field = Field::plain(
            id,
            label,
            &value,
            Kind::Choice {
                choices,
                current: current.to_string(),
                names: None,
                picked: None,
            },
        );
        field.adjusts = true;
        field.enters = true;
        field.enter_what = legends::What::CHOOSE.to_string();
        field
    }

    /// A line of text; a blank one shows (none), and Bksp blanks it.
    pub fn text(id: usize, label: &str, current: &str, blank: &str) -> Field {
        let value = if current.is_empty() { marks::MSG_NONE_SHOWN } else { current };
        let mut field = Field::plain(
            id,
            label,
            value,
            Kind::Text {
                current: current.to_string(),
                blank: blank.to_string(),
            },
        );
        field.enters = true;
        field.clears = true;
        field.clear_what = marks::MSG_NONE_SHOWN.to_string();
        field
    }

    /// A row that acts on ENTER, showing the key it stands for.
    pub fn button(id: usize, label: &str, key_name: &str, enter_what: &str) -> Field {
        let mut field = Field::plain(id, label, "", Kind::Button);
        field.drawn = Drawn::Button;
        field.enters = true;
        field.key_name = key_name.to_string();
        field.enter_what = enter_what.to_string();
        field
    }

    /// A section's heading; said is what it shows after its name in place of the mark of a value inside.
    pub fn heading(id: usize, label: &str, is_set: bool, said: Option<String>, starts_open: bool) -> Field {
        let mut field = Field::plain(id, label, "", Kind::Heading { starts_open });
        field.drawn = Drawn::Heading;
        field.enters = true;
        field.is_set = is_set;
        field.said = said;
        field
    }

    /// The row of tabs, where the cursor stops.
    pub fn tab_row(label: &str) -> Field {
        let mut field = Field::plain(usize::MAX, label, "", Kind::Custom);
        field.drawn = Drawn::TabRow;
        field
    }

    /// A row of settings side by side under one label.
    pub fn cells(id: usize, label: &str, cells: Vec<Field>) -> Field {
        let value = cells.iter().map(|cell| cell.value.clone()).collect::<Vec<_>>().join("  ");
        let mut field = Field::plain(id, label, &value, Kind::Custom);
        field.drawn = Drawn::Cells;
        field.cells = cells;
        field
    }

    /// A row of cells whose cell under the cursor [ and ] step, as a drift's two versions of a value.
    pub fn stepped(mut self) -> Field {
        self.stepped_cells = true;
        self
    }

    /// A row of a table of settings, each cell as wide as its column, and the table's first row with its caption above.
    pub fn table_row(mut self, widths: Vec<usize>, caption: Option<(String, Vec<String>)>) -> Field {
        self.stepped_cells = true;
        self.drawn = match caption {
            None => Drawn::TableRow { widths },
            Some((caption, headings)) => Drawn::CaptionedTableRow { widths, caption, headings },
        };
        self
    }

    pub fn with_clear(mut self, what: &str) -> Field {
        self.clears = true;
        self.clear_what = what.to_string();
        self
    }

    pub fn with_enter(mut self, what: &str) -> Field {
        self.enters = true;
        self.enter_what = what.to_string();
        self
    }

    pub fn with_adjust(mut self) -> Field {
        self.adjusts = true;
        self
    }

    pub fn with_shown_label(mut self, label: &str) -> Field {
        self.shown_label = Some(label.to_string());
        self
    }

    pub fn is_button(&self) -> bool {
        self.kind == Kind::Button
    }

    pub fn is_heading(&self) -> bool {
        matches!(self.kind, Kind::Heading { .. })
    }

    pub fn is_tab_row(&self) -> bool {
        self.drawn == Drawn::TabRow
    }

    pub fn is_cells(&self) -> bool {
        !self.cells.is_empty()
            || matches!(
                self.drawn,
                Drawn::Cells | Drawn::TableRow { .. } | Drawn::CaptionedTableRow { .. } | Drawn::Strip { .. }
            )
    }

    pub fn is_toggle(&self) -> bool {
        matches!(self.kind, Kind::Toggle { .. } | Kind::Heading { .. })
    }

    pub fn value(&self) -> &str {
        &self.value
    }

    /// Which of the lines the field draws holds the cursor.
    pub fn selected_line(&self) -> usize {
        match self.drawn {
            Drawn::Button => 1,
            Drawn::CaptionedTableRow { .. } => 1,
            Drawn::Strip { .. } => 4,
            Drawn::StatementRow { first: true, .. } => 1,
            _ => 0,
        }
    }

    /// Whether a blank line may follow the field.
    pub fn may_leave_a_gap(&self) -> bool {
        !matches!(
            self.drawn,
            Drawn::Heading | Drawn::Cells | Drawn::TableRow { .. } | Drawn::CaptionedTableRow { .. } | Drawn::Strip { .. } | Drawn::StatementRow { .. }
        )
    }

    /// The label as drawn: its shown label where it has one, and a heading's after its open or closed mark.
    pub fn drawn_label(&self, open: bool) -> String {
        if self.is_heading() {
            let mark = if open { marks::MSG_SECTION_OPEN_MARK } else { marks::MSG_SECTION_CLOSED_MARK };
            return named(labels::MSG_SECTION_LABEL, &[("mark", mark.into()), ("name", self.label.as_str().into())]);
        }
        self.shown_label.clone().unwrap_or_else(|| self.label.clone())
    }

    /// A heading's value: what it says, or the mark of a value set inside.
    pub fn heading_value(&self) -> String {
        match &self.said {
            Some(said) => said.clone(),
            None if self.is_set => marks::MSG_SECTION_SET.to_string(),
            None => String::new(),
        }
    }

    /// What [ or ] makes of the field.
    pub fn adjusted(&self, offset: i64) -> Edit {
        match &self.kind {
            Kind::Number {
                number,
                lowest,
                highest,
                start,
            } => Edit::Number(within(number.unwrap_or(*start) + offset, *lowest, *highest)),
            Kind::Choice { choices, current, .. } => Edit::Choice(stepped(choices, current, offset)),
            _ => Edit::Adjust(offset),
        }
    }

    /// What ENTER (or Space on a toggle) makes of the field.
    pub fn entered(&self) -> Edit {
        match &self.kind {
            Kind::Toggle { on } => Edit::Toggle(!on),
            Kind::Number {
                number,
                lowest,
                highest,
                start,
            } => Edit::AskNumber {
                title: self.label.clone(),
                value: number.unwrap_or(*start),
                lowest: *lowest,
                highest: *highest,
            },
            Kind::Choice {
                choices,
                current,
                names,
                picked,
            } => {
                let opens_on = picked.as_deref().unwrap_or(current);
                let place = choices.iter().position(|choice| choice == opens_on).unwrap_or(0);
                Edit::AskChoice {
                    title: self.label.clone(),
                    options: names.clone().unwrap_or_else(|| choices.clone()),
                    current: place,
                    choices: choices.clone(),
                }
            }
            Kind::Text { current, .. } => Edit::AskText {
                title: self.label.clone(),
                value: current.clone(),
            },
            _ => Edit::Enter,
        }
    }

    /// What Bksp makes of the field.
    pub fn cleared(&self) -> Edit {
        match &self.kind {
            Kind::Text { blank, .. } => Edit::Text(blank.clone()),
            _ => Edit::Clear,
        }
    }
}
