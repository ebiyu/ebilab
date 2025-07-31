# sample scripts

All sample scripts have been updated to use the new API (v3) with `BaseExperiment` and `BasePlotter` classes.

- `multimeter.py`: Simple resistance measurement experiment (`SimpleResistanceMeasurement`) with configurable NPLC, range, and interval settings
- `voltage.py`: Voltage measurement experiment (`VoltageMeasurement`) with real-time plotting and configurable voltage range limits
- `random_walk.py`: Random walk experiment (`RandomWalkExperiment`) with dual plotters (transient and histogram views)
- `r_continuous.py`: Continuous resistance measurement experiment (`Experiment`) with K34465A multimeter support and real-time plotting
- `do_nothing.py`: Minimal experiment (`DoNothingExperiment`) that immediately finishes - useful for testing
- `raise_error.py`: Error handling demonstration (`RaiseErrorExperiment`) that intentionally raises a ValueError
- `sleep.py`: Sleep experiment (`ContextSleepExperiment`) demonstrating proper asyncio.sleep usage for interruptible delays

All scripts can be run independently using `uv run <script_name>.py` and will launch the GUI interface.
