import sys
import timeit
import os
import traceback

from PyQt5.QtWidgets import QApplication
from typing import List

from app import App
from graphs.base import ClassPeriodAveragesGraph
from models import Summary
from parser2 import Parser, ParsingError
from utils import ConsoleUtils as CU
from settings import Settings

settings = Settings()

DEBUG = settings.debugging

CU.info("Pasirinkite pusmečių/trimestrų suvestinių Excel failus")

app = QApplication(sys.argv)
ex = App(settings)
filenames = ex.ask_files_dialog()

# Do initial creation of summaries by iterating the submitted files and validating them
summaries: List[Summary] = []
for filename in filenames:
    start_time = timeit.default_timer()
    base_name = os.path.basename(filename)

    try:
        parser = Parser(filename)
        summary = parser.create_summary(fetch_subjects=True)
        parser.close()
    except ParsingError as e:
        CU.parse_error(base_name, str(e))
        continue
    except Exception as e:
        CU.parse_error(base_name, "pateikta ne suvestinė arba netinkamas failas")
        if DEBUG:
            print(e)
            traceback.print_tb(e.__traceback__)
        continue

    if summary.type == "metinis":
        CU.parse_error(base_name, "metinė ataskaita yra nevertinama")
        continue

    if any(s for s in summaries if s.representable_name == summary.representable_name):
        CU.parse_error(base_name, "tokia ataskaita jau vieną kartą buvo pateikta ir perskaityta")
        continue

    summaries.append(summary)
    CU.default(f"'{base_name}' perskaitytas")
    if DEBUG:
        print(f"'{base_name}' skaitymas užtruko {timeit.default_timer() - start_time}s")

if len(summaries) == 0:
    CU.error("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")
    exit()

# Sort summaries by
# 1) term start (year)
# 2) type (semester) (I -> II -> III)
summaries.sort(key=lambda s: (s.term_start, s.type_as_int))

# Get the last (the most recent) statistical data and cache student names for later use
student_cache = [s.name for s in summaries[-1].students]

# Go over each summary and use it to create graph points
_temp_subject_name_dict = {}
graph = ClassPeriodAveragesGraph(summary.grade_name + " mokinių vidurkių pokytis", [s.representable_name for s in summaries])
for i, summary in enumerate(summaries):
    CU.info(f"Nagrinėjamas {summary.period_name} ({summary.term_start}-{summary.term_end})")
    _cached_subs = []
    for student in summary.students:

        # If student name is not in cache, ignore them
        if student.name not in student_cache:
            CU.warn(f"Mokinys '{student.name}' ignoruojamas, nes nėra naujausioje suvestinėje")
            continue

        subjects = student.get_graphing_subjects()

        # Notify user regarding different generic and original subject names
        # Not in use as of now, but future proofing
        for subject in subjects:
            if subject.name not in _cached_subs:
                if subject.name != subject.generic_name:
                    CU.warn(f"Dalykas '{subject.name}' automatiškai pervadintas į '{subject.generic_name}'")
                _cached_subs.append(subject.name)

            if _temp_subject_name_dict.get(subject.name, None) is None:
                _temp_subject_name_dict[subject.name] = (subject.generic_name, summary.grade_name_as_int)

        graph.get_or_create_student(student.name)[i] = student.average

if DEBUG:
    for key in _temp_subject_name_dict.keys():
        name, grade = _temp_subject_name_dict[key]
        print(key, "->", name, f"({grade} kl.)")

graph.display(
    use_styled_colouring=True,
    use_experimental_legend=True
)
