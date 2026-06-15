import requests
from dotenv import load_dotenv
import os

load_dotenv()

clientes = {
    "ecosmart": {"token": os.getenv("ECOSMART_TOKEN"), "location_id": os.getenv("ECOSMART_ID")},
    "tiresias": {"token": os.getenv("TIRESIAS_TOKEN"), "location_id": os.getenv("TIRESIAS_ID")},
}

for nombre, datos in clientes.items():
    token = datos["token"]
    loc = datos["location_id"]
    headers = {"Authorization": f"Bearer {token}", "Version": "2021-07-28"}

    print(f"\n=== {nombre.upper()} ===")

    r = requests.get(f"https://services.leadconnectorhq.com/contacts/", headers=headers, params={"locationId": loc, "limit": 1})
    print(f"Contactos: {r.status_code} - total: {r.json().get('total', 'N/A')}")

    r2 = requests.get(f"https://services.leadconnectorhq.com/calendars/events", headers=headers, params={"locationId": loc})
    print(f"Calendario: {r2.status_code} - {r2.text[:100]}")
