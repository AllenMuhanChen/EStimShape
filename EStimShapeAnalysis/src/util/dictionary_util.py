from __future__ import annotations


def apply_function_to_subdictionaries_values_with_keys(dictionary, keys, function):
    """apply function to all values of subdictionaries with specified keys
    The supplied function should take in the dictionary containing the specified keys and
    return a dictionary"""
    if isinstance(dictionary, dict):
        if set(keys).issubset(dictionary.keys()):
            dictionary = function(dictionary)
        else:
            for key, value in dictionary.items():
                dictionary[key] = apply_function_to_subdictionaries_values_with_keys(value, keys, function)
    elif isinstance(dictionary, list):
        for index, item in enumerate(dictionary):
            dictionary[index] = apply_function_to_subdictionaries_values_with_keys(item, keys, function)
    return dictionary


def check_condition_on_subdictionaries(dictionary: dict, condition, boolean_to_update, *args):
    """Returns true if any of the subdictionaries satisfy the condition"""
    if isinstance(dictionary, dict):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                if check_condition_on_subdictionaries(value, condition, boolean_to_update, *args):
                    return True
            else:
                if condition(key, value, *args):
                    return True

    elif isinstance(dictionary, list):
        for item in dictionary:
            if check_condition_on_subdictionaries(item, condition, boolean_to_update, *args):
                return True


def flatten_dictionary(dictionary: dict, point: list):
    if isinstance(dictionary, dict):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                flatten_dictionary(value, point)
            else:
                point.append(value)
    elif isinstance(dictionary, list):
        for value in dictionary:
            if isinstance(value, dict):
                flatten_dictionary(value, point)
            else:
                point.append(value)


def extract_values_with_key_into_list(dictionary: dict, output_list: list[float], key: str):
    if isinstance(dictionary, dict):
        for k, value in dictionary.items():
            if isinstance(value, dict):
                extract_values_with_key_into_list(value, output_list, key)
            else:
                if k == key:
                    output_list.append(value)

    elif isinstance(dictionary, output_list):
        for value in dictionary:
            if isinstance(value, dict):
                extract_values_with_key_into_list(value, output_list, key)
            else:
                output_list.append(value)