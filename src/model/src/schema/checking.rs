// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Checking a setting's value against its description (the Python model/schema/setting.py and model/file/checks.py), the one
//! check reading a file and a setter share. A value that names something, a pattern, a scale or a track, is checked against
//! the song or the set it is read in, through `Context`.
//!
//! The checks refuse what the Python refuses. Their messages are the Python's texts where they are at hand; the deepest
//! ones (a built-in sound's own settings, keyswitches, statements, a musician's settings by section) check the value's
//! shape alone for now, since llamatron need show errors as the Python does only as far as the comparisons need.

use crate::file::data::Data;
use crate::schema::generated::file_format;
use crate::schema::generated::limits;
use crate::schema::generated::settings::{Check, Described, Nearest, Plain, Setting};
use crate::values::generated::note::ROOT_NAMES;
use crate::values::time_signature::TimeSignature;
use llamatron_math::Rational;
use llamatron_strings::errors;
use llamatron_strings::{named, Value};

/// A value refused, with what is wrong with it, and the value nearest it allowed, where there is one.
#[derive(Clone, Debug, PartialEq)]
pub struct InvalidValue {
    pub message: String,
    pub nearest: NearestValue,
    /// Where inside the thing being read the value was, such as a pattern's row, said after the thing's own place.
    pub within: Option<String>,
}

impl InvalidValue {
    pub fn new(message: String) -> InvalidValue {
        InvalidValue {
            message,
            nearest: NearestValue::None,
            within: None,
        }
    }

    /// The same refusal, found at a place inside the thing being read.
    pub fn within(self, place: &str) -> InvalidValue {
        InvalidValue {
            within: Some(place.to_string()),
            ..self
        }
    }
}

/// The allowed value nearest a wrong one: none, leaving the setting out (its default), or a value.
#[derive(Clone, Debug, PartialEq)]
pub enum NearestValue {
    None,
    LeftOut,
    Value(Data),
}

/// What a check asks of the song or the set a value is read in.
pub trait Context {
    fn has_scale(&self, name: &str) -> bool;
    fn has_pattern(&self, name: &str) -> bool;
    fn is_drum_pattern(&self, name: &str) -> bool;
    fn has_track(&self, name: &str) -> bool;
    fn has_instrument(&self, name: &str) -> bool;
    fn has_groove(&self, name: &str) -> bool;
    fn has_generator_named(&self, name: &str) -> bool;
}

fn refused(template: &str, fields: &[(&str, Value)]) -> Result<(), InvalidValue> {
    Err(InvalidValue::new(named(template, fields)))
}

/// Items as text for a message, separated by commas.
pub fn listed<T: AsRef<str>>(items: &[T]) -> String {
    items.iter().map(|item| item.as_ref().to_string()).collect::<Vec<_>>().join(", ")
}

fn plain_texts(choices: &[Plain]) -> Vec<String> {
    choices.iter().map(plain_shown).collect()
}

fn plain_shown(plain: &Plain) -> String {
    match plain {
        Plain::Text(text) => text.to_string(),
        Plain::Whole(whole) => whole.to_string(),
        Plain::Float(float) => llamatron_math::number::python_float_text(*float),
        Plain::Flag(flag) => if *flag { "True" } else { "False" }.into(),
        Plain::Null => "None".into(),
        Plain::List(items) => format!("[{}]", items.iter().map(plain_shown).collect::<Vec<_>>().join(", ")),
    }
}

/// Whether a value is a choice, as Python's `in` compares them: equal kinds by value, and a whole number equal to a float.
fn is_choice(value: &Data, choice: &Plain) -> bool {
    match (value, choice) {
        (Data::Text(text), Plain::Text(other)) => text == other,
        (Data::Whole(whole), Plain::Whole(other)) => *whole == *other as i128,
        (Data::Bool(flag), Plain::Flag(other)) => flag == other,
        (Data::Bool(flag), Plain::Whole(other)) => (*flag as i64) == *other,
        (Data::Whole(whole), Plain::Flag(other)) => *whole == *other as i128,
        (Data::Float(float), Plain::Float(other)) => float == other,
        (Data::Float(float), Plain::Whole(other)) => *float == *other as f64,
        (Data::Null, Plain::Null) => true,
        _ => false,
    }
}

/// A plain choice as data.
pub fn plain_data(plain: &Plain) -> Data {
    match plain {
        Plain::Text(text) => Data::text(text),
        Plain::Whole(whole) => Data::Whole(*whole as i128),
        Plain::Float(float) => Data::Float(*float),
        Plain::Flag(flag) => Data::Bool(*flag),
        Plain::Null => Data::Null,
        Plain::List(items) => Data::List(items.iter().map(plain_data).collect()),
    }
}

/// Check a value against a setting's description, the song or set given for one that names something.
pub fn check(setting: &Setting, value: &Data, context: Option<&dyn Context>) -> Result<(), InvalidValue> {
    let name = setting.name;
    let shown = || Value::from(value);
    match setting.described {
        Described::Flag { error } | Described::Text { error } => {
            let fits = matches!(
                (setting.described, value),
                (Described::Flag { .. }, Data::Bool(_)) | (Described::Text { .. }, Data::Text(_))
            );
            if fits {
                return Ok(());
            }
            refused(error, &[("name", name.into()), ("value", shown())])
        }
        Described::WholeNumber { lowest, highest, error } => {
            let fits = value
                .as_whole()
                .is_some_and(|whole| lowest.is_none_or(|low| whole >= low as i128) && highest.is_none_or(|high| whole <= high as i128));
            if fits {
                return Ok(());
            }
            let bound = |bound: Option<i64>| bound.map(Value::from).unwrap_or(Value::Text("None".into()));
            let result = refused(
                error,
                &[
                    ("name", name.into()),
                    ("value", shown()),
                    ("lowest", bound(lowest)),
                    ("highest", bound(highest)),
                    ("most", bound(highest)),
                ],
            );
            result.map_err(|refusal| InvalidValue {
                nearest: nearest_whole(value, lowest, highest),
                ..refusal
            })
        }
        Described::Choice { choices, default, error } => {
            if choices.iter().any(|choice| is_choice(value, choice)) {
                return Ok(());
            }
            let nearest = default.map(|choice| NearestValue::Value(plain_data(&choice))).unwrap_or(NearestValue::LeftOut);
            let result = refused(
                error,
                &[("name", name.into()), ("value", shown()), ("choices", listed(&plain_texts(choices)).into())],
            );
            result.map_err(|refusal| InvalidValue { nearest, ..refusal })
        }
        Described::TimeLength { most, blank_allowed } => {
            if value.is_null() && blank_allowed {
                return Ok(());
            }
            written_length(value, Rational::new(most.0 as i128, most.1 as i128)).map(|_| ())
        }
        Described::Checked {
            check: function,
            arguments,
            needs_song,
            nearest,
        } => {
            let context = if needs_song { context } else { None };
            let result = checked(function, arguments, value, context);
            result.map_err(|refusal| InvalidValue {
                nearest: nearest.map(|kind| nearest_of(kind, value)).unwrap_or(NearestValue::None),
                ..refusal
            })
        }
    }
}

fn nearest_whole(value: &Data, lowest: Option<i64>, highest: Option<i64>) -> NearestValue {
    let Some(whole) = value.as_whole() else { return NearestValue::None };
    if let Some(low) = lowest.filter(|low| whole < *low as i128) {
        return NearestValue::Value(Data::Whole(low as i128));
    }
    if let Some(high) = highest.filter(|high| whole > *high as i128) {
        return NearestValue::Value(Data::Whole(high as i128));
    }
    NearestValue::Value(value.clone())
}

fn nearest_of(kind: Nearest, value: &Data) -> NearestValue {
    match kind {
        Nearest::SceneNearestTempoPercent => match number(value) {
            Ok(percent) => {
                let lowest = Rational::whole(limits::MIN_TEMPO_PERCENT as i128);
                let highest = Rational::whole(limits::MAX_TEMPO_PERCENT as i128);
                NearestValue::Value(fraction_data(percent.clamp(lowest, highest)))
            }
            Err(_) => NearestValue::None,
        },
        Nearest::ArpModelNearestOffsets => NearestValue::None,
        Nearest::GrooveNearestCells => match groove_amounts(value) {
            Some(amounts) => NearestValue::Value(Data::List(
                amounts
                    .into_iter()
                    .map(|amount| Data::Whole(amount.clamp(limits::MIN_GROOVE_AMOUNT as i128, limits::MAX_GROOVE_AMOUNT as i128)))
                    .collect(),
            )),
            None => NearestValue::None,
        },
    }
}

/// A groove's amounts, where a value is a list of as many whole numbers as a groove may hold.
fn groove_amounts(value: &Data) -> Option<Vec<i128>> {
    let cells = value.as_list()?;
    if !(limits::MIN_GROOVE_CELLS as usize..=limits::MAX_GROOVE_CELLS as usize).contains(&cells.len()) {
        return None;
    }
    cells.iter().map(Data::as_whole).collect()
}

/// An exact length as a file holds it: a whole number, or text like 3/16.
pub fn fraction_data(value: Rational) -> Data {
    if value.is_whole() {
        return Data::Whole(value.numerator());
    }
    Data::Text(value.to_string())
}

/// A number written like 2 or 1/8, as an exact fraction; true and false refused.
pub fn number(value: &Data) -> Result<Rational, InvalidValue> {
    if matches!(value, Data::Bool(_)) {
        return Err(InvalidValue::new(named(errors::ERR_EXPECTED_NUMBER, &[("value", value.into())])));
    }
    Rational::parse(&value.python_str()).map_err(|_| InvalidValue::new(named(errors::ERR_EXPECTED_NUMBER_LIKE, &[("value", value.into())])))
}

/// A length in whole notes, which has to be more than zero.
pub fn positive_length(value: &Data) -> Result<Rational, InvalidValue> {
    let length = number(value)?;
    if length <= Rational::ZERO {
        return Err(InvalidValue::new(named(errors::ERR_LENGTH_NOT_POSITIVE, &[("value", value.into())])));
    }
    Ok(length)
}

/// Whether a value is a whole number, or text of a fraction of whole numbers.
pub fn is_written_length(value: &Data) -> bool {
    match value {
        Data::Whole(_) => true,
        Data::Text(text) => {
            let (top, bottom) = text.split_once('/').unwrap_or((text, "1"));
            !top.is_empty() && !bottom.is_empty() && top.chars().chain(bottom.chars()).all(|digit| digit.is_ascii_digit())
        }
        _ => false,
    }
}

/// A length written as a whole number or a fraction, more than nothing and at most most; decimals refused.
pub fn written_length(value: &Data, most: Rational) -> Result<Rational, InvalidValue> {
    if !is_written_length(value) {
        return Err(InvalidValue::new(named(errors::ERR_BAD_WRITTEN_LENGTH, &[("value", value.into())])));
    }
    let length = positive_length(value)?;
    if length > most {
        return Err(InvalidValue::new(named(
            errors::ERR_LENGTH_TOO_LONG,
            &[("most", most.to_string().into()), ("value", value.into())],
        )));
    }
    Ok(length)
}

/// A time signature written like 6/8.
pub fn time_signature(value: &Data) -> Result<TimeSignature, InvalidValue> {
    TimeSignature::from_text(&value.python_str()).map_err(|problem| InvalidValue::new(problem.0))
}

/// A time setting: a count of bars, written like `2 bars`, or a length.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum TimeLength {
    Bars(i64),
    Length(Rational),
}

/// The count of bars a text like `2 bars` or `1 bar` says, or None.
pub fn bars_written(value: &Data) -> Option<i64> {
    let text = value.as_str()?;
    if text == file_format::ONE_BAR_WRITTEN {
        return Some(1);
    }
    let words: Vec<&str> = text.split_whitespace().collect();
    let pattern_words = file_format::BARS_WRITTEN.split_whitespace().count();
    if words.len() != pattern_words || !words[0].chars().all(|digit| digit.is_ascii_digit()) {
        return None;
    }
    let count: i64 = words[0].parse().ok()?;
    (named(file_format::BARS_WRITTEN, &[("count", words[0].into())]) == text && count > 0).then_some(count)
}

/// A time setting as bars or a positive length.
pub fn time_length(value: &Data) -> Result<TimeLength, InvalidValue> {
    if let Some(count) = bars_written(value) {
        return Ok(TimeLength::Bars(count));
    }
    let refusal = || InvalidValue::new(named(errors::ERR_BAD_TIME, &[("value", value.into())]));
    let length = number(value).map_err(|_| refusal())?;
    if length <= Rational::ZERO {
        return Err(refusal());
    }
    Ok(TimeLength::Length(length))
}

/// Whether a value is three whole numbers joined by dots, a version.
pub fn is_version(value: &Data) -> bool {
    let Some(text) = value.as_str() else { return false };
    let parts: Vec<&str> = text.split('.').collect();
    parts.len() == 3 && parts.iter().all(|part| !part.is_empty() && part.chars().all(|digit| digit.is_ascii_digit()))
}

fn names_in(value: &Data) -> Option<Vec<&str>> {
    value.as_list()?.iter().map(Data::as_str).collect()
}

fn named_in(context: Option<&dyn Context>, test: impl Fn(&dyn Context) -> bool) -> bool {
    context.is_none_or(test)
}

/// A setting's own check, ported from the Python function its description names.
fn checked(function: Check, arguments: &[Plain], value: &Data, context: Option<&dyn Context>) -> Result<(), InvalidValue> {
    let shown = || Value::from(value);
    match function {
        Check::ChecksCheckName => {
            if value.is_null() || value.as_str().is_some() {
                return Ok(());
            }
            refused(errors::ERR_INVALID_NAME, &[("name", shown())])
        }
        Check::ChecksNumber => number(value).map(|_| ()),
        Check::ChecksTimeLength => time_length(value).map(|_| ()),
        Check::ChecksTimeSignature => time_signature(value).map(|_| ()),
        Check::SceneCheckSceneName => {
            if value.as_str().is_some() {
                return Ok(());
            }
            refused(errors::ERR_SCENE_NAME_NOT_TEXT, &[("value", shown())])
        }
        Check::SceneCheckScaleName => match value {
            Data::Null => Ok(()),
            Data::Text(name) if named_in(context, |song| song.has_scale(name)) => Ok(()),
            _ => refused(errors::ERR_SCENE_NO_SUCH_SCALE, &[("scale", shown())]),
        },
        Check::SongCheckScaleName => match value {
            Data::Null => Ok(()),
            Data::Text(name) if named_in(context, |song| song.has_scale(name)) => Ok(()),
            _ => refused(errors::ERR_SONG_NO_SUCH_SCALE, &[("scale", shown())]),
        },
        Check::ClipSlotCheckScaleName => match value {
            Data::Text(name) if named_in(context, |song| song.has_scale(name)) => Ok(()),
            _ => refused(errors::ERR_SCENE_NO_SUCH_SCALE, &[("scale", shown())]),
        },
        Check::SceneCheckTempoPercent => {
            let percent = number(value)?;
            let fits = Rational::whole(limits::MIN_TEMPO_PERCENT as i128) <= percent && percent <= Rational::whole(limits::MAX_TEMPO_PERCENT as i128);
            if fits {
                return Ok(());
            }
            refused(
                errors::ERR_BAD_TEMPO_PERCENT,
                &[
                    ("lowest", limits::MIN_TEMPO_PERCENT.into()),
                    ("highest", limits::MAX_TEMPO_PERCENT.into()),
                    ("value", shown()),
                ],
            )
        }
        Check::ClipSlotCheckPatternName => match value {
            Data::Text(name) if named_in(context, |song| song.has_pattern(name)) => Ok(()),
            _ => refused(errors::ERR_CLIP_SLOT_NO_SUCH_PATTERN, &[("name", shown())]),
        },
        Check::ClipSlotCheckPatternNames => {
            let Some(names) = names_in(value).filter(|names| !names.is_empty()) else {
                return refused(errors::ERR_NOT_PATTERN_NAMES, &[("value", shown())]);
            };
            let Some(song) = context else { return Ok(()) };
            for name in &names {
                if !song.has_pattern(name) {
                    return refused(errors::ERR_CLIP_SLOT_NO_SUCH_PATTERN, &[("name", (*name).into())]);
                }
            }
            let drums = names.iter().filter(|name| song.is_drum_pattern(name)).count();
            if drums != 0 && drums != names.len() {
                return refused(errors::ERR_PATTERNS_DRUMS_AND_NOTES, &[]);
            }
            Ok(())
        }
        Check::ClipSlotCheckGrabTrackName => match value {
            Data::Text(name) if named_in(context, |song| song.has_track(name)) => Ok(()),
            _ => refused(errors::ERR_NO_GRAB_TRACK, &[("name", shown())]),
        },
        Check::ChainCheckChainNames => {
            let Some(names) = names_in(value) else {
                return refused(errors::ERR_NOT_CHAIN_NAMES, &[("value", shown())]);
            };
            for name in names {
                if !named_in(context, |set| set.has_generator_named(name)) {
                    return refused(errors::ERR_NO_GENERATOR_CALLED, &[("name", name.into())]);
                }
            }
            Ok(())
        }
        Check::GrooveCheckGrooveChoice => match value {
            Data::Null | Data::Bool(false) => Ok(()),
            Data::Text(name) if named_in(context, |song| song.has_groove(name)) => Ok(()),
            Data::Text(_) => refused(errors::ERR_NO_SUCH_GROOVE, &[("name", shown())]),
            _ => refused(errors::ERR_GROOVE_NOT_NAME_OR_FALSE, &[("value", shown())]),
        },
        Check::SongCheckGrooveName => match value {
            Data::Text(name) if named_in(context, |song| song.has_groove(name)) => Ok(()),
            _ => refused(errors::ERR_SONG_NO_SUCH_GROOVE, &[("name", shown())]),
        },
        Check::SongCheckPreviewInstrument => match value {
            Data::Null => Ok(()),
            Data::Text(name) if named_in(context, |song| song.has_instrument(name)) => Ok(()),
            _ => refused(errors::ERR_SONG_NO_SUCH_PREVIEW_INSTRUMENT, &[("name", shown())]),
        },
        Check::TrackCheckInstrumentName => match value {
            Data::Text(name) if named_in(context, |song| song.has_instrument(name)) => Ok(()),
            _ => refused(errors::ERR_NO_SUCH_INSTRUMENT, &[("name", shown())]),
        },
        Check::SongCheckWizardChoices => match value {
            Data::Null | Data::Map(_) => Ok(()),
            _ => refused(errors::ERR_SONG_BAD_WIZARD, &[("value", shown())]),
        },
        Check::SetlistNeverRefused | Check::SongNeverRefused => Ok(()),
        Check::SetlistCheckVersion => {
            if is_version(value) {
                return Ok(());
            }
            refused(errors::ERR_SONG_BAD_VERSION, &[("value", shown())])
        }
        Check::TrackCheckCcNumbers => {
            let lanes = file_format::CC_ROWS.len();
            let fits = value.as_list().is_some_and(|numbers| {
                numbers.len() == lanes
                    && numbers
                        .iter()
                        .all(|number| number.is_null() || number.as_whole().is_some_and(|whole| (0..=127).contains(&whole)))
            });
            if fits {
                return Ok(());
            }
            refused(
                errors::ERR_BAD_CC_NUMBERS,
                &[("lanes", lanes.into()), ("lowest", 0.into()), ("highest", 127.into()), ("value", shown())],
            )
        }
        Check::TraitsCheckResetDraws => {
            let fits = names_in(value).is_some_and(|names| names.iter().all(|name| file_format::DRAW_NAMES.contains(name)));
            if fits {
                return Ok(());
            }
            refused(
                errors::ERR_BAD_RESET_DRAWS,
                &[("names", listed(file_format::DRAW_NAMES).into()), ("value", shown())],
            )
        }
        Check::DrawCheckSlots => {
            let fits = value
                .as_list()
                .is_some_and(|slots| (limits::MIN_DRAW_SLOTS as usize..=limits::MAX_DRAW_SLOTS as usize).contains(&slots.len()));
            if fits {
                return Ok(());
            }
            refused(
                errors::ERR_BAD_DRAW_SLOTS,
                &[
                    ("lowest", limits::MIN_DRAW_SLOTS.into()),
                    ("highest", limits::MAX_DRAW_SLOTS.into()),
                    ("value", shown()),
                ],
            )
        }
        Check::DriftModelCheckRoot => match value {
            Data::Text(name) if ROOT_NAMES.contains(&name.as_str()) => Ok(()),
            _ => refused(errors::ERR_DRIFT_BAD_ROOT, &[("roots", listed(ROOT_NAMES).into()), ("value", shown())]),
        },
        Check::DriftModelCheckScaleName => match value {
            Data::Text(name) if !name.is_empty() => Ok(()),
            _ => refused(errors::ERR_DRIFT_BAD_SCALE, &[("value", shown())]),
        },
        Check::ChordsModelCheckProgressionChords => {
            let fits = value.as_list().is_some_and(|chords| {
                (limits::MIN_PROGRESSION_CHORDS as usize..=limits::MAX_PROGRESSION_CHORDS as usize).contains(&chords.len())
                    && chords.iter().all(|degree| {
                        degree
                            .as_whole()
                            .is_some_and(|whole| (limits::MIN_PROGRESSION_DEGREE as i128..=limits::MAX_PROGRESSION_DEGREE as i128).contains(&whole))
                    })
            });
            if fits {
                return Ok(());
            }
            refused(
                errors::ERR_BAD_PROGRESSION_CHORDS,
                &[
                    ("most", limits::MAX_PROGRESSION_CHORDS.into()),
                    ("lowest", limits::MIN_PROGRESSION_DEGREE.into()),
                    ("highest", limits::MAX_PROGRESSION_DEGREE.into()),
                    ("value", shown()),
                ],
            )
        }
        Check::ChordsModelRowOfCheck => {
            let allowed: Vec<Data> = match arguments.first() {
                Some(Plain::List(items)) => items.iter().map(plain_data).collect(),
                _ => Vec::new(),
            };
            let fits = value
                .as_list()
                .is_some_and(|values| values.iter().all(|item| item.is_null() || allowed.contains(item)));
            if fits {
                return Ok(());
            }
            refused(errors::ERR_BAD_PROGRESSION_ROW, &[("value", shown())])
        }
        Check::ChordsModelTensionsRow => {
            let is_tensions = |item: &Data| {
                item.as_list().is_some_and(|tensions| {
                    let mut seen: Vec<&Data> = Vec::new();
                    !tensions.is_empty()
                        && tensions.iter().all(|tension| {
                            let fresh = !seen.contains(&tension);
                            seen.push(tension);
                            fresh
                                && tension
                                    .as_str()
                                    .is_some_and(|name| file_format::TENSIONS.iter().any(|(known, _)| *known == name))
                        })
                })
            };
            let fits = value
                .as_list()
                .is_some_and(|values| values.iter().all(|item| item.is_null() || is_tensions(item)));
            if fits {
                return Ok(());
            }
            refused(errors::ERR_BAD_PROGRESSION_TENSIONS, &[("value", shown())])
        }
        Check::GuitarifyModelCheckGuitarBar => {
            let fits = value.as_list().is_some_and(|strokes| {
                !strokes.is_empty()
                    && strokes
                        .iter()
                        .all(|stroke| stroke.as_str().is_some_and(|name| file_format::STROKES.contains(&name)))
            });
            if fits {
                return Ok(());
            }
            refused(errors::ERR_BAD_GUITAR_BAR, &[("value", shown())])
        }
        Check::GuitarifyModelCheckGuitarAccents => {
            let fits = value
                .as_list()
                .is_some_and(|accents| accents.iter().all(|accent| matches!(accent, Data::Bool(_))));
            if fits {
                return Ok(());
            }
            refused(errors::ERR_BAD_GUITAR_ACCENTS, &[("value", shown())])
        }
        Check::TimingStepRowCheckStepRow => {
            let fits = value.as_list().is_some_and(|steps| {
                (limits::MIN_STEP_ROW as usize..=limits::MAX_STEP_ROW as usize).contains(&steps.len()) && steps.iter().all(|step| matches!(step, Data::Bool(_)))
            });
            if fits {
                return Ok(());
            }
            refused(errors::ERR_BAD_STEP_ROW, &[("value", shown())])
        }
        Check::TimingModelCheckGlide => number(value).map(|_| ()),
        Check::ArpModelCheckArpOffsets => match value {
            Data::List(_) => Ok(()),
            _ => refused(errors::ERR_GENERATOR_BAD_OFFSETS, &[("problem", shown())]),
        },
        Check::BuiltInSoundCheckSound | Check::BuiltInsCheckBuiltIns | Check::MusicianModelCheckMusicianBySection => match value {
            Data::Map(_) => Ok(()),
            _ => refused(errors::ERR_NOT_SETTINGS, &[("value", shown())]),
        },
        Check::InstrumentCheckKeyswitches => {
            let fits = value.as_list().is_some_and(|slots| slots.len() == file_format::KEYSWITCH_SLOT_COUNT as usize);
            if fits {
                return Ok(());
            }
            refused(
                errors::ERR_BAD_KEYSWITCHES,
                &[("count", file_format::KEYSWITCH_SLOT_COUNT.into()), ("value", shown())],
            )
        }
        Check::InstrumentCheckPreview => match value {
            Data::Map(_) => Ok(()),
            _ => refused(errors::ERR_NOT_SETTINGS, &[("value", shown())]),
        },
        Check::GrooveCheckCells => {
            let fits = groove_amounts(value).is_some_and(|amounts| {
                amounts
                    .iter()
                    .all(|amount| (limits::MIN_GROOVE_AMOUNT as i128..=limits::MAX_GROOVE_AMOUNT as i128).contains(amount))
            });
            if fits {
                return Ok(());
            }
            refused(
                errors::ERR_BAD_GROOVE_CELLS,
                &[
                    ("fewest", limits::MIN_GROOVE_CELLS.into()),
                    ("most", limits::MAX_GROOVE_CELLS.into()),
                    ("lowest", limits::MIN_GROOVE_AMOUNT.into()),
                    ("highest", limits::MAX_GROOVE_AMOUNT.into()),
                    ("value", shown()),
                ],
            )
        }
        Check::NamedScaleCheckRoot => match value {
            Data::Text(root) if crate::values::note::semitones_above_c(root).is_some() => Ok(()),
            _ => refused(errors::ERR_EXPECTED_ROOT_NOTE, &[("root", shown())]),
        },
        Check::NamedScaleCheckKind => {
            // A file's scale type is read as the member name it means, so that 'natural minor' is NATURAL_MINOR.
            let member = value.python_str().trim().to_uppercase().replace(' ', "_");
            if crate::values::scale::ScaleType::named(&member).is_some() {
                return Ok(());
            }
            refused(
                errors::ERR_UNKNOWN_SCALE_TYPE,
                &[("kind", shown()), ("names", crate::values::scale::ScaleType::file_names().join(", ").into())],
            )
        }
        Check::ConditionsStatementsSettingCheck => {
            let fits = value.as_list().is_some_and(|statements| statements.len() <= limits::MAX_STATEMENTS as usize);
            if fits {
                return Ok(());
            }
            refused(errors::ERR_TOO_MANY_STATEMENTS, &[("most", limits::MAX_STATEMENTS.into()), ("value", shown())])
        }
    }
}
