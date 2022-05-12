class ParsingError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)

class InvalidResourceTypeError(ParsingError):
    def __init__(self) -> None:
        super().__init__("Pateiktas ataskaitos tipas yra netinkamas!")

class InconclusiveResourceError(ParsingError):
    def __init__(self) -> None:
        super().__init__((
            "Trūksta duomenų, suvestinė yra nepilna. "
            "Įsitikinkite, ar pusmečio/trimestro įvertinimai yra teisingi!"
        ))
