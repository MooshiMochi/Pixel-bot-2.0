import random


def sec_to_time(seconds:int):
        try:
            seconds = int(seconds)
        except ValueError:
            return f"ValueError: {seconds} is not convertible to INTEGER"

        m, sec = divmod(seconds, 60)
        h, m = divmod(m, 60)

        msg = f"{sec} second"
        msg += "s." if sec != 1 else "."

        msg = f"{m} minutes " + msg if m and m != 1 else f"{m} minute " + msg if m else msg

        msg = f"{h} hours " + msg if h and h != 1 else f"{h} hour " + msg if h else msg

        return msg

print(sec_to_time(1361315))

# 87 hard questions

def scramblestring(string: str):
    result = []
    for word in string.split(" "):
        result.append("".join(random.sample(word, len(word))))

    return " ".join(result)

print(scramblestring("Hello"))

from datetime import datetime

print(datetime.utcnow().timestamp())
print(datetime.utcnow().timestamp())
