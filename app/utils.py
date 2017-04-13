import datetime

def getColumnNameFromIndex(index):

    quo = index/26
    rem = index%26

    pre = ""
    post = ""

    if quo != 0:
        pre = chr(quo+64)

    post = chr(rem+65)

    return pre+post


def stringToDatetime(text):

    return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")

def datetimeToString(date):

    return date.strftime("%Y-%m-%dT%H:%M:%SZ")
