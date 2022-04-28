from pathlib import Path

logFile = None


def setLogFile(lf):
    logFile = Path(lf)
    print(logFile, "logfile set")
    return logFile
