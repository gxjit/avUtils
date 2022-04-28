from pathlib import Path

logFile = None


def setLogFile(lf):
    global logFile
    logFile = Path(lf)
    return logFile


getLogFile = lambda: logFile
