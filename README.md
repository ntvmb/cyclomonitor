# CycloMonitor
Discord bot that automatically updates active TC information based on data from the ATCF.

This project uses the following modules that are not included with Python:  
* py-cord
* requests
* tendo (Optional, for single-instance checking)
### Disclaimer
No party involved with CycloMonitor should make any claim that this bot is intended to replace tropical cyclone advisories/warnings issued by your local RSMC or TCWC. If you need more detailed information than what is provided by the bot, see your local RSMC or TCWC website for forecasts, potential land impacts, or other relevant information.

## Running the bot
Clone this repository:
```
git clone https://github.com/ntvmb/cyclomonitor.git
cd cyclomonitor
```
Install prerequisites:
```
pip3 install --user py-cord requests tendo
```
Some Linux distributions may require you to [set up a virtual environment](https://docs.python.org/3/library/venv.html) to install the necessary packages.

Create a file called `TOKEN` and paste your bot's token into it.

Run the bot:
```
python3 main.py
```
If you're using a virtual environment, ensure it is active before running the bot.  
No feedback is given on the console. Instead, information is written to a file called `bot.log`.
