// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A scene's page (the Python screens/arrange/scene_page.py and pages/scene.py): its name, then its settings in tabs:
//! what it plays, its velocity, its tempo ramps, its shapes, the draws it resets, its other generators and its Bypass
//! When; under them, how long it plays.

use crate::app::App;
use crate::drawing::Style;
use crate::forms::nodes::{Edit, Field};
use crate::forms::tab_box::{columns_of_sections, Tab, TabBox, TabColumn};
use crate::keybindings::{KeyClass, ScenePage as Keys};
use crate::lengths::Lengths;
use crate::page::{clock, Duration};
use crate::screens::arrange::arrange_tabs::{self, bars_shown, labelled, percent_shown, whole, AS_WRITTEN, TEMPO_RAMP_IDS};
use crate::screens::field_page::{Form, Node};
use crate::settings::named_in;
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_math::rational::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::song::Scene;
use llamatron_model::schema::generated::file_format::{SceneSetting, SongSetting, RAMP_WAYS, SECTION_KINDS, TEMPO_RAMP_SETTINGS};
use llamatron_model::schema::generated::limits::{MAX_RAMP_BARS, MAX_SCENE_REPEAT, MAX_TEMPO_PERCENT, MIN_TEMPO_PERCENT};
use llamatron_strings::{labels, legends, marks, messages, named, names};

const NAME: usize = 0;
const SECTION: usize = 1;
const REPEAT: usize = 2;
const LAUNCH_TOGETHER: usize = 3;
const SCALE: usize = 4;
const GROOVE: usize = 5;
const TEMPO: usize = 6;
const MIN_RAMP_BARS: i64 = 1;

pub struct ScenePage {
    pub index: usize,
}

/// A tempo as text, whole where it is, as 120 or 120.5.
fn tempo_text(tempo: Rational) -> String {
    if tempo.denominator() == 1 {
        tempo.numerator().to_string()
    } else {
        llamatron_strings::fill::python_float(tempo.to_float())
    }
}

/// A percentage of a tempo.
fn scaled(tempo: Rational, percent: Rational) -> Rational {
    tempo * percent / Rational::whole(100)
}

fn rational(value: Option<&Data>) -> Option<Rational> {
    value
        .filter(|value| !value.is_null())
        .and_then(|value| llamatron_model::schema::checking::number(value).ok())
}

fn percent_text(percent: Rational) -> String {
    if percent.denominator() == 1 {
        percent_shown(percent.numerator() as i64)
    } else {
        named(marks::MSG_PART_PERCENT_SHOWN, &[("percent", percent.to_float().into())])
    }
}

impl ScenePage {
    /// Write one of the scene's settings, or take it out of the file with None.
    fn write(&self, app: &mut App, setting: &str, value: Option<Data>) {
        arrange_tabs::write_in_song(app, |song| song.set_scene_written(self.index, setting, value));
    }

    /// Store what a key did to one of the scene's fields; false where the field writes nothing so.
    fn write_edit(&self, app: &mut App, id: usize, edit: &Edit) -> bool {
        let Some(scene) = self.scene(app) else { return false };
        if id >= arrange_tabs::BYPASS_IDS {
            use crate::forms::statements::{statement_change, with_statement, StatementChange};
            let statements = scene
                .get_written(SceneSetting::BYPASS_WHEN)
                .and_then(Data::as_list)
                .map(<[Data]>::to_vec)
                .unwrap_or_default();
            match statement_change(&statements, arrange_tabs::BYPASS_IDS, id, edit) {
                StatementChange::Ask(asked) => app.asking = Some(asked),
                StatementChange::Refuse(refusal) => app.refuse(refusal),
                StatementChange::Store { place, statement } => self.write(app, SceneSetting::BYPASS_WHEN, with_statement(&statements, place, statement)),
                StatementChange::Nothing => return false,
            }
            return true;
        }
        match (id, edit) {
            (SECTION, Edit::Choice(chosen)) => self.write(app, SceneSetting::SECTION, (chosen != marks::MSG_NONE_SHOWN).then(|| Data::text(chosen))),
            (REPEAT, Edit::Number(repeat)) => self.write(app, SceneSetting::REPEAT, (*repeat != 1).then_some(Data::Whole(*repeat as i128))),
            (LAUNCH_TOGETHER, Edit::Toggle(on)) => self.write(app, SceneSetting::LAUNCH_TOGETHER, (!on).then_some(Data::Bool(false))),
            (SCALE, Edit::Clear) => self.write(app, SceneSetting::SCALE, None),
            (SCALE, Edit::Enter) => {
                let scales = arrange_tabs::scale_names(app);
                let current = scene.get_written(SceneSetting::SCALE).and_then(Data::as_str).map(str::to_string);
                arrange_tabs::ask_name_or_above(app, messages::MSG_SCENE_SCALE_TITLE, labels::MSG_SONG_OPTION, scales, current.as_deref());
            }
            (SCALE, Edit::Choice(chosen)) => self.write(app, SceneSetting::SCALE, arrange_tabs::chosen_name(chosen)),
            (GROOVE, Edit::Enter) => {
                let current = scene.get_written(SceneSetting::GROOVE).cloned();
                arrange_tabs::ask_groove(app, messages::MSG_SCENE_GROOVE_TITLE, labels::MSG_SONG_OPTION, current.as_ref());
            }
            (GROOVE, Edit::Choice(chosen)) => self.write(app, SceneSetting::GROOVE, arrange_tabs::groove_answer(chosen)),
            (GROOVE, Edit::Adjust(offset)) => {
                let chosen = arrange_tabs::groove_choice_after(app, scene.get_written(SceneSetting::GROOVE), *offset);
                self.write(app, SceneSetting::GROOVE, chosen);
            }
            (GROOVE, Edit::Clear) => self.write(app, SceneSetting::GROOVE, None),
            (TEMPO, Edit::Number(percent)) => self.write(app, SceneSetting::TEMPO, Some(Data::Whole(*percent as i128))),
            (TEMPO, Edit::Clear) => self.write(app, SceneSetting::TEMPO, None),
            (reset, Edit::Toggle(on)) if (arrange_tabs::RESET_IDS..arrange_tabs::GENERATORS).contains(&reset) => {
                let draws = arrange_tabs::draws_with_values(app.document.song());
                let Some(draw) = draws.get(reset - arrange_tabs::RESET_IDS) else {
                    return false;
                };
                let value = arrange_tabs::resets_after(scene.get_written(SceneSetting::RESET_DRAWS), draw, *on);
                self.write(app, SceneSetting::RESET_DRAWS, value);
            }
            _ => {
                let Some(field) = arrange_tabs::field_of(&self.form(app), id) else {
                    return false;
                };
                let (Some(setting), Some(value)) = (field.writes.clone(), field.written(edit)) else {
                    return false;
                };
                self.write(app, &setting, value);
            }
        }
        true
    }

    fn scene<'a>(&self, app: &'a App) -> Option<&'a Scene> {
        app.document.song().scenes().get(self.index)
    }

    fn scene_name(&self, app: &App) -> String {
        self.scene(app)
            .and_then(Scene::get_name)
            .unwrap_or_else(|| named(names::MSG_NEW_SCENE_NAME, &[("number", (self.index + 1).into())]))
    }

    fn song_tempo(app: &App) -> Rational {
        rational(app.document.song().get_written(SongSetting::TEMPO)).unwrap_or(Rational::whole(120))
    }

    /// The tempo the scene plays at: the song's, scaled by its own percentage where it has one.
    fn played_tempo(app: &App, scene: &Scene) -> Rational {
        let song = Self::song_tempo(app);
        rational(scene.get_written(SceneSetting::TEMPO)).map_or(song, |percent| scaled(song, percent))
    }

    fn settings_tab(&self, app: &App, scene: &Scene) -> Tab {
        let song = app.document.song();
        let section = scene
            .get_written(SceneSetting::SECTION)
            .and_then(Data::as_str)
            .unwrap_or(marks::MSG_NONE_SHOWN)
            .to_string();
        let mut sections = vec![marks::MSG_NONE_SHOWN.to_string()];
        sections.extend(SECTION_KINDS.iter().map(|kind| kind.to_string()));
        let repeat = whole(scene.get_written(SceneSetting::REPEAT)).unwrap_or(1);
        let together = !matches!(scene.get_written(SceneSetting::LAUNCH_TOGETHER), Some(Data::Bool(false)));
        let scale = match scene.get_written(SceneSetting::SCALE).and_then(Data::as_str) {
            Some(name) => name.to_string(),
            None => {
                let song_scale = song.get_scale_name().unwrap_or_else(|| messages::MSG_NO_SCALE.to_string());
                named(marks::MSG_SONG_SCALE_SHOWN, &[("scale", song_scale.as_str().into())])
            }
        };
        let groove = match scene.get_written(SceneSetting::GROOVE) {
            None | Some(Data::Null) => {
                let song_groove = song.get_written(SongSetting::GROOVE).and_then(Data::as_str).unwrap_or("none");
                named(marks::MSG_SONG_GROOVE_SHOWN, &[("groove", song_groove.into())])
            }
            Some(Data::Bool(false)) => marks::MSG_GROOVE_OFF_SHOWN.to_string(),
            Some(value) => value.as_str().unwrap_or("").to_string(),
        };
        let percent = rational(scene.get_written(SceneSetting::TEMPO));
        let tempo_shown = match percent {
            None => named(marks::MSG_SONG_TEMPO_SHOWN, &[("tempo", tempo_text(Self::song_tempo(app)).as_str().into())]),
            Some(percent) => named(
                marks::MSG_TEMPO_PERCENT_SHOWN,
                &[
                    ("percent", percent_text(percent).as_str().into()),
                    ("tempo", tempo_text(Self::played_tempo(app, scene)).as_str().into()),
                ],
            ),
        };
        let tempo_number = percent.map(|percent| percent.to_float().round() as i64);
        let playing = vec![
            Field::choice(SECTION, labels::MSG_SCENE_SECTION_LABEL, sections, &section, None),
            Field::number(REPEAT, labels::MSG_REPEAT_LABEL, Some(repeat), Some(1), Some(MAX_SCENE_REPEAT), 1, None),
            Field::toggle(LAUNCH_TOGETHER, labels::MSG_LAUNCH_TOGETHER_LABEL, together),
            Field::custom(SCALE, labels::MSG_SCALE_LABEL, &scale)
                .with_enter(legends::What::CHOOSE)
                .with_clear(legends::MSG_FROM_SONG_WHAT),
            Field::custom(GROOVE, labels::MSG_GROOVE_LABEL, &groove)
                .with_adjust()
                .with_enter(legends::What::CHOOSE)
                .with_clear(legends::MSG_FROM_SONG_WHAT),
            Field::number(
                TEMPO,
                labels::MSG_TEMPO_LABEL,
                tempo_number,
                Some(MIN_TEMPO_PERCENT),
                Some(MAX_TEMPO_PERCENT),
                AS_WRITTEN,
                Some(tempo_shown),
            )
            .with_clear(legends::MSG_FROM_SONG_WHAT),
        ];
        Tab::new(labels::MSG_SETTINGS_TAB, vec![TabColumn::new(Some(labels::MSG_PLAYING_HEADING), playing)])
    }

    fn tempo_ramps_tab(&self, app: &App, scene: &Scene) -> Tab {
        let played = Self::played_tempo(app, scene);
        let blank = named(
            marks::MSG_TEMPO_PERCENT_SHOWN,
            &[
                ("percent", percent_shown(AS_WRITTEN).as_str().into()),
                ("tempo", tempo_text(played).as_str().into()),
            ],
        );
        let mut fields = Vec::new();
        let mut id = TEMPO_RAMP_IDS;
        for way in RAMP_WAYS {
            let setting = |part: &str| labelled(TEMPO_RAMP_SETTINGS, way, part);
            let over = whole(scene.get_written(setting("over")));
            let ramps = over.is_some() && ["start", "end"].iter().any(|part| rational(scene.get_written(setting(part))).is_some());
            id += 1;
            fields.push(Field::heading(id, &named_in(labels::MSG_RAMP_HEADINGS, way), ramps, None, false));
            for part in ["start", "end"] {
                id += 1;
                let number = rational(scene.get_written(setting(part)));
                let shown = match number {
                    None => blank.clone(),
                    Some(percent) => named(
                        marks::MSG_TEMPO_PERCENT_SHOWN,
                        &[
                            ("percent", percent_text(percent).as_str().into()),
                            ("tempo", tempo_text(scaled(played, percent)).as_str().into()),
                        ],
                    ),
                };
                fields.push(
                    Field::number(
                        id,
                        labelled(labels::MSG_TEMPO_RAMP_LABELS, way, part),
                        number.map(|percent| percent.to_float().round() as i64),
                        Some(MIN_TEMPO_PERCENT),
                        Some(MAX_TEMPO_PERCENT),
                        AS_WRITTEN,
                        Some(shown),
                    )
                    .with_clear(&blank)
                    .with_shown_label(&named_in(labels::MSG_RAMP_PART_LABELS, part))
                    .writing(setting(part)),
                );
            }
            id += 1;
            let shown = over.map_or(marks::MSG_NONE_SHOWN.to_string(), bars_shown);
            fields.push(
                Field::number(
                    id,
                    labelled(labels::MSG_TEMPO_RAMP_LABELS, way, "over"),
                    over,
                    Some(MIN_RAMP_BARS),
                    Some(MAX_RAMP_BARS),
                    MIN_RAMP_BARS,
                    Some(shown),
                )
                .with_clear(marks::MSG_NONE_SHOWN)
                .with_shown_label(&named_in(labels::MSG_RAMP_PART_LABELS, "over"))
                .writing(setting("over")),
            );
        }
        Tab::new(labels::MSG_TEMPO_RAMPS_TAB, columns_of_sections(fields))
    }
}

impl Form for ScenePage {
    fn name(&self) -> &'static str {
        "ScenePage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, app: &App) -> Vec<String> {
        vec![
            labels::Crumb::ARRANGE.to_string(),
            named(labels::MSG_SCENE_CRUMB, &[("name", self.scene_name(app).as_str().into())]),
        ]
    }

    fn caption(&self, app: &App) -> Option<String> {
        let what = labels::MSG_SCENE_CAPTION_WORD.to_uppercase();
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", self.scene_name(app).as_str().into())],
        ))
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::FROM_ARRANGE)
    }

    fn duration(&self, app: &App) -> Duration {
        Duration::Seconds(Lengths::of(app.document.get_setlist(), app.document.song()).scene_seconds(self.index))
    }

    fn form(&self, app: &App) -> Vec<Node> {
        let Some(scene) = self.scene(app) else { return Vec::new() };
        let data = scene.to_data();
        let own = |name: &str| whole(scene.get_written(name));
        let above = |_: &str| None;
        let tabs = vec![
            self.settings_tab(app, scene),
            arrange_tabs::velocity_tab(&own, &above),
            self.tempo_ramps_tab(app, scene),
            arrange_tabs::shapes_tab(app, &data),
            arrange_tabs::reset_draws_tab(app.document.song(), scene.get_written(SceneSetting::RESET_DRAWS)),
            arrange_tabs::generators_tab(app, scene.get_written(SceneSetting::CHAINS)),
            arrange_tabs::bypass_tab(scene.get_written(SceneSetting::BYPASS_WHEN)),
        ];
        let name = scene.get_name().unwrap_or_default();
        vec![
            Node::Field(Box::new(Field::name(NAME, &name))),
            Node::TabBox(TabBox {
                label: labels::MSG_TABS_LABEL.to_string(),
                tabs,
            }),
        ]
    }

    fn remarks(&self, app: &App, _width: usize) -> Vec<Text> {
        let lengths = Lengths::of(app.document.get_setlist(), app.document.song());
        let length = clock(lengths.scene_seconds(self.index));
        vec![Text::styled(
            &named(messages::MSG_SCENE_LENGTH_NOTE, &[("length", length.as_str().into())]),
            Style::DIM,
        )]
    }

    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        // ENTER opens a picker only on the fields whose choices the page asks for itself; elsewhere it opens a page.
        let picks = matches!(id, SCALE | GROOVE) || id >= arrange_tabs::BYPASS_IDS;
        if (edit != Edit::Enter || picks) && self.write_edit(app, id, &edit) {
            return;
        }
        if edit == Edit::Enter && id == arrange_tabs::GENERATORS {
            // The list of a scene's generators is not ported yet.
            app.show_page(Box::new(crate::screens::list_page::ListPage::new(
                crate::screens::generators::generator_list_page::GeneratorListPage {
                    holder: crate::screens::generators::generator_list_page::Holder::Scene(self.index),
                    opener_crumbs: self.crumbs(app),
                },
            )));
        }
    }
}
