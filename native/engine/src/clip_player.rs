// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Playing a track's clip in a scene (the Python engine/realizer/clip_slot_player.py): its patterns, laid end to end, passed
//! through repeat times, or for a looping clip as many times as fill its scene, cut where the scene ends.

use crate::clip::Clip;
use crate::error::Rendered;
use crate::generators::chords::ChordsSettings;
use crate::order::{ordered_patterns, DrawnWhenAsked, StepOrder};
use crate::pattern_player::{Pass, PatternPlayer};
use crate::realizer::{SongRealizer, WrittenScene};
use crate::sound::Sound;
use llamatron_math::Rational;
use llamatron_model::objects::song::ClipSlot;
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
        let mut times: HashMap<String, i64> = HashMap::new();
        let bar = self.realizer.song().get_time_signature().bar_length();
        for step in steps {
            if self.realizer.plays_drums(self.scene, self.track_name) {
                continue;
            }
            let count = times.entry(step.kind.to_string()).or_insert(0);
            let key = (step.kind.to_string(), llamatron_strings::names::MSG_BUILT_IN_NAME.to_string(), *count);
            *count += 1;
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
            let mut generator = settings.make_generator(bar, &continuation, followed)?;
            clip = generator.generate(&clip)?;
            self.realizer.keep_end_state(self.scene, self.track_name, key, generator.end_state());
        }
        Ok(clip)
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
