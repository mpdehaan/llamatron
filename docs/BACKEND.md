# Backend

llamatron's backend, `llamatron-backend`, is a program of its own written in
Rust, in `native/backend/`. It plays the built-in synths and FluidSynth, and
sends every MIDI event on time, all in one process. This page explains how it works and how to
change it, for a reader who knows some programming but perhaps no Rust.
[Building the Backend](BUILDING_THE_BACKEND.md) says how to build it.

## Why a Program of Its Own

A synthesizer must hand the sound card a new chunk of sound every few
milliseconds, on time, every time; a late chunk is heard as a click. Python is
too slow to make the sound of many instruments in that time, and its pauses to
tidy memory come at moments nobody chooses. Rust compiles to native code with no
such pauses, so one voice of a synth costs a few microseconds a chunk rather
than about eighty. Keeping the engine in a separate program also means the
tracker, or any other program that speaks its messages, can drive it.

## The Processes

The backend runs in one of three ways, each started by llamatron as a child
process that it talks to through the backend's standard input and output, the
way a shell pipes one program into another:

- **`send`**, the usual way: the real-time sender. The render process hands it
  every event of what plays, and it sends each on time through the MIDI ports,
  the built-in synths and FluidSynth (`sender/`, `daemon/sending.rs`).
- **`play`**: the built-in synths alone, as the Python sender asks for them
  where that sender is chosen, with the messages below.
- **`render`**: no sound card; it plays the WAV export's built-in tracks into
  a file, as fast as it can.
- **`ports`**: lists the computer's MIDI destinations, a line each, and ends.

llamatron2, the tracker in Rust, starts no child process: it links the same
code as a library and runs `send` and `render` on threads of its own process,
handing them the same messages through channels in place of the pipes.

| Direction | Message | What it carries |
| --- | --- | --- |
| to the engine | `instrument` | An instrument's number and its sound, every setting of every part. |
| to the engine | `notes` | Notes, each a time, a kind (start, end, every note ending, a clip starting, or taking notes back), an instrument, a pitch and a velocity. |
| to the engine | `silence` | Stop every sound at once, as Ctrl+T does. |
| to the engine | `close` | End. |
| from the engine | `ready` | The sample rate and how long every note is held back. |
| from the engine | `failed` | Why the engine could not start. |
| from the engine | `load` | Twice a second: how busy the engine is, its voices, and any dropouts. |
| from the engine | `statistics` | As it closes: its timing over the whole run. |

Each message is a MessagePack array, a compact binary form of a list, with its
length written before it in four bytes, so that the reader always knows where
one message ends. `native/backend/src/protocol/` and
`src/llamatron/realtime/synth_process/daemon.py` are the two ends.

A note's time is a moment on the computer's own steady clock, the one Python's
`time.perf_counter` reads, which the engine reads too (`audio/clock.rs`), so that both
programs agree on when a note falls without converting anything.

## The Sender

The sender (`sender/`) does what llamatron's Python sender did, in the same
way, its tests run on both. Each event arrives as a small record: its seconds
on the timeline, its play's tag (a scene and a track), its port, and its MIDI
bytes. On macOS each event is handed to its port a tenth of a second ahead,
stamped with its moment: CoreMIDI delivers a MIDI port's event then, and the
built-in synths and FluidSynth place theirs on the exact sample. What is handed
can be taken back: stopping a clip, stopping everything, or an edit heard at
once flushes the ports holding what is dropped, hands back what they keep, and
undoes what handing the dropped events did to the notes counted as sounding,
so that a stop silences exactly what has sounded. Elsewhere each event is sent
as its moment comes, the sender's thread sleeping and then spinning up to it.

## Threads

Inside the engine, three threads share the work, so that the one that makes the
sound never waits.

- **The reader** reads the tracker's messages. It compiles each instrument,
  building its wavetables, and renders each drum hit the first time it is
  needed, then hands both to the audio thread.
- **The audio thread** is the sound card's own. Each time the card asks for a
  chunk, it takes what the reader handed over, places each note on its exact
  sample, plays every voice and mixes the result. It never allocates memory,
  never waits on a lock and never touches a file.
- **The housekeeper** frees what the audio thread has finished with, such as an
  instrument that has been replaced, so that the audio thread never frees
  memory either.

The reader and the audio thread pass things through lock-free queues
(`rtrb`), which one thread fills and the other empties without either ever
waiting for the other.

## Placing a Note on Its Sample

The sound card says, with each chunk, when the chunk's first sample will reach
the speakers. Every note is held back by the same delay, the card's own latency
and one chunk, so that a note sent on time is never late. The audio thread then
counts how many samples into the chunk the note's moment falls, and the note
starts on exactly that sample, whatever the chunk's size. MIDI sent to other
devices is held back by the same delay, so the two land together.

## The Code's Folders

| Folder | What it holds |
| --- | --- |
| `protocol/` | The messages, and reading the tracker's values with a default for anything left out. |
| `daemon/` | The two ways of running, playing and rendering, and the drum hits rendered as notes arrive. |
| `audio/` | The sound card's stream and its callback, the clock, and WAV files. |
| `engine/` | Notes and MIDI scheduled at exact samples, the mix, and the safety guard. |
| `voice/` | The parts of a built-in instrument's voice, and the patch that plays them together. |
| `drums/` | MechaDrum's recipes. |
| `fluid/` | FluidSynth, loaded at run time. |
| `dsp/` | Filters' building blocks and a seeded random source, which every part shares. |

## The Voice

Every built-in instrument but the drum machine is a voice of swappable parts,
the same parts the Instrument page shows.

| Part | File | What it does |
| --- | --- | --- |
| Oscillators | `voice/oscillators.rs`, `voice/tables.rs` | The raw sound: Basic's band-limited waveforms, the SID-style chip, the Pocket chip, the acid bass's saw or square. |
| Env1, Env2, Env3 | `voice/envelopes.rs` | Env1 shapes the loudness, Env2 the filter's sweep, Env3 the pitch: ADSR, AR, ASR, the SID chip's ADSR, the vactrol, the acid gate and the chip's sixteen steps. |
| LFO1 to LFO4 | `voice/modulation.rs` | Slow movement for the mod matrix. |
| Filter | `voice/filters.rs` | The ladder, diode, OTA, multimode and Sallen-Key filters, or the low-pass gate. |
| Matrix | `voice/modulation.rs` | Six routes from a source, such as an LFO or the velocity, to a destination, such as the cutoff. |
| FX1, FX2 | `voice/effects.rs` | Bitcrush and Drive. |

`voice/patch.rs` puts the parts together into an instrument and plays its notes one
sample at a time. The filters are zero-delay-feedback models: each sample, the
filter's loop is solved exactly, so that the cutoff can sweep as fast as an
envelope moves it without stepping or blowing up, and the ladder at full
resonance rings on by itself as the hardware does.

The drum machine, MechaDrum (`drums/`), renders each hit whole when its note
first arrives, from its five knobs, and replays it. The acoustic tom is a
physical model of a struck drum head's modes, and the Karplus drum a plucked
string turned drum.

## FluidSynth

Where FluidSynth is installed, the engine plays it too, in the same audio
callback (`fluid/`). The tracker gives it the path of FluidSynth's library,
found beside the installed `fluidsynth` program, and the SoundFont; the engine
loads the library at run time, so building the engine never needs FluidSynth.
The MIDI for FluidSynth's instruments arrives timed like every note, and the
engine renders FluidSynth up to each message's sample before playing the
message, so that each lands within FluidSynth's own block of 64 samples. The
mix is stereo: the built-in instruments in the middle, FluidSynth's sounds
where General MIDI pans them, each channel through its own safety guard.

## Safety

`engine/safety.rs` keeps every protection of the built-in synths, which no setting can
turn off. An instrument that produces a number that is not finite, or a level far
past anything a patch makes, is silenced and reset. The whole mix then passes a
filter that removes what is too low or too high to hear, a limiter that holds it
under full scale, a slow guard against sound staying very loud, a final soft
clip, and a latch that fades everything out after repeated faults until Ctrl+T.

## Never Left Behind

The engine exits when its input closes, which happens when the tracker closes it
or the tracker itself ends, however it ends. It also watches its parent process
and exits if that disappears, and on Linux the system tells it at once. The
tracker, for its part, asks it to close, waits two seconds and then ends it. A
problem inside the audio thread plays silence and is counted, never stopping the
sound card's stream, and a problem anywhere else is written to the log in
`~/.llamatron/` and told to the tracker.

## Rendering a WAV File

The WAV export plays the built-in tracks through the same engine, offline: the
tracker starts it with `llamatron-backend render`, sends the instruments and every
note timed from the song's start, and the engine plays them through the same
voices and the same safety guard into a file, as fast as it can.

## Changing the Backend

`.claude/rules/RUST.md` holds the rules the code follows. In short:

- `cargo fmt` lays out the code, and `cargo clippy` with every warning an
  error checks it; `internal_tools/check_before_commit.sh` runs both, and
  `cargo test`, whenever a file under `native/` changes.
- Nothing in the audio thread may allocate, lock or block.
- `unsafe` is used only where the engine calls the operating system, each with
  a comment saying why it is sound.
- Each module's tests sit at its end, in `mod tests`, and run with
  `cargo test --release --manifest-path native/Cargo.toml`.
