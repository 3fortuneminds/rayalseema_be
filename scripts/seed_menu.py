"""
Seed a South Indian menu (veg + non-veg) for the restaurant owned by
harshithc2097@gmail.com so it shows up in the customer dashboard.

Run from the Backend/ directory with the project venv:

    ../food_env/Scripts/python.exe scripts/seed_menu.py

Idempotent: re-running updates existing rows instead of duplicating them.
Images are fetched from Wikimedia Commons (freely licensed) into media/foods/.
Pass --no-images to skip image downloads.
"""

import io
import os
import sys

import django
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from PIL import Image  # noqa: E402

from foods.models import Food, FoodCategory, FoodVariant  # noqa: E402
from restaurants.models import Restaurant  # noqa: E402

OWNER_EMAIL = "harshithc2097@gmail.com"
NO_IMAGES = "--no-images" in sys.argv

UA = {"User-Agent": "RayalseemaMenuSeed/1.0 (local dev seed script)"}
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def fetch_image(terms):
    """Return (jpeg_bytes, source_title) for the first search term that yields a
    usable Commons image, or (None, None)."""
    for term in terms:
        try:
            resp = requests.get(
                COMMONS_API,
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": f"filetype:bitmap {term}",
                    "gsrnamespace": "6",
                    "gsrlimit": "8",
                    "prop": "imageinfo",
                    "iiprop": "url|mime",
                    "iiurlwidth": "800",
                    "format": "json",
                },
                headers=UA,
                timeout=30,
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            for page in sorted(pages.values(), key=lambda p: p.get("index", 99)):
                info = (page.get("imageinfo") or [{}])[0]
                if info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
                    continue
                url = info.get("thumburl") or info.get("url")
                if not url:
                    continue
                img_resp = requests.get(url, headers=UA, timeout=60)
                if img_resp.status_code != 200 or not img_resp.content:
                    continue
                try:
                    Image.open(io.BytesIO(img_resp.content)).verify()
                    im = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                except Exception:
                    continue
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=85)
                return buf.getvalue(), page.get("title", "")
        except Exception as exc:  # noqa: BLE001
            print(f"   ! image lookup failed for '{term}': {exc}")
    return None, None


# category name -> display_order
CATEGORIES = [
    ("Tiffins", 1),
    ("Biryani & Rice", 2),
    ("Rayalaseema Specials", 3),
    ("Andhra Meals & Curries", 4),
    ("Seafood & Starters", 5),
    ("Desserts & Beverages", 6),
]

# category, name, description, price, is_veg, [image search terms], [variants]
MENU = [
    # ---------- Tiffins ----------
    ("Tiffins", "Idli (2 pcs)", "Steamed rice-and-urad-dal cakes, served with sambar and coconut chutney.", 60, True,
     ["idli sambar", "idli"], []),
    ("Tiffins", "Medu Vada (2 pcs)", "Crisp golden urad-dal doughnuts, fluffy inside, with chutney and sambar.", 70, True,
     ["medu vada", "vada sambar"], []),
    ("Tiffins", "Masala Dosa", "Crisp rice crepe wrapped around spiced potato masala, with chutneys and sambar.", 110, True,
     ["masala dosa", "dosa"], []),
    ("Tiffins", "Rava Dosa", "Lacy, crunchy semolina crepe tempered with cumin, ginger and green chilli.", 120, True,
     ["rava dosa", "onion rava dosa"], []),
    ("Tiffins", "Onion Uttapam", "Thick soft pancake topped with onions, green chilli and coriander.", 110, True,
     ["uttapam", "onion uttapam"], []),
    ("Tiffins", "Ghee Pongal", "Comforting rice-and-moong-dal pongal with black pepper, cumin, cashew and ghee.", 90, True,
     ["ven pongal", "pongal dish"], []),

    # ---------- Biryani & Rice ----------
    ("Biryani & Rice", "Hyderabadi Chicken Dum Biryani",
     "Long-grain basmati layered with marinated chicken, saffron and fried onions, sealed and dum-cooked.", 320, False,
     ["hyderabadi chicken biryani", "chicken biryani"],
     [("Half", 200, False), ("Full", 320, True)]),
    ("Biryani & Rice", "Mutton Dum Biryani",
     "Slow-cooked mutton biryani with whole spices, mint and caramelised onions.", 380, False,
     ["mutton biryani", "lamb biryani"],
     [("Half", 240, False), ("Full", 380, True)]),
    ("Biryani & Rice", "Egg Biryani", "Fragrant biryani rice tossed with spiced boiled eggs and herbs.", 180, False,
     ["egg biryani"], []),
    ("Biryani & Rice", "Vegetable Dum Biryani",
     "Basmati dum-cooked with mixed vegetables, paneer, mint and biryani masala.", 190, True,
     ["vegetable biryani", "veg biryani"], []),
    ("Biryani & Rice", "Curd Rice", "Soft rice folded with fresh curd, tempered with mustard, curry leaf and ginger.", 90, True,
     ["curd rice", "thayir sadam"], []),
    ("Biryani & Rice", "Pulihora", "Tangy tamarind rice with peanuts, sesame and a sesame-oil tempering.", 90, True,
     ["tamarind rice", "pulihora"], []),

    # ---------- Rayalaseema Specials ----------
    ("Rayalaseema Specials", "Natu Kodi Pulusu",
     "Country chicken simmered in a fiery Rayalaseema-style tamarind and stone-ground spice gravy.", 340, False,
     ["chicken curry andhra", "natu kodi", "country chicken curry"], []),
    ("Rayalaseema Specials", "Ragi Sangati with Natu Kodi Pulusu",
     "Finger-millet mudde served with spicy country chicken curry - a Rayalaseema staple.", 360, False,
     ["ragi mudde", "ragi sangati", "finger millet ball"], []),
    ("Rayalaseema Specials", "Gongura Mutton",
     "Mutton cooked with tangy gongura (sorrel) leaves and roasted red chillies.", 400, False,
     ["gongura mutton", "mutton curry andhra"], []),
    ("Rayalaseema Specials", "Kodi Vepudu",
     "Dry chicken fry roasted with curry leaves, black pepper and freshly pounded masala.", 300, False,
     ["chicken fry andhra", "chicken vepudu", "kodi vepudu"], []),
    ("Rayalaseema Specials", "Ulavacharu with Rice",
     "Rich horse-gram broth, a Rayalaseema delicacy, served with steamed rice and ghee.", 160, True,
     ["ulavacharu", "horse gram soup"], []),
    ("Rayalaseema Specials", "Gutti Vankaya Kura",
     "Baby brinjals stuffed with peanut-sesame masala and cooked in a thick gravy.", 150, True,
     ["gutti vankaya", "stuffed brinjal curry", "bharli vangi"], []),

    # ---------- Andhra Meals & Curries ----------
    ("Andhra Meals & Curries", "Andhra Veg Thali",
     "Full meal - rice, pappu, two curries, sambar, rasam, curd, pickle, papad and sweet.", 180, True,
     ["south indian thali", "andhra meals", "vegetarian thali"], []),
    ("Andhra Meals & Curries", "Pappu (Toor Dal)",
     "Andhra-style toor dal with tomato or greens, finished with a garlic-red-chilli tempering.", 120, True,
     ["toor dal", "dal curry", "pappu"], []),
    ("Andhra Meals & Curries", "Bendakaya Fry",
     "Okra stir-fried till crisp with onions and mild Andhra spice.", 130, True,
     ["bhindi fry", "okra fry", "lady finger fry"], []),
    ("Andhra Meals & Curries", "Aloo Fry",
     "Potato cubes shallow-fried with turmeric, chilli and curry leaves.", 120, True,
     ["potato fry", "aloo fry", "aloo roast"], []),
    ("Andhra Meals & Curries", "Sambar", "Lentil stew with vegetables, tamarind and sambar masala.", 60, True,
     ["sambar", "sambhar"], []),
    ("Andhra Meals & Curries", "Rasam", "Peppery tamarind rasam with tomato, garlic and crushed pepper-cumin.", 50, True,
     ["rasam", "tomato rasam"], []),

    # ---------- Seafood & Starters ----------
    ("Seafood & Starters", "Apollo Fish",
     "Boneless fish tossed with curry leaves, green chilli and a tangy Hyderabadi glaze.", 320, False,
     ["apollo fish", "fish fry chilli"], []),
    ("Seafood & Starters", "Royyala Vepudu",
     "Prawns roasted dry with onions, curry leaves and coarse Andhra masala.", 360, False,
     ["prawn fry", "prawn roast", "royyala vepudu"], []),
    ("Seafood & Starters", "Chicken 65",
     "Spicy deep-fried chicken bites tempered with curry leaf, garlic and green chilli.", 240, False,
     ["chicken 65"], []),
    ("Seafood & Starters", "Fish Fry",
     "Marinated fish fillets pan-fried with a crisp rava-and-spice crust.", 300, False,
     ["fish fry indian", "masala fish fry"], []),
    ("Seafood & Starters", "Gobi 65",
     "Crisp cauliflower florets in a tangy, spiced batter with a curry-leaf toss.", 180, True,
     ["gobi 65", "cauliflower 65", "gobi manchurian"], []),
    ("Seafood & Starters", "Chicken Majestic",
     "Strips of fried chicken tossed with fried green chilli, curd and curry leaves.", 260, False,
     ["chicken majestic", "chicken fry hyderabad"], []),

    # ---------- Desserts & Beverages ----------
    ("Desserts & Beverages", "Double Ka Meetha",
     "Hyderabadi bread pudding soaked in saffron milk and sugar syrup, topped with nuts.", 120, True,
     ["double ka meetha", "shahi tukda"], []),
    ("Desserts & Beverages", "Qubani Ka Meetha",
     "Stewed dried apricots served warm with a swirl of fresh cream.", 130, True,
     ["qubani ka meetha", "apricot dessert"], []),
    ("Desserts & Beverages", "Bobbatlu (2 pcs)",
     "Griddled flatbread stuffed with a sweet chana-dal and jaggery filling.", 90, True,
     ["puran poli", "bobbatlu", "obbattu"], []),
    ("Desserts & Beverages", "Semiya Payasam",
     "Vermicelli simmered in milk with cardamom, cashew and raisins.", 90, True,
     ["semiya payasam", "vermicelli kheer"], []),
    ("Desserts & Beverages", "Filter Coffee",
     "South Indian filter coffee, decoction and hot milk, served frothy in a tumbler.", 40, True,
     ["filter coffee", "indian filter coffee"], []),
    ("Desserts & Beverages", "Spiced Buttermilk",
     "Chilled churned buttermilk with ginger, curry leaf, coriander and a pinch of salt.", 40, True,
     ["buttermilk drink", "masala chaas", "majjiga"], []),
]


def run():
    restaurant = Restaurant.objects.filter(owner__email__iexact=OWNER_EMAIL).first()
    if restaurant is None:
        raise SystemExit(f"No restaurant found for owner {OWNER_EMAIL}")

    changed = []
    if not restaurant.is_approved:
        restaurant.is_approved = True
        changed.append("is_approved=True")
    if not restaurant.is_active:
        restaurant.is_active = True
        changed.append("is_active=True")
    if changed:
        restaurant.save(update_fields=["is_approved", "is_active", "updated_at"])
    print(f"Restaurant: {restaurant.name} (slug={restaurant.slug}) {'- ' + ', '.join(changed) if changed else '- no change'}")

    cats = {}
    for name, order in CATEGORIES:
        cat, _ = FoodCategory.objects.update_or_create(
            restaurant=restaurant, name=name, defaults={"display_order": order}
        )
        cats[name] = cat
    print(f"Categories ready: {len(cats)}")

    for cat_name, name, desc, price, is_veg, img_terms, variants in MENU:
        food, created = Food.objects.get_or_create(
            restaurant=restaurant, name=name, defaults={"base_price": price}
        )
        food.category = cats[cat_name]
        food.description = desc
        food.base_price = price
        food.is_vegetarian = is_veg
        food.is_available = True

        img_note = "kept"
        if not NO_IMAGES and not food.image:
            data, src = fetch_image(img_terms)
            if data:
                slug = name.lower().replace(" ", "-").replace("(", "").replace(")", "")
                food.image.save(f"{slug}.jpg", ContentFile(data), save=False)
                img_note = f"img <- {src}"
            else:
                img_note = "NO IMAGE FOUND"
        elif food.image:
            img_note = "img exists"

        food.save()

        for vname, vprice, vdefault in variants:
            FoodVariant.objects.update_or_create(
                food=food, name=vname, defaults={"price": vprice, "is_default": vdefault}
            )

        flag = "NEW " if created else "upd "
        vtxt = f" [{', '.join(v[0] for v in variants)}]" if variants else ""
        print(f"  {flag}{'VEG ' if is_veg else 'NON-VEG'} {name} - Rs.{price}{vtxt}  ({img_note})")

    total = Food.objects.filter(restaurant=restaurant).count()
    with_img = Food.objects.filter(restaurant=restaurant).exclude(image="").count()
    print(f"\nDone. {total} food items on '{restaurant.name}', {with_img} with images.")
    print("Customer dashboard: GET /api/foods/?restaurant=" + restaurant.slug)


if __name__ == "__main__":
    run()
