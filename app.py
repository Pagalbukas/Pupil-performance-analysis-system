import os
import timeit
import traceback

from PyQt5.QtWidgets import QWidget, QFileDialog, QPushButton, QVBoxLayout, QDesktopWidget
from typing import List

from graphing import PupilSubjectMonthlyAveragesGraph, ClassPeriodAveragesGraph, ClassMonthlyAveragesGraph
from models import ClassSemesterReportSummary, ClassMonthlyReportSummary, Student
from parsing import PupilSemesterReportParser, PupilMonthlyReportParser, ParsingError
from utils import ConsoleUtils as CU
from settings import Settings

class App(QWidget):

    def __init__(self, settings: Settings):
        super().__init__()

        self.settings = settings
        self.debug = settings.debugging

        self.setWindowTitle('Mokinių pasiekimų analizatorius')

        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480

        self.main_layout = QVBoxLayout()

        self.agg_sem_button = QPushButton('Bendra klasės vidurkių ataskaita pagal trimestrus / pusmečius')
        self.pup_mon_button = QPushButton('Mokinio dalykų vidurkių ataskaita pagal laikotarpį')
        self.agg_mon_button = QPushButton('Bendra klasės vidurkių ataskaita pagal laikotarpį')

        self.agg_sem_button.clicked.connect(self.d_sem_agg)
        self.pup_mon_button.clicked.connect(self.d_mon_pup)
        self.agg_mon_button.clicked.connect(self.d_mon_agg)

        self.main_layout.addWidget(self.agg_sem_button)
        self.main_layout.addWidget(self.pup_mon_button)
        self.main_layout.addWidget(self.agg_mon_button)

        self.setLayout(self.main_layout)

        self.initUI()

    def initUI(self):
        self.setGeometry(self.left, self.top, self.width, self.height)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        self.show()

    def d_mon_agg(self):
        filenames = self.ask_files_dialog()
        summaries: List[ClassMonthlyReportSummary] = []
        for filename in filenames:
            start_time = timeit.default_timer()
            base_name = os.path.basename(filename)

            try:
                parser = PupilMonthlyReportParser(filename)
                summary = parser.create_summary(fetch_subjects=True)
                parser.close()
            except ParsingError as e:
                CU.parse_error(base_name, str(e))
                continue
            except Exception as e:
                CU.parse_error(base_name, "pateikta ne suvestinė arba netinkamas failas")
                if self.debug:
                    print(e)
                    traceback.print_tb(e.__traceback__)
                continue

            if any(s for s in summaries if s.representable_name == summary.representable_name):
                CU.parse_error(base_name, "tokia ataskaita jau vieną kartą buvo pateikta ir perskaityta")
                continue

            summaries.append(summary)
            CU.default(f"'{base_name}' perskaitytas")
            if self.debug:
                print(f"'{base_name}' skaitymas užtruko {timeit.default_timer() - start_time}s")

        if len(summaries) == 0:
            CU.error("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")
            return

        # Sort summaries by
        # 1) term start (YYYY-MM-DD)
        summaries.sort(key=lambda s: (s.term_start))

        # Get the last (the most recent) statistical data and cache student names for later use
        student_cache = [s.name for s in summaries[-1].students]

        # Go over each summary and use it to create graph points
        _temp_subject_name_dict = {}
        graph = ClassMonthlyAveragesGraph(summary.grade_name + " mokinių mėnėsiniai vidurkiai", [s.representable_name for s in summaries])
        for i, summary in enumerate(summaries):
            CU.info(f"Nagrinėjamas ({summary.term_start}-{summary.term_end})")
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

        if self.debug:
            for key in _temp_subject_name_dict.keys():
                name, grade = _temp_subject_name_dict[key]
                print(key, "->", name, f"({grade} kl.)")

        graph.display(
            use_styled_colouring=True,
            use_experimental_legend=True
        )

    def request_parsing(self):
        pass

    def d_sem_agg(self):
        filenames = self.ask_files_dialog()

        # Do initial creation of summaries by iterating the submitted files and validating them
        summaries: List[ClassSemesterReportSummary] = []
        for filename in filenames:
            start_time = timeit.default_timer()
            base_name = os.path.basename(filename)

            try:
                parser = PupilSemesterReportParser(filename)
                summary = parser.create_summary(fetch_subjects=True)
                parser.close()
            except ParsingError as e:
                CU.parse_error(base_name, str(e))
                continue
            except Exception as e:
                CU.parse_error(base_name, "pateikta ne suvestinė arba netinkamas failas")
                if self.debug:
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
            if self.debug:
                print(f"'{base_name}' skaitymas užtruko {timeit.default_timer() - start_time}s")

        if len(summaries) == 0:
            CU.error("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")
            return

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

        if self.debug:
            for key in _temp_subject_name_dict.keys():
                name, grade = _temp_subject_name_dict[key]
                print(key, "->", name, f"({grade} kl.)")

        graph.display(
            use_styled_colouring=True,
            use_experimental_legend=True
        )

    def d_mon_pup(self):
        filenames = self.ask_files_dialog()
        summaries: List[ClassMonthlyReportSummary] = []
        for filename in filenames:
            start_time = timeit.default_timer()
            base_name = os.path.basename(filename)

            try:
                parser = PupilMonthlyReportParser(filename)
                summary = parser.create_summary(fetch_subjects=True)
                parser.close()
            except ParsingError as e:
                CU.parse_error(base_name, str(e))
                continue
            except Exception as e:
                CU.parse_error(base_name, "pateikta ne suvestinė arba netinkamas failas")
                if self.debug:
                    print(e)
                    traceback.print_tb(e.__traceback__)
                continue

            if any(s for s in summaries if s.representable_name == summary.representable_name):
                CU.parse_error(base_name, "tokia ataskaita jau vieną kartą buvo pateikta ir perskaityta")
                continue

            summaries.append(summary)
            CU.default(f"'{base_name}' perskaitytas")
            if self.debug:
                print(f"'{base_name}' skaitymas užtruko {timeit.default_timer() - start_time}s")

        if len(summaries) == 0:
            CU.error("Nerasta jokios tinkamos statistikos, kad būtų galima kurti grafiką!")
            return

        # Sort summaries by
        # 1) term start (YYYY-MM-DD)
        summaries.sort(key=lambda s: (s.term_start))

        # Get the last (the most recent) statistical data and cache student names for later use
        student_cache = [s.name for s in summaries[-1].students]
        students: List[List[Student]] = [[] for _ in range(len(summaries[-1].students))]

        for i, summary in enumerate(summaries):
            CU.info(f"Nagrinėjamas laikotarpis: {summary.representable_name}")
            _cached_subs = []
            for j, student in enumerate(summary.students):

                # If student name is not in cache, ignore them
                if student.name not in student_cache:
                    CU.warn(f"Mokinys '{student.name}' ignoruojamas, nes nėra naujausioje suvestinėje")
                    continue

                subjects = student.get_graphing_subjects()

                students[j].append(student)

                # Notify user regarding different generic and original subject names
                # Not in use as of now, but future proofing
                for subject in subjects:
                    if subject.name not in _cached_subs:
                        if subject.name != subject.generic_name:
                            CU.warn(f"Dalykas '{subject.name}' automatiškai pervadintas į '{subject.generic_name}'")
                        _cached_subs.append(subject.name)

                #graph.get_or_create_student(student.name)[i] = student.average

        print(student_cache)
        print(students)

        for student in students:
            name = student[0].name
            graph = PupilSubjectMonthlyAveragesGraph(name, [s.representable_name for s in summaries])
            for s in student:
                graph.add_subject_list(s.get_graphing_subjects())

            print(name)
            for i, d in enumerate(graph.subject_lists):
                print(i, len(d))
                for a in d:
                    print(a.generic_name, a.clean_mark)

            graph.display(
                use_styled_colouring=True,
                use_experimental_legend=True
            )

    def ask_files_dialog(self, caption: str = "Pasirinkite Excel ataskaitų failus") -> List[str]:
        directory = self.settings.last_dir
        if directory is None or not os.path.exists(directory):
            directory = os.path.join(os.environ["userprofile"], "Downloads")

        files, _ = QFileDialog.getOpenFileNames(
            self,
            caption,
            directory,
            "Excel ataskaitų failai (*.xlsx *.xls)"
        )

        # Store the last dir in the settings
        if len(files) > 0:
            self.settings.last_dir = os.path.dirname(files[0])
            self.settings.save()
        return files
