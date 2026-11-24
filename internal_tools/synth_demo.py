# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A tour of the built-in synths so far (internal_tools/synth_demo.sh): each sound announced by macOS's say, then played
through the Synthesis Process as a scale run, a phrase or a few hits, with the timing report at the end.

    sh internal_tools/synth_demo.sh [--only NAME]
"""

import argparse
import subprocess
import sys
import time

from llamatron.model.objects.built_in_sound import synth_spec
from llamatron.model.schema.file_format import SoundSetting
from llamatron.realtime.synth_process import engine
from llamatron.realtime.synth_process.process import SynthesisProcess

LEAD_IN = 0.15
# The exit code of a tour stopped with Ctrl+C, as the shell gives a program it interrupts.
STOPPED_BY_HAND = 130
MAJOR = (0, 2, 4, 5, 7, 9, 11, 12)
MINOR_PENTATONIC = (0, 3, 5, 7, 10, 12, 15, 17)


def basic(*, oscillators, envelope, voices=4, volume=0.35, effects=()):
    return {'kind': 'basic', 'oscillators': oscillators, 'envelope': envelope, 'voices': voices, 'volume': volume, 'effects': list(effects)}


def drum(*, machine, knobs, choke=None, volume=0.8, effects=()):
    return {'kind': 'drum', 'machine': machine, 'knobs': list(knobs), 'choke': choke, 'volume': volume, 'effects': list(effects)}


def effects_of(*blocks):
    """Return effect blocks, given as the set stores them, as llamatron gives them to the Synthesis Process."""
    return synth_spec({SoundSetting.EFFECTS: list(blocks)})['effects']


def chip(*, engine, **settings):
    """Return a SID or Pocket sound as the set would store it, given by its settings' names, compiled as llamatron gives it."""
    sound = {SoundSetting.ENGINE: engine}
    sound.update(settings)
    return synth_spec(sound)


def run(*, start, root=60, steps=MAJOR, length=0.18, velocity=100, gap=0.0):
    """Return notes of a scale run up and down from a root."""
    notes = []
    sequence = list(steps) + list(reversed(steps[:-1]))
    for place, step in enumerate(sequence):
        when = start + place * (length + gap)
        notes += [(when, engine.NOTE_ON, 0, root + step, velocity), (when + length * 0.85, engine.NOTE_OFF, 0, root + step, 0)]
    return notes, len(sequence) * (length + gap)


def chords(*, start, chords_list, length=1.6, velocity=85):
    notes = []
    for place, chord in enumerate(chords_list):
        when = start + place * length
        for pitch in chord:
            notes += [(when, engine.NOTE_ON, 0, pitch, velocity), (when + length * 0.92, engine.NOTE_OFF, 0, pitch, 0)]
    return notes, len(chords_list) * length + 1.2


def hits(*, start, pattern, step=0.125, pitches=None, velocities=None):
    """Return drum hits on the steps of a pattern string, x for a hit."""
    notes = []
    for place, mark in enumerate(pattern):
        if mark == 'x':
            pitch = pitches[place % len(pitches)] if pitches else 60
            velocity = velocities[place % len(velocities)] if velocities else 110
            notes.append((start + place * step, engine.NOTE_ON, 0, pitch, velocity))
    return notes, len(pattern) * step + 0.6


SAW = [['saw', 0, 1.0]]
TOUR = [
    ('Square wave, a scale', basic(oscillators=[['square', 0, 1.0]], envelope=[0.003, 0.2, 0.7, 0.08]), lambda t: run(start=t)),
    ('Saw wave', basic(oscillators=SAW, envelope=[0.003, 0.2, 0.7, 0.08]), lambda t: run(start=t)),
    ('Sine wave', basic(oscillators=[['sine', 0, 1.0]], envelope=[0.003, 0.2, 0.8, 0.08], volume=0.5), lambda t: run(start=t)),
    ('Triangle wave', basic(oscillators=[['triangle', 0, 1.0]], envelope=[0.003, 0.2, 0.8, 0.08], volume=0.5), lambda t: run(start=t)),
    ('Pulse wave', basic(oscillators=[['pulse', 0, 1.0]], envelope=[0.003, 0.2, 0.7, 0.08]), lambda t: run(start=t)),
    ('A fast chip arpeggio on a square, one voice', basic(oscillators=[['square', 0, 1.0]], envelope=[0.001, 0.05, 0.6, 0.02], voices=1),
     lambda t: run(start=t, root=72, steps=(0, 4, 7, 12, 16, 19, 24, 28), length=0.06)),
    ('Three detuned saws, a lo-fi pad', basic(oscillators=[['saw', 0, 0.45], ['saw', 9, 0.45], ['saw', -7, 0.45]], envelope=[0.6, 1.5, 0.75, 1.4], volume=0.22),
     lambda t: chords(start=t, chords_list=[(57, 60, 64), (53, 57, 60), (55, 59, 62), (52, 55, 59)])),
    ('The same pad, bitcrushed to six bits at eight kilohertz',
     basic(oscillators=[['saw', 0, 0.45], ['saw', 9, 0.45], ['saw', -7, 0.45]], envelope=[0.6, 1.5, 0.75, 1.4], volume=0.22, effects=effects_of({'effect': 'bitcrush', 'bits': 6, 'rate': 8000})),
     lambda t: chords(start=t, chords_list=[(57, 60, 64), (53, 57, 60)])),
    ('A driven square bass', basic(oscillators=[['square', 0, 0.7], ['saw', -5, 0.5]], envelope=[0.002, 0.15, 0.5, 0.05], voices=1, effects=effects_of({'effect': 'drive', 'curve': 'warm', 'amount': 50})),
     lambda t: run(start=t, root=36, steps=MINOR_PENTATONIC, length=0.16)),
    ('Kick', drum(machine='kick', knobs=(28, 70, 40, 30, 50)), lambda t: hits(start=t, pattern='x...x...x..xx...', step=0.12)),
    ('Hard kick', drum(machine='hard_kick', knobs=(30, 45, 64, 50, 40)), lambda t: hits(start=t, pattern='x...x...x...x...', step=0.12)),
    ('Synth kick, the groovebox kick', drum(machine='synth_kick', knobs=(30, 64, 64, 40, 60)), lambda t: hits(start=t, pattern='x...x...x..x.x..', step=0.12)),
    ('Snare', drum(machine='snare', knobs=(56, 50, 70, 72, 30)), lambda t: hits(start=t, pattern='....x.......x..x', step=0.12)),
    ('Clap', drum(machine='clap', knobs=(64, 40, 64, 60, 20)), lambda t: hits(start=t, pattern='....x.......x...', step=0.12)),
    ('Rim', drum(machine='rim', knobs=(50, 40, 64, 50, 0)), lambda t: hits(start=t, pattern='x..x..x.x..x..x.', step=0.12)),
    ('Closed hats, with accents', drum(machine='hats', knobs=(64, 20, 90, 70, 10)), lambda t: hits(start=t, pattern='xxxxxxxxxxxxxxxx', step=0.12, velocities=(120, 70, 90, 70))),
    ('Open hat', drum(machine='hats', knobs=(64, 85, 90, 40, 30)), lambda t: hits(start=t, pattern='..x...x...x...x.', step=0.12)),
    ('Cowbell', drum(machine='cowbell', knobs=(64, 50, 40, 50, 10)), lambda t: hits(start=t, pattern='x..x..x.x.x..x..', step=0.12)),
    ('Acoustic tom, played as a melody', drum(machine='acoustic_tom', knobs=(50, 64, 80, 40, 50)),
     lambda t: hits(start=t, pattern='x.x.x.x.x.x.x.x.', step=0.12, pitches=(60, 62, 64, 67, 69, 67, 64, 62))),
    ('Karplus drum', drum(machine='karplus_drum', knobs=(40, 60, 70, 90, 20)), lambda t: hits(start=t, pattern='x.x.xx.xx.x.x.xx', step=0.12, pitches=(48, 55, 52, 60))),
    ('Karplus drum, crushed to four bits', drum(machine='karplus_drum', knobs=(50, 50, 90, 110, 40), effects=effects_of({'effect': 'bitcrush', 'bits': 4, 'rate': 11000})),
     lambda t: hits(start=t, pattern='xx.xx.x.xx.x.xxx', step=0.1, pitches=(55, 50, 60, 48))),
    ('SID pulse, its width sweeping', chip(engine='sid', pulse_sweep=40, decay=400, sustain=40), lambda t: run(start=t, root=48, steps=MINOR_PENTATONIC, length=0.15)),
    ('SID chord arpeggio, one voice', chip(engine='sid', arpeggio=[0, 3, 7, 12], sustain=80), lambda t: chords(start=t, chords_list=[(57,), (53,), (55,), (52,)], length=0.8)),
    ('SID ring modulated triangle', chip(engine='sid', wave='triangle', modulation='ring', interval=7), lambda t: run(start=t, root=60, steps=MINOR_PENTATONIC, length=0.15)),
    ('SID hard sync saw lead, gliding', chip(engine='sid', wave='saw', modulation='sync', interval=19, glide=60, sustain=70), lambda t: run(start=t, root=60, steps=MAJOR, length=0.2)),
    ('SID noise snare', chip(engine='sid', wave='noise', attack=0, decay=120, sustain=0, release=60), lambda t: run(start=t, root=72, steps=(0, 0, 0, 0), length=0.25)),
    ('Pocket quarter pulse, fading in steps', chip(engine='pocket', level_pace=3), lambda t: run(start=t, root=60, steps=MAJOR, length=0.18)),
    ('Pocket eighth pulse laser, sweeping down', chip(engine='pocket', duty='eighth', sweep_pace=1, sweep_step=2, level_pace=2), lambda t: run(start=t, root=84, steps=(0, 5, 0, 7), length=0.3)),
    ('Pocket wave, the organ shape', chip(engine='pocket', chip_voice='wave', wave_shape='organ', volume=60), lambda t: run(start=t, root=48, steps=MAJOR, length=0.18)),
    ('Pocket short noise, metallic hats', chip(engine='pocket', chip_voice='noise', noise='short', level_pace=1), lambda t: run(start=t, root=90, steps=(0,) * 8, length=0.12)),
    ('Pocket long noise kick, sweeping', chip(engine='pocket', chip_voice='noise', level_pace=1, start_level=15), lambda t: run(start=t, root=40, steps=(0, 0, 0, 0), length=0.25)),
]


def main(*, arguments=None):
    made = argparse.ArgumentParser(prog='synth_demo.sh', description='A tour of the built-in synths.')
    made.add_argument('--only', help='play only the sounds whose names hold this text')
    options = made.parse_args(arguments)
    synthesis = SynthesisProcess(block=128)
    synthesis.start()
    stopped = False
    try:
        play_the_tour(synthesis=synthesis, only=options.only)
    except KeyboardInterrupt:
        # Ctrl+C ends the tour where it is, quietly: the synthesis is closed below all the same.
        stopped = True
    finally:
        statistics = synthesis.close()
    if statistics:
        print('dropouts {underflows}, late notes {late_notes}, slowest callback {longest_callback_ms:.2f} ms of {budget_ms:.2f}'.format(**statistics))
    return STOPPED_BY_HAND if stopped else 0


def play_the_tour(*, synthesis, only):
    """Announce and play each sound of the tour, or those whose names hold only."""
    for number, (name, spec, notes_of) in enumerate(TOUR, start=1):
        if only and only.lower() not in name.lower():
            continue
        synthesis.set_instrument(number=number, spec=spec)
        subprocess.run(['say', name], check=False)
        notes, seconds = notes_of(time.perf_counter() + LEAD_IN)
        synthesis.notes([(when, kind, number, pitch, velocity) for when, kind, _, pitch, velocity in notes])
        time.sleep(seconds + LEAD_IN + 0.3)


if __name__ == '__main__':
    sys.exit(main())
