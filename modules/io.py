from sys import exit
from time import sleep
from traceback import format_exc

from .fs import appendFile
from .helpers import timeNow
from .pkgState import getLogFile


def printNLog(msg):
    msg = str(msg)
    logFile = getLogFile()
    print(msg)
    if logFile:
        appendFile(logFile, msg)


def reportErr(exp=None):
    printNLog("\n------\nERROR: Something went wrong.")
    if exp and exp.stderr:
        printNLog(f"\nStdErr: {exp.stderr}\nReturn Code: {exp.returncode}")
    if exp:
        printNLog(
            f"\nException:\n{exp}\n\nAdditional Details:\n{format_exc()}",
        )


def statusInfo(status, idx, file):
    printNLog(
        f"\n----------------\n{status} file {idx}:" f" {str(file.name)} at {timeNow()}",
    )


def waitN(n):
    print("\n")
    for i in reversed(range(0, n)):
        print(
            f"Waiting for {str(i).zfill(3)} seconds.", end="\r", flush=True
        )  # padding for clearing digits left from multi digit coundown
        sleep(1)
    print("\r")


def getInput():
    print("\nPress Enter Key continue or input 'e' to exit.")
    try:
        choice = input("\n> ")
        if choice not in ["e", ""]:
            raise ValueError

    except ValueError:
        print("\nInvalid input.")
        choice = getInput()

    if choice == "e":
        exit()


def areYouSure():
    print("\nAre you sure you want to continue? (y/n)")
    try:
        choice = str(input("\n> ")).lower()
        if choice not in ["y", "n"]:
            raise ValueError
    except ValueError:
        print("\nInvalid input.")
        areYouSure()

    if choice == "y":
        return
    else:
        exit()


# def nothingExit():
#     print("Nothing to do.")
#     exit()
