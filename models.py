from typing import TYPE_CHECKING, List, Optional, Union
from graphing import PupilSubjectPeriodicAveragesGraph, PupilPeriodicAveragesGraph

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

class Subject:

    if TYPE_CHECKING:
        name: str
        mark: Optional[Union[int, float, str]]
        is_module: bool

    def __init__(self, name: str, mark: Optional[Union[int, float, str]]) -> None:
        self.name = name
        self.mark = mark
        self.is_module = "modulis" in self.name

    def __repr__(self) -> str:
        return f'<Subject name="{self.name}" mark={self.mark}>'

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

    if TYPE_CHECKING:
        name: str
        mark: Optional[Union[int, float, str]]
        is_module: bool

    def __init__(self, name: str) -> None:
        self.name = name
        self.marks: List[Mark] = []
        self.is_module = "modulis" in self.name

    def __repr__(self) -> str:
        return f'<UnifiedSubject name="{self.name}" marks={len(self.marks)}>'

    def add_mark(self, mark: Mark) -> None:
        """Adds a mark to the list."""
        self.marks.append(mark)

    @property
    def is_ignored(self) -> bool:
        """Returns true if subject's mark value should be ignored.

        This is based on many factors, including subjects which are not
        really subjects, per say."""
        return (
            # Informal education
            self.name == "Neformalusis ugdymas"
            or self.name == "Neformalus ugdymas"

            # Moral related
            or self.name.startswith("Dorinis ugdymas")

            # Modules
            or self.is_module

            # Catch clauses for home schooling
            # As observed, the data is transferred to the original subject
            # marking too
            or self.name.startswith("Namų ugdymas")
            or self.name.startswith("Namų mokymas")

            # No idea
            or self.name == "Integruotas technologijų kursas"
            or self.name == "Lietuvių kalbos rašyba, skyryba ir vartojimas (konsultacijos)"
            or self.name == "Žmogaus sauga"
            or self.name == "Karjeros ugdymas"

            # Social work for which you get hours
            or self.name == "Socialinė-pilietinė veikla"
            or self.name == "Socialinė veikla"
        )

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

class UnifiedPupilGrapher:

    def __init__(self, period_names: List[str], pupil_names: List[str]) -> None:
        self.period_names: List[str] = period_names
        self.pupil_names: List[str] = pupil_names
        period_cnt = len(self.period_names)
        pupil_cnt = len(self.pupil_names)
        self.pupil_subjects: List[List[UnifiedSubject]] = [[] for _ in range(pupil_cnt)]
        self.pupil_averages: List[List[Optional[Union[int, float]]]] = [
            [None for _ in range(period_cnt)] for _ in range(pupil_cnt)
        ]

    def display_subjects_graph(self, student_index: int) -> None:
        name = self.pupil_names[student_index]
        graph = PupilSubjectPeriodicAveragesGraph(name, self.period_names, self.pupil_subjects[student_index])
        graph.display(use_experimental_legend=True)

    def display_aggregated_graph(self, student_index: int) -> None:
        name = self.pupil_names[student_index]
        graph = PupilPeriodicAveragesGraph(
            name,
            self.period_names,
            self.pupil_averages[student_index],
            self.compute_class_averages(),
            False
        )
        graph.display(use_experimental_legend=True)

    def compute_class_averages(self) -> List[Optional[float]]:
        averages = [0 for _ in range(len(self.period_names))]
        for pupil in self.pupil_averages:
            for i, average in enumerate(pupil):
                averages[i] += average
        return [round(a / len(self.pupil_names), 2) for a in averages]

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
    def sorted_subjects(self) -> List[Subject]:
        """Returns a sorted subject list by name."""
        return sorted(self.subjects, key=lambda s: s.name)

    @property
    def sane_name(self) -> str:
        """Returns a reversed name of the student.
        Should begin with a name instead of surname."""
        return ' '.join(self.name.split(" ")[::-1])
