import time


def display_time(sec):
    if sec < 0:
        return time.strftime("- %H h:%M mn.", time.gmtime(abs(sec)))
    return time.strftime("+ %H h:%M mn.", time.gmtime(sec))
