// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The document's edits to anything that has a name (the Python document_parts/named_edits.py and set_edits.py's adds):
//! renaming, copying, deleting, moving and sorting take the section the thing is in, the current song's tracks among them,
//! each worked on the set's data through the model's edits; and adding a song, a scale or a groove.

use crate::document::Document;
use llamatron_engine::groove::FACTORY_GROOVES;
use llamatron_model::file::data::Data;
use llamatron_model::objects::edits;
use llamatron_model::objects::naming::{copy_name, new_name};
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::schema::generated::defaults::DEFAULT_TEMPO;
use llamatron_model::schema::generated::file_format::Section;
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_names::words;
use llamatron_strings::{errors, named, names};

/// The cells of a new groove: one bar of sixteenths.
const NEW_GROOVE_CELLS: usize = 16;

pub const TRACKS: &str = file_format::Section::TRACKS;
const SONGS: &str = file_format::Section::SONGS;
const GROOVES: &str = file_format::Section::GROOVES;
const INSTRUMENTS: &str = file_format::Section::INSTRUMENTS;
const CHAINS: &str = file_format::Section::CHAINS;
const PATTERNS: &str = file_format::Section::PATTERNS;
const GROUP: &str = file_format::PatternSetting::GROUP;
/// The cell length a factory groove's copy leaves out, its sixteenths.
const SIXTEENTHS: (i128, i128) = (1, 16);
/// What a new scale is: C major.
const NEW_SCALE_ROOT: &str = "C";
const NEW_SCALE_KIND: &str = file_format::Quality::MAJOR;
const FIRST_NUMBER: i64 = 1;

impl Document {
    /// The names in a section, in order: the current song's for its tracks, the set's otherwise, the factory grooves before
    /// the set's own.
    pub fn names_of(&self, section: &str) -> Vec<String> {
        if section == TRACKS {
            return self.song().get_track_names().into_iter().map(str::to_string).collect();
        }
        let own: Vec<String> = self.get_setlist().items(section).iter().map(|(name, _)| name.clone()).collect();
        if section != GROOVES {
            return own;
        }
        let mut names: Vec<String> = FACTORY_GROOVES.iter().map(|(name, ..)| name.to_string()).collect();
        names.extend(own);
        names
    }

    /// The names a new or copied item of a section may not take: every generator's and chain's for a generator or a chain,
    /// since they share one list in a set file, and the section's own otherwise.
    pub fn names_taken(&self, section: &str) -> Vec<String> {
        if !is_generator_section(section) {
            return self.names_of(section);
        }
        let mut names: Vec<String> = Vec::new();
        for each in PLUGINS.iter().map(|plugin| plugin.section).chain([CHAINS]) {
            names.extend(self.names_of(each));
        }
        names
    }

    /// The name a new item of a section is given: the word, a dash and one more than the highest number in use.
    pub fn new_name(&self, section: &str, word: &str) -> String {
        new_name(word, &self.names_taken(section))
    }

    /// Add a generator of a section with the settings a new one starts with (the Python's settings_of(kind).new()): a chain
    /// with no steps, an arpeggiator playing up, and any other kind with nothing set.
    pub fn add_generator(&mut self, section: &str, name: &str) -> Result<(), String> {
        let item = if section == Section::CHAINS {
            Data::List(Vec::new())
        } else if section == ARPS {
            Data::Map(vec![(Data::text(ARP_ORDER), Data::text(ARP_ORDER_UP))])
        } else {
            Data::Map(Vec::new())
        };
        self.edit_data(|data| {
            let mut data = data.clone();
            let mut items = data.get(section).cloned().unwrap_or(Data::Map(Vec::new()));
            if let Data::Map(pairs) = &mut items {
                pairs.push((Data::text(name), item));
            }
            data.set(section, items);
            data
        })
    }

    // Arrange's edits of the current song's scenes, tracks and clips.

    /// Give every clip of the current song a pattern of its own, and return the names of the copies made.
    pub fn fracture(&mut self) -> Result<Vec<String>, String> {
        let song = self.get_current_song_name().to_string();
        let (changed, copies) = edits::fractured(&self.get_setlist().to_data(), &song);
        if !copies.is_empty() {
            self.edit_data(|_| changed)?;
        }
        Ok(copies)
    }

    /// Put a new scene of no clips at a place in the current song, under a name.
    pub fn add_scene(&mut self, index: usize, name: &str) -> Result<(), String> {
        let song = self.get_current_song_name().to_string();
        self.edit_data(|data| edits::added_scene(data, &song, index, name))
    }

    /// Put a copy of a scene, with its clips, right after it, named after it.
    pub fn copy_scene(&mut self, index: usize) -> Result<(), String> {
        let song = self.get_current_song_name().to_string();
        let taken: Vec<String> = self
            .song()
            .scenes()
            .iter()
            .filter_map(|scene| scene.get_written(file_format::FileLayout::NAME).and_then(Data::as_str).map(str::to_string))
            .collect();
        let name = self
            .song()
            .scenes()
            .get(index)
            .and_then(|scene| scene.get_written(file_format::FileLayout::NAME))
            .and_then(Data::as_str)
            .unwrap_or(llamatron_strings::names::MSG_SCENE_WITHOUT_A_NAME)
            .to_string();
        let new = llamatron_model::objects::naming::copy_name(&name, &taken);
        self.edit_data(|data| edits::copied_scene(data, &song, index, &new))
    }

    /// Take a scene out of the current song, with its clips.
    pub fn remove_scene(&mut self, index: usize) -> Result<(), String> {
        let song = self.get_current_song_name().to_string();
        self.edit_data(|data| edits::removed_scene(data, &song, index))
    }

    /// Add a track of no clips to the current song, before the track at a place or after the last.
    pub fn add_track(&mut self, name: &str, place: Option<usize>, drum: bool) -> Result<(), String> {
        let song = self.get_current_song_name().to_string();
        self.edit_data(|data| edits::added_track(data, &song, name, place, drum, None))
    }

    /// Add a track with an instrument of its own, named after it or counted up from its name where that is taken, as one
    /// step to undo. Hands back the instrument's name.
    pub fn add_track_with_instrument(&mut self, name: &str, place: Option<usize>, drum: bool, instrument: Data) -> Result<String, String> {
        let song = self.get_current_song_name().to_string();
        let taken = self.names_of(INSTRUMENTS);
        let instrument_name = llamatron_model::objects::naming::unique_name(name, &taken);
        self.edit_data(|data| {
            let with_track = edits::added_track(data, &song, name, place, drum, Some(&instrument_name));
            with_item(&with_track, INSTRUMENTS, &instrument_name, instrument)
        })?;
        Ok(instrument_name)
    }

    /// Give a track a copy of its instrument, named after the track or counted up, as one step to undo; nothing for a
    /// track with no instrument.
    pub fn give_track_own_instrument(&mut self, track: &str) -> Result<(), String> {
        use llamatron_model::objects::setlist::Item;
        use llamatron_model::schema::generated::file_format::TrackSetting;
        let Some(instrument) = self.song().get_track(track).and_then(|held| held.get_instrument_name()) else {
            return Ok(());
        };
        let Some(Item::Instrument(held)) = self.get_setlist().get_item(INSTRUMENTS, &instrument).cloned() else {
            return Ok(());
        };
        let copy = llamatron_model::objects::naming::unique_name(track, &self.names_of(INSTRUMENTS));
        let song = self.get_current_song_name().to_string();
        let track = track.to_string();
        self.change_set(|setlist| {
            setlist.add_item(INSTRUMENTS, &copy, Item::Instrument(held));
            if let Some(Item::Song(song)) = setlist.get_item_mut(SONGS, &song) {
                song.set_track_written(&track, TrackSetting::INSTRUMENT, Some(Data::text(&copy)));
            }
        });
        Ok(())
    }

    /// Put a clip, as its data, on a track in a scene of the current song, in place of any there.
    pub fn put_clip(&mut self, index: usize, track: &str, clip: &Data) -> Result<(), String> {
        let song = self.get_current_song_name().to_string();
        self.edit_data(|data| edits::put_clip(data, &song, index, track, clip))
    }

    /// Take the clip on a track in a scene of the current song out of it.
    pub fn remove_clip(&mut self, index: usize, track: &str) -> Result<(), String> {
        let song = self.get_current_song_name().to_string();
        self.edit_data(|data| edits::removed_clip(data, &song, index, track))
    }

    /// Add a pattern of empty steps: a drum pattern, or one written for a scale of a number of notes.
    pub fn add_blank_pattern(&mut self, name: &str, steps: i64, group: Option<&str>, drum: bool, scale_length: Option<i64>) -> Result<(), String> {
        let pattern = edits::blank_pattern(steps, group, drum, scale_length);
        self.edit_data(|data| {
            let mut data = data.clone();
            let mut patterns = data.get(Section::PATTERNS).cloned().unwrap_or(Data::Map(Vec::new()));
            if let Data::Map(pairs) = &mut patterns {
                pairs.push((Data::text(name), pattern));
            }
            data.set(Section::PATTERNS, patterns);
            data
        })
    }

    /// Give clips of the current song, each by its scene's place and its track, copies of the patterns they play, each
    /// pattern copied once under a new name however many of them play it, so that a copied scene or track can be changed
    /// without changing the one it was copied from.
    pub fn give_own_patterns(&mut self, clips: &[(usize, String)]) -> Result<(), String> {
        let mut copies: Vec<(String, String)> = Vec::new();
        for (index, track) in clips {
            let Some(clip) = self.clip_data(*index, track) else { continue };
            for name in edits::clip_patterns(&clip) {
                if !copies.iter().any(|(old, _)| *old == name) {
                    let new = self.copy_named(Section::PATTERNS, &name)?;
                    copies.push((name, new));
                }
            }
        }
        for (index, track) in clips {
            let Some(clip) = self.clip_data(*index, track) else { continue };
            let renamed = |name: &str| copies.iter().find(|(old, _)| old == name).map_or(name.to_string(), |(_, new)| new.clone());
            let playing = edits::clip_playing(&clip, &renamed);
            self.put_clip(*index, track, &playing)?;
        }
        Ok(())
    }

    /// The set's patterns in a group, in the file's order, or in no group for None.
    pub fn patterns_in_group(&self, group: Option<&str>) -> Vec<String> {
        self.get_setlist()
            .items(Section::PATTERNS)
            .iter()
            .filter_map(|(name, item)| match item {
                llamatron_model::objects::setlist::Item::Pattern(pattern) => {
                    let held = pattern.get_written(file_format::PatternSetting::GROUP).and_then(Data::as_str);
                    (held == group).then(|| name.clone())
                }
                _ => None,
            })
            .collect()
    }

    /// Put patterns in a group, or in none.
    fn set_groups(&mut self, names: &[String], group: Option<&str>) {
        self.change_set(|setlist| {
            for name in names {
                if let Some(pattern) = setlist.get_pattern_mut(name) {
                    pattern.set_group(group);
                }
            }
        });
    }

    /// Give a group another name, for every pattern in it.
    pub fn rename_pattern_group(&mut self, old: &str, new: &str) {
        let names = self.patterns_in_group(Some(old));
        self.set_groups(&names, Some(new));
    }

    /// Take every pattern out of a group, deleting none.
    pub fn ungroup_patterns(&mut self, group: &str) {
        let names = self.patterns_in_group(Some(group));
        self.set_groups(&names, None);
    }

    /// Copy every pattern of a group into a new group, and return the copies' names: each named with the new group's name
    /// in place of the old's at its front, or joined to it with an underscore, a taken name counting up. A name longer than
    /// a name may be refuses the whole copy.
    pub fn copy_pattern_group(&mut self, group: &str, new: &str) -> Result<Vec<String>, String> {
        let mut taken = self.names_taken(Section::PATTERNS);
        let mut names = Vec::new();
        for name in self.patterns_in_group(Some(group)) {
            let base = if !group.is_empty() && name.to_lowercase().starts_with(&group.to_lowercase()) {
                format!("{new}{}", &name[group.len()..])
            } else {
                format!("{new}_{name}")
            };
            let copied = llamatron_model::objects::naming::unique_name(&base, &taken);
            taken.push(copied.clone());
            names.push((name, copied));
        }
        let most = llamatron_model::schema::generated::limits::MAX_NAME_LENGTH as usize;
        if let Some((_, long)) = names.iter().find(|(_, copied)| copied.chars().count() > most) {
            return Err(named(
                errors::ERR_GROUP_COPY_NAME_TOO_LONG,
                &[(fill::NAME, long.as_str().into()), (fill::MOST, most.into())],
            ));
        }
        let setlist = self.get_setlist();
        let copies: Vec<(String, llamatron_model::objects::pattern::Pattern)> = names
            .iter()
            .filter_map(|(name, copied)| {
                let mut copy = setlist.get_pattern(name)?.clone();
                copy.set_group(Some(new));
                Some((copied.clone(), copy))
            })
            .collect();
        self.change_set(|setlist| {
            for (copied, copy) in copies {
                setlist.add_item(Section::PATTERNS, &copied, llamatron_model::objects::setlist::Item::Pattern(copy));
            }
        });
        Ok(names.into_iter().map(|(_, copied)| copied).collect())
    }

    /// Put a copy of another pattern's steps and settings in place of a pattern's, keeping its name and its place.
    pub fn load_over(&mut self, name: &str, other: &str) -> Result<(), String> {
        let copy = self
            .get_setlist()
            .get_pattern(other)
            .cloned()
            .ok_or_else(|| named(errors::ERR_CLIP_SLOT_NO_SUCH_PATTERN, &[(fill::NAME, other.into())]))?;
        let name = name.to_string();
        self.change_set(|setlist| {
            if let Some(pattern) = setlist.get_pattern_mut(&name) {
                *pattern = copy;
            }
        });
        Ok(())
    }

    /// Make new patterns of a pattern's steps, so many steps each and the last with what is left, and return their names,
    /// the pattern itself left as it is: each part keeps the pattern's settings and group, named after it with the word
    /// split and a number counted on from the highest such name in use. A part's name longer than a name may be refuses the
    /// whole split.
    pub fn split_pattern(&mut self, name: &str, steps: usize) -> Result<Vec<String>, String> {
        let pattern = self
            .get_setlist()
            .get_pattern(name)
            .cloned()
            .ok_or_else(|| named(errors::ERR_CLIP_SLOT_NO_SUCH_PATTERN, &[(fill::NAME, name.into())]))?;
        let count = pattern.get_steps() as usize;
        let starts: Vec<usize> = (0..count).step_by(steps.max(1)).collect();
        let word = named(names::MSG_SPLIT_BASE, &[(fill::NAME, name.into())]);
        let first =
            llamatron_model::objects::naming::split_trailing_number(&new_name(&word, &self.names_taken(Section::PATTERNS))).map_or(1, |(_, _, number)| number);
        let made: Vec<String> = (0..starts.len())
            .map(|part| {
                named(
                    names::MSG_NUMBERED_NAME,
                    &[(fill::BASE, word.as_str().into()), (fill::NUMBER, (first + part as i64).into())],
                )
            })
            .collect();
        let most = llamatron_model::schema::generated::limits::MAX_NAME_LENGTH as usize;
        if let Some(long) = made.iter().find(|part| part.chars().count() > most) {
            return Err(named(
                errors::ERR_GROUP_COPY_NAME_TOO_LONG,
                &[(fill::NAME, long.as_str().into()), (fill::MOST, most.into())],
            ));
        }
        let mut parts = Vec::new();
        for (part, start) in made.iter().zip(&starts) {
            let mut copy = pattern.clone();
            let order: Vec<usize> = (*start..(*start + steps).min(count)).collect();
            copy.take_steps(&order).map_err(|problem| problem.message)?;
            parts.push((part.clone(), copy));
        }
        self.change_set(|setlist| {
            for (part, copy) in parts {
                setlist.add_item(Section::PATTERNS, &part, llamatron_model::objects::setlist::Item::Pattern(copy));
            }
        });
        Ok(made)
    }

    /// The data of the clip on a track in a scene of the current song.
    fn clip_data(&self, index: usize, track: &str) -> Option<Data> {
        self.song().scenes().get(index)?.get_clip_slot(track).map(|clip| clip.to_data())
    }

    /// Change the set by its data, the change read back into the set, refused with why where the set would not read.
    fn edit_data(&mut self, change: impl FnOnce(&Data) -> Data) -> Result<(), String> {
        let changed = change(&self.get_setlist().to_data());
        let setlist = Setlist::from_data(&changed).map_err(|error| error.message)?;
        self.change_set(|held| *held = setlist);
        Ok(())
    }

    /// Rename an item of a section, which changes every reference to it by name. A renamed song stays current, and a renamed
    /// track renames the pattern group of its name, where there is one and no group has the new name.
    pub fn rename_named(&mut self, section: &str, old: &str, new: &str) -> Result<(), String> {
        let song = self.get_current_song_name().to_string();
        if section == TRACKS {
            self.edit_data(|data| edits::renamed_track(data, &song, old, new))?;
            let groups = pattern_groups(&self.get_setlist().to_data());
            if groups.iter().any(|group| group == old) && !groups.iter().any(|group| group == new) {
                self.edit_data(|data| renamed_group(data, old, new))?;
            }
            return Ok(());
        }
        self.edit_data(|data| edits::renamed_in_set(data, section, old, new))?;
        if section == SONGS && song == old {
            self.select_song(new);
        }
        Ok(())
    }

    /// Add a copy of an item of a section and return the copy's name: at the end of its section, except a track's, which
    /// stands right after the track with a copy of each of its clips; a factory groove's copy is one of the set's own.
    pub fn copy_named(&mut self, section: &str, name: &str) -> Result<String, String> {
        let new = copy_name(name, &self.names_taken(section));
        let song = self.get_current_song_name().to_string();
        if section == TRACKS {
            self.edit_data(|data| edits::copied_track(data, &song, name, &new))?;
        } else if let (GROOVES, Some((_, cells, length))) = (section, FACTORY_GROOVES.iter().find(|(each, ..)| *each == name)) {
            let mut groove = vec![(
                Data::text(file_format::GrooveSetting::CELLS),
                Data::List(cells.iter().map(|cell| Data::Whole(*cell as i128)).collect()),
            )];
            if *length != SIXTEENTHS {
                groove.push((
                    Data::text(file_format::GrooveSetting::CELL_LENGTH),
                    Data::text(&format!("{}/{}", length.0, length.1)),
                ));
            }
            let groove = Data::Map(groove);
            self.edit_data(|data| with_item(data, GROOVES, &new, groove))?;
        } else {
            self.edit_data(|data| edits::copied_in_set(data, section, name, &new))?;
        }
        Ok(new)
    }

    /// Delete an item of a section; whoever asks has checked that nothing uses it. A deleted track takes its clips with it,
    /// the last song cannot be deleted, deleting the current song makes the one before it current, and deleting the last
    /// instrument turns real-time playback off.
    pub fn delete_named(&mut self, section: &str, name: &str) -> Result<(), String> {
        let song = self.get_current_song_name().to_string();
        if section == TRACKS {
            return self.edit_data(|data| edits::removed_track(data, &song, name));
        }
        let before = self.names_of(section);
        if section == SONGS && before.len() <= 1 {
            return Err(errors::ERR_LAST_SONG.to_string());
        }
        self.edit_data(|data| edits::removed_from_set(data, section, name))?;
        if section == SONGS && song == name {
            let place = before.iter().position(|each| each == name).unwrap_or(0).saturating_sub(1);
            let names = self.names_of(SONGS);
            if let Some(chosen) = names.get(place.min(names.len().saturating_sub(1))) {
                let chosen = chosen.clone();
                self.select_song(&chosen);
            }
        }
        Ok(())
    }

    /// Move an item up or down its section, and return whether it moved, which it cannot past either end.
    pub fn move_named(&mut self, section: &str, place: usize, offset: i64) -> bool {
        let song = self.get_current_song_name().to_string();
        let data = self.get_setlist().to_data();
        let items = section_of(&data, section, &song);
        let Some(moved) = edits::moved_in_section(&items, place, offset) else {
            return false;
        };
        self.edit_data(|data| with_section(data, section, &song, moved)).is_ok()
    }

    /// Put a section's items in order of name, for good.
    pub fn sort_named(&mut self, section: &str) -> Result<(), String> {
        let song = self.get_current_song_name().to_string();
        let data = self.get_setlist().to_data();
        let sorted = edits::sorted_section(&section_of(&data, section, &song));
        self.edit_data(|data| with_section(data, section, &song, sorted))
    }

    /// Add a song with its first track and scene at the end of the set, in the set's first scale, and make it current.
    /// Add a song of a main track, main1, and a drum track, drum1, each with an instrument of its own named after it or
    /// counted up where taken, and one scene, and make it current, as one step to undo.
    pub fn add_song(&mut self, name: &str, main_instrument: Data, drum_instrument: Data) -> Result<(), String> {
        use llamatron_model::schema::generated::file_format::TrackSetting;
        let scale = self.names_of(file_format::Section::SCALES).first().cloned();
        let mut song = vec![(Data::text(file_format::SongSetting::TEMPO), Data::Whole(DEFAULT_TEMPO as i128))];
        if let Some(scale) = scale {
            song.push((Data::text(file_format::SongSetting::SCALE), Data::text(&scale)));
        }
        let first_of = |word: &str| {
            named(
                names::MSG_JOINED_NUMBERED_NAME,
                &[(fill::BASE, word.into()), (fill::NUMBER, FIRST_NUMBER.into())],
            )
        };
        let (main, drum) = (first_of(names::MSG_NEW_MAIN_TRACK_WORD), first_of(names::MSG_NEW_DRUM_TRACK_WORD));
        let mut taken = self.names_of(INSTRUMENTS);
        let main_instrument_name = llamatron_model::objects::naming::unique_name(&main, &taken);
        taken.push(main_instrument_name.clone());
        let drum_instrument_name = llamatron_model::objects::naming::unique_name(&drum, &taken);
        let track = |instrument: &str, drum: bool| {
            let mut settings = vec![(Data::text(TrackSetting::INSTRUMENT), Data::text(instrument))];
            if drum {
                settings.insert(0, (Data::text(TrackSetting::DRUM), Data::Bool(true)));
            }
            Data::Map(settings)
        };
        let scene = named(names::MSG_NEW_SCENE_NAME, &[(fill::NUMBER, FIRST_NUMBER.into())]);
        song.push((Data::text(file_format::Section::DRAWS), Data::Map(Vec::new())));
        song.push((
            Data::text(TRACKS),
            Data::Map(vec![
                (Data::text(&main), track(&main_instrument_name, false)),
                (Data::text(&drum), track(&drum_instrument_name, true)),
            ]),
        ));
        song.push((
            Data::text(file_format::Section::SCENES),
            Data::List(vec![Data::Map(vec![(Data::text(file_format::FileLayout::NAME), Data::text(&scene))])]),
        ));
        let song = Data::Map(song);
        self.edit_data(|data| {
            let with_main = with_item(data, INSTRUMENTS, &main_instrument_name, main_instrument);
            let with_drum = with_item(&with_main, INSTRUMENTS, &drum_instrument_name, drum_instrument);
            with_item(&with_drum, SONGS, name, song)
        })?;
        self.select_song(name);
        Ok(())
    }

    /// Add a song the MIDI import made, with its instruments, scales and patterns, as one change, and make it current.
    pub fn import_song(&mut self, imported: &llamatron_importers::writing::ImportedSong) -> Result<(), String> {
        let setlist = llamatron_importers::writing::add_imported(self.get_setlist(), imported)?;
        self.change_set(|held| *held = setlist);
        self.select_song(&imported.name);
        Ok(())
    }

    /// Add a C major scale under a name.
    pub fn add_scale(&mut self, name: &str) -> Result<(), String> {
        let scale = Data::Map(vec![
            (Data::text(file_format::ScaleSetting::ROOT), Data::text(NEW_SCALE_ROOT)),
            (Data::text(file_format::ScaleSetting::TYPE), Data::text(NEW_SCALE_KIND)),
        ]);
        self.edit_data(|data| with_item(data, file_format::Section::SCALES, name, scale))
    }

    /// Add a straight groove of one bar of sixteenths under a name.
    pub fn add_groove(&mut self, name: &str) -> Result<(), String> {
        let groove = Data::Map(vec![(
            Data::text(file_format::GrooveSetting::CELLS),
            Data::List(vec![Data::Whole(0); NEW_GROOVE_CELLS]),
        )]);
        self.edit_data(|data| with_item(data, GROOVES, name, groove))
    }
}

/// Whether a section's items are generators or chains.
fn is_generator_section(section: &str) -> bool {
    section == CHAINS || PLUGINS.iter().any(|plugin| plugin.section == section)
}

/// A set's data with an item added at the end of a section, the section made where it has none.
fn with_item(data: &Data, section: &str, name: &str, item: Data) -> Data {
    let mut data = data.clone();
    if let Data::Map(pairs) = &mut data {
        match pairs.iter_mut().find(|(key, _)| key.as_str() == Some(section)) {
            Some((_, Data::Map(items))) => items.push((Data::text(name), item)),
            Some(pair) => pair.1 = Data::Map(vec![(Data::text(name), item)]),
            None => pairs.push((Data::text(section), Data::Map(vec![(Data::text(name), item)]))),
        }
    }
    data
}

/// A section's items: the set's, or the current song's tracks.
fn section_of(data: &Data, section: &str, song: &str) -> Data {
    let held = if section == TRACKS {
        data.get(SONGS).and_then(|songs| songs.get(song)).and_then(|song| song.get(TRACKS))
    } else {
        data.get(section)
    };
    held.cloned().unwrap_or(Data::Map(Vec::new()))
}

/// A set's data with a section's items replaced: the set's, or the current song's tracks.
fn with_section(data: &Data, section: &str, song: &str, items: Data) -> Data {
    let mut data = data.clone();
    let replace = |pairs: &mut Vec<(Data, Data)>, name: &str, items: Data| {
        if let Some(pair) = pairs.iter_mut().find(|(key, _)| key.as_str() == Some(name)) {
            pair.1 = items;
        }
    };
    let Data::Map(pairs) = &mut data else { return data };
    if section != TRACKS {
        replace(pairs, section, items);
        return data;
    }
    if let Some((_, Data::Map(songs))) = pairs.iter_mut().find(|(key, _)| key.as_str() == Some(SONGS)) {
        if let Some((_, Data::Map(settings))) = songs.iter_mut().find(|(key, _)| key.as_str() == Some(song)) {
            replace(settings, TRACKS, items);
        }
    }
    data
}

/// The groups the set's patterns are in.
fn pattern_groups(data: &Data) -> Vec<String> {
    data.get(PATTERNS).and_then(Data::as_map).map_or(Vec::new(), |patterns| {
        patterns
            .iter()
            .filter_map(|(_, pattern)| pattern.get(GROUP).and_then(Data::as_str).map(str::to_string))
            .collect()
    })
}

/// A set's data with every pattern of a group given the group's new name.
fn renamed_group(data: &Data, old: &str, new: &str) -> Data {
    let mut data = data.clone();
    if let Data::Map(pairs) = &mut data {
        if let Some((_, Data::Map(patterns))) = pairs.iter_mut().find(|(key, _)| key.as_str() == Some(PATTERNS)) {
            for (_, pattern) in patterns.iter_mut() {
                if let Data::Map(settings) = pattern {
                    for (key, value) in settings.iter_mut() {
                        if key.as_str() == Some(GROUP) && value.as_str() == Some(old) {
                            *value = Data::text(new);
                        }
                    }
                }
            }
        }
    }
    data
}

/// The arpeggiators' section, and the order a new one plays in.
const ARPS: &str = words::ARPS;
const ARP_ORDER: &str = words::ORDER;
const ARP_ORDER_UP: &str = file_format::ChipDirection::UP;
