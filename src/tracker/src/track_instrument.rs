// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The instrument a new track gets of its own, by the config file's Track Inst. Default: FluidSynth's grand piano for a
//! melodic track and its drum channel for a drum track; the built-in synths' Basic, or MechaDrum on its Kick; or the
//! first MIDI device found, on channel 1. Where FluidSynth is not installed or no device is connected, the instrument is
//! made unconfigured, its engine Off, for the Instrument page to finish.

use crate::preferences::TrackInstrumentDefault;
use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::file_format::{InstrumentSetting, FLUIDSYNTH_DEVICE};
use llamatron_names::file_format;

/// The instrument's kinds and roles as the set file writes them.
const OFF: &str = file_format::InstrumentKind::OFF;
const BUILT_IN: &str = file_format::TrackSetting::BUILT_IN;
const NORMAL: &str = file_format::InstrumentRole::NORMAL;
const PERCUSSION: &str = file_format::InstrumentRole::PERCUSSION;
/// The sound's engine key, and the engines a new track's built-in instrument plays: Basic, and MechaDrum, whose
/// Machine starts on its Kick.
const ENGINE: &str = file_format::SoundSetting::ENGINE;
const BASIC_ENGINE: &str = file_format::OscillatorType::BASIC;
const DRUM_ENGINE: &str = file_format::TrackSetting::DRUM;
const MACHINE: &str = file_format::PartSetting::MACHINE;
const KICK: &str = file_format::DrumMachine::KICK;
/// General MIDI's first sound, the Acoustic Grand Piano, and the first MIDI channel.
const GRAND_PIANO: i128 = 1;
const FIRST_CHANNEL: i128 = 1;

/// The instrument a new track of a kind gets of its own, by the config file's Track Inst. Default: the first MIDI device
/// found is looked for only where it plays through one.
pub fn for_new_track(preferences: &crate::preferences::Preferences, fluidsynth_installed: bool, drum: bool) -> Data {
    let default = preferences.track_instrument_default(fluidsynth_installed);
    let first_device = if default == TrackInstrumentDefault::ExternalMidi {
        crate::realtime::backend::device_port_names().into_iter().next()
    } else {
        None
    };
    new_track_instrument(default, drum, fluidsynth_installed, first_device.as_deref())
}

/// The new instrument's data: its role by the track's kind, and what it plays through by Track Inst. Default, given
/// whether FluidSynth is installed and the first MIDI device found, if any.
pub fn new_track_instrument(default: TrackInstrumentDefault, drum: bool, fluidsynth_installed: bool, first_device: Option<&str>) -> Data {
    let role = if drum { PERCUSSION } else { NORMAL };
    let mut settings = vec![(Data::text(InstrumentSetting::ROLE), Data::text(role))];
    match default {
        TrackInstrumentDefault::FluidSynth if fluidsynth_installed => {
            settings.push((Data::text(InstrumentSetting::DEVICE), Data::text(FLUIDSYNTH_DEVICE)));
            // A percussion instrument on FluidSynth plays its drum channel, 10, of itself.
            if !drum {
                settings.push((Data::text(InstrumentSetting::GM_SOUND), Data::Whole(GRAND_PIANO)));
            }
        }
        TrackInstrumentDefault::BuiltIn => {
            let sound = if drum {
                vec![(Data::text(ENGINE), Data::text(DRUM_ENGINE)), (Data::text(MACHINE), Data::text(KICK))]
            } else {
                vec![(Data::text(ENGINE), Data::text(BASIC_ENGINE))]
            };
            settings.push((Data::text(InstrumentSetting::KIND), Data::text(BUILT_IN)));
            settings.push((Data::text(InstrumentSetting::SOUND), Data::Map(sound)));
        }
        TrackInstrumentDefault::ExternalMidi if first_device.is_some() => {
            settings.push((Data::text(InstrumentSetting::DEVICE), Data::text(first_device.unwrap_or_default())));
            settings.push((Data::text(InstrumentSetting::CHANNEL), Data::Whole(FIRST_CHANNEL)));
        }
        // FluidSynth not installed, or no device connected: unconfigured, for the Instrument page to finish.
        _ => settings.push((Data::text(InstrumentSetting::KIND), Data::text(OFF))),
    }
    Data::Map(settings)
}

#[cfg(test)]
mod tests {
    use super::*;
    use llamatron_model::objects::setlist::Instrument;

    fn setting<'a>(data: &'a Data, name: &str) -> Option<&'a Data> {
        data.get(name)
    }

    /// Each Track Inst. Default makes an instrument the set accepts: FluidSynth's piano or drums, Basic or MechaDrum's
    /// Kick, the first device on channel 1, and an unconfigured one where FluidSynth or a device is missing.
    #[test]
    fn each_default_makes_its_instrument() {
        let piano = new_track_instrument(TrackInstrumentDefault::FluidSynth, false, true, None);
        assert_eq!(setting(&piano, InstrumentSetting::DEVICE), Some(&Data::text(FLUIDSYNTH_DEVICE)));
        assert_eq!(setting(&piano, InstrumentSetting::GM_SOUND), Some(&Data::Whole(GRAND_PIANO)));
        let drums = new_track_instrument(TrackInstrumentDefault::FluidSynth, true, true, None);
        assert_eq!(setting(&drums, InstrumentSetting::ROLE), Some(&Data::text(PERCUSSION)));
        assert_eq!(setting(&drums, InstrumentSetting::GM_SOUND), None);
        let kick = new_track_instrument(TrackInstrumentDefault::BuiltIn, true, false, None);
        let sound = setting(&kick, InstrumentSetting::SOUND).expect("a sound");
        assert_eq!(sound.get(ENGINE), Some(&Data::text(DRUM_ENGINE)));
        assert_eq!(sound.get(MACHINE), Some(&Data::text(KICK)));
        let outside = new_track_instrument(TrackInstrumentDefault::ExternalMidi, false, false, Some("a synthesizer"));
        assert_eq!(setting(&outside, InstrumentSetting::CHANNEL), Some(&Data::Whole(FIRST_CHANNEL)));
        for unconfigured in [
            new_track_instrument(TrackInstrumentDefault::FluidSynth, false, false, None),
            new_track_instrument(TrackInstrumentDefault::ExternalMidi, false, true, None),
        ] {
            assert_eq!(setting(&unconfigured, InstrumentSetting::KIND), Some(&Data::text(OFF)));
        }
        for made in [piano, drums, kick, outside] {
            assert!(Instrument::from_data(&made).is_ok());
        }
    }
}
