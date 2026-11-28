// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! How the things a set holds are named (the Python model/objects/naming.py): a copy's name, a name nothing has yet, and the
//! order names sort in. Names compare without regard to capitals and are kept as typed.

#[cfg(test)]
use llamatron_names::file_format;
use llamatron_names::fill;
#[cfg(test)]
use llamatron_names::words;
use llamatron_strings::named;
use llamatron_strings::names;

const FIRST_COPY_NUMBER: i64 = 2;
const FIRST_NEW_NUMBER: i64 = 1;

fn is_separator(character: char) -> bool {
    character.is_whitespace() || character == '_' || character == '-'
}

/// A name's words, what joins its number to them and the number it ends in, like ("verse", "-", 1), or None where it
/// ends in no number, as the Python's TRAILING_NUMBER pattern splits it.
pub fn split_trailing_number(name: &str) -> Option<(String, String, i64)> {
    let characters: Vec<char> = name.chars().collect();
    let digits = characters.iter().rev().take_while(|character| character.is_ascii_digit()).count();
    if digits == 0 || digits == characters.len() {
        return None;
    }
    let prefix = &characters[..characters.len() - digits];
    let number: i64 = characters[prefix.len()..].iter().collect::<String>().parse().ok()?;
    // The base is as short as it can be, at least a letter: then the joint is every separator after it, or nothing where the
    // base ends in a character that is neither a digit nor a separator.
    for length in 1..=prefix.len() {
        let rest = &prefix[length..];
        if !rest.is_empty() && rest.iter().all(|character| is_separator(*character)) {
            return Some((prefix[..length].iter().collect(), rest.iter().collect(), number));
        }
        if rest.is_empty() {
            let last = prefix[length - 1];
            if !last.is_ascii_digit() && !is_separator(last) {
                return Some((prefix.iter().collect(), String::new(), number));
            }
        }
    }
    None
}

/// Whether two names are one name, without regard to capitals.
pub fn same_name(one: &str, other: &str) -> bool {
    one.to_lowercase() == other.to_lowercase()
}

/// Whether a name is one of the names taken.
pub fn is_taken<S: AsRef<str>>(name: &str, taken: &[S]) -> bool {
    taken.iter().any(|other| same_name(name, other.as_ref()))
}

/// A name not in use: the name wanted where it is free, else the duplicate's name counted up from it.
pub fn unique_name<S: AsRef<str>>(base: &str, taken: &[S]) -> String {
    if !is_taken(base, taken) {
        return base.to_string();
    }
    copy_name(base, taken)
}

/// The name for a duplicate: a dash and 2 after a name with no number, else counting up from the number it ends in.
pub fn copy_name<S: AsRef<str>>(name: &str, taken: &[S]) -> String {
    let (base, joint, number) = match split_trailing_number(name) {
        Some((base, joint, number)) => (base, joint, number),
        None => (name.to_string(), names::MSG_NUMBER_JOINT.to_string(), FIRST_COPY_NUMBER - 1),
    };
    let mut number = FIRST_COPY_NUMBER.max(number + 1);
    while is_taken(&format!("{base}{joint}{number}"), taken) {
        number += 1;
    }
    format!("{base}{joint}{number}")
}

/// The name for a new thing of a kind: its word, a dash and one more than the highest number any name of that word ends in.
pub fn new_name<S: AsRef<str>>(word: &str, taken: &[S]) -> String {
    numbered_after(word, taken, names::MSG_NUMBERED_NAME)
}

/// The name for a new track of a kind: its word and one more than the highest number any name of that word ends in, with
/// no joiner between, as main1 and drum2.
pub fn new_track_name<S: AsRef<str>>(word: &str, taken: &[S]) -> String {
    numbered_after(word, taken, names::MSG_JOINED_NUMBERED_NAME)
}

/// A word and one more than the highest number any taken name of that word ends in, laid out by a template.
fn numbered_after<S: AsRef<str>>(word: &str, taken: &[S], template: &str) -> String {
    let mut highest = FIRST_NEW_NUMBER - 1;
    for other in taken {
        if let Some((base, _, number)) = split_trailing_number(other.as_ref()) {
            if same_name(&base, word) {
                highest = highest.max(number);
            }
        }
    }
    named(template, &[(fill::BASE, word.into()), (fill::NUMBER, (highest + 1).into())])
}

/// What names sort by everywhere: the words ignoring capitals, then the number a name ends in read as a number.
pub fn name_order(name: &str) -> (String, i64, i64, String) {
    match split_trailing_number(name) {
        None => (name.to_lowercase(), 0, 0, name.to_lowercase()),
        Some((base, _, number)) => (base.to_lowercase(), 1, number, name.to_lowercase()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn names_count_up_keeping_their_joiner() {
        let second = 2;
        assert_eq!(split_trailing_number("bass-2"), Some((file_format::Row::BASS.into(), "-".into(), second)));
        assert_eq!(split_trailing_number(words::NAME1), Some((file_format::FileLayout::NAME.into(), "".into(), 1)));
        assert_eq!(split_trailing_number("bass 2"), Some((file_format::Row::BASS.into(), " ".into(), second)));
        assert_eq!(split_trailing_number("12"), None);
        assert_eq!(split_trailing_number("a1-2"), Some((words::A1.into(), "-".into(), second)));
        assert_eq!(unique_name(words::FOO, &[words::FOO]), "foo-2");
        assert_eq!(unique_name("bass-2", &["Bass-2", "bass-3"]), "bass-4");
        assert_eq!(new_name(file_format::ClipSlotSetting::PATTERN, &["pattern-3", "other-9"]), "pattern-4");
    }
}
