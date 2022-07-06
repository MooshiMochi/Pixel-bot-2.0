# import random
# import os


# def sec_to_time(seconds:int):
#         try:
#             seconds = int(seconds)
#         except ValueError:
#             return f"ValueError: {seconds} is not convertible to INTEGER"

#         m, sec = divmod(seconds, 60)
#         h, m = divmod(m, 60)

#         msg = f"{sec} second"
#         msg += "s." if sec != 1 else "."

#         msg = f"{m} minutes " + msg if m and m != 1 else f"{m} minute " + msg if m else msg

#         msg = f"{h} hours " + msg if h and h != 1 else f"{h} hour " + msg if h else msg

#         return msg

# # print(sec_to_time(1361315))

# # 87 hard questions

# def scramblestring(string: str):
#     result = []
#     for word in string.split(" "):
#         result.append("".join(random.sample(word, len(word))))

#     return " ".join(result)

# # print(scramblestring("Hello"))

# from datetime import datetime

# # print(datetime.utcnow().timestamp())
# # print(datetime.utcnow().timestamp())

# import random

# st = "abcdefghijklmnopqrstuvwxyz"
# print("".join(sorted(random.sample(st, len(st)))) == st)


# import requests

# headers = {"Authorization": os.getenv("BOAT_TOKEN"),
#                    'Accept': 'application/json'}

# # data = requests.patch(f"https://unbelievaboat.com/api/v1/guilds/865870663038271489/users/383287544336613385",
# #                                         headers=headers,
# #                                         json={"bank": -138_824, "reason": "Removnig testing funds"})


# # data = requests.patch(f"https://unbelievaboat.com/api/v1/guilds/865870663038271489/users/695182217692839966",
# #                                         headers=headers,
# #                                         json={"bank": -7_999_998_960_265, "reason": "Robbed testing funds"})

# # resp = data.json()
# # print(resp)

# time = "2022/24/05 12:34"
# # time = "2022/"+time
# scheduled_time = datetime.strptime(time, "%Y/%d/%m %H:%M")
# print(scheduled_time)

# from random import sample

# users = [1, 2, 3, 4, 5]

# winners = 3

# print(sample(users, winners))


import json
import pprint

with open("data/leaderboards_copy.json", "r") as f:
    data = json.loads(json.load(f))

pprint.pprint(data)