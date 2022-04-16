import openpyxl
import xlrd

from typing import TYPE_CHECKING, Union

xlrdSheet: TypeAlias = xlrd.sheet.Sheet
openpyxlSheet: TypeAlias = openpyxl.worksheet._read_only.ReadOnlyWorksheet

class UnifiedSheet:
    """A class which implements a unified Sheet object."""

    def __init__(self, sheet: Union[xlrdSheet, openpyxlSheet]) -> None:
        self._sheet = sheet

    @property
    def xlrd(self) -> bool:
        """Returns true if input sheet instance was of xlrd."""
        return isinstance(self._sheet, xlrdSheet)

    def get_cell(self, column: int, row: int) -> Union[None, str, int, float]:
        """Returns cell value at specified column and row.

        The arguments are flipped than the default implementations."""
        if self.xlrd:
            return self._sheet.cell_value(row - 1, column - 1) or None
        return self._sheet.cell(row, column).value

class SpreadsheetReader:
    """A class which implements a unified Excel spreadsheet reader."""

    if TYPE_CHECKING:
        file_path: str

    def __init__(self, original_path: str) -> None:
        self.file_path = original_path

        if self.has_archive_header:
            self._f = open(self.file_path, "rb")
            doc = openpyxl.load_workbook(self._f, data_only=True, read_only=True)
        else:
            doc = xlrd.open_workbook(self.file_path, ignore_workbook_corruption=True)

        self._doc = doc

        # Initialize a unified sheet object to keep my nerves in check
        if isinstance(doc, xlrd.book.Book):
            self.sheet = UnifiedSheet(doc.sheet_by_index(0))
        else:
            assert isinstance(doc, openpyxl.Workbook)
            self.sheet = UnifiedSheet(doc.worksheets[0])

    @property
    def has_archive_header(self) -> bool:
        """Returns True if file contains an archive header.
        Usually infers that the file is of the new, Open XML variety."""
        with open(self.file_path, "rb") as f:
            return f.read(4) == b'PK\x03\x04'

    def close(self) -> None:
        """Closes the reader."""
        if self.sheet.xlrd:
            self._doc.release_resources()
        else:
            if hasattr(self, "_f"):
                self._f.close()
            self._doc.close()
        del self._doc
