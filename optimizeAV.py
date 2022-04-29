import argparse
import atexit
from functools import partial
from pathlib import Path
from shlex import join as shJoin
from statistics import fmean
from sys import version_info
from time import time

from modules.ffUtils.ffmpeg import getffmpegCmd, optsVideo, selectCodec
from modules.ffUtils.ffprobe import compareDur, formatParams, getMeta, getMetaData
from modules.fs import cleanUp, getFileList, getFileListRec, makeTargetDirs
from modules.helpers import (
    bytesToMB,
    dynWait,
    fileDTime,
    nothingExit,
    round2,
    secsToHMS,
)
from modules.io import printNLog, reportErr, startMsg, statusInfo, waitN
from modules.os import checkPaths, runCmd
from modules.pkgState import setLogFile
from modules.cli import checkDirPath, checkValIn


def parseArgs():

    aCodec = partial(checkValIn, ["opus", "he", "aac", "ac"], str)
    vCodec = partial(checkValIn, ["avc", "hevc", "av1", "vn", "vc"], str)

    parser = argparse.ArgumentParser(
        description="Optimize Video/Audio files by encoding to avc/hevc/aac/opus."
    )
    parser.add_argument(
        "-d", "--dir", required=True, help="Directory path", type=checkDirPath
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
        ', Opus: "opus" and copy: "ac". (default: he)',
    )
    parser.add_argument(
        "-cv",
        "--cVideo",
        default="hevc",
        type=vCodec,
        help='Select a video codec from HEVC/H265: "hevc", AVC/H264: "avc" , '
        'AV1: "av1", copy: "vc" and no video: "vn". (default: hevc)',
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


pargs = parseArgs()

ffprobePath, ffmpegPath = checkPaths(
    {
        "ffprobe": r"C:\ffmpeg\bin\ffprobe.exe",
        "ffmpeg": r"C:\ffmpeg\bin\ffmpeg.exe",
    }
)

noVideo = True if pargs.cVideo == "vn" else False

if noVideo:

    formats = [".flac", ".wav", ".m4a", ".mp3", ".mp4"]

    outExt = ".opus" if pargs.cAudio == "opus" else ".m4a"
else:

    formats = [".mp4", ".mov", ".mkv", ".avi"]

    outExt = ".mp4"

meta = {
    "basic": ["codec_type", "codec_name", "profile", "duration", "bit_rate"],
    "audio": ["channels", "sample_rate"],
    "video": ["height", "r_frame_rate"],
}

dirPath = pargs.dir.resolve()

if pargs.recursive:
    getFilePaths = getFileListRec
else:
    getFilePaths = getFileList

fileList = getFilePaths(dirPath, formats)

if not fileList:
    nothingExit()

outDir = makeTargetDirs(dirPath, [f"out-{outExt[1:]}"])[0]
tmpFile = outDir.joinpath(f"tmp-{fileDTime()}{outExt}")
setLogFile(outDir.joinpath(f"{dirPath.stem}.log"))

if pargs.recursive:
    if version_info >= (3, 9):
        fileList = [f for f in fileList if not f.is_relative_to(outDir)]
    else:
        fileList = [f for f in fileList if not (str(outDir) in str(f))]

outFileList = getFilePaths(outDir, [outExt])

atexit.register(cleanUp, [outDir], [tmpFile])

startMsg()

getMetaDataP = partial(getMetaData, ffprobePath)

totalTime, inSizes, outSizes, lengths = ([] for i in range(4))

for idx, file in enumerate(fileList):

    outFile = Path(outDir.joinpath(file.relative_to(dirPath).with_suffix(outExt)))

    statusInfoP = partial(statusInfo, idx=f"{idx+1}/{len(fileList)}", file=file)

    if any(outFileList) and outFile in outFileList:
        statusInfoP("Skipping")
        continue

    statusInfoP("Processing")

    metaData = getMetaDataP(file)
    if isinstance(metaData, Exception):
        reportErr(metaData)
        break

    getMetaP = partial(getMeta, metaData, meta)

    adoInParams = getMetaP("audio")

    ov = []

    if not noVideo:
        vdoInParams = getMetaP("video")

        if not pargs.cVideo == "vc":
            ov = optsVideo(
                vdoInParams["height"], vdoInParams["r_frame_rate"], pargs.res, pargs.fps
            )

    ca = selectCodec(pargs.cAudio, pargs.qAudio)
    cv = selectCodec(pargs.cVideo, pargs.qVideo, pargs.speed)
    cmd = getffmpegCmd(ffmpegPath, file, tmpFile, ca, cv, ov)

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

    metaData = getMetaDataP(outFile)
    if isinstance(metaData, Exception):
        reportErr(metaData)
        break

    getMetaP = partial(getMeta, metaData, meta)

    if not noVideo:

        vdoOutParams = getMetaP("video")

        printNLog(
            f"\nVideo Input:: {formatParams(vdoInParams)}"
            f"\nVideo Output:: {formatParams(vdoOutParams)}"
        )

        compareDur(
            vdoInParams["duration"],
            vdoOutParams["duration"],
            vdoInParams["codec_type"],
        )

    adoOutParams = getMetaP("audio")

    printNLog(
        f"\nAudio Input:: {formatParams(adoInParams)}"
        f"\nAudio Output:: {formatParams(adoOutParams)}"
    )

    compareDur(
        adoInParams["duration"],
        adoOutParams["duration"],
        adoInParams["codec_type"],
    )

    inSize = bytesToMB(file.stat().st_size)
    outSize = bytesToMB(outFile.stat().st_size)
    length = float(adoInParams["duration"])
    inSizes.append(inSize)
    outSizes.append(outSize)
    lengths.append(length)
    inSum, inMean, = sum(inSizes), fmean(inSizes)  # fmt: skip
    outSum, outMean = sum(outSizes), fmean(outSizes)

    printNLog(
        "\n"
        f"\nProcessed: {secsToHMS(length)} in: {secsToHMS(timeTaken)}"
        f" at speed: x{round2(length/timeTaken)}"
        f"\nInput file size: {inSize} MB, "
        f"Output file size: {outSize} MB"
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
        f"{secsToHMS(fmean(totalTime) * (len(fileList) - (idx+1)))}"
        f" at average speed: x{round2(fmean(lengths)/fmean(totalTime))}"
    )

    if idx + 1 == len(fileList):
        continue

    if pargs.wait:
        waitN(int(pargs.wait))
    else:
        waitN(int(dynWait(timeTaken)))


# H264(x264): medium efficiency, fast encoding, widespread support
# > H265(x265): high efficiency, slow encoding, medicore support
# > VP9(libvpx): high efficiency, slower encoding, less support than h265,
# very little support on apple stuff
# > AV1(svt-av1): higher efficiency, slow encoding, little to no support,
# encoders/decoders are not stable/established enough yet
# libopus > fdk_aac SBR > fdk_aac >= vorbis > libmp3lame > ffmpeg aac
