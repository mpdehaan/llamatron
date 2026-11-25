// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The pattern editor's whole-pattern keys (the Python pattern_editor.py's): S asks for the number of steps, N renames the
//! pattern, R reconfigures it (load over, step size, time signature, drum, direction, rename, scale length) and M munges
//! it, rearranging, copying, clearing and reshaping its steps. Each answers through the editor's cursor request: a step to
//! put the cursor on, or the top of the rows view.

use crate::app::App;
use crate::screens::dialogs::{Answer, ChoiceDialog, ConfirmDialog, MessageDialog, PromptDialog};
use crate::screens::grouped_choice_dialog::GroupedChoiceDialog;
use crate::settings::sorted_names;
use llamatron_math::python_random::PythonRandom;
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::pattern::Pattern;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::{Section, DIRECTIONS};
use llamatron_model::schema::generated::limits::{MAX_SCALE_LENGTH, MAX_STEPS, MAX_STEP_SIZE, MIN_SCALE_LENGTH, MIN_STEPS};
use llamatron_model::schema::generated::midi::{MAX_VELOCITY, MIN_VELOCITY};
use llamatron_strings::{errors, labels, legends, marks, messages, named};
use std::cell::RefCell;

/// What the cursor request says to send the rows view to its top.
pub const TOP: &str = "top";
/// The fewest steps a pattern is rolled or split into.
const FIRST_ROLL: usize = 1;
/// How many steps each new pattern of a split has unless told otherwise, and how many of their names a split lists.
const SPLIT_STEPS: usize = 16;
const SPLIT_NAMES_SHOWN: usize = 8;
/// Voice leading moves a chord toward the chord before it, so a pattern needs this many chords.
const FEWEST_CHORDS_TO_LEAD: usize = 2;

thread_local! {
    /// The program's own random stream, which the munges that edit a pattern at random draw from, no seed applying.
    static RANDOM: RefCell<PythonRandom> = RefCell::new(PythonRandom::unseeded());
}

/// Where the editor is: its pattern, the cursor's step, and what the pattern's notes are measured against.
#[derive(Clone)]
pub struct Place {
    pub name: String,
    pub step: usize,
    pub steps: usize,
    pub drum: bool,
    pub default_octave: i64,
    /// How many notes the scale the pattern is known to play under has, or None where no one scale is known.
    pub scale_size: Option<i64>,
    /// The editor's step length, which dividing long notes measures their gates by.
    pub step_size: Rational,
}

/// The Munge dialog's choices, each its place in MSG_MUNGE_CHOICES.
mod munge {
    pub const REVERSE_AFTER: usize = 0;
    pub const REVERSE_BEFORE: usize = 1;
    pub const REVERSE: usize = 2;
    pub const PIVOT: usize = 3;
    pub const RANDOMIZE: usize = 4;
    pub const COPY_BEFORE_TO_END: usize = 5;
    pub const COPY_AFTER_TO_END: usize = 6;
    pub const COPY_BEFORE_TO_START: usize = 7;
    pub const COPY_AFTER_TO_START: usize = 8;
    pub const RANDOMIZE_AFTER: usize = 9;
    pub const RANDOMIZE_BEFORE: usize = 10;
    pub const CLEAR_ALL_BUT_PITCH: usize = 11;
    pub const CLEAR_STATEMENTS: usize = 12;
    pub const ROLL_LEFT: usize = 13;
    pub const ROLL_RIGHT: usize = 14;
    pub const CLEAR_CHORDS: usize = 15;
    pub const MIRROR: usize = 16;
    pub const INTERLEAVE: usize = 17;
    pub const SMOOTH_CCS: usize = 18;
    pub const SMOOTH_VELOCITY: usize = 19;
    pub const SPLICE: usize = 20;
    pub const SPLICE_BEFORE: usize = 21;
    pub const SPLIT: usize = 22;
    pub const SPLICE_AT_CURSOR: usize = 23;
    pub const ROLL_LEFT_AT_CURSOR: usize = 24;
    pub const ROLL_RIGHT_AT_CURSOR: usize = 25;
    pub const JOIN_NOTES: usize = 26;
    pub const DIVIDE_NOTES: usize = 27;
    pub const RANDOMIZE_RHYTHM: usize = 28;
    pub const RANDOMIZE_PITCHES: usize = 29;
    pub const REVERSE_PITCHES: usize = 30;
    pub const CLEAR_EVERY: usize = 31;
    pub const CROP: usize = 32;
    pub const HUMANIZE_VELOCITY: usize = 33;
    pub const INVERT_MELODY: usize = 34;
    pub const VOICE_LEADING: usize = 35;
    pub const VOICE_LEADING_OCTAVES: usize = 36;
}

/// The heading each munge is listed under.
fn munge_groups_unsorted() -> Vec<(&'static str, Vec<usize>)> {
    use labels::MungeGroup;
    use munge::*;
    vec![
        (MungeGroup::CLEAR, vec![CLEAR_ALL_BUT_PITCH, CLEAR_CHORDS, CLEAR_STATEMENTS, CLEAR_EVERY, CROP]),
        (
            MungeGroup::COPY,
            vec![COPY_BEFORE_TO_END, COPY_AFTER_TO_END, COPY_BEFORE_TO_START, COPY_AFTER_TO_START, MIRROR],
        ),
        (MungeGroup::OTHER_PATTERNS, vec![INTERLEAVE, SPLICE, SPLICE_BEFORE, SPLICE_AT_CURSOR, SPLIT]),
        (
            MungeGroup::PITCH,
            vec![REVERSE_PITCHES, RANDOMIZE_PITCHES, INVERT_MELODY, VOICE_LEADING, VOICE_LEADING_OCTAVES],
        ),
        (
            MungeGroup::REORDER,
            vec![REVERSE_AFTER, REVERSE_BEFORE, REVERSE, PIVOT, RANDOMIZE, RANDOMIZE_AFTER, RANDOMIZE_BEFORE],
        ),
        (MungeGroup::RHYTHM, vec![JOIN_NOTES, DIVIDE_NOTES, RANDOMIZE_RHYTHM]),
        (MungeGroup::ROLL, vec![ROLL_LEFT, ROLL_RIGHT, ROLL_LEFT_AT_CURSOR, ROLL_RIGHT_AT_CURSOR]),
        (MungeGroup::VELOCITY_AND_CCS, vec![HUMANIZE_VELOCITY, SMOOTH_VELOCITY, SMOOTH_CCS]),
    ]
}

/// The munge dialog's headings sorted by name, each with its choices sorted by name, ignoring case.
fn munge_groups() -> Vec<(&'static str, Vec<usize>)> {
    let mut groups = munge_groups_unsorted();
    groups.sort_by_key(|(heading, _)| *heading);
    for (_, choices) in groups.iter_mut() {
        choices.sort_by_key(|choice| labels::MSG_MUNGE_CHOICES[*choice].to_lowercase());
    }
    groups
}

/// Change a pattern of the set by its name, as one edit, saying on the status line why where it refuses.
pub fn change_pattern(app: &mut App, name: &str, change: impl FnOnce(&mut Pattern) -> Result<(), String>) {
    let mut refusal = None;
    app.document.change_set(|setlist| {
        if let Some(Item::Pattern(pattern)) = setlist.get_item_mut(Section::PATTERNS, name) {
            if let Err(problem) = change(pattern) {
                refusal = Some(problem);
            }
        }
    });
    if let Some(refusal) = refusal {
        app.refuse(&refusal);
    }
}

/// Change a pattern through a munge that refuses as the model does.
fn munged(app: &mut App, name: &str, change: impl FnOnce(&mut Pattern) -> Result<(), llamatron_model::schema::checking::InvalidValue>) {
    change_pattern(app, name, |pattern| change(pattern).map_err(|problem| problem.message));
}

/// Parse a typed whole number, saying on the status line why where it is not one.
fn typed_whole(app: &mut App, text: &str) -> Option<i64> {
    match text.trim().parse::<i64>() {
        Ok(number) => Some(number),
        Err(_) => {
            app.refuse(&named(errors::ERR_TYPED_NOT_AN_INTEGER, &[("text", text.into())]));
            None
        }
    }
}

/// Ask for a line of text and hand on what was typed.
fn ask_text(app: &mut App, title: &str, value: &str, then: impl Fn(&mut App, &str) + 'static) {
    let dialog = PromptDialog::new(title, value).then(Box::new(move |app: &mut App, answer: &Answer| {
        if let Answer::Typed(text) = answer {
            then(app, text);
        }
    }));
    app.show_page(Box::new(dialog));
}

/// Ask one choice of a list and hand on its place.
fn ask_choice(app: &mut App, title: &str, options: Vec<String>, current: usize, then: impl Fn(&mut App, usize) + 'static) {
    let mut dialog = ChoiceDialog::new(title, options, current);
    dialog.then = Some(Box::new(move |app: &mut App, answer: &Answer| {
        if let Answer::Chosen(place) = answer {
            then(app, *place);
        }
    }));
    app.show_page(Box::new(dialog));
}

/// Ask YES or NO, and do something on YES alone.
fn confirm(app: &mut App, title: &str, lines: Vec<String>, then: impl Fn(&mut App) + 'static) {
    let dialog = ConfirmDialog::new(title, lines, false, false).then(Box::new(move |app: &mut App, _: &Answer| then(app)));
    app.show_page(Box::new(dialog));
}

/// S: ask for the number of steps, asking first where steps that hold anything would go.
pub fn ask_steps(app: &mut App, place: &Place) {
    let name = place.name.clone();
    ask_text(app, messages::MSG_STEPS_PROMPT, &place.steps.to_string(), move |app, text| {
        let Some(steps) = typed_whole(app, text) else { return };
        if !(MIN_STEPS..=MAX_STEPS).contains(&steps) {
            app.refuse(&named(errors::ERR_STEPS_OUT_OF_RANGE, &[("low", MIN_STEPS.into()), ("high", MAX_STEPS.into())]));
            return;
        }
        let lost = app
            .document
            .get_setlist()
            .get_pattern(&name)
            .map_or(0, |pattern| pattern.steps_with_anything_from(steps as usize));
        let name = name.clone();
        let set = move |app: &mut App| change_pattern(app, &name, |pattern| pattern.set_steps(steps as i128).map_err(|problem| problem.message));
        if lost > 0 {
            confirm(app, &crate::uses::counted(lost, messages::MSG_SHORTEN_QUESTION), Vec::new(), set);
        } else {
            set(app);
        }
    });
}

/// N, and Reconfigure's rename: ask for the pattern's new name, which every clip and chain naming it follows.
pub fn rename(app: &mut App, name: &str) {
    crate::screens::rename::ask_rename(app, Section::PATTERNS, name, messages::MSG_RENAME_PATTERN_PROMPT);
}

/// R: offer the whole-pattern actions in one dialog, and run the chosen one, which may ask on in a dialog of its own; the
/// scale length is offered only for a pattern that is not a drum pattern.
pub fn reconfigure(app: &mut App, place: &Place) {
    let drum_switch = if place.drum { legends::MSG_DRUM_OFF_WHAT } else { legends::MSG_DRUM_ON_WHAT };
    let mut options: Vec<String> = [
        legends::MSG_LOAD_OVER_WHAT,
        legends::MSG_STEP_SIZE_WHAT,
        legends::MSG_TIME_SIGNATURE_WHAT,
        drum_switch,
        legends::MSG_DIRECTION_WHAT,
        legends::What::RENAME,
    ]
    .iter()
    .map(|option| option.to_string())
    .collect();
    if !place.drum {
        options.push(legends::MSG_SCALE_LENGTH_WHAT.to_string());
    }
    let place = place.clone();
    ask_choice(app, messages::MSG_RECONFIGURE_TITLE, options, 0, move |app, chosen| match chosen {
        0 => load_over(app, &place),
        1 => ask_step_size(app, &place.name),
        2 => ask_time_signature(app, &place.name),
        3 => toggle_drum(app, &place),
        4 => pick_direction(app, &place.name),
        5 => rename(app, &place.name),
        _ => pick_scale_length(app, &place.name),
    });
}

/// The names of the set's other patterns, sorted, which Load over and the munges taking another's steps offer.
fn other_pattern_names(app: &App, name: &str) -> Vec<String> {
    let names: Vec<String> = app
        .document
        .get_setlist()
        .items(Section::PATTERNS)
        .iter()
        .map(|(each, _)| each.clone())
        .filter(|each| each != name)
        .collect();
    sorted_names(&names)
}

/// Whether a pattern of the set has any notes.
fn has_notes(app: &App, name: &str) -> bool {
    app.document.get_setlist().get_pattern(name).is_some_and(Pattern::has_note_steps)
}

/// Replace the pattern's contents with a copy of another's, asking first where the pattern has notes.
fn load_over(app: &mut App, place: &Place) {
    let others = other_pattern_names(app, &place.name);
    if others.is_empty() {
        app.refuse(errors::ERR_NO_OTHER_PATTERNS);
        return;
    }
    let name = place.name.clone();
    let title = named(messages::MSG_LOAD_OVER_CHOICE_TITLE, &[("name", name.as_str().into())]);
    ask_choice(app, &title, others.clone(), 0, move |app, chosen| {
        let other = others[chosen].clone();
        let name = name.clone();
        let load = {
            let (name, other) = (name.clone(), other.clone());
            move |app: &mut App| {
                if let Err(problem) = app.document.load_over(&name, &other) {
                    app.refuse(&problem);
                }
                app.cursor_to(TOP);
            }
        };
        if has_notes(app, &name) {
            let question = named(
                messages::MSG_LOAD_OVER_QUESTION,
                &[("name", name.as_str().into()), ("other", other.as_str().into())],
            );
            confirm(app, &question, Vec::new(), load);
        } else {
            load(app);
        }
    });
}

/// Ask for a length, a whole number or a fraction such as 5/16, blank for none, and hand it on where it is in range.
fn ask_length(app: &mut App, title: &str, current: &str, most: Rational, then: impl Fn(&mut App, Option<String>) + 'static) {
    ask_text(app, title, current, move |app, text| {
        let text = text.trim();
        if text.is_empty() {
            then(app, None);
            return;
        }
        let Ok(length) = Rational::parse(text) else {
            app.refuse(&named(errors::ERR_NOT_A_LENGTH, &[("text", text.into())]));
            return;
        };
        if length <= Rational::ZERO || length > most {
            app.refuse(&named(errors::ERR_LENGTH_OUT_OF_RANGE, &[("most", most.to_string().as_str().into())]));
            return;
        }
        then(app, Some(length.to_string()));
    });
}

/// A pattern's own setting as written, or blank.
fn written(app: &App, name: &str, setting: &str) -> String {
    app.document
        .get_setlist()
        .get_pattern(name)
        .and_then(|pattern| pattern.get_written(setting))
        .map(|value| value.as_str().map_or_else(|| value.python_str(), str::to_string))
        .unwrap_or_default()
}

/// Ask for the pattern's own step size, blank to take the set's.
fn ask_step_size(app: &mut App, name: &str) {
    let current = written(app, name, "step_size");
    let name = name.to_string();
    ask_length(
        app,
        messages::MSG_STEP_SIZE_PROMPT,
        &current,
        Rational::whole(MAX_STEP_SIZE as i128),
        move |app, length| {
            let value = length.map(|length| Data::text(&length));
            change_pattern(app, &name, |pattern| {
                pattern.set_written("step_size", value);
                Ok(())
            });
        },
    );
}

/// Ask for the pattern's own time signature, written such as 6/8, blank to take the song's.
fn ask_time_signature(app: &mut App, name: &str) {
    let current = written(app, name, "time_signature");
    let name = name.to_string();
    ask_text(app, messages::MSG_TIME_SIGNATURE_PROMPT, &current, move |app, text| {
        let text = text.trim();
        let value = if text.is_empty() {
            None
        } else if llamatron_model::values::time_signature::TimeSignature::from_text(text).is_ok() {
            Some(Data::text(text))
        } else {
            use llamatron_model::values::generated::time_signature::{MAX_BEATS, MIN_BEATS, UNITS_LISTED};
            app.refuse(&named(
                errors::ERR_TYPED_NOT_A_TIME_SIGNATURE,
                &[
                    ("text", text.into()),
                    ("lowest", MIN_BEATS.into()),
                    ("highest", MAX_BEATS.into()),
                    ("units", UNITS_LISTED.into()),
                ],
            ));
            return;
        };
        change_pattern(app, &name, |pattern| {
            pattern.set_written("time_signature", value);
            Ok(())
        });
    });
}

/// Switch between a drum and a note pattern, always asking first, since the rows change and any notes go.
fn toggle_drum(app: &mut App, place: &Place) {
    let drum = !place.drum;
    let what = if drum { legends::MSG_LETTERS_WHAT } else { legends::MSG_DEGREES_WHAT };
    let question = if has_notes(app, &place.name) {
        messages::MSG_CHANGE_TYPE_QUESTION
    } else {
        messages::MSG_CHANGE_TYPE_EMPTY_QUESTION
    };
    let lines = vec![named(question, &[("what", what.into())])];
    let name = place.name.clone();
    confirm(app, messages::MSG_CHANGE_TYPE_TITLE, lines, move |app| {
        change_pattern(app, &name, |pattern| {
            pattern.set_drum(drum);
            Ok(())
        });
        app.cursor_to(TOP);
    });
}

/// Each direction in words beside what it does, lined up for a picker.
fn direction_choices() -> Vec<String> {
    let rows: Vec<(String, &str)> = DIRECTIONS
        .iter()
        .map(|name| {
            let said = labels::MSG_DIRECTION_NAMES.iter().find(|(each, _)| each == name).map_or("", |(_, said)| *said);
            (name.replace('_', " "), said)
        })
        .collect();
    let widest = rows.iter().map(|(name, _)| name.chars().count()).max().unwrap_or(0);
    rows.iter()
        .map(|(name, said)| {
            let padded = format!("{name:<widest$}");
            named(marks::MSG_COLUMN_LINE, &[("name", padded.as_str().into()), ("description", (*said).into())])
                .trim_end()
                .to_string()
        })
        .collect()
}

/// Ask which way the pattern plays, opening on its own.
fn pick_direction(app: &mut App, name: &str) {
    let current = app
        .document
        .get_setlist()
        .get_pattern(name)
        .and_then(|pattern| pattern.get_written("direction"))
        .and_then(Data::as_str)
        .unwrap_or(DIRECTIONS[0])
        .to_string();
    let place = DIRECTIONS.iter().position(|each| *each == current).unwrap_or(0);
    let name = name.to_string();
    ask_choice(app, messages::MSG_PLAY_DIRECTION_TITLE, direction_choices(), place, move |app, chosen| {
        change_pattern(app, &name, |pattern| {
            pattern.set_direction(DIRECTIONS[chosen]);
            Ok(())
        });
    });
}

/// Ask how many notes the scale has that the pattern was written for, any first.
fn pick_scale_length(app: &mut App, name: &str) {
    let lengths: Vec<i64> = (MIN_SCALE_LENGTH..=MAX_SCALE_LENGTH).collect();
    let current = app
        .document
        .get_setlist()
        .get_pattern(name)
        .and_then(|pattern| pattern.get_written("scale_length"))
        .and_then(Data::as_whole);
    let place = current
        .and_then(|current| lengths.iter().position(|length| *length as i128 == current))
        .map_or(0, |place| place + 1);
    let mut options = vec![marks::MSG_ANY_SCALE_LENGTH.to_string()];
    options.extend(lengths.iter().map(|length| length.to_string()));
    let name = name.to_string();
    ask_choice(app, messages::MSG_SCALE_LENGTH_TITLE, options, place, move |app, chosen| {
        let value = chosen.checked_sub(1).map(|place| Data::Whole(lengths[place] as i128));
        change_pattern(app, &name, |pattern| {
            pattern.set_written("scale_length", value);
            Ok(())
        });
    });
}

/// M: offer the ways of rearranging, copying and clearing the steps, under headings that open and close, and do the
/// chosen one.
pub fn munge(app: &mut App, place: &Place) {
    let groups = munge_groups();
    let order: Vec<usize> = groups.iter().flat_map(|(_, choices)| choices.iter().copied()).collect();
    let shown = groups
        .iter()
        .map(|(heading, choices)| {
            (
                heading.to_string(),
                choices.iter().map(|choice| labels::MSG_MUNGE_CHOICES[*choice].to_string()).collect(),
            )
        })
        .collect();
    let place = place.clone();
    let then = Box::new(move |app: &mut App, answer: &Answer| {
        if let Answer::Chosen(chosen) = answer {
            munge_as(app, &place, order[*chosen]);
        }
    });
    let opened = app.session.open_munge_groups.clone();
    app.show_page(Box::new(GroupedChoiceDialog::new(messages::MSG_MUNGE_TITLE, shown, opened, then)));
}

/// Whether a pattern of so many steps would hold more than a pattern may, saying so on the status line where it would.
fn grown_too_long(app: &mut App, steps: usize) -> bool {
    if steps > MAX_STEPS as usize {
        app.refuse(&named(errors::ERR_MUNGE_TOO_MANY_STEPS, &[("steps", steps.into()), ("most", MAX_STEPS.into())]));
    }
    steps > MAX_STEPS as usize
}

/// Draw from the program's own random stream.
fn at_random<T>(draw: impl FnOnce(&mut PythonRandom) -> T) -> T {
    RANDOM.with(|random| draw(&mut random.borrow_mut()))
}

/// Do one of the munge dialog's choices. A rearranging leaves the cursor on its step, so that choosing the same way again
/// undoes it.
fn munge_as(app: &mut App, place: &Place, choice: usize) {
    use munge::*;
    let (name, step, steps) = (place.name.as_str(), place.step, place.steps);
    let last = steps.saturating_sub(1);
    match choice {
        REVERSE_AFTER if step >= last => app.refuse(errors::ERR_NOTHING_AFTER),
        REVERSE_AFTER => munged(app, name, |pattern| pattern.reverse_after(step)),
        REVERSE_BEFORE if step == 0 => app.refuse(errors::ERR_NOTHING_BEFORE),
        REVERSE_BEFORE => munged(app, name, |pattern| pattern.reverse_before(step)),
        REVERSE if steps < 2 => app.refuse(errors::ERR_ONE_STEP),
        REVERSE => munged(app, name, Pattern::reverse),
        PIVOT if steps < 2 => app.refuse(errors::ERR_NOTHING_TO_PIVOT),
        PIVOT => {
            let mut moved = step;
            munged(app, name, |pattern| pattern.pivot_around(step).map(|to| moved = to));
            app.cursor_to(&moved.to_string());
        }
        RANDOMIZE | RANDOMIZE_AFTER | RANDOMIZE_BEFORE if steps < 2 => app.refuse(errors::ERR_ONE_STEP),
        RANDOMIZE => munged(app, name, |pattern| at_random(|random| pattern.shuffle(random))),
        RANDOMIZE_AFTER => munged(app, name, |pattern| at_random(|random| pattern.shuffle_from(step, random))),
        RANDOMIZE_BEFORE => munged(app, name, |pattern| at_random(|random| pattern.shuffle_through(step, random))),
        COPY_BEFORE_TO_END | COPY_AFTER_TO_END | COPY_BEFORE_TO_START | COPY_AFTER_TO_START => copy_steps(app, place, choice),
        INVERT_MELODY => invert_melody(app, place),
        VOICE_LEADING | VOICE_LEADING_OCTAVES => lead_voices(app, place, choice),
        DIVIDE_NOTES => {
            let covering = app
                .document
                .get_setlist()
                .get_pattern(name)
                .map(|pattern| crate::patterns::covering_notes(pattern, place.step_size))
                .unwrap_or_default();
            munged(app, name, |pattern| {
                pattern.divide_long_notes(&covering);
                Ok(())
            });
        }
        CROP if step >= last => app.refuse(errors::ERR_NOTHING_TO_CROP),
        CROP => munged(app, name, |pattern| pattern.set_steps(step as i128 + 1)),
        CLEAR_EVERY => ask_number(app, name, messages::MSG_CLEAR_EVERY_PROMPT, MIN_STEPS, steps as i64, |pattern, every| {
            pattern.clear_every(every)
        }),
        HUMANIZE_VELOCITY => ask_number(app, name, messages::MSG_HUMANIZE_PROMPT, MIN_VELOCITY, MAX_VELOCITY, |pattern, most| {
            at_random(|random| pattern.humanize_velocity(most, random));
            Ok(())
        }),
        ROLL_LEFT_AT_CURSOR if step == 0 => app.refuse(errors::ERR_NOTHING_BEFORE),
        ROLL_LEFT_AT_CURSOR => munged(app, name, |pattern| pattern.roll_through(step)),
        ROLL_RIGHT_AT_CURSOR if step >= last => app.refuse(errors::ERR_NOTHING_AFTER),
        ROLL_RIGHT_AT_CURSOR => munged(app, name, |pattern| pattern.roll_from(step)),
        ROLL_LEFT | ROLL_RIGHT => ask_roll(app, place, choice == ROLL_LEFT),
        MIRROR if grown_too_long(app, steps * 2) => {}
        MIRROR => munged(app, name, Pattern::mirror),
        SPLIT => ask_split(app, place),
        INTERLEAVE | SPLICE | SPLICE_BEFORE | SPLICE_AT_CURSOR => pick_other_pattern(app, place, choice),
        CLEAR_ALL_BUT_PITCH => munged(app, name, |pattern| {
            pattern.clear_all_but_pitch();
            Ok(())
        }),
        CLEAR_STATEMENTS => munged(app, name, |pattern| {
            pattern.clear_statements();
            Ok(())
        }),
        CLEAR_CHORDS => munged(app, name, |pattern| {
            pattern.clear_chords();
            Ok(())
        }),
        SMOOTH_CCS => munged(app, name, |pattern| {
            pattern.smooth_ccs();
            Ok(())
        }),
        SMOOTH_VELOCITY => munged(app, name, |pattern| {
            pattern.smooth_velocity();
            Ok(())
        }),
        JOIN_NOTES => munged(app, name, |pattern| {
            pattern.join_repeated_notes();
            Ok(())
        }),
        RANDOMIZE_RHYTHM => munged(app, name, |pattern| at_random(|random| pattern.randomize_rhythm(random))),
        RANDOMIZE_PITCHES => munged(app, name, |pattern| {
            at_random(|random| pattern.randomize_pitches(random));
            Ok(())
        }),
        _ => munged(app, name, |pattern| {
            pattern.reverse_pitches();
            Ok(())
        }),
    }
}

/// Copy the cursor's step with the steps before it, or with the steps after it, to the end of the pattern or before its
/// start, unless the pattern would hold too many steps; after a copy before the start the cursor stays on its note.
fn copy_steps(app: &mut App, place: &Place, choice: usize) {
    use munge::*;
    let (first, last) = if matches!(choice, COPY_BEFORE_TO_END | COPY_BEFORE_TO_START) {
        (0, place.step)
    } else {
        (place.step, place.steps - 1)
    };
    let copied = last - first + 1;
    if grown_too_long(app, place.steps + copied) {
        return;
    }
    let to_start = matches!(choice, COPY_BEFORE_TO_START | COPY_AFTER_TO_START);
    munged(app, &place.name, |pattern| {
        if to_start {
            pattern.repeat_at_start(first, last)
        } else {
            pattern.repeat_at_end(first, last)
        }
    });
    if to_start {
        app.cursor_to(&(place.step + copied).to_string());
    }
}

/// Choose another pattern and take its steps into this one, the other left as it is: spliced after the last step, before
/// the first or before the cursor's step, or interleaved, one after each step, which makes this one twice as long. The
/// cursor stays on its note.
fn pick_other_pattern(app: &mut App, place: &Place, choice: usize) {
    use munge::*;
    let others = other_pattern_names(app, &place.name);
    if others.is_empty() {
        app.refuse(errors::ERR_NO_OTHER_PATTERNS);
        return;
    }
    let title = match choice {
        INTERLEAVE => messages::MSG_INTERLEAVE_CHOICE_TITLE,
        SPLICE => messages::MSG_SPLICE_CHOICE_TITLE,
        SPLICE_BEFORE => messages::MSG_SPLICE_BEFORE_CHOICE_TITLE,
        _ => messages::MSG_SPLICE_AT_CURSOR_CHOICE_TITLE,
    };
    let place = place.clone();
    ask_choice(app, title, others.clone(), 0, move |app, chosen| {
        let Some(other) = app.document.get_setlist().get_pattern(&others[chosen]).cloned() else {
            return;
        };
        let added = if choice == INTERLEAVE { place.steps } else { other.get_steps() as usize };
        if other.is_drum() != place.drum {
            app.refuse(errors::ERR_INTERLEAVE_DRUM_MISMATCH);
            return;
        }
        if grown_too_long(app, place.steps + added) {
            return;
        }
        if choice == INTERLEAVE {
            munged(app, &place.name, |pattern| pattern.interleave(&other));
            app.cursor_to(&(place.step * 2).to_string());
            return;
        }
        // Steps put before the cursor's step move it along, and the cursor stays on its note.
        let at = match choice {
            SPLICE => None,
            SPLICE_BEFORE => Some(0),
            _ => Some(place.step),
        };
        munged(app, &place.name, |pattern| pattern.splice(&other, at));
        if at.is_some() {
            app.cursor_to(&(place.step + added).to_string());
        }
    });
}

/// Ask how many steps each new pattern has, make new patterns of the pattern's steps, so many each, and say which were
/// made; the pattern itself is left as it is.
fn ask_split(app: &mut App, place: &Place) {
    let most = place.steps.saturating_sub(1);
    if most < FIRST_ROLL {
        app.refuse(errors::ERR_ONE_STEP);
        return;
    }
    let name = place.name.clone();
    ask_text(app, messages::MSG_SPLIT_PROMPT, &SPLIT_STEPS.min(most).to_string(), move |app, text| {
        let Some(steps) = typed_whole(app, text) else { return };
        if !(FIRST_ROLL as i64..=most as i64).contains(&steps) {
            app.refuse(&named(errors::ERR_SPLIT_OUT_OF_RANGE, &[("low", FIRST_ROLL.into()), ("high", most.into())]));
            return;
        }
        let made = match app.document.split_pattern(&name, steps as usize) {
            Ok(made) => made,
            Err(problem) => return app.refuse(&problem),
        };
        let shown = llamatron_model::schema::checking::listed(&made[..made.len().min(SPLIT_NAMES_SHOWN)]);
        let said = if made.len() > SPLIT_NAMES_SHOWN {
            named(
                messages::MSG_SPLIT_CREATED_MANY,
                &[
                    ("count", made.len().into()),
                    ("names", shown.as_str().into()),
                    ("more", (made.len() - SPLIT_NAMES_SHOWN).into()),
                ],
            )
        } else {
            named(messages::MSG_SPLIT_CREATED, &[("count", made.len().into()), ("names", shown.as_str().into())])
        };
        app.show_page(Box::new(MessageDialog::new(messages::MSG_SPLIT_TITLE, vec![said])));
    });
}

/// Mirror the pattern's notes around the note on the cursor's step, by the degrees of the scale the pattern plays under,
/// or of the scale length it was written for.
fn invert_melody(app: &mut App, place: &Place) {
    let written = app
        .document
        .get_setlist()
        .get_pattern(&place.name)
        .and_then(|pattern| pattern.get_written("scale_length"))
        .and_then(Data::as_whole)
        .map(|size| size as i64);
    let Some(size) = place.scale_size.or(written) else {
        app.refuse(errors::ERR_MUNGE_NO_SCALE);
        return;
    };
    let (step, octave) = (place.step, place.default_octave);
    munged(app, &place.name, |pattern| pattern.invert_melody(step, size, octave));
}

/// Write the inversions that move each chord the least from the chord before, measured in the scale the pattern plays
/// under.
fn lead_voices(app: &mut App, place: &Place, choice: usize) {
    if place.scale_size.is_none() {
        app.refuse(errors::ERR_MUNGE_NO_SCALE);
        return;
    }
    let chords = app.document.get_setlist().get_pattern(&place.name).map_or(0, |pattern| {
        (0..place.steps)
            .filter(|step| crate::patterns::value(pattern, "degree", *step).is_some() && crate::patterns::value(pattern, "chord", *step).is_some())
            .count()
    });
    if chords < FEWEST_CHORDS_TO_LEAD {
        app.refuse(errors::ERR_VOICE_LEADING_NEEDS_CHORDS);
        return;
    }
    let setlist = app.document.get_setlist();
    let Some(scale) = crate::patterns::scales_of_pattern(setlist, app.document.song(), &place.name)
        .first()
        .and_then(|name| {
            let Some(Item::Scale(held)) = setlist.get_item(Section::SCALES, name) else {
                return None;
            };
            crate::chord_text::ChordScale::new(&crate::patterns::scale_root(setlist, name), held.get_kind().as_str()?)
        })
    else {
        return;
    };
    let (octave, octaves) = (place.default_octave, choice == munge::VOICE_LEADING_OCTAVES);
    munged(app, &place.name, |pattern| {
        crate::voice_leading::apply_voice_leading(pattern, &scale, octave, octaves)
    });
}

/// Ask for a whole number within limits and munge the pattern with it, saying on the status line why a number or the munge
/// was refused.
fn ask_number(
    app: &mut App,
    name: &str,
    title: &str,
    low: i64,
    high: i64,
    way: impl Fn(&mut Pattern, i64) -> Result<(), llamatron_model::schema::checking::InvalidValue> + 'static,
) {
    let name = name.to_string();
    ask_text(app, title, "", move |app, text| {
        let Some(number) = typed_whole(app, text) else { return };
        if !(low..=high).contains(&number) {
            app.refuse(&named(errors::ERR_MUNGE_NUMBER_OUT_OF_RANGE, &[("low", low.into()), ("high", high.into())]));
            return;
        }
        munged(app, &name, |pattern| way(pattern, number));
    });
}

/// Ask how many steps to turn the pattern, and turn it: a step pushed off one end comes in at the other.
fn ask_roll(app: &mut App, place: &Place, left: bool) {
    let (name, steps) = (place.name.clone(), place.steps);
    let title = if left {
        messages::MSG_ROLL_LEFT_PROMPT
    } else {
        messages::MSG_ROLL_RIGHT_PROMPT
    };
    ask_text(app, title, "", move |app, text| {
        let Some(count) = typed_whole(app, text) else { return };
        if !(FIRST_ROLL as i64..=steps as i64).contains(&count) {
            app.refuse(&named(errors::ERR_ROLL_OUT_OF_RANGE, &[("low", FIRST_ROLL.into()), ("high", steps.into())]));
            return;
        }
        let count = if left { count } else { -count };
        munged(app, &name, |pattern| pattern.roll(count));
    });
}
