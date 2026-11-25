// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The tabs a scene's page and a clip's page share (the Python pages/arrange_tabs.py, velocity_fields.py and
//! shape_fields.py): how loud it plays and its ramps, its shapes, the draws it resets, its other generators and its
//! Bypass When.

use crate::app::App;
use crate::forms::nodes::Edit;
use crate::forms::nodes::Field;
use crate::forms::statements::statement_lines;
use crate::forms::tab_box::{columns_of_sections, Tab, TabColumn};
use crate::screens::generators::generators_page::label_of;
use crate::screens::generators::plugin_editor::{view_write, Made};
use crate::settings::named_in;
use llamatron_model::file::data::Data;
use llamatron_model::objects::song::Song;
use llamatron_model::schema::generated::file_format::GENERATOR_ENABLED;
use llamatron_model::schema::generated::file_format::{DrawSetting, DRAW_NAMES, PLACED_SHAPES, RAMP_WAYS, VELOCITY_RAMP_SETTINGS};
use llamatron_model::schema::generated::limits::{MAX_RAMP_BARS, MAX_VELOCITY_PERCENT, MIN_VELOCITY_PERCENT};
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_strings::{labels, legends, marks, named};

/// A velocity as written, which a level or a ramp leaves alone.
pub const AS_WRITTEN: i64 = 100;
const MIN_RAMP_BARS: i64 = 1;

/// Where each tab's fields take their ids from, so that no two tabs' fields share one.
pub const VELOCITY_IDS: usize = 100;
pub const TEMPO_RAMP_IDS: usize = 200;
pub const SHAPE_IDS: usize = 300;
pub const RESET_IDS: usize = 400;
pub const GENERATORS: usize = 500;
pub const BYPASS_IDS: usize = 600;

pub fn whole(value: Option<&Data>) -> Option<i64> {
    value.filter(|value| !value.is_null()).and_then(Data::as_whole).map(|whole| whole as i64)
}

/// A percentage as a field shows it.
pub fn percent_shown(percent: i64) -> String {
    named(marks::MSG_PERCENT_SHOWN, &[("percent", percent.into())])
}

/// The bars a ramp takes as its field shows them.
pub fn bars_shown(bars: i64) -> String {
    if bars == MIN_RAMP_BARS {
        marks::MSG_RAMP_ONE_BAR_SHOWN.to_string()
    } else {
        named(marks::MSG_RAMP_BARS_SHOWN, &[("bars", bars.into())])
    }
}

/// What a table keyed by a ramp's way and part holds for one, such as velocity_in_start.
pub fn labelled(table: &'static [(&'static [&'static str], &'static str)], way: &str, part: &str) -> &'static str {
    table.iter().find(|(key, _)| key[0] == way && key[1] == part).map_or("", |(_, label)| label)
}

fn velocity_ramp_setting(way: &str, part: &str) -> &'static str {
    labelled(VELOCITY_RAMP_SETTINGS, way, part)
}

/// The Velocity tab: the level across the top, then a column for each ramp; own reads the page's own setting and above the
/// scene's, for a clip that takes it from there.
pub fn velocity_tab(own: &dyn Fn(&str) -> Option<i64>, above: &dyn Fn(&str) -> Option<i64>) -> Tab {
    let level = own("velocity");
    let level_field = Field::number(
        VELOCITY_IDS,
        labels::MSG_VELOCITY_PERCENT_LABEL,
        level,
        Some(MIN_VELOCITY_PERCENT),
        Some(MAX_VELOCITY_PERCENT),
        AS_WRITTEN,
        Some(percent_shown(level.unwrap_or(AS_WRITTEN))),
    )
    .with_clear(&percent_shown(AS_WRITTEN))
    .writing("velocity");
    let mut fields = Vec::new();
    let mut id = VELOCITY_IDS;
    for way in RAMP_WAYS {
        let names: Vec<&str> = ["start", "end", "over"].iter().map(|part| velocity_ramp_setting(way, part)).collect();
        id += 1;
        let is_set = names.iter().any(|name| own(name).is_some());
        fields.push(Field::heading(id, &named_in(labels::MSG_RAMP_HEADINGS, way), is_set, None, false));
        for (part, name) in ["start", "end"].iter().zip(&names) {
            id += 1;
            let taken = above(name);
            let shown = match (own(name), taken) {
                (Some(value), _) => percent_shown(value),
                (None, Some(value)) => named(marks::MSG_FROM_SCENE_SHOWN, &[("value", percent_shown(value).as_str().into())]),
                (None, None) => percent_shown(AS_WRITTEN),
            };
            let cleared = if taken.is_some() {
                legends::MSG_FROM_SCENE_WHAT.to_string()
            } else {
                percent_shown(AS_WRITTEN)
            };
            fields.push(
                Field::number(
                    id,
                    labelled(labels::MSG_VELOCITY_RAMP_LABELS, way, part),
                    own(name),
                    Some(MIN_VELOCITY_PERCENT),
                    Some(MAX_VELOCITY_PERCENT),
                    taken.unwrap_or(AS_WRITTEN),
                    Some(shown),
                )
                .with_clear(&cleared)
                .with_shown_label(&named_in(labels::MSG_RAMP_PART_LABELS, part))
                .writing(name),
            );
        }
        id += 1;
        let over = names[2];
        let taken = above(over);
        let shown = match (own(over), taken) {
            (Some(bars), _) => bars_shown(bars),
            (None, Some(bars)) => named(marks::MSG_FROM_SCENE_SHOWN, &[("value", bars_shown(bars).as_str().into())]),
            (None, None) => marks::MSG_NONE_SHOWN.to_string(),
        };
        let cleared = if taken.is_some() {
            legends::MSG_FROM_SCENE_WHAT
        } else {
            marks::MSG_NONE_SHOWN
        };
        fields.push(
            Field::number(
                id,
                labelled(labels::MSG_VELOCITY_RAMP_LABELS, way, "over"),
                own(over),
                Some(MIN_RAMP_BARS),
                Some(MAX_RAMP_BARS),
                taken.unwrap_or(MIN_RAMP_BARS),
                Some(shown),
            )
            .with_clear(cleared)
            .with_shown_label(&named_in(labels::MSG_RAMP_PART_LABELS, "over"))
            .writing(over),
        );
    }
    let mut tab = Tab::new(labels::MSG_VELOCITY_TAB, columns_of_sections(fields));
    tab.top = vec![level_field];
    tab
}

/// The Shapes tab: a column for each shape a scene or a clip places on its notes.
pub fn shapes_tab(app: &App, data: &Data) -> Tab {
    let mut made = Made::over(app, data).counting_from(SHAPE_IDS);
    let mut fields = Vec::new();
    for shape in PLACED_SHAPES {
        fields.extend(made.shape_section(shape));
    }
    Tab::new(labels::MSG_SHAPES_TAB, columns_of_sections(fields))
}

/// The draws of a song that hold a value in a slot, in order.
pub fn draws_with_values(song: &Song) -> Vec<&'static str> {
    DRAW_NAMES
        .iter()
        .copied()
        .filter(|name| {
            song.draws().iter().any(|(found, draw)| {
                found == name
                    && draw
                        .get_written(DrawSetting::SLOTS)
                        .and_then(Data::as_list)
                        .is_some_and(|slots| slots.iter().any(|slot| !slot.is_null()))
            })
        })
        .collect()
}

/// The Reset Draws tab: a toggle for each draw that holds a value, on where the scene or clip resets it as it starts.
pub fn reset_draws_tab(song: &Song, reset: Option<&Data>) -> Tab {
    let resets: Vec<&str> = reset
        .and_then(Data::as_list)
        .map_or(Vec::new(), |names| names.iter().filter_map(Data::as_str).collect());
    let names = draws_with_values(song);
    let toggles = names
        .iter()
        .enumerate()
        .map(|(place, name)| {
            Field::toggle(
                RESET_IDS + place,
                &named(labels::MSG_RESET_LABEL, &[("name", (*name).into())]),
                resets.contains(name),
            )
        })
        .collect();
    let mut tab = Tab::new(labels::MSG_RESET_DRAWS_TAB, vec![TabColumn::new(None, toggles)]);
    if names.is_empty() {
        tab.remarks = vec![labels::MSG_NO_DRAWS_CONFIGURED.to_string()];
    }
    tab
}

/// The tab of other generators: one field listing each, its kind before its name.
pub fn generators_tab(app: &App, chains: Option<&Data>) -> Tab {
    let setlist = app.document.get_setlist();
    let listed: Vec<String> = chain_names(chains).iter().map(|name| listed_generator(setlist, name)).collect();
    let shown = if listed.is_empty() {
        marks::MSG_NONE_SHOWN.to_string()
    } else {
        listed.join(marks::MSG_CHAIN_JOIN)
    };
    let field = Field::custom(GENERATORS, labels::MSG_GENERATORS_FIELD_LABEL, &shown)
        .with_enter(legends::What::EDIT)
        .with_clear(marks::MSG_NONE_SHOWN);
    Tab::new(labels::MSG_USER_TAB, vec![TabColumn::new(None, vec![field])])
}

/// A generator of a list as a page shows it, its kind before its name, as Chain (fills).
pub fn listed_generator(setlist: &llamatron_model::objects::setlist::Setlist, name: &str) -> String {
    let kind = PLUGINS
        .iter()
        .find(|plugin| setlist.get_item(plugin.section, name).is_some())
        .map_or(labels::MSG_CHAIN_LABEL, |plugin| label_of(plugin.name));
    named(labels::MSG_LISTED_GENERATOR, &[("kind", kind.into()), ("name", name.into())])
}

/// The names a list of generators holds, as written.
pub fn chain_names(chains: Option<&Data>) -> Vec<String> {
    chains
        .and_then(Data::as_list)
        .map_or(Vec::new(), |names| names.iter().filter_map(|name| name.as_str().map(str::to_string)).collect())
}

/// The Bypass When tab: the table of statements alone.
pub fn bypass_tab(statements: Option<&Data>) -> Tab {
    let held = statements.and_then(Data::as_list).map(<[Data]>::to_vec).unwrap_or_default();
    Tab::new(labels::MSG_BYPASS_WHEN_TAB, vec![TabColumn::new(None, statement_lines(0, &held, BYPASS_IDS))])
}

/// Whether a built-in generator's data says it is switched on, which it is not until enabled.
pub fn built_in_on(data: Option<&Data>) -> bool {
    data.and_then(|settings| settings.get("enabled"))
        .is_some_and(|value| matches!(value, Data::Bool(true)))
}

/// A tab of a generator built into a track or a clip, made from its plugin's view, its fields' ids counting from first_id.
pub fn built_in_tab(app: &App, built_ins: Option<&Data>, kind: &'static str, first_id: usize) -> Tab {
    let empty = Data::Map(Vec::new());
    let data = built_ins.and_then(|built_ins| built_ins.get(kind)).unwrap_or(&empty);
    let bypass = data.get("bypass_when").and_then(Data::as_list).map_or(0, <[Data]>::len);
    let mut made = Made::of(app, kind, data, true).counting_from(first_id);
    made.tab(&tab_label_of(kind), bypass)
}

/// The setting an edit of a built-in generator's tab writes and its value, None leaving it out of the file: its Enabled
/// toggle, which a built-in generator writes only while on, or a field its plugin's view shows.
pub fn built_in_edit(app: &App, built_ins: Option<&Data>, kind: &'static str, first_id: usize, id: usize, edit: &Edit) -> Option<(&'static str, Option<Data>)> {
    if id == first_id + 1 {
        return match edit {
            Edit::Toggle(on) => Some((GENERATOR_ENABLED, on.then_some(Data::Bool(true)))),
            _ => None,
        };
    }
    let empty = Data::Map(Vec::new());
    let data = built_ins.and_then(|built_ins| built_ins.get(kind)).unwrap_or(&empty);
    let mut made = Made::of(app, kind, data, true).counting_from(first_id);
    let _ = made.tab(&tab_label_of(kind), 0);
    let view = made.views().iter().find(|(found, _)| *found == id).map(|(_, view)| *view)?;
    view_write(view, edit, made.mode().as_deref())
}

/// A track's or a clip's built-in generators with one setting of one kind written, or taken out with None; None where none
/// is left.
pub fn with_built_in(built_ins: Option<&Data>, kind: &str, setting: &str, value: Option<Data>) -> Option<Data> {
    let mut kinds: Vec<(Data, Data)> = built_ins.and_then(Data::as_map).map(<[(Data, Data)]>::to_vec).unwrap_or_default();
    let mut settings: Vec<(Data, Data)> = kinds
        .iter()
        .find(|(found, _)| found.as_str() == Some(kind))
        .and_then(|(_, settings)| settings.as_map().map(<[(Data, Data)]>::to_vec))
        .unwrap_or_default();
    settings.retain(|(found, _)| found.as_str() != Some(setting));
    if let Some(value) = value {
        settings.push((Data::text(setting), value));
    }
    match kinds.iter_mut().find(|(found, _)| found.as_str() == Some(kind)) {
        Some((_, held)) => *held = Data::Map(settings.clone()),
        None => kinds.push((Data::text(kind), Data::Map(settings.clone()))),
    }
    kinds.retain(|(_, held)| held.as_map().is_some_and(|pairs| !pairs.is_empty()));
    (!kinds.is_empty()).then_some(Data::Map(kinds))
}

/// A built-in generator's tab's label.
pub fn tab_label_of(kind: &str) -> String {
    use llamatron_strings::plugin_texts::*;
    match kind {
        "chords" => chords::MSG_TAB_LABEL,
        "arp" => arp::MSG_TAB_LABEL,
        "guitarify" => guitarify::MSG_TAB_LABEL,
        "timing" => timing::MSG_TAB_LABEL,
        _ => phrasing::MSG_TAB_LABEL,
    }
    .to_string()
}

/// The kinds built into a track or a clip, in the order their tabs stand.
pub fn built_in_kinds() -> Vec<&'static str> {
    let mut kinds: Vec<(i64, &'static str)> = PLUGINS
        .iter()
        .filter_map(|plugin| plugin.built_in_place.map(|place| (place, plugin.name)))
        .collect();
    kinds.sort();
    kinds.into_iter().map(|(_, name)| name).collect()
}

/// Change the current song, as one edit of the set.
pub fn write_in_song(app: &mut App, change: impl FnOnce(&mut llamatron_model::objects::song::Song)) {
    let name = app.document.get_current_song_name().to_string();
    app.document.change_set(|setlist| {
        if let Some(llamatron_model::objects::setlist::Item::Song(song)) =
            setlist.get_item_mut(llamatron_model::schema::generated::file_format::Section::SONGS, &name)
        {
            change(song);
        }
    });
}

/// The field of an id among a page's nodes, a cell of a row among them.
pub fn field_of(nodes: &[crate::screens::field_page::Node], id: usize) -> Option<Field> {
    use crate::screens::field_page::Node;
    nodes.iter().find_map(|node| match node {
        Node::Field(field) => field.find(id).cloned(),
        Node::TabBox(tab_box) => tab_box
            .tabs
            .iter()
            .find_map(|tab| tab.every_field().into_iter().find_map(|field| field.find(id).cloned())),
    })
}

/// The answer a picker gives for its first choice, the value taken from above or none.
pub const FROM_ABOVE: &str = "";
/// The answer a groove picker gives for playing straight, which no groove's name can be.
const GROOVE_OFF: &str = "\0off";

/// Ask the page's picker for one of a list, opening on the current answer: the options as shown, the answers they give.
pub fn ask_choice(app: &mut App, title: &str, options: Vec<String>, choices: Vec<String>, current: &str) {
    let place = choices.iter().position(|choice| choice == current).unwrap_or(0);
    app.asking = Some(Edit::AskChoice {
        title: title.to_string(),
        options,
        current: place,
        choices,
    });
}

/// Ask for a value taken from above, shown first as `above`, or one of a list of names, opening on the current one.
pub fn ask_name_or_above(app: &mut App, title: &str, above: &str, names: Vec<String>, current: Option<&str>) {
    let mut options = vec![above.to_string()];
    options.extend(names.iter().cloned());
    let mut choices = vec![FROM_ABOVE.to_string()];
    choices.extend(names);
    ask_choice(app, title, options, choices, current.unwrap_or(FROM_ABOVE));
}

/// The value a picker's answer stores: the name chosen, or None for the first choice.
pub fn chosen_name(chosen: &str) -> Option<Data> {
    (chosen != FROM_ABOVE).then(|| Data::text(chosen))
}

/// Ask for a scene's or a track's groove: from above, off, or a groove by name, opening on the current choice.
pub fn ask_groove(app: &mut App, title: &str, above: &str, current: Option<&Data>) {
    let names = crate::settings::sorted_names(&crate::screens::set::grooves_page::groove_names(app));
    let mut options = vec![above.to_string(), labels::MSG_GROOVE_OFF_OPTION.to_string()];
    options.extend(names.iter().cloned());
    let mut choices = vec![FROM_ABOVE.to_string(), GROOVE_OFF.to_string()];
    choices.extend(names);
    let current = match current {
        Some(Data::Bool(false)) => GROOVE_OFF,
        Some(Data::Text(name)) => name.as_str(),
        _ => FROM_ABOVE,
    };
    ask_choice(app, title, options, choices, current);
}

/// The groove choice a groove picker's answer stores: None from above, false off, or the groove's name.
pub fn groove_answer(chosen: &str) -> Option<Data> {
    match chosen {
        FROM_ABOVE => None,
        GROOVE_OFF => Some(Data::Bool(false)),
        name => Some(Data::text(name)),
    }
}

/// A groove choice a step along: from above first, then off, then each groove by name, stopping at both ends.
pub fn groove_choice_after(app: &App, current: Option<&Data>, offset: i64) -> Option<Data> {
    let names = crate::settings::sorted_names(&crate::screens::set::grooves_page::groove_names(app));
    let mut choices = vec![None, Some(Data::Bool(false))];
    choices.extend(names.into_iter().map(|name| Some(Data::Text(name))));
    let current = current.filter(|value| !value.is_null()).cloned();
    let place = choices.iter().position(|choice| *choice == current).unwrap_or(0) as i64;
    choices[(place + offset).clamp(0, choices.len() as i64 - 1) as usize].clone()
}

/// The draws a scene or a clip resets with one switched on or off, in the draws' order, or None where it resets none.
pub fn resets_after(reset: Option<&Data>, draw: &str, on: bool) -> Option<Data> {
    let mut names: Vec<String> = reset
        .and_then(Data::as_list)
        .map_or(Vec::new(), |names| names.iter().filter_map(Data::as_str).map(str::to_string).collect());
    names.retain(|name| name != draw);
    if on {
        names.push(draw.to_string());
    }
    let ordered: Vec<Data> = DRAW_NAMES
        .iter()
        .filter(|name| names.iter().any(|each| each == *name))
        .map(|name| Data::text(name))
        .collect();
    (!ordered.is_empty()).then_some(Data::List(ordered))
}

/// The set's scales by name, sorted.
pub fn scale_names(app: &App) -> Vec<String> {
    let names: Vec<String> = app
        .document
        .get_setlist()
        .items(llamatron_model::schema::generated::file_format::Section::SCALES)
        .iter()
        .map(|(name, _)| name.clone())
        .collect();
    crate::settings::sorted_names(&names)
}
