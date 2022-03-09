from typing import List

class ConsoleUtils:
    ERROR = '\033[91m'
    HEADER = '\033[95m'
    WARNING = '\033[93m'
    END = '\033[0m'

    def __init__(self) -> None:
        pass

    def format_str(string: List[str]):
        return '\n'.join(string)

    @staticmethod
    def print(*values):
        print(*values)

    @staticmethod
    def default(*text: str):
        ConsoleUtils.print('\n'.join(text))

    @staticmethod
    def warn(*text: str):
        ConsoleUtils.print(ConsoleUtils.WARNING + '\n'.join(text) + ConsoleUtils.END)

    @staticmethod
    def info(*text: str):
        ConsoleUtils.print(ConsoleUtils.HEADER + '\n'.join(text) + ConsoleUtils.END)

    @staticmethod
    def error(*text: str):
        ConsoleUtils.print(ConsoleUtils.ERROR + '\n'.join(text) + ConsoleUtils.END)

    @staticmethod
    def parse_error(file: str, message: str):
        ConsoleUtils.error(f"Nevertinamas '{file}': {message}")
