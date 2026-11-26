# Installing

llamatron runs in a terminal on a Mac, and on Linux for everything but
FluidSynth's installer. This page covers installing llamatron, and one
optional component: FluidSynth, which plays every demo with no synthesizer of your own.
When it's installed, [Getting Started](GETTING_STARTED.md) is the next page.

## Requirements

- git
- Python 3, which macOS and most Linux systems include, for the small tools
  beside llamatron
- Rust, which the setup offers to install
- A terminal at least 80 columns wide and 24 rows tall. llamatron draws with
  bold, dim, reverse video and box characters, so it suits any colour scheme.

## Installation

Clone the repository and run the setup script from the project folder:

```
git clone https://github.com/mpdehaan/llamatron.git
cd llamatron
sh setup.sh
```

The script makes a small Python environment in the folder `.venv` for the
development tools, then builds llamatron with `sh build.sh`, which checks for
Rust and offers to install it first, installing nothing without your yes
([Building llamatron](BUILDING_THE_BACKEND.md)). After a `git pull`, run `sh
build.sh` again to build the new code.

From the project folder, `./llamatron.sh` runs llamatron, and every other
script in `user_scripts/` and `internal_tools/` runs from there too.

## FluidSynth (Optional)

FluidSynth is a free software synthesizer, and it is the quickest way to hear
llamatron: with it, every demo plays as it comes, with no synthesizer of your own, no DAW
and no MIDI setup, and a song can be exported as a WAV file. Install it now if
you want to hear the demos right away, or if you have no synthesizer or DAW of your own
set up; skip it if you will play everything through your own instruments. On a
Mac, from the project folder:

```
sh user_scripts/install_fluidsynth.sh
```

[FluidSynth](FLUIDSYNTH.md) describes what the script installs, how the
tracker uses FluidSynth, and when to use your own instruments instead. To
check that it works, open a demo and play it:

```
./llamatron.sh examples/learning/02_pachelbel.yml
```

Press `A` for Arrange, move to the top left corner with the arrows, where `▶
song` shows, and press `Space`.
