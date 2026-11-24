# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The built-in synths' timing trial (internal_tools/builtin_timing.sh): plays a few seconds through the Synthesis Process,
a Synth Kick on every beat, closed hats between and two slow pad chords, and reports what timing needs watching: how long
the process took to start, the delay MIDI is held back by, the chunks played, the underflows (dropouts), the notes that
arrived late, and how long the slowest and the 99th-percentile audio callback took against the chunk's budget. Exits 1 if
anything dropped out or came late. Run it before and after each step of the built-in synths.

    sh internal_tools/builtin_timing.sh [--block 128] [--seconds 4]
"""

import argparse
import sys
import time

from llamatron.realtime.synth_process import engine
from llamatron.realtime.synth_process.process import SynthesisProcess

KICK = 1
HATS = 2
PAD = 3
LEAD_IN_SECONDS = 0.3
BEAT_SECONDS = 0.25
CHORD_SECONDS = 2.0
CHORD = (57, 60, 64)
MIDDLE_C = 60


def main(*, arguments=None):
    """Play the trial and print its report; return 1 if anything dropped out or came late."""
    made = argparse.ArgumentParser(prog='builtin_timing.sh', description='Time the built-in synths.')
    made.add_argument('--block', type=int, default=128)
    made.add_argument('--seconds', type=float, default=4.0)
    options = made.parse_args(arguments)
    synthesis = SynthesisProcess(block=options.block)
    began = time.perf_counter()
    rate, delay = synthesis.start()
    print('started in {:.0f} ms at {} Hz, MIDI held back {:.1f} ms'.format((time.perf_counter() - began) * 1000, rate, delay * 1000))
    synthesis.set_instrument(number=KICK, spec={'kind': 'drum', 'machine': 'synth_kick', 'knobs': [30, 64, 64, 40, 60]})
    synthesis.set_instrument(number=HATS, spec={'kind': 'drum', 'machine': 'hats', 'knobs': [64, 20, 90, 70, 10], 'choke': 1})
    synthesis.set_instrument(number=PAD, spec={'kind': 'basic', 'oscillators': [['saw', 0, 0.4], ['saw', 8, 0.4], ['saw', -6, 0.4]],
                                               'envelope': [0.4, 1.0, 0.7, 1.2], 'voices': 4, 'volume': 0.25})
    synthesis.notes(trial_notes(start=time.perf_counter() + LEAD_IN_SECONDS, seconds=options.seconds))
    time.sleep(options.seconds + LEAD_IN_SECONDS + 0.3)
    statistics = synthesis.close()
    for name, value in statistics.items():
        print('{:22} {}'.format(name, round(value, 3) if isinstance(value, float) else value))
    return 1 if statistics['underflows'] or statistics['late_notes'] else 0


def trial_notes(*, start, seconds):
    """Return the trial's notes: a kick on every beat, hats between, and pad chords."""
    notes = []
    for beat in range(int(seconds / BEAT_SECONDS)):
        when = start + beat * BEAT_SECONDS
        notes.append((when, engine.NOTE_ON, KICK, MIDDLE_C, 110))
        notes.append((when + BEAT_SECONDS / 2, engine.NOTE_ON, HATS, MIDDLE_C, 90))
    for chord in range(int(seconds / CHORD_SECONDS)):
        when = start + chord * CHORD_SECONDS
        for pitch in CHORD:
            notes.append((when, engine.NOTE_ON, PAD, pitch, 80))
            notes.append((when + CHORD_SECONDS * 0.9, engine.NOTE_OFF, PAD, pitch, 0))
    return notes


if __name__ == '__main__':
    sys.exit(main())
