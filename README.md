# CycloMonitor
Command-line tool and Discord bot which presents ATCF and Best Track data.

Dependencies:  
* aiohttp (provided by py-cord)
* py-cord (Optional, for running the bot)
* tendo (Optional, for running the bot)
### Disclaimer
No party involved with CycloMonitor should make any claim that this program is intended to replace tropical cyclone advisories/warnings issued by your local RSMC or TCWC. If you need more detailed information than what is provided by the program, see your local RSMC or TCWC website for forecasts, potential land impacts, or other relevant information.

## Running interactively
Install the package:
```
pip install cyclomonitor
```
Start an interactive session:
`python3 -m cyclomonitor -i` or `python3 -m cyclomonitor.cli`  
When running interactively, type `help` to see available commands.

## Running the bot
Install the package with everything needed to run the bot:
```
pip install cyclomonitor[bot]
```
If you cloned the GitHub repository, you might want to install the package in dev mode:
```
cd cyclomonitor
pip install -e .[bot]
``` 
Some Linux distributions may require you to [set up a virtual environment](https://docs.python.org/3/library/venv.html).

Until I get the project to use absolute paths, you'll probably want to create a separate directory to store its data:
```
mkdir cyclomonitor_temp
cd cyclomonitor_temp
```

To run the bot:
```
python3 -m cyclomonitor -b -t your.token.here
```
If you don't want to specify `-t` every time, paste your bot's token into a file called `TOKEN` in your working directory.  
For full argument list: `python3 -m cyclomonitor -h` or run the module with no arguments.  
Windows users: You might want to replace `python3` with `python`.

If you're using a virtual environment, ensure it is active before running the bot.  
CycloMonitor logs to stdout by default. To log to a file, specify the parameter `-l LOGFILE`, where `LOGFILE` is the path to the log file.

## Configuring the bot 
See CONFIGURATION.md for details.

Supports Python 3.8+, but Python 3.11+ is recommended.
