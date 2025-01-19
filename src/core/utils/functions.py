import base64
from enum import Enum
from typing import Type, Optional, Any
import requests


def get_enum_from_value(value: Any, enum_class: Type[Enum]) -> Enum:
    """
    Function that given the value of an enum object and the enum class. It gets you the actual enum object
    :param value: Value that wants to get matched against an enum class
    :param enum_class: Enum class

    :return: Enum. The Enum object
    """
    for member in enum_class:
        if member.value == value:
            return member
    raise ValueError(f"No matching enum for value: {value}")


def get_base64_from_url(url: str):
    """
    Fetches the content from a URL and returns its Base64-encoded bytes.

    :param: url (str): The URL to fetch the content from.

    :returns: str: Base64-encoded string of the content.
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an error for HTTP issues
        base64_encoded = base64.b64encode(response.content).decode("utf-8")
        return base64_encoded

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None


def is_function(function_name: str, obj: Optional[object] = None) -> bool:
    """
    Checks if a function exists in the global scope or within a given object.

    :param: function_name (str): The name of the function to check.
    :param: obj (optional): The object (class or instance) to search for the function.

    :returns: bool: True if the function exists and is callable, False otherwise.
    """

    return (
        function_name in globals() and callable(globals()[function_name])
    ) or (
        obj is not None
        and hasattr(obj, function_name)
        and callable(getattr(obj, function_name, None))
    )


def get_function_by_name(
    function_name: str, obj: Optional[object] = None
) -> object:
    """
    Retrieves a function by name from the global scope or within a given object.

    :param: function_name (str): The name of the function to retrieve.
    :param: obj (optional): The object (class or instance) to search for the function.

    :returns: function: The callable function object if found.

    :raise: ValueError: If the function is not found or is not callable.
    """

    if function_name in globals() and callable(globals()[function_name]):
        return globals()[function_name]
    elif (
        obj
        and hasattr(obj, function_name)
        and callable(getattr(obj, function_name, None))
    ):
        return getattr(obj, function_name)
    raise ValueError(
        f"Function '{function_name}' is not defined or not callable in the given object."
    )


def boldify_unicode(text: str) -> str:
    """
    Converts text enclosed within `**` to Unicode bold characters.

    :param: text (str): The input string containing text enclosed within `**`.

    :returns: str: The input string with text within `**` converted to Unicode bold characters.
    """
    import re

    def to_unicode_bold(s: str) -> str:
        bold_chars = {
            "a": "\U0001d41a",
            "b": "\U0001d41b",
            "c": "\U0001d41c",
            "d": "\U0001d41d",
            "e": "\U0001d41e",
            "f": "\U0001d41f",
            "g": "\U0001d420",
            "h": "\U0001d421",
            "i": "\U0001d422",
            "j": "\U0001d423",
            "k": "\U0001d424",
            "l": "\U0001d425",
            "m": "\U0001d426",
            "n": "\U0001d427",
            "o": "\U0001d428",
            "p": "\U0001d429",
            "q": "\U0001d42a",
            "r": "\U0001d42b",
            "s": "\U0001d42c",
            "t": "\U0001d42d",
            "u": "\U0001d42e",
            "v": "\U0001d42f",
            "w": "\U0001d430",
            "x": "\U0001d431",
            "y": "\U0001d432",
            "z": "\U0001d433",
            "A": "\U0001d400",
            "B": "\U0001d401",
            "C": "\U0001d402",
            "D": "\U0001d403",
            "E": "\U0001d404",
            "F": "\U0001d405",
            "G": "\U0001d406",
            "H": "\U0001d407",
            "I": "\U0001d408",
            "J": "\U0001d409",
            "K": "\U0001d40a",
            "L": "\U0001d40b",
            "M": "\U0001d40c",
            "N": "\U0001d40d",
            "O": "\U0001d40e",
            "P": "\U0001d40f",
            "Q": "\U0001d410",
            "R": "\U0001d411",
            "S": "\U0001d412",
            "T": "\U0001d413",
            "U": "\U0001d414",
            "V": "\U0001d415",
            "W": "\U0001d416",
            "X": "\U0001d417",
            "Y": "\U0001d418",
            "Z": "\U0001d419",
            "0": "\U0001d7ce",
            "1": "\U0001d7cf",
            "2": "\U0001d7d0",
            "3": "\U0001d7d1",
            "4": "\U0001d7d2",
            "5": "\U0001d7d3",
            "6": "\U0001d7d4",
            "7": "\U0001d7d5",
            "8": "\U0001d7d6",
            "9": "\U0001d7d7",
        }
        return "".join(bold_chars.get(char, char) for char in s)

    def replacer(match: re.Match) -> str:
        return to_unicode_bold(match.group(1))

    return re.sub(r"\*\*(.*?)\*\*", replacer, text)
