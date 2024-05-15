CycloMonitor changelog

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