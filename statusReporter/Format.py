import re

class Format:
    uline = '\033[4m'
    end   = '\033[0m'
    bold  = '\033[1m'
    ansicodes = re.compile(r'\x1B\[[0-?9;]*[mK]')
    fgblack = '\033[30m'
    bgwhite = '\033[47m'