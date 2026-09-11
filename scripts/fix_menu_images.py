"""
Attach curated Wikimedia Commons images to the seeded menu items.

Fills every food that has no image and overwrites the few that the automatic
first pass picked badly (e.g. Sambar -> a deer skeleton). Polite: one request
at a time with a delay, so Commons does not rate-limit us.

Run from Backend/ with the project venv:

    ../food_env/Scripts/python.exe scripts/fix_menu_images.py
"""

import io
import os
import sys
import time

import django
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from PIL import Image  # noqa: E402

from foods.models import Food  # noqa: E402
from restaurants.models import Restaurant  # noqa: E402

OWNER_EMAIL = "harshithc2097@gmail.com"
DELAY = 1.6
UA = {"User-Agent": "RayalseemaMenuSeed/1.0 (local educational seed; contact site owner)"}

# food name -> Commons File name (without the "File:" prefix)
IMAGES = {
    "Hyderabadi Chicken Dum Biryani": "Hyderabadi Chicken Biryani.jpg",
    "Mutton Dum Biryani": "Mutton Biriyani.jpg",
    "Curd Rice": "Curd rice.jpg",
    "Pulihora": "Tamarind rice.jpg",
    "Natu Kodi Pulusu": "Natu kodi pulusu.jpg",
    "Ragi Sangati with Natu Kodi Pulusu": "Ragi mudda with Natukodi pulusu.jpg",
    "Gongura Mutton": "Mutton curry.jpg",
    "Kodi Vepudu": "Chicken fry.jpg",
    "Ulavacharu with Rice": "Kollu rasam.JPG",
    "Gutti Vankaya Kura": "Gutti Vankaya Kura.jpg",
    "Andhra Veg Thali": "South Indian Thali.jpg",
    "Pappu (Toor Dal)": "Toor dal.jpg",
    "Bendakaya Fry": "Bhindi Masala.jpg",
    "Sambar": "Idli with sambar and chutney.jpg",
    "Apollo Fish": "Chilli fish.jpg",
    "Fish Fry": "Indian Style Fish Fry.jpg",
    "Chicken Majestic": "Chicken 65.jpg",
    "Qubani Ka Meetha": "Qubani ka Meetha ( Apricot Sauce with Custard ).jpg",
    "Bobbatlu (2 pcs)": "Puran Poli.jpg",
    "Semiya Payasam": "Semiya Payasam.jpg",
    "Filter Coffee": "Filter Coffee.jpg",
    "Spiced Buttermilk": "Buttermilk.jpg",
}

# these had a wrong/weak auto-picked image and must be replaced even if set
FORCE = {
    "Hyderabadi Chicken Dum Biryani",
    "Mutton Dum Biryani",
    "Sambar",
    "Apollo Fish",
    "Fish Fry",
    "Chicken Majestic",
}


def download(commons_file):
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + commons_file.replace(" ", "_")
    resp = requests.get(url, params={"width": 900}, headers=UA, timeout=60, allow_redirects=True)
    resp.raise_for_status()
    if not resp.headers.get("content-type", "").startswith("image"):
        raise ValueError(f"not an image: {resp.headers.get('content-type')}")
    Image.open(io.BytesIO(resp.content)).verify()
    im = Image.open(io.BytesIO(resp.content)).convert("RGB")
    im.thumbnail((900, 900))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def run():
    restaurant = Restaurant.objects.filter(owner__email__iexact=OWNER_EMAIL).first()
    if restaurant is None:
        raise SystemExit(f"No restaurant for {OWNER_EMAIL}")

    done = skipped = failed = 0
    for name, commons_file in IMAGES.items():
        food = Food.objects.filter(restaurant=restaurant, name=name).first()
        if food is None:
            print(f"  ?? no food row named {name!r}")
            continue
        if food.image and name not in FORCE:
            skipped += 1
            continue
        try:
            data = download(commons_file)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  !! {name}: {exc}")
            time.sleep(DELAY)
            continue
        slug = name.lower().replace(" ", "-").replace("(", "").replace(")", "")
        food.image.save(f"{slug}.jpg", ContentFile(data), save=True)
        done += 1
        print(f"  ok {name}  <-  {commons_file}  ({len(data) // 1024} KB)")
        time.sleep(DELAY)

    total = Food.objects.filter(restaurant=restaurant).count()
    with_img = Food.objects.filter(restaurant=restaurant).exclude(image="").count()
    print(f"\nUpdated {done}, kept {skipped}, failed {failed}.")
    print(f"{with_img}/{total} menu items now have an image.")


if __name__ == "__main__":
    run()
