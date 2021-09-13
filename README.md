# pipen-diagram

Draw pipeline diagrams for [pipen][1].

## Features

- Different coloring for different roles of processes (start, end, etc)
- Diagram theming
- Hiding processes from diagram

## Configurations

- `diagram_theme`: The name of the theme to use, or a dict of a custom theme.
  - See `pipen_diagram/diagram.py` for the a theme definition
- `diagram_savedot`: Whhether to save the dot file (for debugging purpose)
- `diagram_hide`: Process-level item, whether to hide current process from the diagram

## Installation

```
pip install -U pipen-diagram
```

## Enabling/Disabling the plugin

The plugin is registered via entrypoints. It's by default enabled. To disable it:
`plugins=[..., "no:diagram"]`, or uninstall this plugin.

## Usage

`example.py`
```python
from pipen import Proc, Pipen

class Process(Proc):
    input = 'a'
    output = 'b:{{in.a}}'

class P1(Process):
    input_data = [1]

class P2(Process):
    requires = P1

class P3(Process):
    requires = P2
    plugin_opts = {"diagram_hide": True}

class P4(Process):
    requires = P3

Pipen().run(P1)
```

Running `python example.py` will generate `pipen-0_results/diagram.svg`:

![diagram](./diagram.png)

[1]: https://github.com/pwwang/pipen
