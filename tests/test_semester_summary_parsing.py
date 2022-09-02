import datetime
import json
import os

from analyser.models import UnifiedPupil
from analyser.parsing import PupilSemesterReportParser

SEMESTER_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_data', 'semesters')
COMPARISON_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_data', 'semester_comparison_data.json')

with open(COMPARISON_FILE_PATH, "r") as f:
    PUPIL_DATA_TABLE = json.load(f)

def generate_test_data() -> None:
    """Generates test data for comparison, should only be called when updating source test data."""
    data = {}
    for file in os.listdir(SEMESTER_FILE_PATH):
        path = os.path.join(SEMESTER_FILE_PATH, file)
        print(path)
    
        parser = PupilSemesterReportParser(path)
        summary = parser.create_summary(fetch_subjects=True)
        parser.close()

        data[file] = [to_dict(p) for p in summary.pupils]
    with open(COMPARISON_FILE_PATH, "w") as f:
        json.dump(data, f)

def to_dict(pupil: UnifiedPupil) -> dict:
    """Returns pupil object as a dictionary."""
    return {
        "name": pupil.name,
        "average": pupil.average.clean,
        "attendance": {
            "total_missed": pupil.attendance.total_missed,
            "illness": pupil.attendance.justified_by_illness,
            "other": pupil.attendance.justified_by_other,
            "not_justified": pupil.attendance.not_justified
        },
        "subjects": [
            {
                "name": s.name,
                "is_module": s.is_module,
                "generic_name": s.generic_name,
                "is_ignored": s.is_ignored,
                "mark": s.mark.clean
            } for s in pupil.sorted_subjects
        ]
    }

def test_first_semester_mark():
    sem_path = os.path.join(SEMESTER_FILE_PATH, "5-sem1.xlsx")
    
    parser = PupilSemesterReportParser(sem_path)
    summary = parser.create_summary(fetch_subjects=True)
    parser.close()

    assert summary.grade_name == "5 klasė"
    assert summary.grade_name_as_int == 5
    assert summary.type == "I"
    assert summary.type_as_int == 1
    assert summary.period_name == "I trimestras"

    assert summary.term_start == datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    assert summary.term_end == datetime.datetime(1971, 1, 1, tzinfo=datetime.timezone.utc)

    for i, pupil in enumerate(summary.pupils):
        assert to_dict(pupil) == PUPIL_DATA_TABLE['5-sem1.xlsx'][i]

def test_second_semester_mark():
    sem_path = os.path.join(SEMESTER_FILE_PATH, "5-sem2.xlsx")
    
    parser = PupilSemesterReportParser(sem_path)
    summary = parser.create_summary(fetch_subjects=True)
    parser.close()

    assert summary.grade_name == "5 klasė"
    assert summary.grade_name_as_int == 5
    assert summary.type == "II"
    assert summary.type_as_int == 2
    assert summary.period_name == "II trimestras"

    assert summary.term_start == datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    assert summary.term_end == datetime.datetime(1971, 1, 1, tzinfo=datetime.timezone.utc)

    for i, pupil in enumerate(summary.pupils):
        assert to_dict(pupil) == PUPIL_DATA_TABLE['5-sem2.xlsx'][i]

def test_third_semester_mark():
    sem_path = os.path.join(SEMESTER_FILE_PATH, "5-sem3.xlsx")
    
    parser = PupilSemesterReportParser(sem_path)
    summary = parser.create_summary(fetch_subjects=True)
    parser.close()

    assert summary.grade_name == "5 klasė"
    assert summary.grade_name_as_int == 5
    assert summary.type == "III"
    assert summary.type_as_int == 3
    assert summary.period_name == "III trimestras"

    assert summary.term_start == datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    assert summary.term_end == datetime.datetime(1971, 1, 1, tzinfo=datetime.timezone.utc)

    for i, pupil in enumerate(summary.pupils):
        assert to_dict(pupil) == PUPIL_DATA_TABLE['5-sem3.xlsx'][i]

def test_first_semester_grade6_mark():
    sem_path = os.path.join(SEMESTER_FILE_PATH, "6-sem1.xlsx")
    
    parser = PupilSemesterReportParser(sem_path)
    summary = parser.create_summary(fetch_subjects=True)
    parser.close()

    assert summary.grade_name == "6 klasė"
    assert summary.grade_name_as_int == 6
    assert summary.type == "I pusmetis"
    assert summary.type_as_int == 1
    assert summary.period_name == summary.type

    assert summary.term_start == datetime.datetime(1971, 1, 1, tzinfo=datetime.timezone.utc)
    assert summary.term_end == datetime.datetime(1972, 1, 1, tzinfo=datetime.timezone.utc)

    for i, pupil in enumerate(summary.pupils):
        assert to_dict(pupil) == PUPIL_DATA_TABLE['6-sem1.xlsx'][i]

def test_second_semester_grade6_mark():
    sem_path = os.path.join(SEMESTER_FILE_PATH, "6-sem2.xlsx")
    
    parser = PupilSemesterReportParser(sem_path)
    summary = parser.create_summary(fetch_subjects=True)
    parser.close()

    assert summary.grade_name == "6 klasė"
    assert summary.grade_name_as_int == 6
    assert summary.type == "II pusmetis"
    assert summary.type_as_int == 2
    assert summary.period_name == summary.type

    assert summary.term_start == datetime.datetime(1971, 1, 1, tzinfo=datetime.timezone.utc)
    assert summary.term_end == datetime.datetime(1972, 1, 1, tzinfo=datetime.timezone.utc)

    for i, pupil in enumerate(summary.pupils):
        assert to_dict(pupil) == PUPIL_DATA_TABLE['6-sem2.xlsx'][i]

if __name__ == "__main__":
    generate_test_data()
