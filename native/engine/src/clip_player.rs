// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Playing a track's clip in a scene (the Python engine/realizer/clip_slot_player.py): its patterns, laid end to end, passed
//! through repeat times, or for a looping clip as many times as fill its scene, cut where the scene ends.

use crate::clip::Clip;
use crate::error::Rendered;
use crate::generators::arp::Arp;
use crate::generators::chords::ChordsSettings;
use crate::generators::guitarify::Guitarify;
use crate::generators::Generator;
use crate::order::{ordered_patterns, DrawnWhenAsked, StepOrder};
use crate::pattern_player::{Pass, PatternPlayer};
use crate::realizer::{SongRealizer, WrittenScene};
use crate::shapes::{shape_values, PlacedRamp, PlacedShape, PlacedVelocity, Reshaping, Velocity, ARTICULATE, DENSITY, PLACED_SHAPES, SHAPES, SWELL};
use crate::sound::Sound;
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::song::ClipSlot;
use llamatron_model::schema::generated::file_format::Restart;
use llamatron_model::schema::generated::file_format::GENERATOR_RESTART;
use llamatron_model::values::scale::Scale;
use std::collections::HashMap;

const PROBABILITY_SEED: &str = "{seed}/{scene}/{track}";
const DIRECTION_SEED: &str = "{seed}/{scene}/{track}/direction";
const PATTERN_ORDER_SEED: &str = "{seed}/{scene}/{track}/pattern order";

pub struct ClipSlotPlayer<'r, 'a> {
    realizer: &'r SongRealizer<'a>,
    scene: &'r WrittenScene<'a>,
    track_name: &'r str,
    clip_slot: &'a ClipSlot,
}

impl<'r, 'a> ClipSlotPlayer<'r, 'a> {
    pub fn new(realizer: &'r SongRealizer<'a>, scene: &'r WrittenScene<'a>, track_name: &'r str, clip_slot: &'a ClipSlot) -> ClipSlotPlayer<'r, 'a> {
        ClipSlotPlayer {
            realizer,
            scene,
            track_name,
            clip_slot,
        }
    }

    /// The finished clip.
    pub fn play(&self) -> Rendered<Clip> {
        let setlist = self.realizer.setlist();
        let track = self.realizer.track(self.track_name)?;
        let scale = self.clip_scale()?;
        let player = PatternPlayer::new(setlist, self.realizer.song(), track, self.scene.number, self.scale_name());
        let looping = self.clip_slot.loops();
        let fill = if looping { Some(self.realizer.get_scene_length(self.scene)?) } else { None };
        let clip = self.play_passes(&player, scale, fill)?;
        let clip = self.through_chain(clip)?;
        let clip = self.shaped(clip)?;
        let sounds = finished_sounds(&clip, looping, fill)?;
        // A clip carries its pattern's own time signature, if it has one, for the bars a DAW draws.
        let signature = player.pattern(&self.clip_slot.get_pattern_name())?.get_time_signature();
        Ok(Clip {
            name: Some(self.clip_slot.get_display_name()),
            sounds,
            scale,
            length: None,
            note_length: None,
            looping,
            time_signature: signature,
            groove: None,
        })
    }

    /// The clip after each generator of its chains, in order; a generator that moves pitches leaves a drum pattern alone,
    /// since moving a drum note changes the drum.
    fn through_chain(&self, clip: Clip) -> Rendered<Clip> {
        let steps = self.realizer.chains_of(self.scene, self.track_name)?;
        if steps.is_empty() || clip.total_length()? == Rational::ZERO {
            return Ok(clip);
        }
        let mut clip = clip;
        let mut times: HashMap<(String, String), i64> = HashMap::new();
        let bar = self.realizer.song().get_time_signature().bar_length();
        // Each step is counted along all of the clip's chains for its seed, whether or not it runs.
        for (index, step) in steps.into_iter().enumerate() {
            // A shape works on the finished clip after the chains, and a progression and a Follow Chords leave a drum pattern
            // alone, since moving a drum note changes the drum.
            let runs = match step.kind.as_str() {
                "shapes" => false,
                "chords" => !self.realizer.plays_drums(self.scene, self.track_name),
                _ => true,
            };
            if !runs {
                continue;
            }
            let count = times.entry((step.kind.clone(), step.name.clone())).or_insert(0);
            let key = (step.kind.clone(), step.name.clone(), *count);
            *count += 1;
            let mut generator = match step.kind.as_str() {
                "chords" => {
                    let settings = ChordsSettings::of(&step.settings)?;
                    let continuation = self
                        .realizer
                        .continuation(self.scene, self.track_name, &key, settings.get_restart().as_deref())?;
                    let followed = match settings.get_mode().as_str() {
                        "follow_progression" => self
                            .realizer
                            .chords_followed(self.scene, self.track_name, settings.get_chords_from().as_deref())?,
                        _ => None,
                    };
                    Generator::Chords(settings.make_generator(bar, &continuation, followed)?)
                }
                "guitarify" => {
                    let seed = self.realizer.chain_step_seed(self.scene, self.track_name, index as i128)?;
                    let restart = step.settings.get(GENERATOR_RESTART).map(|restart| restart.python_str());
                    let continuation = self.realizer.continuation(self.scene, self.track_name, &key, restart.as_deref())?;
                    Generator::Guitarify(Guitarify::of(&step.settings, bar, self.tempo(), seed, continuation.offset)?)
                }
                _ => {
                    let seed = self.realizer.chain_step_seed(self.scene, self.track_name, index as i128)?;
                    Generator::Arp(Arp::of(&step.settings, self.pattern_step()?, bar, seed)?)
                }
            };
            clip = generator.generate(&clip)?;
            self.realizer.keep_end_state(self.scene, self.track_name, key, generator.end_state());
        }
        Ok(clip)
    }

    /// The clip with its Density, Swell and Articulate laid over it, the last Shapes generator of each its chains name, else
    /// the clip's own Density or Articulate, else its scene's; and with how loud the clip and its scene play.
    fn shaped(&self, clip: Clip) -> Rendered<Clip> {
        let signature = self.realizer.song().get_time_signature();
        let bar = signature.bar_length();
        let mut named: HashMap<&str, Data> = HashMap::new();
        for step in self.realizer.chains_of(self.scene, self.track_name)? {
            if step.kind != "shapes" {
                continue;
            }
            for shape in SHAPES {
                if shape_values(&|name| step.settings.get(name).cloned(), shape, 0, bar).is_some() {
                    named.insert(shape, step.settings.clone());
                }
            }
        }
        let clip_length = clip.total_length()?;
        let scene_length = self.realizer.get_scene_length(self.scene)?;
        let mut placed: HashMap<&str, PlacedShape> = HashMap::new();
        for shape in SHAPES {
            if let Some(settings) = named.get(shape) {
                let accent = match *shape {
                    SWELL => settings.get("swell_accent").and_then(Data::as_whole).unwrap_or(0) as i64,
                    _ => 0,
                };
                let restart = settings.get(GENERATOR_RESTART).map(Data::python_str);
                let span = self.realizer.run_span(self.scene, restart.as_deref(), clip_length)?;
                let offset = self.realizer.run_offset(self.scene, restart.as_deref())?;
                if let Some(values) = shape_values(&|name| settings.get(name).cloned(), shape, accent, bar) {
                    placed.insert(shape, (values, span, offset));
                }
            } else if PLACED_SHAPES.contains(shape) {
                if let Some(values) = shape_values(&|name| self.clip_slot.get_written(name).cloned(), shape, 0, bar) {
                    placed.insert(shape, (values, clip_length, Rational::ZERO));
                } else if let Some(values) = shape_values(&|name| self.scene.scene.get_written(name).cloned(), shape, 0, bar) {
                    placed.insert(shape, (values, scene_length, Rational::ZERO));
                }
            }
        }
        let velocity = self.placed_velocity(clip_length, scene_length, bar)?;
        if placed.is_empty() && velocity.is_none() {
            return Ok(clip);
        }
        let reshaping = Reshaping {
            density: placed.remove(DENSITY),
            swell: placed.remove(SWELL),
            articulate: placed.remove(ARTICULATE),
            velocity,
            span: clip_length,
            bar,
            beat: signature.beat_length(),
        };
        let sounds = reshaping.reshaped(&clip.resolved_sounds()?);
        Ok(Clip { sounds, ..clip })
    }

    /// How loud the clip plays over its time, or None where every note plays as written: a ramp whose bars the scene gives
    /// counted across the scene's whole play, every repeat together, and one whose bars the clip gives over the clip's own.
    fn placed_velocity(&self, clip_length: Rational, scene_length: Rational, bar: Rational) -> Rendered<Option<PlacedVelocity>> {
        let setlist = self.realizer.setlist();
        let track = self.realizer.track(self.track_name)?;
        let percent = |value: Option<&Data>| value.and_then(Data::as_whole).map(Rational::whole);
        let instrument = self
            .realizer
            .song()
            .instrument_of(track, setlist)
            .and_then(|instrument| instrument.get_written("velocity"));
        let outer = [percent(instrument), percent(track.get_written("velocity"))];
        let velocity = Velocity::of(
            &|name| self.scene.scene.get_written(name).cloned(),
            &|name| self.clip_slot.get_written(name).cloned(),
            &outer,
        );
        if velocity.changes_nothing() {
            return Ok(None);
        }
        let before = self.realizer.run_offset(self.scene, Some(Restart::ON_NEW_SCENE))?;
        let ramp_in = velocity.ramp_in.map(|ramp| PlacedRamp {
            start: ramp.start,
            end: ramp.end,
            span: ramp.over * bar,
            begins: if ramp.of_clip { Rational::ZERO } else { Rational::ZERO - before },
        });
        let ramp_out = match velocity.ramp_out {
            None => None,
            Some(ramp) => {
                let end = if !ramp.of_clip {
                    self.realizer.run_span(self.scene, Some(Restart::ON_NEW_SCENE), clip_length)? - before
                } else if self.clip_slot.loops() {
                    scene_length
                } else {
                    clip_length
                };
                Some(PlacedRamp {
                    start: ramp.start,
                    end: ramp.end,
                    span: ramp.over * bar,
                    begins: end - ramp.over * bar,
                })
            }
        };
        Ok(Some(PlacedVelocity {
            level: velocity.level,
            ramp_in,
            ramp_out,
        }))
    }

    /// The scene's tempo, or the song's where the scene sets none.
    fn tempo(&self) -> llamatron_math::Number {
        if let Some(tempo) = self.scene.tempo {
            return llamatron_math::Number::Float(tempo);
        }
        match self.realizer.song().get_tempo() {
            llamatron_model::file::data::Data::Float(tempo) => llamatron_math::Number::Float(tempo),
            other => llamatron_math::Number::Whole(other.as_whole().unwrap_or(120)),
        }
    }

    /// The step size of the pattern the clip plays.
    fn pattern_step(&self) -> Rendered<Rational> {
        let setlist = self.realizer.setlist();
        let pattern = setlist
            .get_pattern(&self.clip_slot.get_pattern_name())
            .ok_or_else(|| crate::error::RenderError::Refused("a clip's pattern is missing".to_string()))?;
        Ok(setlist.get_pattern_step_size(pattern))
    }

    /// The scale the clip plays in: its own, or else its scene's, which is the song's when the scene has none.
    fn scale_name(&self) -> Option<String> {
        self.clip_slot.get_scale_name().or_else(|| self.scene.scale_name.clone())
    }

    /// The clip's scale rooted at the octave of the first note its pattern plays, or None where nothing gives it one.
    fn clip_scale(&self) -> Rendered<Option<Scale>> {
        let Some(name) = self.scale_name() else { return Ok(None) };
        let setlist = self.realizer.setlist();
        let named = setlist
            .get_named_scale(&name)
            .ok_or_else(|| crate::error::RenderError::NotPorted(format!("a scale the set does not name ({name})")))?;
        let pattern = setlist
            .get_pattern(&self.clip_slot.get_pattern_name())
            .ok_or_else(|| crate::error::RenderError::Refused("a clip's pattern is missing".to_string()))?;
        let octave = pattern.get_first_octave().unwrap_or(setlist.get_default_octave());
        named
            .scale_at(octave)
            .map(Some)
            .map_err(|problem| crate::error::RenderError::Refused(problem.0))
    }

    fn seed_for(&self, template: &str) -> Option<String> {
        let seed = self.realizer.seed()?;
        Some(
            template
                .replace("{seed}", &seed.to_string())
                .replace("{scene}", &self.scene.number.to_string())
                .replace("{track}", self.track_name),
        )
    }

    /// What the clip plays before any chains: its repeats, or enough passes to fill a length, cut there.
    fn play_passes(&self, player: &PatternPlayer, scale: Option<Scale>, fill: Option<Rational>) -> Rendered<Clip> {
        let mut rolls = DrawnWhenAsked::new(self.seed_for(PROBABILITY_SEED));
        let mut order = StepOrder::new(DrawnWhenAsked::new(self.seed_for(DIRECTION_SEED)));
        let mut pattern_rolls = DrawnWhenAsked::new(self.seed_for(PATTERN_ORDER_SEED));
        let repeat = self.clip_slot.get_repeat();
        let mut sounds: Vec<Sound> = Vec::new();
        let mut total = Rational::ZERO;
        let mut place = 0;
        loop {
            let going = match fill {
                None => place < repeat,
                Some(fill) => total < fill,
            };
            if !going {
                break;
            }
            let names = ordered_patterns(
                &self.clip_slot.get_pattern_names(),
                self.clip_slot.get_pattern_order().as_deref(),
                place,
                &mut pattern_rolls,
            );
            let played = self.play_patterns(player, &names, &mut rolls, &mut order)?;
            if played.length == Rational::ZERO {
                break;
            }
            // Ties at the start of this pass hold the note the passes so far ended with.
            if played.tied_from_before > Rational::ZERO {
                sounds = tied_on(sounds, played.tied_from_before);
            }
            sounds.extend(played.sounds);
            total = total + played.length;
            place += 1;
            if played.done {
                break;
            }
        }
        let clip = Clip::of(sounds, scale);
        match fill {
            Some(fill) if fill != Rational::ZERO => clip.section(Rational::ZERO, fill),
            _ => Ok(clip),
        }
    }

    /// One pass through the clip's patterns in the order given, each played whole after the one before.
    fn play_patterns(&self, player: &PatternPlayer, names: &[String], rolls: &mut DrawnWhenAsked, order: &mut StepOrder) -> Rendered<Pass> {
        let direction = self.clip_slot.get_direction();
        if names.len() == 1 {
            return player.play_pass(&names[0], direction.as_deref(), rolls, order);
        }
        let mut sounds = Vec::new();
        let mut total = Rational::ZERO;
        let mut tied_from_before = Rational::ZERO;
        let mut done = false;
        for (place, name) in names.iter().enumerate() {
            let played = player.play_pass(name, direction.as_deref(), rolls, order)?;
            if place == 0 {
                tied_from_before = played.tied_from_before;
            } else if played.tied_from_before > Rational::ZERO {
                sounds = tied_on(sounds, played.tied_from_before);
            }
            sounds.extend(played.sounds);
            total = total + played.length;
            if played.done || played.length != player.pattern_length(player.pattern(name)?) {
                done = played.done;
                break;
            }
        }
        Ok(Pass {
            sounds,
            tied_from_before,
            length: total,
            done,
        })
    }
}

/// The sounds a clip finishes with: a looping clip's cut where its scene ends, and the whole of what any other clip played.
fn finished_sounds(clip: &Clip, looping: bool, fill: Option<Rational>) -> Rendered<Vec<Sound>> {
    let Some(fill) = fill.filter(|_| looping) else { return clip.played_sounds() };
    if fill <= Rational::ZERO {
        return Ok(Vec::new());
    }
    if clip.total_length()? == fill {
        return clip.played_sounds();
    }
    Ok(clip.section(Rational::ZERO, fill)?.sounds)
}

/// A clip's sounds with the note still sounding at their end held for extra longer, for ties that follow; a rest at the end
/// means nothing sounds, unless it is the rest of a pass of ties after a held note that sounds through it.
fn tied_on(mut sounds: Vec<Sound>, extra: Rational) -> Vec<Sound> {
    let Some(last) = sounds.last().cloned() else { return sounds };
    let place = last.place();
    let held = match &last {
        Sound::Note(_) | Sound::Chord { .. } => Sound::held(last.lasting(Some(place + extra)), place),
        Sound::Held { sound, .. } if place <= sound.place() => Sound::held(sound.lasting(Some(sound.place() + extra)), place),
        Sound::Rest(_) => return held_through_rests(sounds, extra),
        _ => return sounds,
    };
    let end = sounds.len() - 1;
    sounds[end] = held;
    sounds
}

fn held_through_rests(mut sounds: Vec<Sound>, extra: Rational) -> Vec<Sound> {
    let mut first_rest = sounds.len();
    let mut resting = Rational::ZERO;
    while first_rest > 0 && sounds[first_rest - 1].is_rest() {
        first_rest -= 1;
        resting = resting + sounds[first_rest].place();
    }
    if first_rest == 0 {
        return sounds;
    }
    let Sound::Held { length, sound } = &sounds[first_rest - 1] else {
        return sounds;
    };
    if sound.place() != *length + resting {
        return sounds;
    }
    sounds[first_rest - 1] = Sound::held(sound.lasting(Some(sound.place() + extra)), *length);
    sounds
}
