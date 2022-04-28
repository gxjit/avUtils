import argparse
import atexit
from fractions import Fraction
from functools import partial
from json import loads as jLoads
from pathlib import Path
from shlex import join as shJoin
from statistics import fmean
from sys import exit, version_info
from time import time

from modules.fs import getFileList, getFileListRec, makeTargetDirs, rmEmptyDirs
from modules.helpers import (
    bytesToMB,
    dynWait,
    fileDTime,
    now,
    defVal,
    round2,
    secsToHMS,
    noNoneCast,
)
from modules.io import printNLog, reportErr, statusInfo, waitN
from modules.os import checkPaths, runCmd
from modules.pkgState import setLogFile


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

    aCodec = partial(checkCodec, codecs=["opus", "he", "aac", "cp"])
    vCodec = partial(checkCodec, codecs=["avc", "hevc", "av1"])

    parser = argparse.ArgumentParser(
        description="Optimize Video/Audio files by encoding to avc/hevc/aac/opus."
    )
    parser.add_argument(
        "-d", "--dir", required=True, help="Directory path", type=dirPath
    )
    parser.add_argument(
        "-r",
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
        "-rs",
        "--res",
        default=720,
        type=int,
        help="Limit video resolution; can be 480, 540, 720, etc. (default: 720)",
    )
    parser.add_argument(
        "-fr",
        "--fps",
        default=30,
        type=int,
        help="Limit video frame rate; can be 24, 25, 30, 60, etc. (default: 30)",
    )
    parser.add_argument(
        "-s",
        "--speed",
        default=None,
        type=str,
        help="Video encoding speed; avc & hevc: slow, medium and fast etc; "
        "av1: 0-13/6-8 (lower is slower and efficient). "
        "(defaults:: avc: slow, hevc: medium and av1: 8)",
    )
    parser.add_argument(
        "-ca",
        "--cAudio",
        default="he",
        type=aCodec,
        help='Select an audio codec from AAC-LC: "aac", HE-AAC/AAC-LC with SBR: "he" '
        ', Opus: "opus" and copy audio: "cp". (default: he)',
    )
    parser.add_argument(
        "-cv",
        "--cVideo",
        default="hevc",
        type=vCodec,
        help='Select a video codec from HEVC/H265: "hevc", AVC/H264: "avc" and '
        'AV1: "av1". (default: hevc)',
    )
    parser.add_argument(
        "-qv",
        "--qVideo",
        default=None,
        type=int,
        help="Video Quality(CRF) setting; avc:23:17-28, hevc:28:20-32 and av1:50:0-63, "
        "lower crf means less compression. (defaults:: avc: 28, hevc: 32 and av1: 52)",
    )
    parser.add_argument(
        "-qa",
        "--qAudio",
        default=None,
        type=int,
        help="Audio Quality/bitrate in kbps; (defaults:: opus: 48, he: 56 and aac: 72)",
    )
    return parser.parse_args()


def cleanExit(outDir, tmpFile):
    print("\nPerforming exit cleanup...")
    if tmpFile.exists():
        tmpFile.unlink()
    rmEmptyDirs([outDir])


def nothingExit():
    print("Nothing to do.")
    exit()


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

getffmpegCmd = lambda ffmpegPath, file, outFile, cv, ca, ov: [
    ffmpegPath,
    "-i",
    str(file),
    "-c:v",
    *cv,
    *ov,
    "-c:a",
    *ca,
    "-loglevel",
    "warning",  # info
    str(outFile),
]


def selectCodec(codec, quality=None, speed=None):

    # quality = None if quality is None else str(quality)
    quality = noNoneCast(str, quality)

    if codec == "aac":
        cdc = [
            "libfdk_aac",
            "-b:a",
            defVal("72k", quality),
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
            defVal("56k", quality),
            "-afterburner",
            "1",
        ]
        # mono he-aac encodes are reported as stereo by ffmpeg/ffprobe
        # https://trac.ffmpeg.org/ticket/3361

    elif codec == "opus":
        cdc = [
            "libopus",
            "-b:a",
            defVal("48k", quality),
            "-vbr",
            "on",
            "-compression_level",
            "10",
            "-frame_duration",
            "20",
        ]

    elif codec == "cp":
        cdc = ["copy"]

    elif codec == "avc":
        cdc = [
            "libx264",
            "-preset:v",
            "slow" if speed is None else speed,
            "-crf",
            defVal("28", quality),
            "-profile:v",
            "high",
        ]

    elif codec == "hevc":
        cdc = [
            "libx265",
            "-preset:v",
            "medium" if speed is None else speed,
            "-crf",
            defVal("32", quality),
        ]

    elif codec == "av1":
        cdc = [
            "libsvtav1",
            "-crf",
            defVal("52", quality),
            "-preset:v",
            "8" if speed is None else speed,
            "-g",
            "240",
        ]  # -g fps*10

    # elif codec == "vp9":
    #     cdc = [
    #         "libvpx-vp9",
    #         "-crf",
    #         "42" if quality is None else quality,
    #         "-b:v",
    #         "0",
    #         "-quality",
    #         "good",
    #         "-speed",
    #         "3" if speed is None else speed,
    #         "-g",  # fps*10
    #         "240",
    #         "-tile-columns",
    #         "1",  # 1 for 720p, 2 for 1080p, 3 for 2160p etc
    #         "-row-mt",
    #         "1",
    #     ]  # prefer 2 pass for HQ vp9 encodes

    return cdc


def optsVideo(fps, res):
    opts = [
        "-pix_fmt",
        "yuv420p",
        "-vsync",
        "vfr",
        "-r",
        str(fps),
    ]
    if res is not None:
        opts = [*opts, "-vf", f"scale=-2:{str(res)}"]
    return opts


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


def compareDur(sourceDur, outDur, strmType):
    diff = abs(float(sourceDur) - float(outDur))
    n = 1  # < n seconds difference will trigger warning
    # if diff:
    #     msg = f"\n\nINFO: Mismatched {strmType} source and output duration."
    if diff > n:
        msg = (
            f"\n********\nWARNING: Differnce between {strmType} source and output "
            f"durations({str(round2(diff))} seconds) is more than {str(n)} second(s).\n"
        )
        printNLog(msg)


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
    getFilePaths = getFileListRec
else:
    getFilePaths = getFileList

fileList = getFilePaths(dirPath, formats)


if not fileList:
    nothingExit()


(outDir,) = makeTargetDirs(dirPath, [f"out-{outExt}"])
tmpFile = outDir.joinpath(f"tmp-{fileDTime()}.{outExt}")
setLogFile(outDir.joinpath(f"{dirPath.stem}.log"))

if pargs.recursive:
    if version_info >= (3, 9):
        fileList = [f for f in fileList if not f.is_relative_to(outDir)]
    else:
        fileList = [f for f in fileList if not (str(outDir) in str(f))]

outFileList = getFilePaths(outDir, [f".{outExt}"])

atexit.register(cleanExit, outDir, tmpFile)

printNLog(f"\n\n====== {Path(__file__).stem} Started at {now()} ======\n")

totalTime, inSizes, outSizes, lengths = ([] for i in range(4))

for idx, file in enumerate(fileList):

    outFile = Path(outDir.joinpath(file.relative_to(dirPath).with_suffix(f".{outExt}")))

    statusInfoP = partial(statusInfo, idx=f"{idx+1}/{len(fileList)}", file=file)

    if any(outFileList) and outFile in outFileList:
        statusInfoP("Skipping")
        continue

    statusInfoP("Processing")

    metaData = getMetaData(ffprobePath, file)
    if isinstance(metaData, Exception):
        break

    vdoInParams, adoInParams = getMeta(metaData, "video"), getMeta(metaData, "audio")

    res = pargs.res
    if int(vdoInParams["height"]) < res:
        res = None

    fps = pargs.fps
    if float(Fraction(vdoInParams["r_frame_rate"])) < fps:
        fps = vdoInParams["r_frame_rate"]

    ca = selectCodec(pargs.cAudio, pargs.qAudio)
    cv = selectCodec(pargs.cVideo, pargs.qVideo, pargs.speed)
    ov = optsVideo(fps, res)
    cmd = getffmpegCmd(ffmpegPath, file, tmpFile, cv, ca, ov)

    printNLog(f"\n{shJoin(cmd)}")
    strtTime = time()
    cmdOut = runCmd(cmd)
    if isinstance(cmdOut, Exception):
        reportErr(cmdOut)
        break
    timeTaken = time() - strtTime
    totalTime.append(timeTaken)

    printNLog(cmdOut)
    if pargs.recursive and not outFile.parent.exists():
        outFile.parent.mkdir(parents=True)

    tmpFile.rename(outFile)

    statusInfoP("Processed")

    metaData = getMetaData(ffprobePath, outFile)
    if isinstance(metaData, Exception):
        break

    vdoOutParams, adoOutParams = getMeta(metaData, "video"), getMeta(metaData, "audio")

    printNLog(
        f"\nInput:: {formatParams(vdoInParams)}\n{formatParams(adoInParams)}"
        f"\nOutput:: {formatParams(vdoOutParams)}\n{formatParams(adoOutParams)}"
    )

    compareDur(
        vdoInParams["duration"],
        vdoOutParams["duration"],
        vdoInParams["codec_type"],
    )
    compareDur(
        adoInParams["duration"],
        adoOutParams["duration"],
        adoInParams["codec_type"],
    )

    inSize = bytesToMB(file.stat().st_size)
    outSize = bytesToMB(outFile.stat().st_size)
    length = float(vdoInParams["duration"])
    inSizes.append(inSize)
    outSizes.append(outSize)
    lengths.append(length)
    inSum, inMean, = sum(inSizes), fmean(inSizes)  # fmt: skip
    outSum, outMean = sum(outSizes), fmean(outSizes)

    printNLog(
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


# H264: medium efficiency, fast encoding, widespread support
# > H265: high efficiency, slow encoding, medicore support
# > VP9: high efficiency, slower encoding, less support than h265,
# very little support on apple stuff
# > AV1: higher efficiency, slow encoding, little to no support
# libopus > fdk_aac SBR > fdk_aac >= vorbis > libmp3lame > ffmpeg aac
