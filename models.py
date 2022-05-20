from __future__ import annotations

import logging

from typing import List, Optional, Union

from files import get_ignored_item_filters

IGNORED_ITEM_FILTERS = get_ignored_item_filters()

logger = logging.getLogger("analizatorius")

class Attendance:

    def __init__(
        self,
        total_missed: int,
        justified_by_illness: int,
        justified_by_other: int,
        not_justified: int
    ) -> None:
        self.total_missed = total_missed
        self.justified_by_illness = justified_by_illness
        self.justified_by_other = justified_by_other
        self.not_justified = not_justified

class SubjectNames:
    """This class contains constants for subject names."""

    # Local language
    LITHUANIAN = "Lietuvių kalba ir literatūra"

    # Foreign languages
    ENGLISH = "Užsienio kalba (anglų)"
    RUSSIAN = "Užsienio kalba (rusų)"
    # Future proofing, jic
    GERMAN = "Užsienio kalba (vokiečių)"
    FRENCH = "Užsienio kalba (prancūzų)"

    # Social
    GEOGRAPHY = "Geografija"
    HISTORY = "Istorija"

    # Precise
    MATHEMATICS = "Matematika"
    PHYSICS = "Fizika"
    BIOLOGY = "Biologija"
    CHEMISTRY = "Chemija"
    INFORMATION_TECHNOLOGY = "Informacinės technologijos"

    # Temporary
    ECONOMICS = "Ekonomika"
    CITIZENSHIP = "Pilietiškumas"

    # Moral
    ETHICS = "Etika"
    FAITH = "Tikyba"

    # Other
    ART = "Dailė"
    MUSIC = "Muzika"
    PHYSICAL_EDUCATION = "Fizinis ugdymas"
    TECHNOLOGIES = "Technologijos"

    # Abbreviations
    MATH = MATHEMATICS
    BIO = BIOLOGY
    PE = PHYSICAL_EDUCATION
    IT = INFORMATION_TECHNOLOGY


COMMON_GENERIC_NAMES = {
    "informatika": SubjectNames.IT,
    "kūno kultūra": SubjectNames.PE
}

class Mark:

    def __init__(self, raw_value: Optional[Union[int, float, str]]) -> None:
        self.raw_value = raw_value

    def __repr__(self) -> str:
        return f'<Mark raw="{self.raw_value}">'

    @property
    def is_number(self) -> bool:
        """Returns true if mark is a number."""
        return not isinstance(self.raw_value, str)

    @property
    def type(self) -> str:
        """Returns mark type as string as either `str` or `int`."""
        return "str" if not self.is_number else "int"

    @property
    def clean(self) -> Optional[Union[bool, int, float]]:
        if self.raw_value is None:
            return None

        if isinstance(self.raw_value, (int, float)):
            return self.raw_value

        if self.raw_value == "-":
            return None
        if self.raw_value == "įsk":
            return True
        if self.raw_value == "nsk":
            return False
        if self.raw_value == "atl":
            return None

        if isinstance(self.raw_value, str):
            new_mark = self.raw_value.replace("IN", "")
            new_mark = new_mark.replace("PR", "")
            if new_mark == "0":
                return None
            if new_mark.isdecimal():
                return float(new_mark)
            elif new_mark.replace('.', '', 1).isdigit():
                return float(new_mark)
        raise ValueError(f"Could not convert '{self.raw_value}' to a clean mark")

class UnifiedSubject:

    def __init__(self, name: str, mark: Mark) -> None:
        self.name = name
        self.mark = mark
        self.is_module = "modulis" in self.name

    def __repr__(self) -> str:
        return f'<UnifiedSubject name="{self.name}" mark={self.mark}>'

    def is_name_ignored(self) -> bool:
        """Returns true if subject name is ignored as defined in ignoruoti_dalykai.txt"""
        for item_filter in IGNORED_ITEM_FILTERS:
            t, word = item_filter
            check = False
            # Normal check of matching the name
            if t == 1:
                check = self.name == word
            # Check if name starts with
            elif t == 3:
                check = self.name.startswith(word)
            # Check if name ends with
            elif t == 5:
                check = self.name.endswith(word)
            # Check if in string
            else:
                check = word in self.name
            if check:
                return True
        return False

    @property
    def is_ignored(self) -> bool:
        """Returns true if subject's mark value should be ignored.

        This is based on whether the subject is a module or the name is ignored."""
        return self.is_module or self.is_name_ignored()

    @property
    def generic_name(self) -> str:
        """Returns a generic, representative name of the subject.

        Note that this is based on guesswork and may not be 100% correct."""

        # Lowercase the name and remove any whitespaces
        cleaned_name = self.name.lower().strip()

        # A very optimistic approach at obtaining the generic name
        genericized_name = COMMON_GENERIC_NAMES.get(cleaned_name, self.name)

        low_generic = genericized_name.lower()

        # Could be anything, but related to art
        if "menas" in low_generic:

            # Should be technologies for boys
            if "amatai" in low_generic:
                return SubjectNames.TECHNOLOGIES

            # Just notify for debug reasons
            logger.debug(f"Dalykas '{genericized_name}' yra susijęs su Daile arba Technologijomis")

        # Usually hits technologies for girls
        if "tekstilė" in low_generic or "apranga" in low_generic:
            return SubjectNames.TECHNOLOGIES

        return genericized_name

class UnifiedPupil:

    def __init__(self, name: str, subjects: List[UnifiedSubject], average: Mark, attendance: Attendance) -> None:
        self.name = name
        self.subjects = subjects
        self.average = average
        self.attendance = attendance

    def __repr__(self) -> str:
        return f'<UnifiedPupil name="{self.name}" average={self.average} subjects={len(self.subjects)}>'

    @property
    def sorted_subjects(self) -> List[UnifiedSubject]:
        """Returns a sorted subject list by name."""
        return sorted(self.subjects, key=lambda s: s.name)

    @property
    def sane_name(self) -> str:
        """Returns a reversed name of the student.
        Should begin with a name instead of surname."""
        return ' '.join(self.name.split(" ")[::-1])
