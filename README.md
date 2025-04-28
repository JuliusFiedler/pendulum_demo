# Inverted Pendulum Demo
- Demo for "Lange Nacht der Wissenschaften"
- stabilization and swingup of inverted pendulum, by hand and with controller

## Installation
- `pip install -r requirements.txt`

## Execution
- run `python main.py`

## Parameters
- `core/loops.py` line 96 -> max tries before returning to start screen

## Swingup
- Trajectory is loaded a from csv: list of actions
- record new swingup trajectory: `core/loops.py` line 437 -> set `self.number_of_modes = 3` to activate swingdown mode
- record swingdown + stabilization up lower eq -> reverse actions -> swingup
