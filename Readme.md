usage: optimizeVideo.py [-h] -d DIR [-r] [-w [WAIT]] [-rs RES] [-fr FPS] [-s SPEED]
                        [-ca CAUDIO] [-cv CVIDEO] [-qv QVIDEO] [-qa QAUDIO]

Optimize Video/Audio files by encoding to avc/hevc/aac/opus.

options:
  -h, --help            show this help message and exit
  -d DIR, --dir DIR     Directory path
  -r, --recursive       Process files recursively in all child directories.
  -w [WAIT], --wait [WAIT]
                        Wait time in seconds between each iteration, default is 10
  -rs RES, --res RES    Limit video resolution; can be 480, 540, 720, etc. (default: 720)
  -fr FPS, --fps FPS    Limit video frame rate; can be 24, 25, 30, 60, etc. (default: 30)
  -s SPEED, --speed SPEED
                        Video encoding speed; avc & hevc: slow, medium and fast etc; av1:
                        0-13/6-8 (lower is slower and efficient). (defaults:: avc: slow,
                        hevc: medium and av1: 8)
  -ca CAUDIO, --cAudio CAUDIO
                        Select an audio codec from AAC-LC: "aac", HE-AAC/AAC-LC with SBR:
                        "he" , Opus: "opus" and copy audio: "cp". (default: he)
  -cv CVIDEO, --cVideo CVIDEO
                        Select a video codec from HEVC/H265: "hevc", AVC/H264: "avc" and
                        AV1: "av1". (default: hevc)
  -qv QVIDEO, --qVideo QVIDEO
                        Video Quality(CRF) setting; avc:23:17-28, hevc:28:20-32 and
                        av1:50:0-63, lower crf means less compression. (defaults:: avc:
                        28, hevc: 32 and av1: 52)
  -qa QAUDIO, --qAudio QAUDIO
                        Audio Quality/bitrate in kbps; (defaults:: opus: 48, he: 56 and
                        aac: 72)
