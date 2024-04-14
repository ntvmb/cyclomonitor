# CycloMonitor
Discord bot that automatically updates active TC information based on data from the ATCF.

This project uses the following modules that are not included with Python:  
* py-cord
* aiohttp (provided by py-cord)
* tendo (Optional, for single-instance checking)
### Disclaimer
No party involved with CycloMonitor should make any claim that this bot is intended to replace tropical cyclone advisories/warnings issued by your local RSMC or TCWC. If you need more detailed information than what is provided by the bot, see your local RSMC or TCWC website for forecasts, potential land impacts, or other relevant information.

## Running the bot
Clone this repository:
```
git clone https://github.com/ntvmb/cyclomonitor.git
cd cyclomonitor
```
Install to your current environment:
```
pip install .
```
Optional: Install `tendo` for single instance checking: `pip install tendo`   
Some Linux distributions may require you to [set up a virtual environment](https://docs.python.org/3/library/venv.html).

Create a file called `TOKEN` and paste your bot's token into it.

Run the bot:
```
python3 -m cyclomonitor
```
If you're using a virtual environment, ensure it is active before running the bot.  
No feedback is given on the console. Instead, information is written to a file called `bot.log`.

Note: This bot is designed to work on Python 3.11+. If you encounter issues due to being on an older version, chances are I won't fix them.
