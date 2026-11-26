// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Writing a set's data as the text of a set file, line for line as the Python program writes it (model/file/
//! setlist_writer.py), so that llamatron saves the very file llamatron saves: the set's settings, its notes as a block,
//! then what every song shares, each a list whose items begin with their names, then the songs, one setting or pattern row
//! a line, every value in braces and brackets.

use crate::file::data::{json_text, load, yaml_float, Data};
use crate::schema::generated::file_format::{FileLayout, PatternSetting, Section, SetlistSetting, SongSetting, OPEN_GENERATOR_TYPES, PATTERN_ROWS};

const INDENT: &str = "  ";
const LIST_ITEM: &str = "- ";
const EMPTY_LIST: &str = "[]";
const EMPTY_MAP: &str = "{}";
const NULL: &str = "~";
const DRUM_LINE: &str = "drum: true";

fn settings_order() -> [&'static str; 15] {
    [
        SetlistSetting::VERSION,
        SetlistSetting::TITLE,
        SetlistSetting::AUTHOR,
        SetlistSetting::DESCRIPTION,
        SetlistSetting::STEP_SIZE,
        SetlistSetting::DEFAULT_OCTAVE,
        SetlistSetting::DEFAULT_DRUM_OCTAVE,
        SetlistSetting::OCTAVE_LABELS,
        SetlistSetting::DEFAULT_FOLLOW_ACTION,
        SetlistSetting::REAL_TIME,
        SetlistSetting::VISUALIZER,
        SetlistSetting::HIDDEN_VISUALIZERS,
        SetlistSetting::GENERATOR_ORDER,
        SetlistSetting::PROTECTED,
        OPEN_GENERATOR_TYPES,
    ]
}

fn before_notes() -> [&'static str; 4] {
    [
        SetlistSetting::VERSION,
        SetlistSetting::TITLE,
        SetlistSetting::AUTHOR,
        SetlistSetting::DESCRIPTION,
    ]
}

fn song_settings() -> [&'static str; 12] {
    [
        SongSetting::TEMPO,
        SongSetting::TIME_SIGNATURE,
        SongSetting::ENTRY_SIZE,
        SongSetting::SCALE,
        SongSetting::GROOVE,
        SongSetting::GENRE,
        SongSetting::SUBGENRE,
        SongSetting::VARIANT,
        SongSetting::LIVE_RESPONSIVENESS,
        SongSetting::VISUALIZER,
        SongSetting::PREVIEW_INSTRUMENT,
        SongSetting::WIZARD,
    ]
}

fn pattern_settings() -> [&'static str; 5] {
    [
        PatternSetting::GROUP,
        PatternSetting::STEP_SIZE,
        PatternSetting::TIME_SIGNATURE,
        PatternSetting::ENTRY_SIZE,
        PatternSetting::DIRECTION,
    ]
}

/// Whether a value is what Python takes as true: anything but nothing, false, zero, and empty text, lists and mappings.
fn truthy(value: Option<&Data>) -> bool {
    match value {
        None | Some(Data::Null) | Some(Data::Bool(false)) => false,
        Some(Data::Whole(whole)) => *whole != 0,
        Some(Data::Float(float)) => *float != 0.0,
        Some(Data::Text(text)) => !text.is_empty(),
        Some(Data::List(items)) => !items.is_empty(),
        Some(Data::Map(pairs)) => !pairs.is_empty(),
        Some(Data::Bool(true)) => true,
    }
}

/// Whether text can be written without quotes and still read back as itself: plain characters, and YAML reading it back as
/// the same text inside brackets.
fn reads_back_as_itself(text: &str) -> bool {
    let mut characters = text.chars();
    let Some(first) = characters.next() else { return false };
    let plain_first = first.is_ascii_alphanumeric() || first == '_';
    let plain_rest = characters.all(|character| character.is_ascii_alphanumeric() || "_#./ -".contains(character));
    plain_first && plain_rest && load(&format!("[{text}]")).is_ok_and(|read| read == Data::List(vec![Data::text(text)]))
}

/// A value as YAML that is safe inside brackets and braces.
pub fn text(value: &Data) -> String {
    match value {
        Data::Null => NULL.into(),
        Data::Bool(flag) => if *flag { "true" } else { "false" }.into(),
        Data::Whole(whole) => whole.to_string(),
        Data::Float(float) => yaml_float(*float),
        Data::Text(written) if reads_back_as_itself(written) => written.clone(),
        Data::Text(written) => json_text(written),
        Data::List(items) => format!("[{}]", items.iter().map(text).collect::<Vec<_>>().join(", ")),
        Data::Map(_) => braces(value),
    }
}

fn braces(settings: &Data) -> String {
    let Some(pairs) = settings.as_map().filter(|pairs| !pairs.is_empty()) else {
        return EMPTY_MAP.into();
    };
    let items: Vec<String> = pairs.iter().map(|(key, value)| format!("{}: {}", text(key), text(value))).collect();
    format!("{{ {} }}", items.join(", "))
}

fn setting(key: &str, value: &str) -> String {
    format!("{key}: {value}")
}

fn heading(key: &str) -> String {
    format!("{key}:")
}

/// The notes as a block, so that each line reads as it was written.
fn notes(written: &str) -> Vec<String> {
    let key = SetlistSetting::NOTES;
    if written.trim().is_empty() {
        return vec![setting(key, &text(&Data::text(written)))];
    }
    // A block whose first line starts with a space says how far it is indented, which YAML can't work out from that line.
    let indent = if written.trim_start_matches('\n').starts_with(' ') { "2" } else { "" };
    let mut chomp = "-";
    let mut body = written;
    if let Some(trimmed) = written.strip_suffix('\n') {
        chomp = if written.ends_with("\n\n") { "+" } else { "" };
        body = trimmed;
    }
    let mut lines = vec![format!("{key}: |{indent}{chomp}")];
    lines.extend(
        body.split('\n')
            .map(|line| if line.is_empty() { String::new() } else { format!("{INDENT}{line}") }),
    );
    lines
}

fn keyed(section: &str, items: &Data) -> Vec<String> {
    let mut lines = vec![heading(section)];
    for (name, item) in items.as_map().unwrap_or(&[]) {
        lines.push(format!("{INDENT}{}", setting(&text(name), &braces(item))));
    }
    lines
}

fn items(section: &str, listed: Option<&Data>) -> Vec<String> {
    let Some(listed) = listed.and_then(Data::as_list).filter(|listed| !listed.is_empty()) else {
        return vec![setting(section, EMPTY_LIST)];
    };
    let mut lines = vec![heading(section)];
    for item in listed {
        lines.push(format!("{INDENT}{LIST_ITEM}{}", braces(item)));
    }
    lines
}

fn patterns(listed: &[Data]) -> Vec<String> {
    let mut lines = vec![heading(Section::PATTERNS)];
    for pattern in listed {
        let name = pattern.get(FileLayout::NAME).cloned().unwrap_or(Data::Null);
        lines.push(format!("{INDENT}{LIST_ITEM}{}", setting(FileLayout::NAME, &text(&name))));
        lines.extend(indented(pattern_lines(pattern), 2));
    }
    lines
}

/// A pattern's settings and then its rows, one to a line, leaving out the rows it doesn't have.
fn pattern_lines(pattern: &Data) -> Vec<String> {
    let steps = pattern.get(PatternSetting::STEPS).cloned().unwrap_or(Data::Null);
    // The steps are written with str(), as the Python writes them, not as YAML.
    let mut lines = vec![setting(PatternSetting::STEPS, &python_str(&steps))];
    if truthy(pattern.get(PatternSetting::DRUM)) {
        lines.push(DRUM_LINE.into());
    }
    for key in pattern_settings() {
        if truthy(pattern.get(key)) {
            lines.push(setting(key, &text(pattern.get(key).unwrap_or(&Data::Null))));
        }
    }
    for row in PATTERN_ROWS {
        if let Some(value) = pattern.get(row).filter(|value| !value.is_null()) {
            lines.push(setting(row, &text(value)));
        }
    }
    lines
}

/// A value as Python's str() writes it, for the one place the writer formats a value with no YAML: a pattern's steps.
fn python_str(value: &Data) -> String {
    match value {
        Data::Null => "None".into(),
        Data::Bool(flag) => if *flag { "True" } else { "False" }.into(),
        Data::Whole(whole) => whole.to_string(),
        Data::Float(float) => llamatron_math::number::python_float_text(*float),
        Data::Text(written) => written.clone(),
        other => text(other),
    }
}

fn scenes(listed: &[Data]) -> Vec<String> {
    if listed.is_empty() {
        return vec![setting(Section::SCENES, EMPTY_LIST)];
    }
    let mut lines = vec![heading(Section::SCENES)];
    for scene in listed {
        lines.extend(scene_lines(scene));
    }
    lines
}

/// One scene as a list item: its settings, then its clips, each on its own line.
fn scene_lines(scene: &Data) -> Vec<String> {
    let pairs = scene.as_map().unwrap_or(&[]);
    if pairs.is_empty() {
        return vec![format!("{INDENT}{LIST_ITEM}{EMPTY_MAP}")];
    }
    let mut lines: Vec<String> = Vec::new();
    for (key, value) in pairs {
        // The first setting starts the list item, and the rest line up under it.
        let prefix = if lines.is_empty() { format!("{INDENT}{LIST_ITEM}") } else { INDENT.repeat(2) };
        let key_text = python_str(key);
        let clips = matches!(key, Data::Text(written) if written == FileLayout::CLIPS);
        if !clips {
            lines.push(format!("{prefix}{}", setting(&key_text, &text(value))));
        } else if !truthy(Some(value)) {
            lines.push(format!("{prefix}{}", setting(&key_text, EMPTY_LIST)));
        } else {
            lines.push(format!("{prefix}{}", heading(&key_text)));
            for clip in value.as_list().unwrap_or(&[]) {
                lines.push(format!("{}{LIST_ITEM}{}", INDENT.repeat(3), braces(clip)));
            }
        }
    }
    lines
}

fn setting_lines(data: &Data, keys: &[&str]) -> Vec<String> {
    keys.iter().filter_map(|key| data.get(key).map(|value| setting(key, &text(value)))).collect()
}

/// The set's settings, with the notes as a block straight after the title, author and description.
fn settings_lines(setlist: &Data) -> Vec<String> {
    let mut settings = setting_lines(setlist, &settings_order());
    if let Some(Data::Text(written)) = setlist.get(SetlistSetting::NOTES).filter(|value| truthy(Some(value))) {
        let place = setting_lines(setlist, &before_notes()).len();
        let block = notes(written);
        settings.splice(place..place, block);
    }
    settings
}

/// One song's lines in groups: its settings, registers, tracks and scenes, leaving out what it doesn't have.
fn song_groups(song: &Data) -> Vec<Vec<String>> {
    let mut groups = Vec::new();
    let settings = setting_lines(song, &song_settings());
    if !settings.is_empty() {
        groups.push(settings);
    }
    if let Some(draws) = song.get(Section::DRAWS).filter(|draws| truthy(Some(draws))) {
        groups.push(keyed(Section::DRAWS, draws));
    }
    groups.push(items(Section::TRACKS, song.get(Section::TRACKS)));
    groups.push(scenes(song.get(Section::SCENES).and_then(Data::as_list).unwrap_or(&[])));
    groups
}

fn songs(listed: &[Data]) -> Vec<String> {
    if listed.is_empty() {
        return vec![setting(Section::SONGS, EMPTY_LIST)];
    }
    let mut lines = vec![heading(Section::SONGS)];
    for (number, song) in listed.iter().enumerate() {
        if number > 0 {
            lines.push(String::new());
        }
        let name = song.get(FileLayout::NAME).cloned().unwrap_or(Data::Null);
        lines.push(format!("{INDENT}{LIST_ITEM}{}", setting(FileLayout::NAME, &text(&name))));
        for (place, group) in song_groups(song).into_iter().enumerate() {
            if place > 0 {
                lines.push(String::new());
            }
            lines.extend(indented(group, 2));
        }
    }
    lines
}

fn indented(lines: Vec<String>, depth: usize) -> Vec<String> {
    let indent = INDENT.repeat(depth);
    lines.into_iter().map(|line| format!("{indent}{line}")).collect()
}

/// A set's data, already laid out as the file is, as the text of a set file.
pub fn dump_file_layout(setlist: &Data) -> String {
    let mut sections = vec![settings_lines(setlist)];
    if truthy(setlist.get(Section::SCALES)) {
        sections.push(items(Section::SCALES, setlist.get(Section::SCALES)));
    }
    if let Some(listed) = setlist.get(Section::PATTERNS).and_then(Data::as_list).filter(|listed| !listed.is_empty()) {
        sections.push(patterns(listed));
    }
    for section in [FileLayout::GENERATORS, Section::GROOVES, Section::INSTRUMENTS] {
        if truthy(setlist.get(section)) {
            sections.push(items(section, setlist.get(section)));
        }
    }
    sections.push(songs(setlist.get(Section::SONGS).and_then(Data::as_list).unwrap_or(&[])));
    let written: Vec<Vec<String>> = sections.into_iter().filter(|section| !section.is_empty()).collect();
    joined(&written) + "\n"
}

/// Sections joined with a blank line between, except after one ending in a blank line, which kept notes' block would absorb.
fn joined(sections: &[Vec<String>]) -> String {
    let Some((first, rest)) = sections.split_first() else { return String::new() };
    let mut written = first.join("\n");
    for section in rest {
        written.push_str(if written.ends_with('\n') { "\n" } else { "\n\n" });
        written.push_str(&section.join("\n"));
    }
    written
}
