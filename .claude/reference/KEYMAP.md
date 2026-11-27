# Key Map

Written by `internal_tools/key_map.sh` from a walk of llamatron (`llamatron-compare keymap`); never edit it by hand. For
every page and dialog the walk reaches, it says what each key does with the cursor at each kind of place, as the page names
the place. The keys that work everywhere are listed once:

- `Ctrl+S` SAVE
- `Ctrl+O` OPEN
- `Ctrl+X` EXPORT
- `Ctrl+T` SILENCE
- `Ctrl+Z` UNDO
- `Ctrl+Y` REDO
- `F1` HELP
- `F3` ABOUT
- `Ctrl+C` QUIT NOW


## AboutDialog

- **anywhere**: `ENTER/ESC` close


## ArrangePage

- **scene**: `ESC` back · `←↑↓→` move · `Space` play scene · `ENTER` scene settings · `V` scene view · `C` copy scene · `Bksp` delete scene · `I` insert scene · `T` cut scene · `D` details · `Tab` cell details · `Z` visualizer · `F` fracture
- **clip**: `ESC` back · `←↑↓→` move · `Space` play clip · `ENTER` edit clip · `J` jump to pattern · `T` cut clip · `C` copy clip · `Bksp` delete clip · `M` mute · `S` solo · `I` insert scene · `D` details · `Tab` cell details · `Z` visualizer · `F` fracture
- **corner**: `ESC` back · `←↑↓→` move · `Space` play song · `D` details · `Z` visualizer · `F` fracture
- **track**: `ESC` back · `←↑↓→` move · `ENTER` track settings · `C` copy track · `I` insert track · `T` cut track · `Bksp` delete track · `M` mute · `S` solo · `D` details · `Tab` cell details · `Z` visualizer · `F` fracture
- **drum track plus**: `ESC` back · `←↑↓→` move · `I` insert track · `D` details · `Z` visualizer · `F` fracture
- **empty**: `ESC` back · `←↑↓→` move · `ENTER` add clip · `B` blank pattern · `M` mute · `S` solo · `I` insert scene · `D` details · `Z` visualizer · `F` fracture


## ChainEditor

- **row**: `ESC` back · `↑↓` move · `A` add · `ENTER` change · `C` copy · `Bksp` remove · `M` move · `N/F2` rename chain · `/` search
- **plus**: `ESC` back · `ENTER` add · `↑↓` move · `A` add · `N/F2` rename chain · `/` search
- **searching**: `ESC` CANCEL · `↑↓` move · `A-Z 0-9` search · `Bksp` erase · `Tab` complete · `ENTER` keep


## ChoiceDialog

- **anywhere**: `ESC` CANCEL · `↑↓` move · `ENTER` choose · `A-Z 0-9` search


## ChordDialog

- **anywhere**: `ESC` CANCEL · `←↑↓→` move · `Tab` next list · `ENTER` choose


## ChordsEditor

- **anywhere**: `ESC` back · `←↑↓→` move · `[` dec · `]` inc · `0-9` type · `I` insert step · `D` remove step · `H` pick progression


## ClipPage

- **Name**: `ESC` back · `↑↓` move · `ENTER` rename · `Bksp` from pattern · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Patterns**: `ESC` back · `↑↓` move · `ENTER` edit · `Bksp` remove · `Tab` to tabs · `F2` rename · `A` add pattern · `M` move pattern · `J` jump to pattern · `L` listen
- **Tabs**: `ESC` back · `↑↓` move · `←→` move · `Tab` into tab · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **anywhere**: `ESC` back · `↑↓` move · `ENTER` add · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Pattern order**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Step direction**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` from pattern · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Scale**: `ESC` back · `↑↓` move · `←→` move · `ENTER` choose · `Bksp` from scene · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Velocity in start**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Repeat**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Grab track**: `ESC` back · `↑↓` move · `←→` move · `ENTER` choose · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Velocity in end**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Velocity out start**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Velocity**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Density start**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` clear · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Loop**: `ESC` back · `↑↓` move · `←→` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Velocity in over**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Listen**: `ESC` back · `↑↓` move · `←→` move · `ENTER` listen · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Velocity out end**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Density end**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` clear · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Articulate start**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` clear · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Follow action**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Velocity out over**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Density over**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (whole) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Articulate end**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` clear · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Articulate over**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (whole) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Density then**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Articulate then**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen
- **Morph to**: `ESC` back · `↑↓` move · `←→` move · `ENTER` choose · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `A` add pattern · `J` jump to pattern · `L` listen


## ConfirmDialog

- **anywhere**: `ESC` NO · `←→` move · `ENTER` answer


## DrawsPage

- **AD**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next section
- **BD**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next section
- **CD**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next section
- **DD**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next section
- **ED**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next section
- **FD**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next section
- **GD**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next section
- **HD**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next section


## ExportDialog

- **anywhere**: `ESC` CANCEL · `↑↓` move · `ENTER` choose · `A-Z 0-9` search


## FilePage

- **Tabs**: `ESC` back · `↑↓` move · `←→` move · `Tab` into tab
- **Title**: `ESC` back · `↑↓` move · `←→` move · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs
- **Author**: `ESC` back · `↑↓` move · `←→` move · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs
- **Follow action**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs
- **Track Inst. Default**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs
- **Description**: `ESC` back · `↑↓` move · `←→` move · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs
- **Drum octave**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `PgUp/PgDn` next tab · `Tab` to tabs
- **New**: `ESC` back · `↑↓` move · `←→` move · `ENTER` new · `Tab` to tabs
- **Notes**: `ESC` back · `↑↓` move · `←→` move · `ENTER` edit · `PgUp/PgDn` next tab · `Tab` to tabs
- **Octave**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `PgUp/PgDn` next tab · `Tab` to tabs
- **Open**: `ESC` back · `↑↓` move · `←→` move · `ENTER` OPEN · `Tab` to tabs
- **Protected**: `ESC` back · `↑↓` move · `←→` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs
- **Step size**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs
- **Save**: `ESC` back · `↑↓` move · `←→` move · `ENTER` SAVE · `Tab` to tabs
- **Octave labels**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs
- **Save As**: `ESC` back · `↑↓` move · `←→` move · `ENTER` save as · `Tab` to tabs
- **Visualizer**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs
- **Hide Visualizers**: `ESC` back · `↑↓` move · `←→` move · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs


## GeneratorListPage

- **plus**: `ESC` back · `ENTER` add · `↑↓` move · `A` add · `/` search
- **searching**: `ESC` CANCEL · `↑↓` move · `A-Z 0-9` search · `Bksp` erase · `Tab` complete · `ENTER` keep


## GeneratorsPage

- **generator arp**: `ESC` back · `↑↓` move · `A` add · `ENTER` edit · `N/F2` rename · `C` copy · `Bksp` delete · `/` search
- **generator chain**: `ESC` back · `↑↓` move · `A` add · `ENTER` edit · `N/F2` rename · `C` copy · `Bksp` delete · `/` search
- **searching**: `ESC` CANCEL · `↑↓` move · `A-Z 0-9` search · `Bksp` erase · `Tab` complete · `ENTER` keep
- **generator chords**: `ESC` back · `↑↓` move · `A` add · `ENTER` edit · `N/F2` rename · `C` copy · `Bksp` delete · `/` search
- **plus**: `ESC` back · `ENTER` add · `↑↓` move · `A` add · `/` search


## GridChoiceDialog

- **anywhere**: `ESC` CANCEL · `←↑↓→` move · `ENTER` choose


## GrooveEditor

- **anywhere**: `ESC` back · `←→` move · `[` dec · `]` inc · `0-9` type · `I` insert cell · `D` remove cell · `S` cell length · `N/F2` rename


## GroovesPage

- **row**: `ESC` back · `↑↓` move · `A` add · `ENTER` view · `C` copy · `/` search
- **searching**: `ESC` CANCEL · `↑↓` move · `A-Z 0-9` search · `Bksp` erase · `Tab` complete · `ENTER` keep
- **plus**: `ESC` back · `ENTER` add · `↑↓` move · `A` add · `/` search


## GroupedChoiceDialog

- **anywhere**: `ESC` CANCEL · `↑↓` move · `Space/ENTER` open · `PgUp/PgDn` next section · `A-Z 0-9` search


## HelpDialog

- **anywhere**: `ENTER/ESC` close


## InstrumentEditor

- **Name**: `ESC` back · `↑↓` move · `ENTER` rename · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **Default velocity**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 127 · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **Tabs**: `ESC` back · `↑↓` move · `←→` move · `Tab` into tab · `F2` rename · `K` keyswitch map · `L` listen
- **Accent**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` +0 · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **Velocity**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **Engine**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **Percussion**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **GM sound**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **Pan**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 50% (center) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **Channel**: `ESC` back · `↑↓` move · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **Preview pattern**: `ESC` back · `↑↓` move · `←→` move · `ENTER` edit · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **Keyswitch Map**: `ESC` back · `↑↓` move · `←→` move · `ENTER` keyswitch map · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen
- **Listen**: `ESC` back · `↑↓` move · `←→` move · `ENTER` listen · `Tab` to tabs · `F2` rename · `K` keyswitch map · `L` listen


## InstrumentsPage

- **row**: `ESC` back · `↑↓` move · `A` add · `ENTER` edit · `N/F2` rename · `C` copy · `Bksp` delete · `M` move · `S` sort · `/` search
- **plus**: `ESC` back · `ENTER` add · `↑↓` move · `A` add · `/` search
- **searching**: `ESC` CANCEL · `↑↓` move · `A-Z 0-9` search · `Bksp` erase · `Tab` complete · `ENTER` keep


## KeyswitchDialog

- **anywhere**: `ESC` CANCEL · `↑↓` move · `Space` toggle · `0-9` toggle · `ENTER` done


## KeyswitchMapDialog

- **anywhere**: `ESC` CANCEL · `↑↓` move · `→` note · `N/F2` rename · `ENTER` note · `Bksp` clear


## MainPage

- **anywhere**: `F` File/Global · `S` Songs · `W` Wizard · `P` Patterns · `G` Generators · `Z` Scales · `V` Grooves · `I` Instruments · `D` Draws · `A` Arrange · `O` OPEN · `X` EXPORT · `L` LOAD MIDI · `Q` QUIT · `←↑↓→` move · `ENTER` open


## MessageDialog

- **anywhere**: `ENTER` close


## NewPatternDialog

- **anywhere**: `ESC` CANCEL · `↑↓` move · `[` dec · `]` inc · `ENTER` OK


## NotesPage

- **anywhere**: `ESC` CANCEL · `←↑↓→` move · `ENTER` new line · `Bksp` erase · `Tab` Save or CANCEL


## OffsetsEditor

- **anywhere**: `ESC` back · `←→` move · `[` dec · `]` inc · `0-9` type · `Space/ENTER` silent · `I` insert step · `D` remove step


## OpenPage

- **row**: `ESC` back · `↑↓` move · `ENTER` open · `/` search
- **searching**: `ESC` CANCEL · `↑↓` move · `A-Z 0-9` search · `Bksp` erase · `Tab` complete · `ENTER` keep


## PatternEditor

- **anywhere**: `ESC` back · `←↑↓→` move · `Home/End` ends · `Tab` to editor · `S` size · `M` munge · `R` reconfigure · `L` listen · `F2` rename · `Space/ENTER` note · `H` chord · `K` keyswitch · `[` shrink · `]` stretch · `X` split · `.` #/b · `Bksp` erase · `G` grab · `E` entry size


## PatternsPage

- **pattern**: `ESC` back · `↑↓` move · `ENTER` edit · `G` group · `A` add · `N/F2` rename · `C` copy · `Bksp` delete · `L` listen · `Tab` to tabs · `PgUp/PgDn` next tab · `/` search
- **tabs**: `ESC` back · `↑↓` move · `←→` move · `A` add · `N/F2` rename · `C` copy · `Bksp` ungroup · `Tab` into tab · `PgUp/PgDn` next tab · `/` search
- **new group**: `ESC` back · `↑↓` move · `ENTER` new group · `Tab` to tabs · `PgUp/PgDn` next tab · `/` search
- **searching**: `ESC` CANCEL · `↑↓` move · `A-Z 0-9` search · `Bksp` erase · `Tab` complete · `ENTER` keep
- **plus**: `ESC` back · `↑↓` move · `ENTER` new pattern · `Tab` to tabs · `PgUp/PgDn` next tab · `/` search


## PickManyDialog

- **anywhere**: `ESC` CANCEL · `↑↓` move · `Space` toggle · `ENTER` done


## PluginEditor

- **arp Name**: `ESC` back · `↑↓` move · `ENTER` rename · `F2` rename
- **arp Enabled**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `F2` rename
- **arp Step**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (from pattern) · `F2` rename
- **arp Order**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `F2` rename
- **arp Octave range**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 1 · `F2` rename
- **arp Octave jump**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `F2` rename
- **arp Offsets**: `ESC` back · `↑↓` move · `ENTER` edit · `Bksp` (none) · `F2` rename
- **arp Restart**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `F2` rename
- **chords Name**: `ESC` back · `↑↓` move · `ENTER` rename · `F2` rename
- **chords Enabled**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `F2` rename
- **chords Mode**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `F2` rename
- **chords Every**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` 1 bar · `F2` rename
- **chords Chords**: `ESC` back · `↑↓` move · `ENTER` edit · `F2` rename
- **chords Voice leading**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `F2` rename
- **chords Lowest octave**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 2 · `F2` rename
- **chords Highest octave**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 4 · `F2` rename
- **chords Keep the root in the bass**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `F2` rename
- **chords Restart**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `F2` rename


## PromptDialog

- **anywhere**: `ESC` CANCEL · `←→` move · `ENTER` done · `Bksp` erase


## ScalePage

- **Name**: `ESC` back · `↑↓` move · `ENTER` rename · `F2` rename
- **Root**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `F2` rename
- **Kind**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `F2` rename


## ScalesPage

- **row**: `ESC` back · `↑↓` move · `A` add · `ENTER` edit · `N/F2` rename · `C` copy · `Bksp` delete · `M` move · `S` sort · `/` search
- **plus**: `ESC` back · `ENTER` add · `↑↓` move · `A` add · `/` search
- **searching**: `ESC` CANCEL · `↑↓` move · `A-Z 0-9` search · `Bksp` erase · `Tab` complete · `ENTER` keep


## ScenePage

- **Name**: `ESC` back · `↑↓` move · `ENTER` rename · `Tab` to tabs · `F2` rename
- **Tabs**: `ESC` back · `↑↓` move · `←→` move · `Tab` into tab · `F2` rename
- **Section**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Repeat**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Velocity in start**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Launch together**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Velocity in end**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Velocity**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Velocity out start**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Tempo in start**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% (120 BPM) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Scale**: `ESC` back · `↑↓` move · `ENTER` choose · `Bksp` from song · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Velocity in over**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Velocity out end**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Tempo in end**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% (120 BPM) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Tempo out start**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% (120 BPM) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Density start**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` clear · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Groove**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` from song · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Velocity out over**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Tempo in over**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Tempo out end**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% (120 BPM) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Density end**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` clear · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Articulate start**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` clear · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Tempo**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` from song · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Tempo out over**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Density over**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (whole) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Articulate end**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` clear · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Articulate over**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (whole) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Density then**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Articulate then**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename


## SongPage

- **Name**: `ESC` back · `↑↓` move · `ENTER` rename · `F2` rename
- **Tempo**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `F2` rename
- **Time signature**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `F2` rename
- **Entry size**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (one step) · `F2` rename
- **Scale**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (none) · `F2` rename
- **Groove**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `F2` rename
- **Genre**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (none) · `F2` rename
- **Subgenre**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (none) · `F2` rename
- **Variant**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (none) · `F2` rename
- **Live response**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `F2` rename
- **Preview instrument**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (General MIDI piano) · `F2` rename
- **Visualizer**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `F2` rename
- **Export**: `ESC` back · `↑↓` move · `←→` move · `ENTER` EXPORT · `F2` rename


## SongsPage

- **row**: `ESC` back · `↑↓` move · `A` add · `Space` make current · `ENTER` settings · `N/F2` rename · `C` copy · `Bksp` delete · `M` move · `S` sort · `/` search
- **plus**: `ESC` back · `ENTER` add · `↑↓` move · `A` add · `/` search
- **searching**: `ESC` CANCEL · `↑↓` move · `A-Z 0-9` search · `Bksp` erase · `Tab` complete · `ENTER` keep


## SoundDialog

- **anywhere**: `ESC` CANCEL · `↑↓` move · `Space/ENTER` open · `/` search


## TrackEditor

- **Name**: `ESC` back · `↑↓` move · `ENTER` rename · `Tab` to tabs · `F2` rename
- **Tabs**: `ESC` back · `↑↓` move · `←→` move · `Tab` into tab · `F2` rename
- **Instrument**: `ESC` back · `↑↓` move · `←→` move · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Kind**: `ESC` back · `↑↓` move · `←→` move · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Transpose**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 0 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **CC 2**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Mute**: `ESC` back · `↑↓` move · `←→` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Lowest octave**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` -2 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **CC 3**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **CC 1**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Voice leading**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Groove**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` from song · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Highest octave**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 8 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **CC 4**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Mode**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Step**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (from pattern) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Default velocity**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` from instrument · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Enabled**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Order**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Shape chords**: `ESC` back · `↑↓` move · `←→` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Accent**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` +15 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Octave range**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 1 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Tuning**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Play strokes**: `ESC` back · `↑↓` move · `←→` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Restart**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Velocity**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 100% · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Octave jump**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Position**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` open · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Bar**: `ESC` back · `↑↓` move · `←→` move · `ENTER` edit · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Rush step**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (from pattern) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Line**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Offsets**: `ESC` back · `↑↓` move · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Keep the root in the bass**: `ESC` back · `↑↓` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Capo**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Let ring**: `ESC` back · `↑↓` move · `←→` move · `Space/ENTER` toggle · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Rush amount**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 15 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Drag step**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (from pattern) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Breath**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Generators**: `ESC` back · `↑↓` move · `ENTER` edit · `Bksp` (none) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Strings**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 6 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Spread**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 8 ms · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Rush steps**: `ESC` back · `↑↓` move · `←→` move · `ENTER` edit · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Drag amount**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 20 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Shorten step**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (from pattern) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Rise and fall**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Single notes**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Fade**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 20 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Drag steps**: `ESC` back · `↑↓` move · `←→` move · `ENTER` edit · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Shorten amount**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 70 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Glide step**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `Bksp` (from pattern) · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Notes**: `ESC` back · `↑↓` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Color**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Loose timing**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 10 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Shorten steps**: `ESC` back · `↑↓` move · `←→` move · `ENTER` edit · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Glide amount**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Upstroke strings**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` edit · `Bksp` 4 · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Glide steps**: `ESC` back · `↑↓` move · `←→` move · `ENTER` edit · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
- **Approach**: `ESC` back · `↑↓` move · `←→` move · `[` dec · `]` inc · `ENTER` choose · `PgUp/PgDn` next tab · `Tab` to tabs · `F2` rename
