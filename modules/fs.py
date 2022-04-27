from .helpers import flatten
from unicodedata import normalize
from re import sub

getFileList = lambda dirPath, exts: [
    f for f in dirPath.iterdir() if f.is_file() and f.suffix.lower() in exts
]

getFileListRec = lambda dirPath, exts: list(
    flatten([dirPath.rglob(f"*{ext}") for ext in exts])
)


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


getFileSizes = lambda fileList: sum([file.stat().st_size for file in fileList])


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


def slugifyNReplace(value, replace={}, keepSpace=True):
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


# def getFileSizes(fileList):
#     totalSize = 0
#     for file in fileList:
#         totalSize += file.stat().st_size
#     return totalSize
