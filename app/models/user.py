from dataclasses import dataclass


@dataclass
class User:
    id: int | None = None
    email: str = ""
    password: str = ""
