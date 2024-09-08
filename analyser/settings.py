import json
import os

from itertools import cycle
from typing import List, Optional, TypedDict

from analyser.files import get_data_dir

SECRET_KEY = b"tikrai-slapta"

class SettingDict(TypedDict):
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

class Settings:

    def __init__(self) -> None:
        self.username: Optional[str] = None
        self.last_dir: Optional[str] = None
        self.debugging: bool = False
        self.hide_names: bool = False
        self.flip_names: bool = False
        self.last_ver: Optional[List[int]] = None
        self.outlined_values: bool = True
        self.corner_legend: bool = True
        self.styled_colouring: bool = True
        self.mano_dienynas_url: str = "https://www.manodienynas.lt"

    def _deserialize(self, data: SettingDict) -> None:
        self.username = data["username"]
        self.last_dir = data["last_dir"]
        self.debugging = data["debugging"]
        self.hide_names = data["hide_names"]
        self.flip_names = data["flip_names"]
        self.last_ver = data["last_ver"]
        self.outlined_values = data["outlined_values"]
        self.corner_legend = data["corner_legend"]
        self.styled_colouring = data["styled_colouring"]
        self.mano_dienynas_url = data["mano_dienynas_url"]

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
        """Utility method to XOR bytes using a secret key."""
        return bytes(a ^ b for a, b in zip(data, cycle(SECRET_KEY)))

    def _load_encrypted_content(self, file_path: str) -> SettingDict:
        """Loads encrypted settings from the specified file."""
        file = open(file_path, "rb")
        data = self._xor_bytes(file.read())
        file.close()
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {}

    def _save_encrypted_content(self, file_path: str) -> None:
        """Encrypts the current settings by XOR'ing and save them to file."""
        with open(file_path, "wb") as f:
            _ = f.write(self._xor_bytes(str.encode(self._serialize())))

    def load(self):
        settings_file = os.path.join(get_data_dir(), "settings")
        if os.path.exists(settings_file):
            data = self._load_encrypted_content(settings_file)
            self._deserialize(data)

    def save(self):
        settings_file = os.path.join(get_data_dir(), "settings")
        self._save_encrypted_content(settings_file)
