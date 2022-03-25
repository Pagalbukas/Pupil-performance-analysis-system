import datetime

from typing import TYPE_CHECKING, List, Optional, Union

from reading import SpreadsheetReader
from models import Student, Subject
from summaries import ClassSemesterReportSummary, ClassPeriodReportSummary

class ParsingError(Exception):

    def __init__(self, message: str) -> None:
        super().__init__(message)

class BaseParser:

    if TYPE_CHECKING:
        _average_col: int
        _last_student_row: int

    def __init__(self, file_path: str) -> None:
        self._reader = SpreadsheetReader(file_path)
        self._sheet = self._reader.sheet

        self._average_col = None
        self._last_student_row = None

    @property
    def average_mark_column(self) -> int:
        return self._find_average_column()

    @property
    def last_student_row(self) -> int:
        return self._find_last_student_row()

    def _find_average_column(self) -> int:
        """Returns the column for the average mark column in the spreadsheet."""
        raise NotImplementedError

    def _find_last_student_row(self) -> int:
        """Returns a row of the last student in the spreadsheet."""
        raise NotImplementedError

    def close(self) -> None:
        """Closes the reader. No operations should be performed afterwards."""
        self._reader.close()

    def cell(self, col: int, row: int) -> Optional[Union[str, int, float]]:
        """Boilerplate function for returning value at the specified column and row of the cell."""
        return self._sheet.get_cell(col, row)

    def create_summary(self) -> None:
        """Attempts to create a Summary object.

        May raise an exception."""
        raise NotImplementedError


class PupilSemesterReportParser(BaseParser):

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path)
        # Obtain term start, end and type
        raw_term_value = self.cell(9, 2)
        # Laikotarpis: 2020-2021m.m.II pusmetis -> 2020-2021m.m.II pusmetis
        raw_term_value = raw_term_value.split(": ")[1].strip() # Split here because the word 'Periodas' could also be used
        term_value = raw_term_value.split("-")

        self.term_start = int(term_value[0])
        self.term_end = int(term_value[1][:4])
        self.type = term_value[1][8:]

        self._subject_name_cache = {}

    def _find_average_column(self) -> int:
        """Returns the column for the average mark column."""
        if self._average_col is None:
            off_col = 2
            while True:
                # Row of 'Pasiekimų lygiai'
                value = self.cell(off_col + 2, 3)
                if value is not None:
                    break
                off_col += 1
            self._average_col = off_col + 1
        return self._average_col

    def _find_last_student_row(self) -> int:
        """Returns a row of the last student."""
        if self._last_student_row is None:
            off_row = 13
            while True:
                value = self.cell(1, off_row + 1)
                # Encounter string 'Dalyko vidurkis' in a list of digits
                if isinstance(value, str):
                    break
                off_row += 1
            self._last_student_row = off_row
        return self._last_student_row

    def get_grade_name(self) -> str:
        """Returns the name of the grade."""
        return self.cell(9, 1)[7:]

    def get_student_data(self, fetch_subjects: bool = True) -> List[Student]:
        """Returns a list of student objects."""
        students = []
        for row in range(14, self.last_student_row + 1):
            offset = row - 14
            students.append(Student(
                self.cell(2, row),
                self.get_student_subjects(offset) if fetch_subjects else [],
                self.get_student_average(offset)
            ))
        return students

    def get_student_subjects(self, student_idx: int) -> List[Subject]:
        """Returns a list of student's subject objects."""
        offset = student_idx + 14
        subjects = []
        for col in range(3, self.average_mark_column):
            # Cache subject names as reading a cell with openpyxl is expensive op
            name = self._subject_name_cache.get(col)
            if name is None:
                name = self.cell(col, 4)
                self._subject_name_cache[col] = name
            subjects.append(Subject(
                name,
                self.cell(col, offset)
            ))
        return subjects

    def get_student_average(self, student_idx: int) -> Optional[float]:
        """Returns student's average mark."""
        value = self.cell(self.average_mark_column, student_idx + 14)
        if value == 0:
            return None
        return value

    def create_summary(self, fetch_subjects: bool = True) -> ClassSemesterReportSummary:
        """Attempts to create a Summary object.

        May raise an exception."""

        # Check whether Excel file is of correct type
        # TODO: investigate future proofing
        if self.cell(1, 2) != "Ataskaita: Mokinių pasiekimų ir lankomumo suvestinė":
            raise ParsingError("Pateiktas ataskaitos tipas yra netinkamas")

        # Check whether group average is a zero, if it is, throw parsing error due to incomplete file
        if self.cell(self.average_mark_column, self.last_student_row + 1) == 0:
            raise ParsingError((
                "Trūksta duomenų, suvestinė yra nepilna."
                " Įsitikinkite ar pusmetis/trimestras yra tikrai ir pilnai išvestas!"
            ))

        return ClassSemesterReportSummary(
            self.get_grade_name(),
            self.type,
            (self.term_start, self.term_end),
            self.get_student_data(fetch_subjects)
        )

class PupilPeriodicReportParser(BaseParser):

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path)
        term_value = self.cell(7, 1).split(" - ")
        self.term_start = datetime.datetime.strptime(term_value[0], "%Y-%m-%d")
        self.term_end = datetime.datetime.strptime(term_value[1], "%Y-%m-%d")

        self._subject_name_cache = {}

    def _find_average_column(self) -> int:
        """Returns the column for the average mark column."""
        if self._average_col is None:
            off_col = 4
            while True:
                # Row of 'Pasiekimų lygiai'
                value = self.cell(off_col + 1, 2)
                if value is not None:
                    break
                off_col += 1
            self._average_col = off_col + 1
        return self._average_col

    def _find_last_student_row(self) -> int:
        """Returns a row of the last student."""
        if self._last_student_row is None:
            off_row = 13
            while True:
                value = self.cell(1, off_row + 1)
                # Encounter string 'Dalyko vidurkis' in a list of digits
                if isinstance(value, str):
                    break
                off_row += 1
            self._last_student_row = off_row
        return self._last_student_row

    def get_grade_name(self) -> str:
        """Returns the name of the grade."""
        return self.cell(5, 1)[7:-2] # Remove comma

    def get_student_data(self, fetch_subjects: bool = True) -> List[Student]:
        """Returns a list of student objects."""
        students = []
        for row in range(12, self.last_student_row + 1):
            students.append(Student(
                self.cell(2, row),
                self.get_student_subjects(row) if fetch_subjects else [],
                self.get_student_average(row)
            ))
        return students

    def get_student_subjects(self, student_row: int) -> List[Subject]:
        """Returns a list of student's subject objects."""
        subjects = []
        for col in range(4, self.average_mark_column):
            # Cache subject names as reading a cell with openpyxl is expensive op
            name = self._subject_name_cache.get(col)
            if name is None:
                name = self.cell(col, 3)
                self._subject_name_cache[col] = name
            subjects.append(Subject(
                name,
                self.cell(col, student_row)
            ))
        return subjects

    def get_student_average(self, student_row: int) -> Optional[float]:
        """Returns student's average mark."""
        value = self.cell(self.average_mark_column, student_row)
        if value == 0:
            return None
        return value

    def create_summary(self, fetch_subjects: bool = True) -> ClassPeriodReportSummary:
        """Attempts to create a Summary object.

        May raise an exception."""

        # Check whether Excel file is of correct type
        # TODO: investigate future proofing
        if self.cell(1, 1)[:-1] != "Ataskaita: Mokinių vidurkių suvestinė":
            raise ParsingError("Pateiktas ataskaitos tipas yra netinkamas")

        # Check whether group average is a zero, if it is, throw parsing error due to incomplete file
        if self.cell(self.average_mark_column, self.last_student_row + 1) == 0:
            raise ParsingError((
                "Trūksta duomenų, suvestinė yra nepilna."
                " Įsitikinkite ar pusmetis/trimestras yra tikrai ir pilnai išvestas!"
            ))

        return ClassPeriodReportSummary(
            self.get_grade_name(),
            (self.term_start, self.term_end),
            self.get_student_data(fetch_subjects)
        )
