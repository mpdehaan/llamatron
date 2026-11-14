# Installing

llamatron runs in a terminal on a Mac, and on Linux for everything but FluidSynth's installer. This page covers installing llamatron, and two optional components: FluidSynth, which plays every demo with no synthesizer, and a faster YAML parser. When it's installed, [Getting Started](GETTING_STARTED.md) is the next page.

## Requirements

- Python 3.15
- git
- A terminal at least 80 columns wide and 24 rows tall. llamatron draws with bold, dim, reverse video and box characters, so it suits any colour scheme.

## Installation

Clone the repository and run the setup script from the project folder:

```
git clone https://github.com/mpdehaan/llamatron.git
cd llamatron
sh user_scripts/setup.sh
```

The script makes a Python virtual environment in the folder `.venv` and installs llamatron into it, together with its dependencies, [mido](https://github.com/mido/mido), python-rtmidi, PyYAML and [Textual](https://textual.textualize.io/), and the Live set that exports are built from. llamatron is installed in editable form, so the command always runs the code in the folder you cloned, and a `git pull` updates it without installing again.

The `llamatron` command lives in the virtual environment, so typing `llamatron` works once the environment is activated with `source .venv/bin/activate`, which each new terminal needs once. From the project folder, `./llamatron.sh` runs llamatron without activating anything, and every other script in `user_scripts/` and `internal_tools/` finds the environment by itself.

## FluidSynth (Optional)

FluidSynth is a free software synthesizer, and it is the quickest way to hear llamatron: with it, every demo plays as it comes, with no synthesizer, no DAW and no MIDI setup, and a song can be exported as a WAV file. Install it now if you want to hear the demos right away, or if you have no synthesizer or DAW set up; skip it if you will play everything through your own instruments. On a Mac, from the project folder:

```
sh user_scripts/install_fluidsynth.sh
```

[FluidSynth](FLUIDSYNTH.md) describes what the script installs, how the tracker uses FluidSynth, and when to use your own instruments instead. To check that it works, open a demo and play it:

```
./llamatron.sh examples/learning/13_classic_strum.yml
```

Press `A` for Arrange, move to the top left corner with the arrows, where `▶ song` shows, and press `Space`.

## Faster YAML Parser (Optional)

Set files are YAML, and PyYAML reads them about ten times faster when it's built with [libyaml](https://github.com/yaml/libyaml), which makes a large set open almost at once. Everything works without it. To see which parser you have:

```
.venv/bin/python -c "import yaml; print(yaml.__with_libyaml__)"
```

`True` means libyaml is in use. The PyYAML wheels on PyPI include it, so a Python version that has a wheel gets it with the install above. For a Python version with no wheel yet, pip builds PyYAML from source, and includes libyaml only if it finds the library and a working C compiler at that moment, so install those first and then rebuild:

```
brew install libyaml                                   # macOS; on Debian or Ubuntu: sudo apt install libyaml-dev
.venv/bin/python -m pip install --force-reinstall --no-binary pyyaml --no-cache-dir "pyyaml==6.0.3"
```

On a Mac the compiler is Xcode's, whose license has to have been accepted once (`sudo xcodebuild -license accept`), and the library has to match the Python: an Apple Silicon Python needs the Apple Silicon Homebrew in `/opt/homebrew`, not the Intel one in `/usr/local`. If the C parser can't be built, pip quietly builds PyYAML without it, and llamatron falls back to the pure-Python parser.
