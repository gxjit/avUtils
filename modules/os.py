from shutil import which as shWhich


def checkPaths(paths):  # check abs paths too?
    retPaths = []
    for path, absPath in paths.items():
        retPath = shWhich(path)
        if isinstance(retPath, type(None)) and not isinstance(absPath, type(None)):
            retPaths.append(absPath)
        else:
            retPaths.append(retPath)
    return retPaths
