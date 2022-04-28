from functools import partial
from pathlib import Path
from re import sub
from unicodedata import normalize

from .helpers import nSort

getFileList = lambda dirPath, exts: [
    f for f in dirPath.iterdir() if f.is_file() and f.suffix.lower() in exts
]

getFileListAll = lambda dirPath: [f for f in dirPath.iterdir() if f.is_file()]


getFileListRec = lambda dirPath, exts: [
    f for f in dirPath.rglob("*.*") if f.suffix.lower() in exts
]

getFileListAllRec = lambda dirPath: dirPath.rglob("*")

getDirList = lambda dirPath: [x for x in dirPath.iterdir() if x.is_dir()]

pathifyList = lambda paths: [Path(x) for x in paths]

stringifyPaths = lambda paths: [str(x) for x in paths]


def cleanUp(emptyDirs, files):
    rmEmptyDirs(emptyDirs)
    rmFiles(files)


def appendFile(file, contents):
    # if not file.exists():
    #     file.touch()
    with open(file, "a") as f:
        f.write(str(contents))


def makeTargetDirs(dirPath, names):
    retNames = []
    for name in names:
        newPath = dirPath.joinpath(name)
        if not newPath.exists():
            newPath.mkdir()
        retNames.append(newPath)
    return retNames


def rmEmptyDirs(paths):
    for path in paths:
        if not list(path.iterdir()):
            path.rmdir()


def rmFiles(paths):
    for path in paths:
        if path.exists():
            path.unlink()


getFileSizes = lambda fileList: sum([file.stat().st_size for file in fileList])

nPathSort = partial(sorted, key=lambda k: nSort(str(k.stem)))
# non recursive

deepPathSort = partial(sorted, key=lambda k: nSort(str(f"{k.parent}/{k.name}")))
# one lvl deep


def readFile(file):  # or Path.read_text()
    with open(file, "r") as f:
        return f.read()


def slugify(value, allow_unicode=False):
    """
    Adapted from django.utils.text.slugify
    https://docs.djangoproject.com/en/3.0/_modules/django/utils/text/#slugify
    """
    value = str(value)
    if allow_unicode:
        value = normalize("NFKC", value)
    else:
        value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = sub(r"[^\w\s-]", "", value).strip().lower()
    return sub(r"[-\s]+", "-", value)


def slugifyCustom(value, replace={}, keepSpace=True):
    """
    Adapted from django.utils.text.slugify
    https://docs.djangoproject.com/en/3.0/_modules/django/utils/text/#slugify
    """
    replace.update({"[": "(", "]": ")", ":": "_"})
    value = str(value)
    value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")

    for k, v in replace.items():
        value = value.replace(k, v)
    value = sub(r"[^\w\s)(_-]", "", value).strip()

    if keepSpace:
        value = sub(r"[\s]+", " ", value)
    else:
        value = sub(r"[-\s]+", "-", value)
    return value


# getFileListRec = lambda dirPath, exts: list(
#     flatten([dirPath.rglob(f"*{ext}") for ext in exts])
# )

# getDirSize, cleanExit

# def getFileSizes(fileList):
#     totalSize = 0
#     for file in fileList:
#         totalSize += file.stat().st_size
#     return totalSize

# nPathSort = lambda (paths): sorted(paths, key=lambda k: nSort(str(k.stem)))
