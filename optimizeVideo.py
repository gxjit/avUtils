import argparse
import atexit
from datetime import datetime, timedelta
from fractions import Fraction
from functools import partial
from json import loads as jLoads
from os import mkdir
from pathlib import Path
from shlex import join as shJoin
from shutil import which as shWhich
from statistics import fmean
from subprocess import run
from sys import exit, version_info
from time import sleep, time
from traceback import format_exc
from itertools import chain


def parseArgs():
    def dirPath(pth):
        pthObj = Path(pth)
        if pthObj.is_dir():
            return pthObj
        else:
            raise argparse.ArgumentTypeError("Invalid Directory path")

    def checkCodec(cdc, codecs):
        cdc = cdc.lower()
        if cdc in codecs:
            return cdc
        else:
            raise argparse.ArgumentTypeError("Invalid Codec")

    aCodec = partial(checkCodec, codecs=["opus", "he", "aac"])
    vCodec = partial(checkCodec, codecs=["avc", "hevc"])

    parser = argparse.ArgumentParser(
        description="Optimize Video/Audio files by encoding to avc/hevc/aac/opus."
    )
    parser.add_argument(
        "-d", "--dir", required=True, help="Directory path", type=dirPath
    )
    parser.add_argument(
        "-re",
        "--recursive",
        action="store_true",
        help="Process files recursively in all child directories.",
    )
    parser.add_argument(
        "-w",
        "--wait",
        nargs="?",
        default=None,
        const=10,
        type=int,
        help="Wait time in seconds between each iteration, default is 10",
    )
    parser.add_argument(
        "-r",
        "--res",
        default=540,
        type=int,
        help="Limit video resolution; can be 360, 480, 540, 720, etc.(default: 540)",
    )
    parser.add_argument(
        "-f",
        "--fps",
        default=24,
        type=int,
        help="Limit video frame rate; can be 24, 25, 30, 60, etc.(default: 24)",
    )
    parser.add_argument(
        "-qv",
        "--qVideo",
        default=None,
        type=str,
        help="Video Quality(CRF) setting; avc:23:17-28, hevc:28:20-32; "
        "lower means less compression, (defaults:: avc: 28, hevc: 30)",
    )
    parser.add_argument(
        "-s",
        "--speed",
        default=None,
        type=str,
        help="Encoding speed; can be slow, medium, fast, veryfast, etc."
        "(defaults:: avc: slow, hevc: medium)(use ultrafast for testing)",
    )
    parser.add_argument(
        "-ca",
        "--cAudio",
        default="opus",
        type=aCodec,
        help='Select an audio codec from AAC LC: "aac", HE-AAC: "he" and Opus: "opus".'
        "(default: opus)",
    )
    parser.add_argument(
        "-cv",
        "--cVideo",
        default="hevc",
        type=vCodec,
        help='Select a video codec from HEVC/H265: "hevc" and AVC/H264: "avc".'
        "(default: hevc)",
    )
    return parser.parse_args()


fileDTime = lambda: datetime.now().strftime("%y%m%d-%H%M%S")

secsToHMS = lambda sec: str(timedelta(seconds=sec)).split(".")[0]

round2 = partial(round, ndigits=2)

bytesToMB = lambda bytes: round2(bytes / float(1 << 20))

now = lambda: str(datetime.now()).split(".")[0]

timeNow = lambda: str(datetime.now().time()).split(".")[0]

dynWait = lambda secs, n=7.5: secs / n


def waitN(n):
    print("\n")
    for i in reversed(range(0, n)):
        print(
            f"Waiting for {str(i).zfill(3)} seconds.", end="\r", flush=True
        )  # padding for clearing digits left from multi digit coundown
        sleep(1)
    print("\r")


def makeTargetDirs(dirPath, names):
    retNames = []
    for name in names:
        newPath = dirPath.joinpath(name)
        if not newPath.exists():
            mkdir(newPath)
        retNames.append(newPath)
    return retNames


def checkPaths(paths):
    retPaths = []
    for path, absPath in paths.items():
        retPath = shWhich(path)
        if isinstance(retPath, type(None)) and not isinstance(absPath, type(None)):
            retPaths.append(absPath)
        else:
            retPaths.append(retPath)
    return retPaths


def getInput():
    print("\nPress Enter Key continue or input 'e' to exit.")
    try:
        choice = input("\n> ")
        if choice not in ["e", ""]:
            raise ValueError

    except ValueError:
        print("\nInvalid input.")
        choice = getInput()

    return choice


def getFileSizes(fileList):
    totalSize = 0
    for file in fileList:
        totalSize += file.stat().st_size
    return totalSize


def rmEmptyDirs(paths):
    for path in paths:
        if not list(path.iterdir()):
            path.rmdir()


def appendFile(file, contents):
    # if not file.exists():
    #     file.touch()
    with open(file, "a") as f:
        f.write(str(contents))


def readFile(file):
    with open(file, "r") as f:
        return f.read()


def printNLog(logFile, msg):
    print(str(msg))
    appendFile(logFile, msg)


def swr(currFile, logFile, exp=None):
    printNLog(
        logFile,
        f"\n------\nERROR: Something went wrong while processing following file."
        f"\n > {str(currFile.name)}.",
    )
    if exp and exp.stderr:
        printNLog(logFile, f"\nStdErr: {exp.stderr}\nReturn Code: {exp.returncode}")
    if exp:
        printNLog(
            logFile,
            f"\nException:\n{exp}\n\nAdditional Details:\n{format_exc()}",
        )


def runCmd(cmd, currFile, logFile):
    try:
        cmdOut = run(cmd, check=True, capture_output=True, text=True)
        cmdOut = cmdOut.stdout
    except Exception as callErr:
        swr(currFile, logFile, callErr)
        return callErr
    return cmdOut


getFileList = lambda dirPath, exts: [
    f for f in dirPath.iterdir() if f.is_file() and f.suffix.lower() in exts
]

getFileListRec = lambda dirPath, exts: list(
    chain.from_iterable([dirPath.rglob(f"*{ext}") for ext in exts])
)

getffprobeCmd = lambda ffprobePath, file: [
    ffprobePath,
    "-v",
    "quiet",
    "-print_format",
    "json",
    # "-show_format",
    "-show_streams",
    str(file),
]

getffmpegCmd = lambda ffmpegPath, file, outFile, cv, ca, res, fps: [
    ffmpegPath,
    "-i",
    str(file),
    "-c:v",
    *cv,
    "-pix_fmt",
    "yuv420p",
    "-vsync",
    "vfr",
    "-r",
    str(fps),
    "-vf",
    f"scale=-1:{str(res)}",
    "-c:a",
    *ca,
    "-loglevel",
    "warning",  # info
    str(outFile),
]


def selectCodec(codec, quality=None, speed=None):

    if codec == "aac":
        cdc = [
            "libfdk_aac",
            "-b:a",
            "72k" if quality is None else quality,
            "-afterburner",
            "1",
            "-cutoff",
            "15500",
            "-ar",
            "32000",
        ]
        # fdk_aac defaults to a LPF cutoff around 14k
        # https://wiki.hydrogenaud.io/index.php?title=Fraunhofer_FDK_AAC#Bandwidth

    elif codec == "he":
        cdc = [
            "libfdk_aac",
            "-profile:a",
            "aac_he",
            "-b:a",
            "56k" if quality is None else quality,
            "-afterburner",
            "1",
        ]
        # mono he-aac encodes are reported as stereo
        # https://trac.ffmpeg.org/ticket/3361

    elif codec == "opus":
        cdc = [
            "libopus",
            "-b:a",
            "48k" if quality is None else quality,
            "-vbr",
            "on",
            "-compression_level",
            "10",
            "-frame_duration",
            "20",
        ]

    elif codec == "avc":
        cdc = [
            "libx264",
            "-preset:v",
            "slow" if speed is None else speed,
            "-crf",
            "28" if quality is None else quality,
            "-profile:v",
            "high",
        ]

    elif codec == "hevc":
        cdc = [
            "libx265",
            "-preset:v",
            "medium" if speed is None else speed,
            "-crf",
            "30" if quality is None else quality,
        ]

    # elif codec == "av1":
    #     cdc = [
    #         "libsvtav1",
    #         "-crf",
    #         "52" if quality is None else quality,
    #         "-preset:v",
    #         "8" if speed is None else speed,
    #     ] # -g 240 or keyint based on fps for svt-av1

    return cdc


def getMetaData(ffprobePath, currFile, logFile):
    ffprobeCmd = getffprobeCmd(ffprobePath, currFile)
    cmdOut = runCmd(ffprobeCmd, currFile, logFile)
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


def getMeta(metaData, cType):
    params = {}
    for strm in range(2):
        basicMeta = getParams(
            metaData,
            strm,
            ["codec_type", "codec_name", "profile", "duration", "bit_rate"],
        )
        if basicMeta["codec_type"] == cType == "audio":  # audio stream
            params = getParams(
                metaData,
                strm,
                [*basicMeta, "channels", "sample_rate"],
            )
        elif basicMeta["codec_type"] == cType == "video":  # video stream
            params = getParams(
                metaData,
                strm,
                [*basicMeta, "height", "r_frame_rate"],
            )
    try:
        params["bit_rate"] = str(round2(float(params["bit_rate"]) / 1000))
    except KeyError:
        pass
    return params


formatParams = lambda params: "".join(
    [f"{param}: {value}; " for param, value in params.items()]
)


def statusInfo(status, idx, file, logFile):
    printNLog(
        logFile,
        f"\n----------------\n{status} file {idx}:" f" {str(file.name)} at {timeNow()}",
    )


def cleanExit(outDir, tmpFile):
    print("\nPerforming exit cleanup...")
    if tmpFile.exists():
        tmpFile.unlink()
    rmEmptyDirs([outDir])


def nothingExit():
    print("Nothing to do.")
    exit()


def compareDur(sourceDur, outDur, strmType, logFile):
    diff = abs(float(sourceDur) - float(outDur))
    n = 1  # < n seconds difference will trigger warning
    # if diff:
    #     msg = f"\n\nINFO: Mismatched {strmType} source and output duration."
    if diff > n:
        msg = (
            f"\n********\nWARNING: Differnce between {strmType} source and output "
            f"durations({str(round2(diff))} seconds) is more than {str(n)} second(s).\n"
        )
        printNLog(logFile, msg)


ffprobePath, ffmpegPath = checkPaths(
    {
        "ffprobe": r"C:\ffmpeg\bin\ffprobe.exe",
        "ffmpeg": r"C:\ffmpeg\bin\ffmpeg.exe",
    }
)

formats = [".mp4", ".avi", ".mov", ".mkv"]

outExt = "mp4"

pargs = parseArgs()

dirPath = pargs.dir.resolve()


if pargs.recursive:
    getFileList = getFileListRec

fileList = getFileList(dirPath, formats)


if not fileList:
    nothingExit()


(outDir,) = makeTargetDirs(dirPath, [f"out-{outExt}"])
tmpFile = outDir.joinpath(f"tmp-{fileDTime()}.{outExt}")
logFile = outDir.joinpath(f"{dirPath.stem}.log")
printNLogP = partial(printNLog, logFile)

if pargs.recursive:
    if version_info >= (3, 9):
        fileList = [f for f in fileList if not f.is_relative_to(outDir)]
    fileList = [f for f in fileList if not (str(outDir) in str(f))]

outFileList = getFileList(outDir, [f".{outExt}"])

atexit.register(cleanExit, outDir, tmpFile)

printNLogP(f"\n\n====== {Path(__file__).stem} Started at {now()} ======\n")

totalTime, inSizes, outSizes, lengths = ([] for i in range(4))

for idx, file in enumerate(fileList):

    outFile = Path(outDir.joinpath(file.relative_to(dirPath).with_suffix(f".{outExt}")))

    statusInfoP = partial(
        statusInfo, idx=f"{idx+1}/{len(fileList)}", file=file, logFile=logFile
    )

    if any(outFileList) and outFile in outFileList:
        statusInfoP("Skipping")
        continue

    statusInfoP("Processing")

    metaData = getMetaData(ffprobePath, file, logFile)
    if isinstance(metaData, Exception):
        break

    vdoInParams, adoInParams = getMeta(metaData, "video"), getMeta(metaData, "audio")

    res = pargs.res
    if int(vdoInParams["height"]) < res:
        res = int(vdoInParams["height"])

    fps = pargs.fps
    if float(Fraction(vdoInParams["r_frame_rate"])) < fps:
        fps = vdoInParams["r_frame_rate"]

    ca = selectCodec(pargs.cAudio)
    cv = selectCodec(pargs.cVideo, quality=pargs.qVideo, speed=pargs.speed)
    cmd = getffmpegCmd(ffmpegPath, file, tmpFile, cv, ca, res, fps)

    printNLog(logFile, f"\n{shJoin(cmd)}")
    strtTime = time()
    cmdOut = runCmd(cmd, file, logFile)
    if isinstance(cmdOut, Exception):
        break
    timeTaken = time() - strtTime
    totalTime.append(timeTaken)

    printNLogP(cmdOut)
    if pargs.recursive and not outFile.parent.exists():
        outFile.parent.mkdir(parents=True)

    tmpFile.rename(outFile)

    statusInfoP("Processed")

    metaData = getMetaData(ffprobePath, outFile, logFile)
    if isinstance(metaData, Exception):
        break

    vdoOutParams, adoOutParams = getMeta(metaData, "video"), getMeta(metaData, "audio")

    printNLogP(
        f"\nInput:: {formatParams(vdoInParams)}\n{formatParams(adoInParams)}"
        f"\nOutput:: {formatParams(vdoOutParams)}\n{formatParams(adoOutParams)}"
    )

    compareDur(
        vdoInParams["duration"],
        vdoOutParams["duration"],
        vdoInParams["codec_type"],
        logFile,
    )
    compareDur(
        adoInParams["duration"],
        adoOutParams["duration"],
        adoInParams["codec_type"],
        logFile,
    )

    inSize = bytesToMB(file.stat().st_size)
    outSize = bytesToMB(outFile.stat().st_size)
    length = float(vdoInParams["duration"])
    inSizes.append(inSize)
    outSizes.append(outSize)
    lengths.append(length)
    inSum, inMean, = sum(inSizes), fmean(inSizes)  # fmt: skip
    outSum, outMean = sum(outSizes), fmean(outSizes)

    printNLogP(
        f"\n\nInput file size: {inSize} MB, "
        f"Output file size: {outSize} MB"
        f"\nProcessed {secsToHMS(length)} in: {secsToHMS(timeTaken)}, "
        f"Processing Speed: x{round2(length/timeTaken)}"
        f"\nTotal Input Size: {round2(inSum)} MB, "
        f"Average Input Size: {round2(inMean)} MB"
        f"\nTotal Output Size: {round2(outSum)} MB, "
        f"Average Output Size: {round2(outMean)} MB"
        "\nTotal Size Reduction: "
        f"{round2(((inSum-outSum)/inSum)*100)}%, "
        "Average Size Reduction: "
        f"{round2(((inMean-outMean)/inMean)*100)}%"
        f"\nTotal Processing Time: {secsToHMS(sum(totalTime))}, "
        f"Average Processing Time: {secsToHMS(fmean(totalTime))}"
        "\nEstimated time: "
        f"{secsToHMS(fmean(totalTime) * (len(fileList) - (idx+1)))}, "
        f"Average Speed: x{round2(fmean(lengths)/fmean(totalTime))}"
    )

    if idx + 1 == len(fileList):
        continue

    if pargs.wait:
        waitN(int(pargs.wait))
    else:
        waitN(int(dynWait(timeTaken)))
        # choice = getInput()
        # if choice == "e":
        #     break


# H264: medium efficiency, fast encoding, widespread support
# > H265: high efficiency, slow encoding, medicore support
# > AV1: higher efficiency, slow encoding, little to no support
# libopus > fdk_aac SBR > fdk_aac >= vorbis > libmp3lame > ffmpeg aac
