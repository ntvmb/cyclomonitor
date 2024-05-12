"""CycloMonitor CLI"""

import asyncio
import datetime
from sys import exit
from .atcf import *
from . import errors
from .ibtracs import *
from .dir_calc import get_dir
from .locales import *
from io import StringIO
from typing import Callable, Awaitable, Generator

COPYRIGHT_NOTICE = """\
CycloMonitor - ATCF and IBTrACS wrapper for Discord
Copyright (c) 2023 Virtual Nate

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
details.

For those hosting a copy of this bot, you should have received a copy of the
GNU Affero General Public License along with this program. If not, see
<https://www.gnu.org/licenses/>."""
KT_TO_MPH = 1.15077945
KT_TO_KMH = 1.852
# fmt: off
# Callable attributes that probably shouldn't be called from the CLI
PRIVATE_ATTRS = [
    "zip_longest", "ATCFError", "WrongData", "NoActiveStorms", "main",
    "dataclass", "Iterable", "Storm", "Query", "query_group", "varchar",
    "numeric", "bit", "StringIO", "Callable", "Awaitable", "Generator",
    "Internal",
]
# fmt: on


class Internal:
    """
    Methods internal to the CLI.
    All methods in this class (except for __repr__) are static.
    """

    def __repr__(self):
        return CLI_PARSER_REPR

    @staticmethod
    def parse(line: str):
        # TODO: Support quoted arguments
        if not line:
            return ""
        args = line.split()
        kwargs = {
            arg.split("=")[0]: arg.split("=")[1] for arg in args[1:] if "=" in arg
        }
        # Separate args and kwargs
        to_delete = []
        for arg in args[1:]:
            if "=" in arg:
                to_delete.append(arg)
        for arg in to_delete:
            args.remove(arg)

        for index, arg in enumerate(args):
            if index == 0:
                continue
            if "." in arg:
                try:
                    args[index] = float(arg)
                except ValueError:
                    pass
            else:
                try:
                    args[index] = int(arg)
                except ValueError:
                    pass
        for k, v in kwargs.items():
            if "." in v:
                try:
                    kwargs[k] = float(v)
                except ValueError:
                    pass
            else:
                try:
                    kwargs[k] = int(v)
                except ValueError:
                    pass

        if args[0] in globals() and args[0] not in PRIVATE_ATTRS:
            command = globals()[args[0]]
            if isinstance(command, Callable):
                try:
                    out = command(*args[1:], **kwargs)
                except Exception as e:
                    if e.args:
                        return f"{type(e).__name__}: {e}"
                    else:
                        return type(e).__name__

                if isinstance(out, Awaitable):
                    try:
                        out = asyncio.run(out)
                    except Exception as e:
                        if e.args:
                            return f"{type(e).__name__}: {e}"
                        else:
                            return type(e).__name__

                if out is not None and not isinstance(out, (str, Storm, Generator)):
                    return repr(out)
                elif out is None:
                    return ""
                # almost certainly the output of ibtracs.get_storm
                elif isinstance(out, Storm):
                    if out.name == "NOT_NAMED":
                        header = CM_UNNAMED_STORM.format(out.nature())
                    else:
                        header = f"{out.nature()} {out.name}"
                    return CM_PAST_STORM_INFO.format(
                        header,
                        out.season,
                        out.basin,
                        out.peak_winds,
                        out.peak_pres,
                        out.time_of_peak,
                        out.atcf_id,
                        out.best_track_id,
                    )
                elif isinstance(out, Generator):
                    out_temp = StringIO()
                    if args[0] == "get_storm":
                        out_temp.write(CM_MULTIPLE_STORMS)
                    out_temp.writelines([f"{s}\n" for s in out])
                    out = out_temp.getvalue()
                    out_temp.close()
                return out
            elif isinstance(command, str):
                return command
            else:
                return repr(command)
        else:
            return CLI_SYMBOL_NOT_FOUND.format(args[0])

    @staticmethod
    def get_nature_name(name, wind, tc_class):
        # see cyclomonitor.update_guild for more info
        if name == "INVEST" and (not (tc_class == "SD" or tc_class == "SS")):
            tc_class = CLASS_AOI
        if tc_class == "EX":
            if not name == "INVEST":
                tc_class = CLASS_PTC
        elif tc_class == "LO" or tc_class == "INVEST":
            if not name == "INVEST":
                tc_class = CLASS_PTC
        elif tc_class == "DB" or tc_class == "WV":
            if not name == "INVEST":
                tc_class = CLASS_RL
        elif wind < 35:
            if not (tc_class == "SD" or name == "INVEST"):
                tc_class = CLASS_TD
            elif name == "INVEST" and not tc_class == "SD":
                pass
            else:
                tc_class = CLASS_SD
        elif wind > 34 and wind < 65:
            if not (tc_class == "SS" or name == "INVEST"):
                tc_class = CLASS_TS
            elif name == "INVEST" and not tc_class == "SS":
                pass
            else:
                tc_class = CLASS_SS
        else:
            if basin == "ATL" or basin == "EPAC" or basin == "CPAC":
                if wind < 100:
                    tc_class = CLASS_HU
                else:
                    tc_class = CLASS_MH
            elif basin == "WPAC":
                if wind < 130:
                    tc_class = CLASS_TY
                else:
                    tc_class = CLASS_STY
            else:
                tc_class = CLASS_CY
        return tc_class


def echo(*args):
    """Print a string to the screen."""
    out = StringIO()
    for arg in args:
        out.write(f"{arg} ")
    return out.getvalue()


def copyright(*args):
    """Get the copyright notice."""
    return COPYRIGHT_NOTICE


def commands(*args):
    """Get the list of commands usable in the CLI."""
    return (
        key
        for key, value in globals().items()
        if isinstance(value, (Callable, Awaitable)) and key not in PRIVATE_ATTRS
    )


def help(command_name="", *args):
    """Stop it. Get some help."""
    if command_name:
        try:
            command = globals()[command_name]
            if isinstance(command, Callable) and command_name not in PRIVATE_ATTRS:
                if command.__doc__ is not None:
                    return command.__doc__
                else:
                    return CLI_MISSING_DOCSTRING
            elif not isinstance(command, Callable):
                return CLI_IS_A_VAR.format(command_name)
            else:
                return CLI_SYMBOL_NOT_FOUND.format(command_name)
        except (AttributeError, KeyError):
            return CLI_SYMBOL_NOT_FOUND.format(command_name)
    else:
        return CLI_HELP


def present(name_or_id: str):
    """Present a TC in the ATCF data.

    Parameters:
    name_or_id - The TC name or identifier.
    """
    if not (cyclones and names):
        raise NoActiveStorms
    name_or_id = name_or_id.upper()
    if name_or_id in names:
        name = name_or_id
        index = names.index(name_or_id)
        id = cyclones[index]
    elif name_or_id in cyclones:
        id = name_or_id
        index = cyclones.index(name_or_id)
        name = names[index]
    else:
        raise ValueError(CLI_STORM_NOT_FOUND.format(name_or_id))

    tc_class = tc_classes[index]
    wind = winds[index]
    tc_class = Internal.get_nature_name(name, wind, tc_class)
    timestamp = (
        datetime.datetime.fromtimestamp(timestamps[index])
        .replace(tzinfo=datetime.timezone.utc)
        .isoformat()
    )
    if name == "INVEST":
        name = display_name = id
    else:
        display_name = f"{id} ({name})"
    lat = lats[index]
    long = longs[index]
    mph = round(wind * KT_TO_MPH / 5) * 5
    kmh = round(wind * KT_TO_KMH / 5) * 5
    pres = pressures[index]
    movement_speed = movement_speeds[index]
    movement_dir = get_dir(movement_dirs[index])
    if (not movement_dir) or (movement_speed) < 0:
        movement_str = NOT_AVAILABLE
    else:
        movement_mph = movement_speed * KT_TO_MPH
        movement_kmh = movement_speed * KT_TO_KMH
        movement_str = STORM_MOVEMENT.format(
            movement_dir, movement_speed, movement_mph, movement_kmh
        )
    return CM_STORM_INFO.format(
        "",
        tc_class,
        display_name,
        timestamp,
        name,
        lat,
        long,
        wind,
        mph,
        kmh,
        pres,
        movement_str,
    )


def cli():
    """The main function of the CLI."""
    print(CLI_STARTUP)
    while True:
        try:
            request = input("cyclomonitor> ")
        except EOFError:
            print("\n", end="")
            break
        except KeyboardInterrupt:
            print("\n", end="")
            continue
        except Exception:
            logging.exception(CLI_INTERNAL_ERROR)
            continue
        try:
            out = Internal.parse(request)
        except Exception:
            logging.exception(CLI_INTERNAL_ERROR)
            continue
        if out:
            if out.endswith("\n"):
                print(out, end="")
            else:
                print(out)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s.%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.WARNING,
    )
    locale_init()
    cli()
