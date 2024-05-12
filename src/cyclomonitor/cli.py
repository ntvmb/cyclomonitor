"""CycloMonitor CLI"""

import asyncio
import sys
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
PRIVATE_ATTRS = [
    "zip_longest", "ATCFError", "WrongData", "NoActiveStorms", "main",
    "dataclass", "Iterable", "Storm", "Query", "query_group", "varchar",
    "numeric", "bit", "StringIO", "Callable", "Awaitable", "Generator",
    "Internal",
]
# fmt: on


class Internal:
    def __repr__(self):
        return CLI_PARSER_REPR

    @staticmethod
    def parse(line: str):
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
                    if out.name == "Not_Named":
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
            else:
                return repr(command)
        else:
            return CLI_SYMBOL_NOT_FOUND.format(args[0])


def echo(*args):
    out = StringIO()
    for arg in args:
        out.write(f"{arg} ")
    return out.getvalue()


def copyright(*args):
    return COPYRIGHT_NOTICE


def commands(*args):
    return (
        key
        for key, value in globals().items()
        if isinstance(value, (Callable, Awaitable)) and key not in PRIVATE_ATTRS
    )


def cli():
    print(CLI_STARTUP)
    while True:
        try:
            request = input("> ")
        except EOFError:
            print("\n", end="")
            break
        except Exception:
            logging.exception(CLI_INTERNAL_ERROR)
            continue
        out = Internal.parse(request)
        if out:
            if out.endswith("\n"):
                print(out, end="")
            else:
                print(out)


if __name__ == "__main__":
    locale_init()
    cli()
