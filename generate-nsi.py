import os
import sys
from typing import List

DEFINITIONS = {
    "APP_NAME": "Mokinių pasiekimų ir lankomumo stebėsenos sistema",
    "COMP_NAME": "Dominykas Svetikas",
    "VERSION": "1.1.4.0",
    "COPYRIGHT": "Dominykas Svetikas © 2022",
    "DESCRIPTION": "Application",
    "INSTALLER_NAME": "Analizatorius.exe",
    "MAIN_APP_EXE": "main.exe",
    "INSTALL_TYPE": "SetShellVarContext current",
    "REG_ROOT": "HKCU",
    "REG_APP_PATH": "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\${MAIN_APP_EXE}",
    "UNINSTALL_PATH": "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}",
    "INSTALL_PATH": "$PROGRAMFILES\\Pagalbukas-Analizatorius"
}

class NSIScript:
    
    def __init__(self) -> None:
        self.string = ""

    def define(self, name: str, value: str):
        self.string += f'!define {name} "{value}"\n'
        self.directory_list: List[str] = []
        self.file_list: List[str] = []

    def set_version_data(self):
        self.string += (
            'VIProductVersion  "${VERSION}"\n'
            'VIAddVersionKey "ProductName"  "${APP_NAME}"\n'
            'VIAddVersionKey "CompanyName"  "${COMP_NAME}"\n'
            'VIAddVersionKey "LegalCopyright"  "${COPYRIGHT}"\n'
            'VIAddVersionKey "FileDescription"  "${DESCRIPTION}"\n'
            'VIAddVersionKey "FileVersion"  "${VERSION}"\n'
        )

    def set_installer(self):
        self.string += (
            'SetCompressor ZLIB\n'
            'Name "${APP_NAME}"\n'
            'Caption "${APP_NAME}"\n'
            'OutFile "${INSTALLER_NAME}"\n'
            'BrandingText "${APP_NAME}"\n'
            'XPStyle on\n'
            'InstallDirRegKey "${REG_ROOT}" "${REG_APP_PATH}" ""\n'
            'InstallDir "${INSTALL_PATH}"\n'
        )

    def set_language(self):
        self.string += (
            '!include "MUI.nsh"\n'

            '!define MUI_ABORTWARNING\n'
            '!define MUI_UNABORTWARNING\n'

            '!define MUI_LANGDLL_REGISTRY_ROOT "${REG_ROOT}"\n'
            '!define MUI_LANGDLL_REGISTRY_KEY "${UNINSTALL_PATH}"\n'
            '!define MUI_LANGDLL_REGISTRY_VALUENAME "Installer Language"\n'

            '!define MUI_WELCOMEPAGE_TITLE_3LINES\n'
            '!define MUI_FINISHPAGE_TITLE_3LINES\n'
            '!insertmacro MUI_PAGE_WELCOME\n'

            '!ifdef LICENSE_TXT\n'
            '!insertmacro MUI_PAGE_LICENSE "${LICENSE_TXT}"\n'
            '!endif\n'

            '!insertmacro MUI_PAGE_DIRECTORY\n'

            '!ifdef REG_START_MENU\n'
            '!define MUI_STARTMENUPAGE_NODISABLE\n'
            '!define MUI_STARTMENUPAGE_DEFAULTFOLDER "${APP_NAME}"\n'
            '!define MUI_STARTMENUPAGE_REGISTRY_ROOT "${REG_ROOT}"\n'
            '!define MUI_STARTMENUPAGE_REGISTRY_KEY "${UNINSTALL_PATH}"\n'
            '!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "${REG_START_MENU}"\n'
            '!insertmacro MUI_PAGE_STARTMENU Application $SM_Folder\n'
            '!endif\n'

            '!insertmacro MUI_PAGE_INSTFILES\n'
            '!insertmacro MUI_PAGE_FINISH\n'
            '!define MUI_WELCOMEPAGE_TITLE_3LINES\n'
            '!define MUI_FINISHPAGE_TITLE_3LINES\n'
            '!insertmacro MUI_UNPAGE_CONFIRM\n'
            '!insertmacro MUI_UNPAGE_INSTFILES\n'
            '!insertmacro MUI_UNPAGE_FINISH\n'
            '!insertmacro MUI_LANGUAGE "Lithuanian"\n'
            '!insertmacro MUI_RESERVEFILE_LANGDLL\n'
        )

    def set_install_registry(self):
        self.string += (
            'Section -Icons_Reg\n'
            'SetOutPath "$INSTDIR"\n'
            'WriteUninstaller "$INSTDIR\\uninstall.exe"\n'

            '!ifdef REG_START_MENU\n'
            '!insertmacro MUI_STARTMENU_WRITE_BEGIN Application\n'
            'CreateDirectory "$SMPROGRAMS\\$SM_Folder"\n'
            'CreateShortCut "$SMPROGRAMS\\$SM_Folder\${APP_NAME}.lnk" "$INSTDIR\\${MAIN_APP_EXE}"\n'
            'CreateShortCut "$DESKTOP\\${APP_NAME}.lnk" "$INSTDIR\${MAIN_APP_EXE}"\n'
            'CreateShortCut "$SMPROGRAMS\\$SM_Folder\\Uninstall ${APP_NAME}.lnk" "$INSTDIR\\uninstall.exe"\n'
            '!insertmacro MUI_STARTMENU_WRITE_END\n'
            '!endif\n'

            '!ifndef REG_START_MENU\n'
            'CreateDirectory "$SMPROGRAMS\\${APP_NAME}"\n'
            'CreateShortCut "$SMPROGRAMS\\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\\${MAIN_APP_EXE}"\n'
            'CreateShortCut "$DESKTOP\\${APP_NAME}.lnk" "$INSTDIR\\${MAIN_APP_EXE}"\n'
            'CreateShortCut "$SMPROGRAMS\\${APP_NAME}\\Uninstall ${APP_NAME}.lnk" "$INSTDIR\\uninstall.exe"\n'
            '!endif\n'

            'WriteRegStr ${REG_ROOT} "${REG_APP_PATH}" "" "$INSTDIR\\${MAIN_APP_EXE}"\n'
            'WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "DisplayName" "${APP_NAME}"\n'
            'WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "UninstallString" "$INSTDIR\\uninstall.exe"\n'
            'WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "DisplayIcon" "$INSTDIR\\${MAIN_APP_EXE}"\n'
            'WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "DisplayVersion" "${VERSION}"\n'
            'WriteRegStr ${REG_ROOT} "${UNINSTALL_PATH}"  "Publisher" "${COMP_NAME}"\n'

            'SectionEnd\n'
        )

    def set_uninstall_registry(self):
        self.string += (
            '!ifdef REG_START_MENU\n'
            '!insertmacro MUI_STARTMENU_GETFOLDER "Application" $SM_Folder\n'
            'Delete "$SMPROGRAMS\\$SM_Folder\\${APP_NAME}.lnk"\n'
            'Delete "$SMPROGRAMS\\$SM_Folder\\Uninstall ${APP_NAME}.lnk"\n'
            'Delete "$DESKTOP\\${APP_NAME}.lnk"\n'

            'RmDir "$SMPROGRAMS\\$SM_Folder"\n'
            '!endif\n'

            '!ifndef REG_START_MENU\n'
            'Delete "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"\n'
            'Delete "$SMPROGRAMS\\${APP_NAME}\\Uninstall ${APP_NAME}.lnk"\n'
            'Delete "$DESKTOP\\${APP_NAME}.lnk"\n'

            'RmDir "$SMPROGRAMS\\${APP_NAME}"\n'
            '!endif\n'

            'DeleteRegKey ${REG_ROOT} "${REG_APP_PATH}"\n'
            'DeleteRegKey ${REG_ROOT} "${UNINSTALL_PATH}"\n'
            'SectionEnd\n'
        )

    def add_output_path(self, output_path: str):
        self.string += f'SetOutPath "{output_path}"\n'
        self.directory_list.append(output_path)

    def add_file(self, file_path: str):
        self.string += f'File "{file_path}"\n'
        self.file_list.append(file_path)

    def remove_file(self, file_path: str):
        self.string += f'Delete "{file_path}"\n'

    def remove_dir(self, output_path: str):
        self.string += f'RmDir "{output_path}"\n'

def create_definition(name: str, value: str) -> str:
    return f'!define {name} "{value}"\n'

def generate_definitions() -> str:
    string = ""
    for definition in DEFINITIONS.keys():
        string += create_definition(definition, DEFINITIONS[definition])
    return string


def main(args: List[str]):

    if len(args) < 2:
        sys.exit("Distribution directory not specified")

    if not os.path.exists(args[1]):
        sys.exit("Specified directory does not exist")

    if len(args) == 3:
        DEFINITIONS['INSTALLER_NAME'] = args[2]
        print(f"Set installer name to '{args[2]}'")

    script = NSIScript()

    for definition in DEFINITIONS.keys():
        script.define(definition, DEFINITIONS[definition])

    script.set_version_data()
    script.set_installer()
    script.set_language()

    # set up installer file index
    script.string += (
        'Section -MainProgram\n'
        '${INSTALL_TYPE}\n'
        'SetOverwrite ifnewer\n'
    )
    for cur, _, files in os.walk(args[1]):
        clean_cur = cur.replace(args[1], "$INSTDIR", 1)
        script.add_output_path(clean_cur)
        for file in files:
            script.add_file(os.path.join(cur, file))
    script.string += "SectionEnd\n"

    # setup install registry
    script.set_install_registry()

    # Uninstall files
    script.string += (
        'Section Uninstall\n'
        '${INSTALL_TYPE}\n'
    )
    for file in script.file_list:
        script.remove_file(file.replace(args[1], "$INSTDIR", 1))

    for dir in  sorted(script.directory_list, reverse=True):
        path = dir.replace(args[1], "$INSTDIR", 1)
        if path != "$INSTDIR":
            script.remove_dir(path)
    script.string += (
        'Delete "$INSTDIR\\uninstall.exe"\n'
        'RmDir "$INSTDIR"\n'
    )

    script.set_uninstall_registry()

    # This is required for NSIS to parse UTF-8 strings, the BOM signature
    with open("install-script.nsi", encoding='utf-8-sig', mode="w") as f:
        f.write(script.string)

if __name__ == "__main__":
    main(sys.argv)