from argparse import ArgumentTypeError
from pathlib import Path


def checkDirPath(pth):
    pthObj = Path(pth)
    if pthObj.is_dir():
        return pthObj
    else:
        raise ArgumentTypeError("Invalid Directory path")


def checkValIn(valIn, typ, val):
    val = val.lower()
    if val in valIn:
        return typ(val)
    else:
        raise ArgumentTypeError("Invalid Value")


# change excetion type?
