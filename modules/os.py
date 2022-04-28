from shutil import which as shWhich
from subprocess import run


def runCmd(cmd):
    try:
        cmdOut = run(cmd, check=True, capture_output=True, text=True)
        cmdOut = cmdOut.stdout
    except Exception as callErr:
        return callErr
    return cmdOut


def checkPaths(paths):  # check abs paths too?
    retPaths = []
    for path, absPath in paths.items():
        retPath = shWhich(path)
        if isinstance(retPath, type(None)) and not isinstance(absPath, type(None)):
            retPaths.append(absPath)
        else:
            retPaths.append(retPath)
    return retPaths
