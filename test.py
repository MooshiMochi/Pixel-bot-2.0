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

Question_to_edit = "How are you?"
Difficulty = "easy"
Answer = "I am well!"
First_Incorrect_Option = "I am not well!"
Second_Incorrect_Option = "I am fantastic!"

text = (
    f"Question data changed to:\n"
    f"> Question: {Question_to_edit}\n"
    f"> Difficulty: {Difficulty.capitalize()}\n"
    f"> Correct Answer: {Answer}\n"
    f"> First Incorrect Answer: {First_Incorrect_Option}"
)

text += f"\n> Second Incorrect Answer: {Second_Incorrect_Option}" if Second_Incorrect_Option else ""

print(text)
