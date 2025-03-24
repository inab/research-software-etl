import json

def log_types(data):
    '''write in file the types of instances with more than one type'''
    several_types_tools = 0
    with open('data/types.txt', 'w') as f:
        for key, value in data.items():
            unique_types = set()
            for inst in value["instances"]:
                type_ = inst["data"].get("type", "undefined")
                if type_ not in ["", None, "undefined"]:
                    unique_types.add(inst["data"].get("type", "undefined"))
            if len(unique_types) > 1:
                f.write(f"-----------------\n{key}\n")
                for unique_type in unique_types:
                    f.write(f"\t- {unique_type}\n")
                several_types_tools += 1
    
    print(f"Tools with more than one type: {several_types_tools}")


def log_names(data):
    '''write in file the names of instances with more than one name'''
    several_names_tools = 0
    with open('data/names.txt', 'w') as f:
        for key, value in data.items():
            unique_names = set()
            for inst in value["instances"]:
                name_ = inst["data"].get("name", "undefined")
                if name_ not in ["", None, "undefined"]:
                    unique_names.add(inst["data"].get("name", "undefined"))
            if len(unique_names) > 1:
                f.write(f"-----------------\n{key}\n")
                for unique_name in unique_names:
                    f.write(f"\t- {unique_name}\n")
                several_names_tools += 1
    print(f"Tools with more than one name (case sensitive): {several_names_tools}")


def log_names_case_insensitive(data):
    '''write in file the names of instances with more than one name'''
    several_names_tools = 0
    for key, value in data.items():
        unique_names = set()
        for inst in value["instances"]:
            name_ = inst["data"].get("name", "undefined")
            if name_ not in ["", None, "undefined"]:
                unique_names.add(inst["data"].get("name", "undefined").lower())
        if len(unique_names) > 1:
            several_names_tools += 1
    print(f"Tools with more than one name (case-insensitive): {several_names_tools}")
    

if __name__ == "__main__":
    input_file = "data/grouped.json"

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f'There are {len(data)} tools groups in the dataset.')

    log_types(data)
    log_names(data)
    log_names_case_insensitive(data)

    with open('data/shared_links.json', 'r') as f:
        shared_links = json.load(f)

    number_of_groups = 0
    unique_name_groups = 0
    for link in shared_links:
        unique_names = set()
        for tool in shared_links[link]:
            name = tool.split('/')[0]
            unique_names.add(name)

        if len(unique_names) == 1:
            unique_name_groups += 1
            number_of_groups += len(shared_links[link])
    
    print(f"Groups with shared links and same name: {unique_name_groups}")
    print(f"Number of tools in these same name groups: {number_of_groups}")

        