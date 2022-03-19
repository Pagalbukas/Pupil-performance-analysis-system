import datetime
import getpass

from mano_dienynas.client import Client
from settings import Settings

settings = Settings()

email = input("El. paštas: ")
password = getpass.getpass("Slaptažodis: ")

settings.username = email
settings.password = password
settings.save()

# Log in to the client
client = Client("https://www.manodienynas.lt")
success = client.login(settings.username, settings.password)
if not success:
    exit("Prisijungimas nepavyko")
print("Prisijungimas pavyko")

roles = client.get_user_roles()
filtered_roles = [r for r in roles if r.title == "Klasės vadovas" or r.title == "Sistemos administratorius"]

if len(filtered_roles) == 0:
    exit("Paskyra neturi vartotojo teisių. Kol kas palaikomos tik paskyros su 'Klasės vadovas' ir 'Sistemos administratorius' tipais.")

elif len(filtered_roles) == 1:
    selected_role = filtered_roles[0]

else:
    print("Rasti keli tinkami paskyros tipai, pasirinkite vieną:")
    for i, role in enumerate(filtered_roles):

        title = role.title
        if role.classes is not None:
            title += " " + role.classes

        print(f"{i + 1})", title, f"({role.school_name})")

    while True:
        val = input("Pasirinkite vieną paskyros tipą (skaičius): ")
        try:
            val = int(val)
        except ValueError:
            continue

        if val > len(filtered_roles) or val == 0:
            continue
        break
    selected_role = filtered_roles[val - 1]

# Change role to the selected one
if not selected_role.is_active:
    selected_role.change_role()
print(f"Pasirinktas tipas '{selected_role.title}'")

# Fetch data
#date = datetime.today().strftime('%Y-%m-%d')
response = client.get_class_averages_report_options(selected_role.get_class_id())

print(response)
exit()

for option in a.find(".//select[@name='ClassNormal']").getchildren()[1:2]:
    group = int(option.text)
    group_id = int(option.attrib['value'])
    print(f"Pasirinkta klasė: {group}")
    client.generate_class_averages_report(
        group_id,
        datetime.datetime.now(datetime.timezone.utc), datetime.datetime.now(datetime.timezone.utc)
    )
