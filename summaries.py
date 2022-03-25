import datetime

from typing import List, Tuple

from models import Student

ROMAN_VALUE_BINDINGS = {
    "I": 9,
    "II": 10,
    "III": 11,
    "IV": 12
}

class ClassPeriodReportSummary:

    def __init__(
        self,
        grade_name: str,
        sum_period: Tuple[datetime.datetime, datetime.datetime],
        students: List[Student]
    ) -> None:
        self.grade_name = grade_name
        # For grades which are not gymnasium ones
        if grade_name.isdigit():
            self.grade_name = grade_name + " klasė"
        self.term_start, self.term_end = sum_period
        self.students = students

    def __repr__(self) -> str:
        return f'<ClassPeriodReportSummary period="{self.term_start}-{self.term_end}" students={len(self.students)}>'

    @property
    def grade_name_as_int(self) -> int:
        """Returns grade name representation as an integer."""
        value = self.grade_name.split(" ")[0]
        try:
            return int(value)
        except ValueError:
            return ROMAN_VALUE_BINDINGS.get(value, -1)

    @property
    def representable_name(self) -> str:
        """Returns a human representable name of the summary."""
        return f'{self.term_start.strftime("%Y-%m-%d")} - {self.term_end.strftime("%Y-%m-%d")}'

    @property
    def yearless_representable_name(self) -> str:
        """Returns a human representable name of the summary without the year."""
        return f'{self.term_start.strftime("%m-%d")} - {self.term_end.strftime("%m-%d")}'


class ClassSemesterReportSummary:

    def __init__(
        self,
        grade_name: str,
        sum_type: str, sum_period: Tuple[int, int],
        students: List[Student]
    ) -> None:
        self.grade_name = grade_name
        # For grades which are not gymnasium ones
        if grade_name.isdigit():
            self.grade_name = grade_name + " klasė"
        self.type = sum_type
        self.term_start, self.term_end = sum_period
        self.students = students

    def __repr__(self) -> str:
        period = f'{self.term_start}-{self.term_end}'
        return f'<ClassSemesterReportSummary type="{self.type}" period="{period}" students={len(self.students)}>'

    @property
    def type_as_int(self) -> int:
        """Returns type representation as an integer.

        I semester -> 1, II semester -> 2, ...

        Returns -1 for the yearly type.
        """
        if self.type == "metinis":
            return -1
        numeric_val = 0
        roman_number = self.type.split(" ")[0]
        for _ in roman_number:
            numeric_val += 1 # Assuming there's no 4th semester
        return numeric_val

    @property
    def grade_name_as_int(self) -> int:
        """Returns grade name representation as an integer."""
        value = self.grade_name.split(" ")[0]
        try:
            return int(value)
        except ValueError:
            return ROMAN_VALUE_BINDINGS.get(value, -1)

    @property
    def period_name(self) -> str:
        """Returns period name based on the grade."""
        name = self.type
        if self.grade_name_as_int < 11:
            return name + " trimestras" # TODO: not future proof, investigate later
        return name

    @property
    def representable_name(self) -> str:
        """Returns a human representable name of the summary."""
        period = f'{self.term_start}-{self.term_end}'
        return f"{self.grade_name_as_int} kl.\n{self.period_name}\n({period})"
