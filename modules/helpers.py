from datetime import datetime, timedelta
from functools import partial
from itertools import chain
from re import compile


flatten = chain.from_iterable

flatMap = lambda x, y: list(flatten(map(x, y)))

round2 = partial(round, ndigits=2)

secsToHMS = lambda sec: str(timedelta(seconds=sec)).split(".")[0]

now = lambda: str(datetime.now()).split(".")[0]

timeNow = lambda: str(datetime.now().time()).split(".")[0]

dateNow = lambda: str(datetime.now().date()).split(".")[0]

bytesToMB = lambda bytes: round2(bytes / float(1 << 20))

fileDTime = lambda: datetime.now().strftime("%y%m%d-%H%M%S")


def nSort(s, nsre=compile("([0-9]+)")):
    return [int(text) if text.isdigit() else text.lower() for text in nsre.split(s)]


dynWait = lambda secs, n=7.5: secs / n

addDots = lambda exts: [f".{x}" for x in exts]
