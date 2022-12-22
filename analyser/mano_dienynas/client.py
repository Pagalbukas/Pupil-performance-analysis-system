from __future__ import annotations

import datetime
import os
import requests # type: ignore

from lxml import etree # type: ignore
from lxml.etree import _ElementTree, ElementBase # type: ignore
from io import StringIO
from requests.models import Response # type: ignore
from typing import Dict, List, Optional, Tuple, Union

from analyser.errors import ClientError, ClientRequestError
from analyser.files import get_temp_dir

PARSER = etree.HTMLParser()

class UserRole:
    def __init__(self, client: Client, title: str, classes: Optional[str], school_name: str, url: str, is_active: bool) -> None: # noqa
        self._client = client
        self.title = title
        if classes is not None:
            classes = classes.strip()
        self.classes = classes
        self.school_name = school_name
        self.url = url
        self.is_active = is_active

    def __repr__(self) -> str:
        if self.classes is None:
            return f'<UserRole title="{self.title}" classes=None school_name="{self.school_name}" is_active={self.is_active}>' # noqa
        return f'<UserRole title="{self.title}" classes="{self.classes}" school_name="{self.school_name}" is_active={self.is_active}>' # noqa
    
    @property
    def is_teacher(self) -> bool:
        return self.title == "Mokytojas"

    @property
    def representable_name(self) -> str:
        """Returns clean, representable name of the role."""
        if self.classes:
            return f'{self.school_name} {self.title} ({self.classes})'
        return f'{self.school_name} {self.title}'

    def change_role(self) -> None:
        """Changes current client role to this one."""
        if self.is_active:
            return
        r = self._client.request("GET", self._client.BASE_URL + self.url)
        if r.status_code != 200:
            raise ClientError("Keičiant paskyros tipą įvyko nenumatyta klaida!")
        for role in self._client._cached_roles:
            role.is_active = role.url == self.url

    def get_class_id(self) -> Optional[str]:
        """Returns class ID as a string if user role is a class teacher."""
        if self.title != "Klasės vadovas":
            return None
        return self.url.split("/")[-1]

class Class:
    def __init__(self, class_id: str, name: str) -> None:
        self.id = class_id
        self.name = name

    def __repr__(self) -> str:
        return f'<Class id="{self.id}" name="{self.name}">'

class Group:
    def __init__(self, group_id: str, name: str) -> None:
        self.id = group_id
        self.name = name

    def __repr__(self) -> str:
        return f'<Group id="{self.id}" name="{self.name}">'

class ClassAveragesReportGenerator:
    def __init__(self, client: Client, class_id: str, dates: List[Tuple[datetime.datetime, datetime.datetime]]) -> None:
        self._client = client
        self.class_id = class_id
        self.dates = dates
        self.generated_count = 0

    def __repr__(self) -> str:
        return f'<ClassAveragesReportGenerator class_id="{self.class_id}">'

    @property
    def expected_period_report_count(self) -> int:
        """Returns expected amount of periodic reports to be generated."""
        now = datetime.datetime.now(datetime.timezone.utc)
        return sum([1 for d in self.dates if d[0] <= now])

    @property
    def expected_monthly_report_count(self) -> int:
        """Returns expected amount of monthly reports to be generated."""
        now = datetime.datetime.now(datetime.timezone.utc)
        count = 1
        analysed_date = now
        while analysed_date.month != 9:
            analysed_date = analysed_date.replace(day=1) - datetime.timedelta(days=1)
            count += 1
        return count

    def generate_periodic_reports(self):
        """Returns a list of file paths to generated periodic reports."""
        now = datetime.datetime.now(datetime.timezone.utc)
        for date in self.dates:
            if date[0] > now:
                break
            yield self._client.generate_class_averages_report(self.class_id, date[0], date[1])

    def generate_monthly_reports(self):
        """Returns a list of file paths to generated periodic reports."""

        def get_first_date(date: datetime.datetime):
            return datetime.datetime(date.year, date.month, 1)

        def get_last_date(date: datetime.datetime):
            return datetime.datetime(date.year, date.month, date.day)

        now = datetime.datetime.now(datetime.timezone.utc)

        dates = [(get_first_date(now), get_last_date(now))]
        analysed_date = now
        while analysed_date.month != 9:
            analysed_date = analysed_date.replace(day=1) - datetime.timedelta(days=1)
            dates.append((get_first_date(analysed_date), get_last_date(analysed_date)))

        for date in dates:
            yield self._client.generate_class_averages_report(self.class_id, date[0], date[1])

class GroupReportGenerator:
    def __init__(self, client: Client, group_id: str, dates: List[Tuple[datetime.datetime, datetime.datetime]]) -> None:
        self._client = client
        self.group_id = group_id
        self.dates = dates

    def __repr__(self) -> str:
        return f'<GroupReportGenerator group_id="{self.group_id}">'
    
    def generate_report(self):
        yield self._client.generate_group_report(self.group_id, self.dates[0][0], self.dates[-1][-1])

class Client:
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Safari/537.36' # noqa 501
    }

    def __init__(self, base_url: str = "https://www.manodienynas.lt") -> None:
        self.BASE_URL = base_url
        self.cookies: Dict[str, str] = {}

        self._session_expires: Optional[datetime.datetime] = None
        self._cached_roles: List[UserRole] = []

    @property
    def is_logged_in(self) -> bool:
        if self._session_expires is None:
            return False
        # Consider session expired after 20 minutes
        if datetime.datetime.now(datetime.timezone.utc).timestamp() - self._session_expires.timestamp() < 60 * 20:
            return True
        # Logout after session expiration
        self.logout()
        return False

    def request(
        self,
        method: str,
        url: str,
        data: Optional[dict] = None,
        no_cookies: bool = False,
        timeout: Optional[int] = 30
    ) -> Response:
        try:
            if no_cookies:
                return requests.request(method, url, data=data, headers=self.HEADERS, timeout=timeout)
            return requests.request(method, url, data=data, headers=self.HEADERS, cookies=self.cookies, timeout=timeout)
        except requests.RequestException:
            raise ClientRequestError

    def logout(self) -> None:
        """Destroys the client session and clears cache."""
        self.cookies = {}
        self._cached_roles = []
        self._session_expires = None

    def login(self, email: str, password: str) -> bool:
        """Attempts to login to manodienynas.lt platform.\n
        Returns boolean on whether the operation was successful."""
        request = self.request("POST", self.BASE_URL + "/1/lt/ajax/user/login", {
            'username': email,
            'password': password,
            'dienynas_remember_me': 1
        }, no_cookies=True)
        response = request.json()
        if response.get('message') is not False:
            return False

        self._session_expires = datetime.datetime.now(datetime.timezone.utc)
        self.cookies["PHPSESSID"] = request.cookies['PHPSESSID']
        self.cookies["PAS"] = request.cookies['pas']
        self.cookies["username"] = request.cookies['username']
        return True

    def get_filtered_user_roles(self) -> List[UserRole]:
        """Returns a list of user roles capable of generating averages reports."""
        roles = self.get_user_roles()
        return [
            r for r in roles
            if r.title == "Klasės vadovas"
            or r.title == "Sistemos administratorius"
            or r.title == "Administracija"
            or r.title == "Mokytojas"
        ]

    def get_user_roles(self) -> List[UserRole]:
        """Returns a list of user role objects."""
        if len(self._cached_roles) > 0:
            return self._cached_roles

        r = self.request("GET", self.BASE_URL + "/1/lt/page/message_new/message_list")
        tree: _ElementTree = etree.parse(StringIO(r.text), PARSER)

        curr_roles = tree.xpath("//li[@class='additional-school-user-type current_role']")
        other_roles = tree.xpath("//li[@class='additional-school-user-type ']")

        roles = []
        for elem in curr_roles + other_roles:
            assert isinstance(elem, etree._Element)
            spans: List[ElementBase] = elem.xpath(".//span")
            role_name = spans[0].text
            classes = spans[1].text
            school_name = spans[2].attrib["title"]
            # window.location.href = '/1/lt/action/user/change_role/x-xxxx-xx/xx'
            url = elem.attrib["onclick"][24:-1]
            roles.append(
                UserRole(self, role_name, classes, school_name, url, 'current_role' in elem.attrib["class"])
            )
        self._cached_roles = roles
        return roles

    def fetch_user_groups(self) -> List[Group]:
        """Returns a list of groups for the currently active user role."""
        r = self.request("GET", self.BASE_URL + "/1/lt/page/report/choose_normal/81")
        tree: _ElementTree = etree.parse(StringIO(r.text), PARSER)
        form: ElementBase = tree.find("//form[@name='reportNormalForm']") # type: ignore
        groups = []
        group_select_elem: ElementBase = form.find(".//select[@id='GroupNormal']") # type: ignore
        for opt in group_select_elem.getchildren():
            assert isinstance(opt, etree._Element)
            value = opt.attrib["value"]
            if value == "0":
                continue
            groups.append(Group(value, opt.text.strip()))
        return groups
    
    def fetch_group_report_options(self, group_id: str) -> GroupReportGenerator:
        r = self.request("GET", self.BASE_URL + f"/1/lt/page/report/choose_normal/81/{group_id}")
        tree: _ElementTree = etree.parse(StringIO(r.text), PARSER)
        form: ElementBase = tree.find("//form[@name='reportNormalForm']") # type: ignore
        date_quick_select_elems: List[ElementBase] = form.xpath(".//a[@class='termDateSetter whiteButton']")
        if len(date_quick_select_elems) % 2 != 0:
            raise ClientError("Neįmanoma automatiškai nustatyti trimestrų/pusmečių laikotarpių!")
        half = len(date_quick_select_elems) // 2
        dates = []
        for e in date_quick_select_elems:
            date = datetime.datetime.strptime(e.attrib["href"], "%Y-%m-%d")
            dates.append(date.replace(tzinfo=datetime.timezone.utc))
        new_dates = []
        for i in range(half - 1):
            new_dates.append((dates[:half][i], dates[half:][i]))
        return GroupReportGenerator(self, group_id, new_dates)

    def get_class_averages_report_options(self, class_id: Optional[str] = None) -> Union[ClassAveragesReportGenerator, List[Class]]:
        """Returns response for selecting monthly averages report."""
        if class_id is None:
            r = self.request("GET", self.BASE_URL + "/1/lt/page/report/choose_normal/12")
        else:
            r = self.request("GET", self.BASE_URL + "/1/lt/page/report/choose_normal/12/" + class_id)

        tree: _ElementTree = etree.parse(StringIO(r.text), PARSER)
        form: ElementBase = tree.find("//form[@name='reportNormalForm']") # type: ignore

        # If class ID was specified, provide unified interface for downloading either monthly or semester
        if class_id is not None:
            date_quick_select_elems: List[ElementBase] = form.xpath(".//a[@class='termDateSetter whiteButton']")
            if len(date_quick_select_elems) % 2 != 0:
                raise ClientError("Neįmanoma automatiškai nustatyti trimestrų/pusmečių laikotarpių!")

            half = len(date_quick_select_elems) // 2
            dates = []
            for e in date_quick_select_elems:
                date = datetime.datetime.strptime(e.attrib["href"], "%Y-%m-%d")
                dates.append(date.replace(tzinfo=datetime.timezone.utc))
            new_dates = []
            for i in range(half - 1):
                new_dates.append((dates[:half][i], dates[half:][i]))
            return ClassAveragesReportGenerator(self, class_id, new_dates)

        # Otherwise, return a list of Class classes for selection
        classes = []
        class_select_elem: ElementBase = form.find(".//select[@id='ClassNormal']") # type: ignore
        for opt in class_select_elem.getchildren():
            assert isinstance(opt, etree._Element)
            value = opt.attrib["value"]
            if value == "0":
                continue
            classes.append(Class(value, opt.text.strip()))
        return classes

    def generate_group_report(
        self,
        group_id: str,
        term_start: datetime.datetime,
        term_end: datetime.datetime
    ) -> str:
        """Generates averages report for specified class and period.
        Returns a path to the generated file."""
        date_from = term_start.strftime("%Y-%m-%d")
        date_to = term_end.strftime("%Y-%m-%d")
        req_dict = {
            "ReportNormal": "81", # Generate group report
            "GroupNormal": group_id,
            "DateFromNormal": date_from,
            "DateToNormal": date_to,
            "FileTypeNormal": "0",
            "submitNormal": ""
        }

        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp = now.timestamp()

        # This handles cache
        for file in os.listdir(get_temp_dir()):
            file_path = os.path.join(get_temp_dir(), file)

            # Remove files which are a week old based on filesystem reporting
            if timestamp - 60 * 60 * 24 * 7 > os.path.getmtime(file_path):
                os.remove(file_path)
                continue

            # Handle still potentially cached files
            split = file[1:].split("_")
            f_group_id, period_start, period_end, time_generated = split
            if file[0] == "g" and f_group_id == group_id and period_start == date_from and period_end == date_to:
                if timestamp - 60 * 60 < int(time_generated.split(".")[0]):
                    return file_path
                os.remove(file_path)

        file_name = f'g{group_id}_{date_from}_{date_to}_{int(timestamp)}.xls'
        file_path = os.path.join(get_temp_dir(), file_name)

        request = self.request(
            "POST", self.BASE_URL + f"/1/lt/page/report/choose_normal/81/{group_id}",
            req_dict, timeout=60
        )
        with open(file_path, "wb") as f:
            f.write(request.content)
        return file_path

    def generate_class_averages_report(
        self,
        class_id: str,
        term_start: datetime.datetime,
        term_end: datetime.datetime
    ) -> str:
        """Generates averages report for specified class and period.
        Returns a path to the generated file."""
        date_from = term_start.strftime("%Y-%m-%d")
        date_to = term_end.strftime("%Y-%m-%d")
        req_dict = {
            "ReportNormal": "12", # Generate averages report
            "ClassNormal": class_id,
            "PupilNormal": "0", # Select all pupils
            "ShowCourseNormal": "0",
            "DateFromNormal": date_from,
            "DateToNormal": date_to,
            "FileTypeNormal": "0",
            "submitNormal": ""
        }

        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp = now.timestamp()

        # This handles cache
        for file in os.listdir(get_temp_dir()):
            file_path = os.path.join(get_temp_dir(), file)

            # Remove files which are a week old based on filesystem reporting
            if timestamp - 60 * 60 * 24 * 7 > os.path.getmtime(file_path):
                os.remove(file_path)
                continue

            # Handle still potentially cached files
            split = file.split("_")
            f_class_id, period_start, period_end, time_generated = split
            if f_class_id == class_id and period_start == date_from and period_end == date_to:
                if timestamp - 60 * 60 < int(time_generated.split(".")[0]):
                    return file_path
                os.remove(file_path)

        file_name = f'{class_id}_{date_from}_{date_to}_{int(timestamp)}.xls'
        file_path = os.path.join(get_temp_dir(), file_name)

        request = self.request(
            "POST", self.BASE_URL + f"/1/lt/page/report/choose_normal/12/{class_id}",
            req_dict, timeout=60
        )
        with open(file_path, "wb") as f:
            f.write(request.content)
        return file_path
