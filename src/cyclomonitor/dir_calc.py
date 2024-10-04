def get_dir(deg: float) -> str:
    if deg < 0:
        return ""
    deg %= 360
    if deg > 348.75 or deg <= 11.25:
        return "N"
    elif deg > 11.25 and deg <= 33.75:
        return "NNE"
    elif deg > 33.75 and deg <= 56.25:
        return "NE"
    elif deg > 56.25 and deg <= 78.75:
        return "ENE"
    elif deg > 78.75 and deg <= 101.25:
        return "E"
    elif deg > 101.25 and deg <= 123.75:
        return "ESE"
    elif deg > 123.75 and deg <= 146.25:
        return "SE"
    elif deg > 146.25 and deg <= 168.75:
        return "SSE"
    elif deg > 168.75 and deg <= 191.25:
        return "S"
    elif deg > 191.25 and deg <= 213.75:
        return "SSW"
    elif deg > 213.75 and deg <= 236.25:
        return "SW"
    elif deg > 236.25 and deg <= 258.75:
        return "WSW"
    elif deg > 258.75 and deg <= 281.25:
        return "W"
    elif deg > 281.25 and deg <= 303.75:
        return "WNW"
    elif deg > 303.75 and deg <= 326.25:
        return "NW"
    elif deg > 326.25 and deg <= 348.75:
        return "NNW"
