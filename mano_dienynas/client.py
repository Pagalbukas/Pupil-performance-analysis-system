from __future__ import annotations

import datetime
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
        self._client.request("GET", self._client.BASE_URL + self.url)

    def get_class_id(self) -> Optional[str]:
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

    def request(self, method: str, url: str, data: dict = None) -> Response:
        return requests.request(method, url, data=data, headers=self.HEADERS, cookies=self.cookies)

    def login(self, email: str, password: str) -> bool:
        """Attempts to login to manodienynas.lt platform.\n
        Returns boolean on whether the operation was successful."""
        request = self.request("POST", self.BASE_URL + "/1/lt/ajax/user/login", {
            'username': email,
            'password': password,
            'dienynas_remember_me': 1
        })
        loginResponse = request.json()
        if loginResponse.get('message') is not False:
            return False

        self.cookies["PHPSESSID"] = request.cookies['PHPSESSID']
        self.cookies["PAS"] = request.cookies['pas']
        self.cookies["username"] = request.cookies['username']
        return True

    def get_user_roles(self) -> List[UserRole]:
        """Returns a list of user role objects."""
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

    def generate_class_averages_report(
        self,
        group_id: int,
        term_start: datetime.datetime,
        term_end: datetime.datetime,
        file_path: str = None
    ) -> None:
        req_dict = {
            "ReportNormal": "12", # Generate averages report
            "ClassNormal": str(group_id),
            "PupilNormal": "0", # Select all pupils
            "ShowCourseNormal": "0",
            "DateFromNormal": term_start.strftime("%Y-%m-%d"),
            "DateToNormal": term_end.strftime("%Y-%m-%d"),
            "FileTypeNormal": "0",
            "submitNormal": ""
        }
        req_dict["DateFromNormal"] = "2022-01-01"

        request = self.request("POST", self.BASE_URL + f"/1/lt/page/report/choose_normal/12/{group_id}", req_dict)
        with open("failas.xls", "wb") as f:
            f.write(request.content)
