# Configuring CycloMonitor
First off, make sure your configuration is in JSON format, as shown in `example_config.json`.

To run CycloMonitor with a configuration file:
`python3 -m cyclomonitor -b -c CONFIG.json`

`token`: A string containing your bot's token. This field is required.
```json
{
    "token": "your.token.here"
}
```

`log_file`: If set, CycloMonitor will log to the specified file, relative to the working directory.
```json
{
    "log_file": "bot.log"
}
```

`client_id`: The ID of your bot. This is used by the `/invite` command.
```json
{
    "client_id": 1107462705004167230
}
```

`github`: A link to a git repository containing the bot's source code (it doesn't have to be GitHub).
```json
{
    "github": "https://github.com/ntvmb/cyclomonitor"
}
```

`emojis`: A dictionary consisting of emojis to use when designating TCs. If any one of them is not set, a default emoji is used.  
* `ex`: Extratropical cyclone
* `low`: Post-tropical low/invest
* `remnants`: Remnant low
* `td`: Tropical depression
* `sd`: Subtropical depression
* `ts`: Tropical storm
* `ss`: Subtropical storm
* `cat1`: Category 1 (SSHWS)
* `cat2`: Category 2 (SSHWS)
* `cat3`: Category 3 (SSHWS)
* `cat4`: Category 4 (SSHWS)
* `cat5`: Category 5 (137-152 kt)
* `cat5intense`: Category 5 (153-167 kt)
* `cat5veryintense`: Category 5 (>167 kt)
```json
{
    "emojis": {
        "ex": "<:ex:1109994645431259187>",
        "low": "<:low:1109997033227558923>",
        "remnants": "<:remnants:1109994646932836386>",
        "td": "<:td:1109994651169079297>",
        "sd": "<:sd:1109994648300163142>",
        "ts": "<:ts:1109994652368650310>",
        "ss": "<:ss:1109994649654935563>",
        "cat1": "<:cat1:1109994357257420902>",
        "cat2": "<:cat2:1109994593895862364>",
        "cat3": "<:cat3:1109994641094357024>",
        "cat4": "<:cat4:1109994643057295401>",
        "cat5": "<:cat5:1109994644386893864>",
        "cat5intense": "<:cat5intense:1111376977664954470>",
        "cat5veryintense": "<:cat5veryintense:1111378049448026126>"
    }
}
```

`server`: An invite to a Discord server dedicated to the bot. This is shown in the `/server` command.
```json
{
    "server": "https://discord.gg/xBHESnJYz5"
}
```

Full example:
```json
{
    "token": "your.token.here",
    "log_file": "bot.log",
    "client_id": 1107462705004167230,
    "github": "https://github.com/ntvmb/cyclomonitor",
    "emojis": {
        "ex": "<:ex:1109994645431259187>",
        "low": "<:low:1109997033227558923>",
        "remnants": "<:remnants:1109994646932836386>",
        "td": "<:td:1109994651169079297>",
        "sd": "<:sd:1109994648300163142>",
        "ts": "<:ts:1109994652368650310>",
        "ss": "<:ss:1109994649654935563>",
        "cat1": "<:cat1:1109994357257420902>",
        "cat2": "<:cat2:1109994593895862364>",
        "cat3": "<:cat3:1109994641094357024>",
        "cat4": "<:cat4:1109994643057295401>",
        "cat5": "<:cat5:1109994644386893864>",
        "cat5intense": "<:cat5intense:1111376977664954470>",
        "cat5veryintense": "<:cat5veryintense:1111378049448026126>"
    },
    "server": "https://discord.gg/xBHESnJYz5"
}
```
