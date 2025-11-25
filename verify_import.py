"""
Verifiziere L-Shop Import
Prueft ob alle Artikel in der Datenbank sind
"""
from app import create_app
from src.models import db, Article, Brand, ProductCategory

def main():
    print("=" * 80)
    print("L-SHOP IMPORT VERIFIKATION")
    print("=" * 80)

    app = create_app()

    with app.app_context():
        # Zaehle Artikel
        total_articles = Article.query.count()
        lshop_articles = Article.query.filter_by(supplier='L-Shop').count()

        print(f"\n[INFO] Gesamt-Artikel in DB: {total_articles}")
        print(f"[INFO] L-Shop Artikel: {lshop_articles}")

        # Zaehle Brands
        total_brands = Brand.query.count()
        print(f"[INFO] Brands: {total_brands}")

        # Zaehle Kategorien
        total_categories = ProductCategory.query.count()
        print(f"[INFO] Kategorien: {total_categories}")

        # Zeige erste 5 L-Shop Artikel
        print("\n[INFO] Erste 5 L-Shop Artikel:")
        sample_articles = Article.query.filter_by(supplier='L-Shop').limit(5).all()

        for article in sample_articles:
            print(f"\n  {article.id} - {article.article_number}")
            print(f"    Name: {article.name}")
            print(f"    Marke: {article.brand_obj.name if article.brand_obj else 'N/A'}")
            print(f"    Produktart: {article.product_type or 'N/A'}")
            print(f"    Farbe: {article.color or 'N/A'}")
            print(f"    Groesse: {article.size or 'N/A'}")
            print(f"    Hersteller-Nr: {article.manufacturer_number or 'N/A'}")
            print(f"    EK-Einzel: {article.purchase_price_single}")
            print(f"    VK-Preis: {article.price}")

        # Zaehle nach Brand
        print("\n[INFO] Top 10 Brands (nach Artikel-Anzahl):")
        brands = db.session.query(
            Brand.name,
            db.func.count(Article.id).label('count')
        ).join(Article, Article.brand_id == Brand.id)\
         .group_by(Brand.name)\
         .order_by(db.func.count(Article.id).desc())\
         .limit(10).all()

        for brand_name, count in brands:
            print(f"  {brand_name:30} - {count:5} Artikel")

        # Zaehle nach Kategorie
        print("\n[INFO] Top 10 Kategorien (nach Artikel-Anzahl):")
        categories = db.session.query(
            ProductCategory.name,
            db.func.count(Article.id).label('count')
        ).join(Article, Article.category_id == ProductCategory.id)\
         .group_by(ProductCategory.name)\
         .order_by(db.func.count(Article.id).desc())\
         .limit(10).all()

        for cat_name, count in categories:
            print(f"  {cat_name:30} - {count:5} Artikel")

        print("\n" + "=" * 80)
        print("[OK] VERIFIKATION ABGESCHLOSSEN")
        print("=" * 80)

if __name__ == '__main__':
    main()
