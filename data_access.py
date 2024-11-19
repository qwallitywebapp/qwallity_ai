import random
import json
from jsonpath_ng import parse


#methods
def assign_code(email, sec_code):
    jsonpath_email = parse("data[*][email]")

    with open("email_code.py", "r") as f:
        old_data = f.read()
        old_data = json.loads(old_data)
        email_list = jsonpath_email.find(old_data)

        for i in range(0, len(email_list)):
            if email == email_list[i].value:
                jsonpath_code = parse(f"data[{i}][code]")
                code = jsonpath_code.find(old_data)
                for j in range(0, len(code)):
                    if sec_code == code[j].value:
                        print(code[j].value)
                        old_data["data"][i]["access"] = 1
                return old_data["data"][i]["access"]

    with open("email_code.py", "w") as f:
        f.write(json.dumps(old_data, indent=4))
