from ..helpers import noNoneCast, defVal

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
    "warning",  # or info
    str(outFile),
]


def selectCodec(codec, quality=None, speed=None):

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
            defVal("slow", speed),
            "-crf",
            defVal("28", quality),
            "-profile:v",
            "high",
        ]

    elif codec == "hevc":
        cdc = [
            "libx265",
            "-preset:v",
            defVal("medium", speed),
            "-crf",
            defVal("32", quality),
        ]

    elif codec == "av1":
        cdc = [
            "libsvtav1",
            "-crf",
            defVal("52", quality),
            "-preset:v",
            defVal("8", speed),
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


def optsVideo(fps, res):  # fps only when specified?
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


#

# res = pargs.res
# if int(vdoInParams["height"]) < res:
#     res = None

# fps = pargs.fps
# if float(Fraction(vdoInParams["r_frame_rate"])) < fps:
#     fps = vdoInParams["r_frame_rate"] # or None

# ca = selectCodec(pargs.cAudio, pargs.qAudio)
# cv = selectCodec(pargs.cVideo, pargs.qVideo, pargs.speed)
# ov = optsVideo(fps, res)
