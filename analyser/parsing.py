import datetime
import os
import timeit
import logging

from typing import TYPE_CHECKING, Dict, List, Optional, Union

from analyser.errors import InconclusiveResourceError, InvalidResourceTypeError, ParsingError
from analyser.reading import SpreadsheetReader
from analyser.models import Attendance, Mark, UnifiedPupil, UnifiedSubject
from analyser.summaries import ClassSemesterReportSummary, ClassPeriodReportSummary

logger = logging.getLogger("analizatorius")

class BaseParser:

    if TYPE_CHECKING:
        _average_col: Optional[int]
        _last_pupil_row: Optional[int]
        _attendance_col: Optional[int]

    def __init__(self, file_path: str) -> None:
        self._reader = SpreadsheetReader(file_path)
        self._sheet = self._reader.sheet

        self._average_col = None
        self._last_pupil_row = None
        self._attendance_col = None

    @property
    def average_mark_column(self) -> int:
        """Returns the column for the average mark column in the spreadsheet."""
        return self._find_average_column()

    @property
    def last_pupil_row(self) -> int:
        """Returns a row of the last pupil in the spreadsheet."""
        return self._find_last_pupil_row()

    @property
    def attendance_column(self) -> int:
        """Returns the column for the attendance column in the spreadsheet."""
        return self._find_attendance_column()

    def _find_average_column(self) -> int:
        """Returns the column for the average mark column in the spreadsheet."""
        raise NotImplementedError

    def _find_last_pupil_row(self) -> int:
        """Returns a row of the last pupil in the spreadsheet."""
        if self._last_pupil_row is None:
            off_row = 13
            while True:
                value = self.cell(1, off_row + 1)
                # Encounter string 'Dalyko vidurkis' in a list of digits
                if isinstance(value, str):
                    break
                off_row += 1
            self._last_pupil_row = off_row
        return self._last_pupil_row

    def _find_attendance_column(self) -> int:
        """Returns the column for the attendance column in the spreadsheet."""
        raise NotImplementedError

    def get_pupil_attendance(self, pupil_row: int) -> Attendance:
        """Returns a dict containing pupil's attendance."""

        def convert_value(raw: Optional[Union[str, float, int]]) -> int:
            """Helper function to convert cell values to integers."""
            if raw is None:
                return 0
            return int(raw)

        return Attendance(
            convert_value(self.cell(self.attendance_column, pupil_row)),
            convert_value(self.cell(self.attendance_column + 1, pupil_row)),
            convert_value(self.cell(self.attendance_column + 2, pupil_row)),
            convert_value(self.cell(self.attendance_column + 3, pupil_row))
        )

    def get_pupil_average(self, pupil_row: int) -> Mark:
        """Returns pupil's average mark."""
        value = self.cell(self.average_mark_column, pupil_row)
        if value == 0:
            return Mark(None)
        return Mark(value)

    def close(self) -> None:
        """Closes the reader. No operations should be performed afterwards."""
        self._reader.close()

    def cell(self, col: int, row: int) -> Optional[Union[str, int, float]]:
        """Boilerplate function for returning value at the specified column and row of the cell."""
        return self._sheet.get_cell(col, row)

    def create_summary(self) -> Union[ClassSemesterReportSummary, ClassPeriodReportSummary]:
        """Attempts to create a Summary object.

        May raise an exception."""
        raise NotImplementedError


class PupilSemesterReportParser(BaseParser):

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path)
        # Obtain term start, end and type
        raw_term_value = self.cell(9, 2)
        # Laikotarpis: 2020-2021m.m.II pusmetis -> 2020-2021m.m.II pusmetis
        raw_term_value = raw_term_value.split(": ")[1].strip() # type: ignore # Split here because the word 'Periodas' could also be used
        term_value = raw_term_value.split("-")

        self.term_start = datetime.datetime(int(term_value[0]), 1, 1, tzinfo=datetime.timezone.utc)
        self.term_end = datetime.datetime(int(term_value[1][:4]), 1, 1, tzinfo=datetime.timezone.utc)
        self.type = term_value[1][8:]

        self._subject_name_cache: Dict[int, str] = {}

    def _find_average_column(self) -> int:
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

    def _find_attendance_column(self) -> int:
        if self._attendance_col is None:
            offset = self.average_mark_column
            string_encountered_before = False
            while True:
                value = self.cell(offset + 1, 3)
                if isinstance(value, str):
                    if string_encountered_before:
                        break
                    string_encountered_before = True
                offset += 1
            self._attendance_col = offset + 1
        return self._attendance_col

    def get_grade_name(self) -> str:
        """Returns the name of the grade."""
        return self.cell(9, 1)[7:] # type: ignore

    def get_pupil_data(self, fetch_subjects: bool = True) -> List[UnifiedPupil]:
        """Returns a list of pupil objects."""
        students = []
        for row in range(14, self.last_pupil_row + 1):
            students.append(UnifiedPupil(
                self.cell(2, row), # type: ignore
                self.get_pupil_subjects(row) if fetch_subjects else [],
                self.get_pupil_average(row),
                self.get_pupil_attendance(row)
            ))
        return students

    def get_pupil_subjects(self, offset: int) -> List[UnifiedSubject]:
        """Returns a list of pupil's subject objects."""
        subjects = []
        for col in range(3, self.average_mark_column):
            # Cache subject names as reading a cell with openpyxl is expensive op
            name = self._subject_name_cache.get(col)
            if name is None:
                name = self.cell(col, 4) # type: ignore
                assert isinstance(name, str)
                self._subject_name_cache[col] = name
            subjects.append(UnifiedSubject(
                name,
                Mark(self.cell(col, offset))
            ))
        return subjects

    def create_summary(self, fetch_subjects: bool = True) -> ClassSemesterReportSummary:
        """Attempts to create a Summary object.

        May raise an exception."""

        # Check whether Excel file is of correct type
        # TODO: investigate future proofing
        if self.cell(1, 2) != "Ataskaita: Mokinių pasiekimų ir lankomumo suvestinė":
            raise InvalidResourceTypeError

        # Check whether group average is a zero, if it is, throw parsing error due to incomplete file
        if self.cell(self.average_mark_column, self.last_pupil_row + 1) == 0:
            raise InconclusiveResourceError

        return ClassSemesterReportSummary(
            self.get_grade_name(),
            self.type,
            (self.term_start, self.term_end),
            self.get_pupil_data(fetch_subjects)
        )

class PupilPeriodicReportParser(BaseParser):

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path)
        term_value = self.cell(7, 1).split(" - ") # type: ignore
        self.term_start = datetime.datetime.strptime(term_value[0], "%Y-%m-%d")
        self.term_start = self.term_start.replace(tzinfo=datetime.timezone.utc)
        self.term_end = datetime.datetime.strptime(term_value[1], "%Y-%m-%d")
        self.term_end = self.term_end.replace(tzinfo=datetime.timezone.utc)

        self._subject_name_cache: Dict[int, str] = {}

    def _find_average_column(self) -> int:
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

    def _find_attendance_column(self) -> int:
        return self.average_mark_column + 1

    def get_grade_name(self) -> str:
        """Returns the name of the grade."""
        return self.cell(5, 1)[7:-2] # type: ignore # Remove comma

    def get_pupil_data(self, fetch_subjects: bool = True) -> List[UnifiedPupil]:
        """Returns a list of pupil objects."""
        students = []
        for row in range(12, self.last_pupil_row + 1):
            students.append(UnifiedPupil(
                self.cell(2, row), # type: ignore
                self.get_pupil_subjects(row) if fetch_subjects else [],
                self.get_pupil_average(row),
                self.get_pupil_attendance(row)
            ))
        return students

    def get_pupil_subjects(self, student_row: int) -> List[UnifiedSubject]:
        """Returns a list of pupil's subject objects."""
        subjects = []
        for col in range(4, self.average_mark_column):
            # Cache subject names as reading a cell with openpyxl is expensive op
            name = self._subject_name_cache.get(col)
            if name is None:
                name = self.cell(col, 3) # type: ignore
                assert isinstance(name, str)
                self._subject_name_cache[col] = name
            subjects.append(UnifiedSubject(
                name,
                Mark(self.cell(col, student_row))
            ))
        return subjects

    def create_summary(self, fetch_subjects: bool = True) -> ClassPeriodReportSummary:
        """Attempts to create a Summary object.

        May raise an exception."""

        # Check whether Excel file is of correct type
        # TODO: investigate future proofing
        if self.cell(1, 1)[:-1] != "Ataskaita: Mokinių vidurkių suvestinė": # type: ignore
            raise InvalidResourceTypeError

        # Check whether group average is a zero, if it is, throw parsing error due to incomplete file
        if self.cell(self.average_mark_column, self.last_pupil_row + 1) == 0:
            raise InconclusiveResourceError

        return ClassPeriodReportSummary(
            self.get_grade_name(),
            (self.term_start, self.term_end),
            self.get_pupil_data(fetch_subjects)
        )

class GroupParser(BaseParser):

    def get_pupil_attendance(self, pupil_row: int) -> Attendance:
        """Returns a dict containing pupil's attendance."""

        def convert_value(raw: Optional[Union[str, float, int]]) -> int:
            """Helper function to convert cell values to integers."""
            if raw is None:
                return 0
            return int(raw)

        return Attendance(
            convert_value(self.cell(self.attendance_column + 2, pupil_row)),
            convert_value(self.cell(self.attendance_column, pupil_row)),
            convert_value(self.cell(self.attendance_column + 1, pupil_row)),
            convert_value(self.cell(self.attendance_column + 3, pupil_row))
        )

class GroupPeriodicReportParser(GroupParser):

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path)
        term_value = self.cell(4, 3).split(" - ") # type: ignore
        self.term_start = datetime.datetime.strptime(term_value[0], "%Y-%m-%d")
        self.term_start = self.term_start.replace(tzinfo=datetime.timezone.utc)
        self.term_end = datetime.datetime.strptime(term_value[1], "%Y-%m-%d")
        self.term_end = self.term_end.replace(tzinfo=datetime.timezone.utc)

    def _find_average_column(self) -> int:
        if self._average_col is None:
            off_col = 4
            while True:
                # Row of 'Pasiekimų lygiai'
                value = self.cell(off_col + 1, 17)
                if value == "Vidurkis":
                    break
                off_col += 1
            self._average_col = off_col + 1
        return self._average_col

    def _find_last_pupil_row(self) -> int:
        """Returns a row of the last pupil in the spreadsheet."""
        if self._last_pupil_row is None:
            off_row = 17
            while True:
                value = self.cell(1, off_row + 1)
                # Encounter string 'Dalyko vidurkis' in a list of digits
                if value is None:
                    break
                off_row += 1
            self._last_pupil_row = off_row
        return self._last_pupil_row

    def _find_attendance_column(self) -> int:
        return self.average_mark_column + 1

    def get_grade_name(self) -> str:
        """Returns the name of the grade."""
        val = self.cell(4, 5)
        if isinstance(val, float):
            return str(int(val))
        if isinstance(val, int):
            return str(val)
        return val
    
    def get_group_name(self) -> str:
        """Returns the name of the subject."""
        return self.cell(4, 7)

    def get_pupil_data(self) -> List[UnifiedPupil]:
        """Returns a list of pupil objects."""
        pupils = []
        for row in range(18, self.last_pupil_row + 1):
            pupils.append(UnifiedPupil(
                self.cell(2, row), # type: ignore
                self.get_pupil_subjects(row),
                self.get_pupil_average(row),
                self.get_pupil_attendance(row)
            ))
        return pupils

    def get_pupil_subjects(self, student_row: int) -> List[UnifiedSubject]:
        """Returns a list of pupil's subject objects."""
        subjects = []
        for col in range(6, self.average_mark_column):
            # Resolve date item
            raw_date = self.cell(col, 17).replace('\n', "-")
            date = datetime.datetime.strptime(raw_date, "%m-%d")
            date = date.replace(tzinfo=datetime.timezone.utc)
            subjects.append(UnifiedSubject(
                self.get_group_name(),
                Mark(self.cell(col, student_row), date)
            ))
        return subjects

    def create_summary(self) -> ClassPeriodReportSummary:
        """Attempts to create a Summary object.

        May raise an exception."""

        # Check whether Excel file is of correct type
        # TODO: investigate future proofing
        if self.cell(1, 1) != "Ataskaita pagal grupę": # type: ignore
            raise InvalidResourceTypeError

        # Check whether group average is a zero, if it is, throw parsing error due to incomplete file
        if self.cell(self.average_mark_column, self.last_pupil_row + 1) == 0:
            raise InconclusiveResourceError

        return ClassPeriodReportSummary(
            self.get_grade_name(),
            (self.term_start, self.term_end),
            self.get_pupil_data()
        )

def parse_semester_summary_files(files: List[str]) -> List[ClassSemesterReportSummary]:
    """Generates a list of semester type summaries."""
    summaries: List[ClassSemesterReportSummary] = []
    for filename in files:
        start_time = timeit.default_timer()
        base_name = os.path.basename(filename)

        try:
            parser = PupilSemesterReportParser(filename)
            summary = parser.create_summary(fetch_subjects=True)
            parser.close()
        except ParsingError as e:
            logger.error(f"{base_name}: {e}")
            continue
        except Exception as e:
            logger.exception(f"{base_name}: {e}")
            continue

        if summary.type == "metinis":
            logger.warn(f"{base_name}: metinė ataskaita yra nevertinama")
            continue

        if any(s for s in summaries if s.representable_name == summary.representable_name):
            logger.warn(f"{base_name}: tokia ataskaita jau vieną kartą buvo pateikta ir perskaityta")
            continue

        logger.debug(f"{base_name}: skaitymas užtruko {timeit.default_timer() - start_time}s")
        summaries.append(summary)

    if len(summaries) == 0:
        logger.error("Nerasta jokių tinkamų ataskaitų, kad būtų galima kurti grafiką!")
    logger.debug(f"Pusmečių/trimestrų suvestinės sugeneruotos: {len(summaries)}")
    return summaries

def parse_periodic_summary_files(files: List[str]) -> List[ClassPeriodReportSummary]:
        """Generates a list of periodic summaries."""
        summaries: List[ClassPeriodReportSummary] = []
        for filename in files:
            start_time = timeit.default_timer()
            base_name = os.path.basename(filename)

            try:
                parser = PupilPeriodicReportParser(filename)
                summary = parser.create_summary(fetch_subjects=True)
                parser.close()
            except ParsingError as e:
                logger.error(f"{base_name}: {e}")
                continue
            except Exception as e:
                logger.exception(f"{base_name}: {e}")
                continue

            if any(s for s in summaries if s.representable_name == summary.representable_name):
                logger.warn(f"{base_name}: tokia ataskaita jau vieną kartą buvo pateikta ir perskaityta")
                continue

            if any(s.average is None for s in summary.students):
                logger.warn(f"{base_name}: bent vieno mokinio vidurkis yra ne-egzistuojantis, neskaitoma")
                continue

            logger.debug(f"{base_name}: skaitymas užtruko {timeit.default_timer() - start_time}s")
            summaries.append(summary)

        if len(summaries) == 0:
            logger.error("Nerasta jokių tinkamų ataskaitų, kad būtų galima kurti grafiką!")
        logger.debug(f"Laikotarpių suvestinės sugeneruotos: {len(summaries)}")
        return summaries

def parse_group_summary_files(files: List[str]) -> List[ClassPeriodReportSummary]:
        """Generates a list of periodic summaries."""
        summaries: List[ClassPeriodReportSummary] = []
        for filename in files:
            start_time = timeit.default_timer()
            base_name = os.path.basename(filename)

            try:
                parser = GroupPeriodicReportParser(filename)
                summary = parser.create_summary()
                parser.close()
            except ParsingError as e:
                logger.error(f"{base_name}: {e}")
                continue
            except Exception as e:
                logger.exception(f"{base_name}: {e}")
                continue

            if any(s for s in summaries if s.representable_name == summary.representable_name):
                logger.warn(f"{base_name}: tokia ataskaita jau vieną kartą buvo pateikta ir perskaityta")
                continue

            if any(s.average is None for s in summary.students):
                logger.warn(f"{base_name}: bent vieno mokinio vidurkis yra ne-egzistuojantis, neskaitoma")
                continue

            logger.debug(f"{base_name}: skaitymas užtruko {timeit.default_timer() - start_time}s")
            summaries.append(summary)

        if len(summaries) == 0:
            logger.error("Nerasta jokių tinkamų ataskaitų, kad būtų galima kurti grafiką!")
        logger.debug(f"Laikotarpių suvestinės sugeneruotos: {len(summaries)}")
        return summaries

