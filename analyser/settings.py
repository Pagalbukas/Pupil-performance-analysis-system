import json
import os

from itertools import cycle
from typing import TYPE_CHECKING, List, Optional

from analyser.files import get_data_dir

class Settings:

    if TYPE_CHECKING:
        username: Optional[str]
        last_dir: Optional[str]
        debugging: bool
        hide_names: bool
        flip_names: bool
        last_ver: Optional[List[int]]
        outlined_values: bool
        corner_legend: bool
        styled_colouring: bool
        mano_dienynas_url: str

    def __init__(self, auto_load: bool = True) -> None:
        if auto_load:
            self.load()

    def _load_params(self, data: dict) -> None:
        self.username = data.get("username")
        self.last_dir = data.get("last_dir")
        self.debugging = data.get("debugging", False)
        self.hide_names = data.get("hide_names", False)
        self.flip_names = data.get("flip_names", False)
        self.last_ver = data.get("last_ver")
        self.outlined_values = data.get("outlined_values", True)
        self.corner_legend = data.get("corner_legend", True)
        self.styled_colouring = data.get("styled_colouring", True)
        self.mano_dienynas_url = data.get("mano_dienynas_url", "https://www.manodienynas.lt")

    def _serialize(self) -> str:
        return json.dumps({
            "username": self.username,
            "last_dir": self.last_dir,
            "debugging": self.debugging,
            "hide_names": self.hide_names,
            "flip_names": self.flip_names,
            "last_ver": self.last_ver,
            "outlined_values": self.outlined_values,
            "corner_legend": self.corner_legend,
            "styled_colouring": self.styled_colouring,
            "mano_dienynas_url": self.mano_dienynas_url
        })

    def _xor_bytes(self, data: bytes) -> bytes:
        return bytes(a ^ b for a, b in zip(data, cycle(b"tikrai-slapta")))

    def _decrypt(self, file_path) -> dict:
        file = open(file_path, "rb")
        data = self._xor_bytes(file.read())
        file.close()
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {}

    def _encrypt(self, file_path) -> None:
        with open(file_path, "wb") as f:
            f.write(self._xor_bytes(str.encode(self._serialize())))

    def load(self):
        data = {}
        settings_file = os.path.join(get_data_dir(), "settings")
        if os.path.exists(settings_file):
            data = self._decrypt(settings_file)
        self._load_params(data)

    def save(self):
        settings_file = os.path.join(get_data_dir(), "settings")
        self._encrypt(settings_file)
