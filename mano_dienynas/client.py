from __future__ import annotations

import datetime
import os
import requests

from lxml import etree
from lxml.etree import _ElementTree, ElementBase
from io import StringIO
from requests.models import Response
from typing import List, Optional

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

    def change_role(self) -> None:
        """Changes current client role to this one."""
        self._client.request("GET", self._client.BASE_URL + self.url)

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

class Client:
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Safari/537.36' # noqa 501
    }

    def __init__(self, base_url: str = "https://www.manodienynas.lt") -> None:
        self.BASE_URL = base_url
        self.cookies = {}

        self._session_expires = None
        self._cached_roles = []

    @property
    def is_logged_in(self) -> bool:
        if self._session_expires is None:
            return False
        # Consider session expired after 600 seconds
        return datetime.datetime.now(datetime.timezone.utc).timestamp() - self._session_expires.timestamp() < 600

    def request(self, method: str, url: str, data: dict = None, no_cookies: bool = False) -> Response:
        if no_cookies:
            return requests.request(method, url, data=data, headers=self.HEADERS)
        return requests.request(method, url, data=data, headers=self.HEADERS, cookies=self.cookies)

    def logout(self) -> None:
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
        loginResponse = request.json()
        if loginResponse.get('message') is not False:
            return False

        self._session_expires = datetime.datetime.now(datetime.timezone.utc)
        self.cookies["PHPSESSID"] = request.cookies['PHPSESSID']
        self.cookies["PAS"] = request.cookies['pas']
        self.cookies["username"] = request.cookies['username']
        return True

    def get_filtered_user_roles(self) -> List[UserRole]:
        roles = self.get_user_roles()
        return [
            r for r in roles
            if r.title == "Klasės vadovas" or r.title == "Sistemos administratorius"
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
            elem: ElementBase
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

    def get_class_averages_report_options(self, class_id: str = None) -> Response:
        """Returns response for selecting monthly averages report."""
        if class_id is None:
            r = self.request("GET", self.BASE_URL + "/1/lt/page/report/choose_normal/12")
        else:
            r = self.request("GET", self.BASE_URL + "/1/lt/page/report/choose_normal/12/" + class_id)

        tree: _ElementTree = etree.parse(StringIO(r.text), PARSER)
        form: ElementBase = tree.find("//form[@name='reportNormalForm']")

        class_select_elem: ElementBase = form.find(".//select[@id='ClassNormal']")
        date_quick_select_elems: List[ElementBase] = form.xpath(".//a[@class='termDateSetter whiteButton']")

        print(date_quick_select_elems)

        classes = []
        for opt in class_select_elem.getchildren():
            opt: ElementBase
            value = opt.attrib["value"]
            if value == "0":
                continue
            classes.append(Class(value, opt.text.strip()))
        print(classes)
        return None

    def generate_class_monthly_averages_report(
        self,
        group_id: str,
    ) -> List[str]:

        def get_first_date(date: datetime.datetime):
            return datetime.datetime(date.year, date.month, 1)

        def get_last_date(date: datetime.datetime):
            return datetime.datetime(date.year, date.month, date.day)

        current_date = datetime.datetime.now(tz=datetime.timezone.utc)

        dates = [(get_first_date(current_date), get_last_date(current_date))]
        analysed_date = current_date
        while analysed_date.month != 9:
            analysed_date = analysed_date.replace(day=1) - datetime.timedelta(days=1)
            dates.append((get_first_date(analysed_date), get_last_date(analysed_date)))

        paths = []
        for date in dates:
            paths.append(self.generate_class_averages_report(group_id, date[0], date[1]))
        return paths

    def generate_class_averages_report(
        self,
        group_id: str,
        term_start: datetime.datetime,
        term_end: datetime.datetime
    ) -> str:
        date_from = term_start.strftime("%Y-%m-%d")
        date_to = term_end.strftime("%Y-%m-%d")
        req_dict = {
            "ReportNormal": "12", # Generate averages report
            "ClassNormal": group_id,
            "PupilNormal": "0", # Select all pupils
            "ShowCourseNormal": "0",
            "DateFromNormal": date_from,
            "DateToNormal": date_to,
            "FileTypeNormal": "0",
            "submitNormal": ""
        }

        file_name = f'{group_id}_{date_from}_{date_to}_{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}.xls'
        if not os.path.exists(".temp"):
            os.mkdir(".temp")
        file_path = os.path.join(".temp", file_name)

        request = self.request("POST", self.BASE_URL + f"/1/lt/page/report/choose_normal/12/{group_id}", req_dict)
        with open(file_path, "wb") as f:
            f.write(request.content)
        return file_path
