// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What a pattern's step may hold on each row, checked as a file opens: a Degree a scale degree, or a note letter in a
//! drum pattern; a Gate a length; a number row a whole number within its limits; a choice row one of its choices; a
//! chosen-set row a few of its choices, each once; an on or off row true or false, never blank; a draw's row 1, -1 or 0;
//! a statement's row one of its parts' choices, or a number or a draw's name. A row that means nothing without a chord or
//! a scale, such as Chord, Tension or a draw's Note row, is refused on a drum pattern. A blank step is never asked about,
//! except on an on or off row.

use crate::file::data::Data;
use crate::schema::checking::{listed, plain_data, written_length, InvalidValue};
use crate::schema::generated::file_format::{
    Row, BASS_NOTES, CC_ROWS, CHORD_SYMBOLS, DOUBLINGS, DRAW_NOTE_ROWS, DRAW_RESET_ROWS, DRAW_VELOCITY_ROWS, KEYSWITCH_SLOTS, NOTE_LETTERS, OMISSIONS,
    STATEMENT_OF_ROW, TENSIONS, VALUE_NAMES,
};
use crate::schema::generated::limits::{INVERSIONS, MAX_GATE, MAX_STATEMENT_NUMBER, MIN_DEGREE};
use crate::schema::generated::rows::{RowDescription, ROW_DESCRIPTIONS};
use crate::values::scale::ScaleType;
use llamatron_math::Rational;
use llamatron_strings::{errors, named};

/// The part of a statement a row holds that is a number or a draw's name, rather than a choice.
const STATEMENT_VALUE_PARTS: [&str; 2] = ["value", "against"];
/// What a draw's row adds of the draw: the draw, its negative, or nothing.
const DRAW_USES: [i128; 3] = [1, -1, 0];

/// How a row's steps are checked.
enum StepCheck {
    Degree,
    Gate,
    Octave,
    /// A whole number within the row's limits.
    Number,
    /// One of the row's choices, refused in these words, and on a drum pattern in those, where it means nothing there.
    Choice {
        problem: String,
        on_drums: Option<&'static str>,
    },
    /// The Chord row, whose symbols a file may write as a bare number.
    Chord,
    /// A few of the row's choices, each once.
    ChosenSet {
        problem: String,
        on_drums: Option<&'static str>,
    },
    Toggle,
    /// A draw's row: 1, -1 or 0, or true or false from an older file; a Note row moves notes, which a drum pattern has none
    /// to move.
    DrawUse {
        moves_notes: bool,
    },
    StatementValue,
}

/// The check of a row, by its name.
fn check_of(row: &str) -> StepCheck {
    let choices = |items: &[&str]| listed(items);
    let numbers = |items: &[i64]| listed(&items.iter().map(i64::to_string).collect::<Vec<_>>());
    let named_choices = |template: &str, list: String| named(template, &[("choices", list.into())]);
    match row {
        Row::DEGREE => StepCheck::Degree,
        Row::GATE => StepCheck::Gate,
        Row::OCTAVE => StepCheck::Octave,
        Row::DOT => StepCheck::Choice {
            problem: errors::ERR_NOT_GATE_MODIFIER.to_string(),
            on_drums: None,
        },
        Row::ACCIDENTAL => StepCheck::Choice {
            problem: errors::ERR_NOT_ACCIDENTAL.to_string(),
            on_drums: None,
        },
        Row::CHORD => StepCheck::Chord,
        Row::INVERSION => StepCheck::Choice {
            problem: named_choices(errors::ERR_NOT_INVERSION, numbers(INVERSIONS)),
            on_drums: Some(errors::ERR_INVERSION_ON_DRUMS),
        },
        Row::DOUBLE => StepCheck::Choice {
            problem: named_choices(errors::ERR_NOT_DOUBLING, choices(DOUBLINGS)),
            on_drums: Some(errors::ERR_DOUBLING_ON_DRUMS),
        },
        Row::OMIT => StepCheck::Choice {
            problem: named_choices(errors::ERR_NOT_OMISSION, choices(OMISSIONS)),
            on_drums: Some(errors::ERR_OMISSION_ON_DRUMS),
        },
        Row::BASS => StepCheck::Choice {
            problem: named_choices(
                errors::ERR_NOT_BASS_NOTE,
                choices(&BASS_NOTES.iter().map(|(name, _)| *name).collect::<Vec<_>>()),
            ),
            on_drums: Some(errors::ERR_BASS_NOTE_ON_DRUMS),
        },
        Row::CHORD_SCALE => StepCheck::Choice {
            problem: named_choices(errors::ERR_NOT_CHORD_SCALE, listed(&ScaleType::file_names())),
            on_drums: Some(errors::ERR_CHORD_SCALE_ON_DRUMS),
        },
        Row::TENSION => StepCheck::ChosenSet {
            problem: named_choices(errors::ERR_NOT_TENSIONS, choices(&TENSIONS.iter().map(|(name, _)| *name).collect::<Vec<_>>())),
            on_drums: Some(errors::ERR_TENSION_ON_DRUMS),
        },
        Row::KEYSWITCH => StepCheck::ChosenSet {
            problem: named_choices(errors::ERR_NOT_KEYSWITCHES, numbers(KEYSWITCH_SLOTS)),
            on_drums: None,
        },
        row if DRAW_NOTE_ROWS.iter().any(|(_, name)| *name == row) => StepCheck::DrawUse { moves_notes: true },
        row if DRAW_VELOCITY_ROWS.iter().any(|(_, name)| *name == row) => StepCheck::DrawUse { moves_notes: false },
        row if DRAW_RESET_ROWS.iter().any(|(_, name)| *name == row) => StepCheck::Toggle,
        row if CC_ROWS.contains(&row) => StepCheck::Number,
        row => match STATEMENT_OF_ROW.iter().find(|(name, _)| *name == row) {
            Some((_, parts)) if STATEMENT_VALUE_PARTS.contains(&parts[1]) => StepCheck::StatementValue,
            Some(_) => StepCheck::Choice {
                problem: String::new(),
                on_drums: None,
            },
            None if described(row).is_some_and(|description| description.lowest.is_some()) => StepCheck::Number,
            None => StepCheck::Toggle,
        },
    }
}

/// A row's description, where it has one.
fn described(row: &str) -> Option<&'static RowDescription> {
    ROW_DESCRIPTIONS.iter().find(|description| description.name == row)
}

/// Whether a value is one of a row's choices as its description lists them.
fn is_a_choice(row: &str, value: &Data) -> bool {
    described(row).is_some_and(|description| description.choices.iter().any(|choice| plain_data(choice) == *value))
}

/// Refuse a value a step of a row cannot hold, saying which row and what the value has to be; a blank step is refused
/// only on an on or off row, which a file never leaves blank.
pub fn check_step(row: &str, value: &Data, drum: bool) -> Result<(), InvalidValue> {
    let check = check_of(row);
    if value.is_null() {
        if matches!(check, StepCheck::Toggle) {
            return Err(InvalidValue::new(named(errors::ERR_TOGGLE_IS_NULL, &[("row", row.into())])));
        }
        return Ok(());
    }
    if let StepCheck::Gate = check {
        return written_length(value, Rational::whole(MAX_GATE as i128)).map(|_| ());
    }
    let description = described(row);
    let lowest = description.and_then(|description| description.lowest).unwrap_or(0);
    let highest = description.and_then(|description| description.highest).unwrap_or(0);
    if let StepCheck::Octave = check {
        let fits = value.as_whole().is_some_and(|octave| (lowest as i128..=highest as i128).contains(&octave));
        if !fits {
            let message = named(
                errors::ERR_CHECKS_BAD_OCTAVE,
                &[("lowest", lowest.into()), ("highest", highest.into()), ("value", value.into())],
            );
            return Err(InvalidValue::new(message));
        }
        return Ok(());
    }
    let problem = match check {
        StepCheck::Degree if drum => unless(is_note_letter(value), errors::ERR_NOT_NOTE_LETTER.to_string()),
        StepCheck::Degree => {
            let degree = value.as_whole().is_some_and(|degree| degree >= MIN_DEGREE as i128);
            unless(degree, named(errors::ERR_NOT_DEGREE, &[("lowest", MIN_DEGREE.into())]))
        }
        StepCheck::Number => {
            let within = value.as_whole().is_some_and(|number| (lowest as i128..=highest as i128).contains(&number));
            unless(
                within,
                named(errors::ERR_NOT_IN_RANGE, &[("lowest", lowest.into()), ("highest", highest.into())]),
            )
        }
        StepCheck::Chord if drum => Some(errors::ERR_CHORD_ON_DRUMS.to_string()),
        StepCheck::Chord => {
            let symbol = CHORD_SYMBOLS.contains(&value.python_str().as_str());
            unless(symbol, named(errors::ERR_NOT_CHORD, &[("symbols", listed(CHORD_SYMBOLS).into())]))
        }
        StepCheck::Choice { on_drums: Some(on_drums), .. } if drum => Some(on_drums.to_string()),
        StepCheck::Choice { problem, .. } if problem.is_empty() => {
            let choices: Vec<String> = described(row).map_or(Vec::new(), |description| {
                description.choices.iter().map(|choice| plain_data(choice).python_str()).collect()
            });
            unless(
                is_a_choice(row, value),
                named(errors::ERR_NOT_STATEMENT_CHOICE, &[("choices", listed(&choices).into())]),
            )
        }
        StepCheck::Choice { problem, .. } => unless(is_a_choice(row, value), problem),
        StepCheck::ChosenSet { on_drums: Some(on_drums), .. } if drum => Some(on_drums.to_string()),
        StepCheck::ChosenSet { problem, .. } => unless(is_chosen_set(row, value), problem),
        StepCheck::Toggle => unless(matches!(value, Data::Bool(_)), errors::ERR_PATTERN_NOT_TRUE_OR_FALSE.to_string()),
        StepCheck::DrawUse { moves_notes } => {
            let used = match value {
                Data::Bool(on) => Some(i128::from(*on)),
                Data::Whole(whole) if DRAW_USES.contains(whole) => Some(*whole),
                _ => None,
            };
            match used {
                None => Some(errors::ERR_NOT_REGISTER_USE.to_string()),
                Some(used) if moves_notes && drum && used != 0 => Some(errors::ERR_REGISTER_NOTE_ON_DRUMS.to_string()),
                Some(_) => None,
            }
        }
        StepCheck::StatementValue => {
            let named_draw = value.as_str().is_some_and(|name| VALUE_NAMES.contains(&name));
            let number = value.as_whole().is_some_and(|number| number.abs() <= MAX_STATEMENT_NUMBER as i128);
            let choices = listed(VALUE_NAMES);
            let bounds = [
                ("lowest", (-MAX_STATEMENT_NUMBER).into()),
                ("highest", MAX_STATEMENT_NUMBER.into()),
                ("choices", choices.into()),
            ];
            unless(named_draw || number, named(errors::ERR_NOT_STATEMENT_VALUE, &bounds))
        }
        StepCheck::Gate | StepCheck::Octave => None,
    };
    match problem {
        Some(problem) => Err(InvalidValue::new(named(
            errors::ERR_BAD_STEP_VALUE,
            &[("row", row.into()), ("problem", problem.into()), ("value", value.into())],
        ))),
        None => Ok(()),
    }
}

/// Whether a value is one note letter, A to G, as a drum pattern's Degree row holds.
fn is_note_letter(value: &Data) -> bool {
    value
        .as_str()
        .is_some_and(|letter| letter.chars().count() == 1 && NOTE_LETTERS.contains(letter))
}

/// Whether a value is a list of some of a row's choices, each once.
fn is_chosen_set(row: &str, value: &Data) -> bool {
    let Some(items) = value.as_list() else { return false };
    let each_once = items.iter().enumerate().all(|(place, item)| !items[..place].contains(item));
    !items.is_empty() && each_once && items.iter().all(|item| is_a_choice(row, item))
}

/// The problem, where what a step must be does not hold; nothing where it does.
fn unless(holds: bool, problem: String) -> Option<String> {
    if holds {
        None
    } else {
        Some(problem)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Each kind of row takes what it may hold and refuses the rest, a drum pattern refusing what needs a chord or scale.
    #[test]
    fn each_row_takes_its_values_and_refuses_the_rest() {
        let taken = [
            (Row::DEGREE, Data::Whole(3), false),
            (Row::DEGREE, Data::text("C"), true),
            (Row::GATE, Data::text("1/8"), false),
            (Row::VELOCITY, Data::Whole(90), false),
            (Row::CHORD, Data::Whole(7), false),
            (Row::TENSION, Data::List(vec![Data::text("9")]), false),
            (Row::KEYSWITCH, Data::List(vec![Data::Whole(0), Data::Whole(2)]), true),
            (Row::TIE, Data::Bool(true), false),
            ("ad_note", Data::Whole(-1), false),
            ("ad_note", Data::Whole(0), true),
            ("stop_c3", Data::text("AD"), false),
        ];
        for (row, value, drum) in &taken {
            assert!(check_step(row, value, *drum).is_ok(), "{row} {value:?}");
        }
        let refused = [
            (Row::DEGREE, Data::text("banana"), false),
            (Row::DEGREE, Data::Whole(3), true),
            (Row::VELOCITY, Data::Whole(500), false),
            (Row::CHORD, Data::text("M"), true),
            (Row::TENSION, Data::List(vec![Data::text("9"), Data::text("9")]), false),
            (Row::TIE, Data::Null, false),
            ("ad_note", Data::Whole(1), true),
            ("stop_c2", Data::text("about"), false),
        ];
        for (row, value, drum) in &refused {
            assert!(check_step(row, value, *drum).is_err(), "{row} {value:?}");
        }
    }
}
