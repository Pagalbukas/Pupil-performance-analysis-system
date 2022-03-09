import json
import os

from itertools import cycle
from typing import TYPE_CHECKING, Optional

class Settings:

    if TYPE_CHECKING:
        username: Optional[str]
        password: Optional[str]
        last_dir: Optional[str]
        debugging: bool

    def __init__(self, auto_load: bool = True) -> None:
        if auto_load:
            self.load()

    def _load_params(self, data: dict) -> None:
        self.username = data.get("username")
        self.password = data.get("password")
        self.last_dir = data.get("last_dir")
        self.debugging = data.get("debugging", False)

    def _serialize(self) -> str:
        return json.dumps({
            "username": self.username,
            "password": self.password,
            "last_dir": self.last_dir,
            "debugging": self.debugging
        })

    def _xor_bytes(self, data: bytes) -> bytes:
        return bytes(a ^ b for a, b in zip(data, cycle(b"tikrai-slapta")))

    def _decrypt(self, file_path) -> bytes:
        file = open(file_path, "rb")
        data = self._xor_bytes(file.read())
        file.close()
        return json.loads(data)

    def _encrypt(self, file_path) -> None:
        with open(file_path, "wb") as f:
            f.write(self._xor_bytes(str.encode(self._serialize())))

    def _create_dir(self) -> str:
        file_dir = os.path.join(os.environ["APPDATA"], "Pagalbukas-statistika")
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)
        return file_dir

    def load(self):
        data = {}
        settings_file = os.path.join(self._create_dir(), "settings")
        if os.path.exists(settings_file):
            data = self._decrypt(settings_file)
        self._load_params(data)

    def save(self):
        settings_file = os.path.join(self._create_dir(), "settings")
        self._encrypt(settings_file)
