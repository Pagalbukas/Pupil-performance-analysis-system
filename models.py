from typing import TYPE_CHECKING, List, Optional, Tuple, Union

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

ROMAN_VALUE_BINDINGS = {
    "I": 9,
    "II": 10,
    "III": 11,
    "IV": 12
}

class Subject:

    if TYPE_CHECKING:
        name: str
        mark: Optional[int]
        is_module: bool

    def __init__(self, name: str, mark: Optional[Union[int, str]]) -> None:
        self.name = name
        self.mark = mark
        self.is_module = "modulis" in self.name

    def __repr__(self) -> str:
        return f'<Subject name="{self.name}" is_number={self.is_number} mark={self.mark}>'

    @property
    def type(self) -> str:
        """Returns stored mark type as string as either `str` or `int`."""
        return "str" if isinstance(self.mark, str) else "int"

    @property
    def is_number(self) -> bool:
        """Returns true if stored mark is a number."""
        return not isinstance(self.mark, str)

    @property
    def is_ignored(self) -> bool:
        """Returns true if subject's mark value should be ignored.

        This is based on many factors, including subjects which are not
        really subjects, per say."""
        return self.name == "Neformalusis ugdymas"

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
            print(f"Dalykas '{genericized_name}' yra susijęs su Daile arba Technologijomis")

        # Usually hits technologies for girls
        if "tekstilė" in low_generic or "apranga" in low_generic:
            return SubjectNames.TECHNOLOGIES

        return genericized_name

class Student:

    if TYPE_CHECKING:
        name: str
        subjects: List[Subject]
        average: Optional[float]

    def __init__(self, name: str, subjects: List[Subject], average: Optional[float]) -> None:
        self.name = name
        self.subjects = subjects
        self.average = average

    def __repr__(self) -> str:
        return f'<Student name="{self.name}" average={self.average} subjects={len(self.subjects)}>'

    @property
    def sane_name(self) -> str:
        """Returns a reversed name of the student.
        Should begin with a name instead of surname."""
        return ' '.join(self.name.split(" ")[::-1])

    def get_non_none_subjects(self, ignore_modules: bool = False) -> List[Subject]:
        """Returns a list of subjects whose marks are not None."""
        return [
            s for s in self.subjects
            if s.mark is not None # If subject's average was not None
            and not (ignore_modules and s.is_module) # If subject was not module and it modules are ignored
            and not s.is_ignored # If subject is not ignored
        ]

class Summary:

    def __init__(
        self,
        school_name: str,
        grade_name: str,
        sum_type: str, sum_period: Tuple[int, int],
        students: List[Student]
    ) -> None:
        self.school_name = school_name
        self.grade_name = grade_name
        # For grades which are not gymnasium ones
        if grade_name.isdigit():
            self.grade_name = grade_name + " klasė"
        self.type = sum_type
        self.term_start, self.term_end = sum_period
        self.students = students

    def __repr__(self) -> str:
        return f'<Summary type="{self.type}" period="{self.term_start}-{self.term_end}" students={len(self.students)}>'

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
