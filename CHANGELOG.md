CycloMonitor changelog

# 2024.7.27
* New dependency: `aiofiles`
    * This is used by `atcf` and `ibtracs` so disk writes are not blocking
* Fix: Automatic routines actually restart on reconnect
* Fix: NameError in `cli.present` and in `atcf.get_forecast` when getting NHC forecasts
* Changed: Full IBTrACS update now runs once per month instead of once per year
* Changed: `atcf.WrongData` and `atcf.NoActiveStorms` now inherit from `atcf.ATCFError`
* Changed: CLI start-up message is now hidden when `stdin` is a pipe.

# 2024.5.25
* Change: Try to accomodate for recent dissipations when considering whether or not to suppress an automatic update
* Fix: Fix desynced lists in the get_forecast command when the last update was from the main source
* Removed: Warning message on CLI startup removed since it's not longer relevant

# 2024.5.15
* Fix: Fix [#3](https://github.com/ntvmb/cyclomonitor/issues/3)

# 2024.5.14
* Added: CLI now supports user-defined variables
* Fix: CLI now works on Python <3.11
    * Known issue: ATCF commands can break ([#3](https://github.com/ntvmb/cyclomonitor/issues/3))
* Changed: ibtracs no longer depends on the `sqlite3` shell

# 2024.5.12
* Added: Command-line interface
    * Run the CLI with `python3 -m cyclomonitor.cli`. Type `help` for commands

# 2024.4.24
* Added: `/server` command
    * Set the invite through the `server` config parameter

# 2024.4.19
* Added: New configuration file parameters: `client_id`, `github`, `emojis`
* Added: Docs for configuration file
* **Changed: Client ID, GitHub link, and custom Emojis are no longer hardcoded.**

# 2024.4.15
* Added: command-line arguments
* Added: support for configuration files
* Fix: Fixed UnboundLocalError in the `/atcf_reset` command
* Fix: Moved the logger setup to the main function
* Fix: Running the main module no longer raises a RuntimeWarning

# 2024.4.14
* Initial release