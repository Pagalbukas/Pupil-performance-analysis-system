from __future__ import annotations

import datetime
import random

from copy import deepcopy
from typing import TYPE_CHECKING, Dict, List, Tuple, TypeVar, Union

from analyser.models import ClassPupil, GroupPupil

ROMAN_VALUE_BINDINGS = {
    "I": 9,
    "II": 10,
    "III": 11,
    "IV": 12
}

AnySummary = TypeVar('AnySummary', 'ClassSemesterReportSummary', 'ClassPeriodReportSummary', 'GroupReportSummary')

class BaseReportSummary:

    def __init__(
        self,
        period: Tuple[datetime.datetime, datetime.datetime],
        pupils: Union[List[ClassPupil], List[GroupPupil]]
    ) -> None:
        self.term_start, self.term_end = period
        self.pupils = pupils

    @property
    def period(self) -> str:
        """Returns representation of summary period in years."""
        return f'{self.term_start.year}-{self.term_end.year}'

    @property
    def representable_name(self) -> str:
        """Returns a human representable name of the summary."""
        return f'{self.term_start.strftime("%m-%d")} - {self.term_end.strftime("%m-%d")}'

    @property
    def full_representable_name(self) -> str:
        """Returns a human representable name of the summary without the year."""
        return f'{self.term_start.strftime("%Y-%m-%d")} - {self.term_end.strftime("%Y-%m-%d")}'

class GroupReportSummary(BaseReportSummary):

    if TYPE_CHECKING:
        pupils: List[GroupPupil]

    def __init__(
        self,
        group_name: str,
        period: Tuple[datetime.datetime, datetime.datetime],
        pupils: List[GroupPupil]
    ) -> None:
        self.group_name = group_name
        super().__init__(period, pupils)

    def __repr__(self) -> str:
        return f'<GroupReportSummary period="{self.period}" pupils={len(self.pupils)}>'

class ClassReportSummary(BaseReportSummary):

    if TYPE_CHECKING:
        pupils: List[ClassPupil]

    def __init__(
        self,
        grade_name: str,
        period: Tuple[datetime.datetime, datetime.datetime],
        pupils: List[ClassPupil]
    ) -> None:
        self.grade_name = grade_name
        # For grades which are not gymnasium ones
        if grade_name.isdigit():
            self.grade_name = grade_name + " klasė"
        super().__init__(period, pupils)

    @property
    def grade_name_as_int(self) -> int:
        """Returns grade name representation as an integer."""
        value = self.grade_name.split(" ")[0]
        try:
            return int(value)
        except ValueError:
            return ROMAN_VALUE_BINDINGS.get(value, -1)

class ClassPeriodReportSummary(ClassReportSummary):

    if TYPE_CHECKING:
        pupils: List[ClassPupil]

    def __init__(
        self,
        grade_name: str,
        period: Tuple[datetime.datetime, datetime.datetime],
        pupils: List[ClassPupil]
    ) -> None:
        super().__init__(grade_name, period, pupils)

    def __repr__(self) -> str:
        return f'<ClassPeriodReportSummary period="{self.period}" pupils={len(self.pupils)}>'

class ClassSemesterReportSummary(ClassReportSummary):

    if TYPE_CHECKING:
        pupils: List[ClassPupil]

    def __init__(
        self,
        grade_name: str,
        type: str,
        period: Tuple[datetime.datetime, datetime.datetime],
        pupils: List[ClassPupil]
    ) -> None:
        super().__init__(grade_name, period, pupils)
        self.type = type

    def __repr__(self) -> str:
        return f'<ClassSemesterReportSummary type="{self.type}" period="{self.period}" pupils={len(self.pupils)}>'

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
    def period_name(self) -> str:
        """Returns period name based on the grade."""
        name = self.type
        if name.endswith("pusmetis"):
            return name
        return name + " trimestras"

    @property
    def representable_name(self) -> str:
        """Returns a human representable name of the summary."""
        return f"{self.grade_name_as_int} kl.\n{self.period_name}\n({self.period})"


def anonymize_pupil_names(summaries: List[AnySummary]) -> List[AnySummary]:
    """Anonymizes the names of pupils in the specified summary list."""
    summaries = deepcopy(summaries)

    cached_combinations: List[str] = []
    def generate_unique_name(cached_combinations: List[str]) -> str:
        names = ["Antanas", "Bernardas", "Cezis", "Dainius", "Ernestas", "Henrikas", "Jonas", "Petras", "Tilius"]
        surnames = ["Antanivičius", "Petraitis", "Brazdžionis", "Katiliškis", "Mickevičius", "Juozevičius", "Eilėraštinis"]
        
        name = f"{random.choice(names)} {random.choice(surnames)}"
        while name in cached_combinations:
            name = f"{random.choice(names)} {random.choice(surnames)}"
        cached_combinations.append(name)
        return name
    
    pupil_name_binds: Dict[str, str] = {}
    
    # First, we obtain pupil names and generate unique names
    for summary in summaries:
        for pupil in summary.pupils:
            name = pupil_name_binds.get(pupil.name)
            if name is None:
                pupil_name_binds[pupil.name] = generate_unique_name(cached_combinations)
            continue
    
    # Apply the modified names
    for i, summary in enumerate(summaries):
        for j, pupil in enumerate(summary.pupils):
            summaries[i].pupils[j].name = pupil_name_binds[pupil.name]
    
    # Return modified list
    return summaries
