from json import loads as jLoads

from ..helpers import round2
from ..os import runCmd
from ..io import printNLog

getffprobeCmd = lambda ffprobePath, file: [
    ffprobePath,
    "-v",
    "quiet",
    "-print_format",
    "json",
    "-show_format",
    "-show_streams",
    str(file),
]


def getMetaData(ffprobePath, file):
    ffprobeCmd = getffprobeCmd(ffprobePath, file)
    cmdOut = runCmd(ffprobeCmd)
    if isinstance(cmdOut, Exception):
        return cmdOut
    metaData = jLoads(cmdOut)
    return metaData


def getParams(metaData, strm, params):
    paramDict = {}
    for param in params:
        try:
            paramDict[param] = metaData["streams"][strm][param]
        except KeyError:
            paramDict[param] = "N/A"
    return paramDict


def filterMeta(metaData, cdcType, basics, xtr=None):
    params = {}
    nbStreams = int(metaData["format"]["nb_streams"])
    for strm in range(nbStreams):
        basicMeta = getParams(
            metaData,
            strm,
            [*basics],
        )
        if basicMeta["codec_type"] == cdcType == "audio":  # audio stream
            if xtr:
                params = getParams(
                    metaData,
                    strm,
                    [*basicMeta, *xtr],
                )
            else:
                params = basicMeta
        elif basicMeta["codec_type"] == cdcType == "video":  # video stream
            if xtr:
                params = getParams(
                    metaData,
                    strm,
                    [*basicMeta, *xtr],
                )
            else:
                params = basicMeta
    try:
        params["bit_rate"] = str(round2(float(params["bit_rate"]) / 1000))
    except (KeyError, ValueError):
        pass
    return params


def getMeta(metaData, meta, cdcType):
    return filterMeta(metaData, cdcType, meta["basic"], meta[cdcType])

def getTags(metaData, tags):
    js = metaData["format"]["tags"]
    return [js.get(tag, "") for tag in tags]

formatParams = lambda params: "".join(
    [f"{param}: {value}; " for param, value in params.items()]
)


def compareDur(sourceDur, outDur, strmType, n=1):
    # < n seconds difference will trigger warning
    diff = abs(float(sourceDur) - float(outDur))
    # if diff:
    #     msg = f"\n\nINFO: Mismatched {strmType} source and output duration."
    if diff > n:
        msg = (
            f"\n********\nWARNING: Differnce between {strmType} source and output "
            f"durations({str(round2(diff))} seconds) is more than {str(n)} second(s).\n"
        )
        printNLog(msg)


