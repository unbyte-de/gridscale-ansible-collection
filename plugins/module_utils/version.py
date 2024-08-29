def compare_version(v1: str, v2: str) -> bool:
    if isinstance(v1, str) is False:
        raise ValueError(f"v1 must be a string, not a {type(v1)}.")
    elif isinstance(v2, str) is False:
        raise ValueError(f"v1 must be a string, not a {type(v2)}.")
    # convert versions into lists
    # compare only first 3 digits
    # if version has digits less than 3, fill with 0
    v1_list: list[str] = v1.split(".")[:3]
    v1_list = v1_list[:3] + ["0"] * (3 - len(v1_list))
    v2_list: list[str] = v2.split(".")[:3]
    v2_list = v2_list[:3] + ["0"] * (3 - len(v2_list))
    # Return if v1 >= v2
    return tuple(int(d) for d in v1_list) >= tuple(int(d) for d in v2_list)
