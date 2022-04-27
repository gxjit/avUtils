from time import sleep


def waitN(n):
    print("\n")
    for i in reversed(range(0, n)):
        print(
            f"Waiting for {str(i).zfill(3)} seconds.", end="\r", flush=True
        )  # padding for clearing digits left from multi digit coundown
        sleep(1)
    print("\r")


def getInput():  # add exit() on choice == e
    print("\nPress Enter Key continue or input 'e' to exit.")
    try:
        choice = input("\n> ")
        if choice not in ["e", ""]:
            raise ValueError

    except ValueError:
        print("\nInvalid input.")
        choice = getInput()

    return choice


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
