from decimal import Decimal

from django.core.management.base import BaseCommand

from store.models import Category, Product

DATA = {
    "Apparel": [
        ("Classic Crest Hoodie", "Heavyweight fleece hoodie with the embroidered college crest.", "45.00", 25),
        ("Campus Tee", "Soft cotton t-shirt with the college name across the chest.", "15.00", 60),
        ("Varsity Jacket", "Wool-blend varsity jacket with leather-look sleeves.", "90.00", 10),
        ("Sports Day Jersey", "Breathable jersey in house colours.", "30.00", 30),
    ],
    "Accessories": [
        ("Embroidered Cap", "Adjustable cotton cap with a small crest on the front.", "12.00", 40),
        ("Lanyard & ID Holder", "Woven lanyard with a clear ID sleeve.", "5.00", 100),
        ("Canvas Tote Bag", "Sturdy tote for books and a laptop.", "10.00", 50),
    ],
    "Stationery": [
        ("Crest Notebook", "A5 ruled notebook, 120 pages, crest on the cover.", "6.00", 80),
        ("Pen Set", "Three gel pens in college colours.", "4.00", 120),
        ("Desk Planner", "Undated weekly planner for the academic year.", "9.00", 35),
    ],
    "Drinkware": [
        ("Steel Water Bottle", "Insulated 750 ml bottle that keeps drinks cold for 24 hours.", "18.00", 45),
        ("Ceramic Mug", "350 ml mug with the college motto.", "8.00", 50),
    ],
}


class Command(BaseCommand):
    help = "Create demo categories and products. Prices are kept low for eSewa test limits."

    def handle(self, *args, **options):
        created = 0
        for cat_name, products in DATA.items():
            cat, _ = Category.objects.get_or_create(name=cat_name)
            for name, desc, price, stock in products:
                _, was_created = Product.objects.get_or_create(
                    name=name,
                    defaults={"category": cat, "description": desc, "price": Decimal(price), "stock": stock},
                )
                created += was_created
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} new products."))
