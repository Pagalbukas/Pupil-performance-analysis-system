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

class GraphingError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)

class ClientError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)

class ClientRequestError(ClientError):
    def __init__(self) -> None:
        super().__init__((
            "Prisijungiant įvyko nenumatyta prašymo klaida.\n"
            "Patikrinkite savo interneto ryšį ir bandykite dar kartą vėliau."
        ))
