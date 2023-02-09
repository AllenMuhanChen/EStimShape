from __future__ import annotations

from typing import Union

"""This module contains functions for working with nested dictionaries and lists of (nested) dictionaries """


def apply_function_to_subdictionaries_values_with_keys(dictionary: Union[dict, list], keys: list, function):
    """apply function to the subdictionary that contains the specified keys
    The supplied function should take in the dictionary containing the specified keys and
    return a new dictionary"""
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


def check_condition_on_subdictionaries(dictionary: Union[dict, list], condition, boolean_to_update, *args):
    """Returns true if any of the key-value pairs satisfy the condition. The condition is a function that returns a boolean
    and has parameters: (key, value, *args)"""
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


def flatten_dictionary(dictionary: Union[dict, list], output_value_list: list, output_key_list):
    """Converts a nested dictionary into a single list of values and appends those values into output_list
    :param output_key_list:
    """
    if isinstance(dictionary, dict):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                flatten_dictionary(value, output_value_list, output_key_list)
            else:
                output_value_list.append(value)
                if output_key_list is not None:
                    output_key_list.append(key)

    elif isinstance(dictionary, list):
        for value in dictionary:
            if isinstance(value, dict) or isinstance(value, list):
                flatten_dictionary(value, output_value_list, output_key_list)
            else:
                output_value_list.append(value)
                if output_key_list is not None:
                    output_key_list.append(None)




def extract_values_with_key_into_list(dictionary: Union[dict, list], output_list: list, key: str):
    if isinstance(dictionary, dict):
        for k, value in dictionary.items():
            if isinstance(value, dict):
                extract_values_with_key_into_list(value, output_list, key)
            else:
                if k == key:
                    output_list.append(value)

    elif isinstance(dictionary, list):
        for value in dictionary:
            if isinstance(value, dict) or isinstance(value, list):
                extract_values_with_key_into_list(value, output_list, key)
            else:
                output_list.append(value)
