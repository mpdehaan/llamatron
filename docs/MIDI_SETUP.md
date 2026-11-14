# MIDI Setup

This page covers getting llamatron's real-time playback into a synthesizer or a DAW on a Mac, and finding out what is wrong when nothing sounds. [Playing Live](PLAYING_LIVE.md) covers the tracker's side; this page covers everything outside the tracker: the MIDI ports, Ableton Live's settings, and the test tool. With no synthesizer or DAW, an instrument whose Device is `*FluidSynth` plays through FluidSynth instead, with none of this setup, as [FluidSynth](FLUIDSYNTH.md) describes.

## IAC Driver

A MIDI port is where messages leave one program and enter another. A Mac has none until one is turned on, and the built-in one is the IAC driver, Apple's "Inter-Application Communication" bus: a cable with both ends inside the computer, so that one program can play another.

1. Open **Audio MIDI Setup**, in Applications, Utilities.
2. In the **Window** menu choose **Show MIDI Studio**.
3. Double-click the **IAC Driver** icon.
4. Tick **Device is online**. The list of ports holds **Bus 1**; add more with `+` if you want one
   cable per instrument. Each bus is one port, named `IAC Driver Bus 1` and so on.

Every program that opens the bus sees the bus by that name. A hardware MIDI interface or a USB synthesizer shows up the same way under its own name, and everything below works the same for it.

## llamatron Setup

On the main screen, `I` opens **Instruments**. Add an instrument, and on its page set **Device** to the port, `IAC Driver Bus 1`, and **Channel** to the channel the synthesizer listens on, 1 unless you have set another. Adding the first instrument turns the main screen's **Real Time** switch on.

On Arrange, `Enter` on a track's name opens the track editor, whose **Instrument** field picks the instrument for that track; a track with no instrument is silent in real time. Then, with the cursor on the `▶ song` corner over the scene names, `Space` plays the song from the top. While the song plays, the corner reads `■ song`, a playing clip shows a red `■`, and a green `●` follows a track's name while a note sounds on the track. `Space` on the corner again stops everything.

## Ableton Live Setup

Three settings decide whether MIDI that reaches Live also reaches an instrument. The lights that show MIDI arriving come before all three, so a track's meter can blink while the track stays silent. The first setting is the one that catches almost everybody.

1. **The track's Monitor switch**, under MIDI From, with **In**, **Auto** and **Off**. A new MIDI track
   is on **Auto**, which passes live input to the instrument only while the track is record-armed.
   Clips in the track still play, since clips don't go through monitoring, and the input meter still
   blinks, since the meter sits before the switch, which is what makes this setting hard to spot. Set
   Monitor to **In**, or arm the track with the record button at the bottom of its strip; either is enough.
2. **The track's input.** Set **MIDI From** to `IAC Driver Bus 1` rather than `All Ins`, so that
   nothing else joins in, and the channel chooser under it to `All Channels` or the instrument's
   channel.
3. **The port's Track switch.** In Live's Preferences, under **Link, Tempo & MIDI**, the **MIDI Ports**
   list has an input row for `IAC Driver Bus 1` with **Track** and **Remote** switches. A track only
   receives from a port whose Track switch is on. When MIDI From offers the bus by name, the switch
   is on already.

## Test Tool

`internal_tools/iac_check.sh` is the one tool in the repository that touches a real MIDI port, and the tool only ever opens a port with `IAC` in its name. It plays a C major scale up and down, one note a beat, out of the
bus on channel 1, through the same Realtime Sender Process the tracker uses, and prints each message
as its moment comes:

```
sending 30 events of a C major scale up and down, a note a beat, 7.5 s, out of (IAC Driver Bus 1) on channel 1 through the Realtime Sender Process
    0.15 s  IAC Driver Bus 1  channel  1  note on  C5 (60) velocity 127
    0.65 s  IAC Driver Bus 1  channel  1  note off C5 (60)
    0.65 s  IAC Driver Bus 1  channel  1  note on  D5 (62) velocity 127
```

Each note is named in llamatron's own octaves, where `C5` is MIDI note 60, middle C, which Live calls `C3`. If a Live track is listening on the bus with Monitor set to In, you hear the scale as the lines go by. If the lines go by and nothing sounds, the problem is on the receiving side, in the settings above, because the tool also opens the bus as an input and reads back what it sent:

```
  30 of 30 events came back on the bus
  lateness against the schedule: least 0.122 ms, mean 0.157 ms, most 0.381 ms, standard deviation 0.044 ms, 99th percentile 0.525 ms
  timing: good, nothing more than 10 ms off
  the channel was silenced on close: all notes off and all sound off arrived
verdict: the real port plays what the export holds
```

The lateness is each message's arrival against its scheduled time, measured on the receiving thread, so the sending itself is tighter than the numbers. Anything under a few milliseconds is inaudible, and the tool calls more than ten milliseconds poor, since a listener can hear that much. To play a set's first seconds instead of the scale, name the set:

```
internal_tools/iac_check.sh examples/by_genre/electronic/minimal_techno.yml --seconds 20
```

### Other Messages on the Bus

```
  2 other messages were on the bus too, from something else sending to it, such as the tracker playing (the first 2):
    [144, 76, 127]  channel 1: note on E6 (76) velocity 127
    [248]  MIDI clock tick, which a DAW sends 24 times a beat while it plays
  so the order and the lateness cannot be judged this run: stop whatever else sends to the bus and run again
```

An IAC bus is shared: everything any program sends to the bus comes back to every program listening. When the tracker is playing, or Live is sending its clock to the bus, those messages arrive among the tool's, and the tool decodes the first ten so that you can tell where they came from. The order and the times mean nothing in such a run, so stop the other sender and run the tool again.

### Asking Claude for Help

Save the report to a file and name the file in your question, so that Claude reads the whole run rather than a paste cut short by the terminal:

```
internal_tools/iac_check.sh > /tmp/iac_check.txt 2>&1
```

Then ask, for example, "look at /tmp/iac_check.txt: the scale shows in Live's input lights but the piano doesn't sound". The report says what left the bus and what came back, but Claude can't see Live's settings, so say what MIDI From and Monitor are set to.

## Symptoms and Causes

- **Nothing came back on the bus**: the bus is off in Audio MIDI Setup, or another program holds its
  input exclusively.
- **The tracker says a device isn't connected**: the instrument's Device names a port the Mac doesn't
  list now. Open the Instruments page and pick the port again, under the name it has today.
- **Live's lights blink but nothing sounds**: the track's Monitor switch is on Auto and the track isn't armed, as above. Set Monitor to In.
- **Notes sound but late or uneven**: the tool's lateness line says whether the bus is at fault. If it
  reads well under a millisecond, as it does on a quiet machine, look at Live's audio buffer size in
  its Audio preferences instead.
- **Notes hang after stopping**: `Ctrl+T` on any page of the tracker sends note offs, all notes off
  and all sound off on every channel the instruments use.
