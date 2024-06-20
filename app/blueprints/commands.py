import asyncio
import csv
from datetime import datetime
from functools import wraps
from uuid import UUID

from flask import Blueprint
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine

from app.extensions import db
from app.models import (
    BlogArticle,
    BlogAuthor,
    BlogSession,
    BlogUser,
    BlogView,
    Country,
    Customer,
    Language,
    Manufacturer,
    Order,
    OrderItem,
    Product,
    ProductCountry,
    ProductReview,
)

commands = Blueprint("commands", __name__, cli_group=None)


def async_command(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@commands.cli.command()
@async_command
async def initdb():
    """Create database."""
    engine = create_async_engine(db.engine.url)
    async with engine.begin() as con:
        await con.run_sync(db.Model.metadata.drop_all)
        await con.run_sync(db.Model.metadata.create_all)
    print("Database created.")


@commands.cli.group()
def fake():
    """Generate fake data."""
    pass


@fake.command()
@async_command
async def products():
    """Generate products data."""
    async with db.Session() as session:
        await session.execute(delete(ProductCountry))
        await session.execute(delete(Product))
        await session.execute(delete(Manufacturer))
        await session.execute(delete(Country))

        with open("./data/products.csv") as f:
            reader = csv.DictReader(f)
            all_manufacturers = {}
            all_countries = {}

            for row in reader:
                row["year"] = int(row["year"])
                manufacturer = row.pop("manufacturer")
                countries = row.pop("country").split("/")
                p = Product(**row)

                if manufacturer not in all_manufacturers:
                    m = Manufacturer(name=manufacturer)
                    session.add(m)
                    all_manufacturers[manufacturer] = m

                all_manufacturers[manufacturer].products.append(p)

                for country in countries:
                    if country not in all_countries:
                        c = Country(name=country)
                        session.add(c)
                        all_countries[country] = c
                    all_countries[country].products.append(p)

            await session.commit()

    print("Products data created.")


@fake.command()
@async_command
async def orders():
    """Generate orders data."""
    async with db.Session() as session:
        await session.execute(delete(OrderItem))
        await session.execute(delete(Order))
        await session.execute(delete(Customer))

        all_customers = {}
        all_products = {}

        with open("./data/orders.csv") as f:
            reader = csv.DictReader(f)

            for row in reader:
                if row["name"] not in all_customers:
                    c = Customer(
                        name=row["name"], address=row["address"], phone=row["phone"]
                    )
                    all_customers[row["name"]] = c
                o = Order(
                    timestamp=datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
                )
                all_customers[row["name"]].orders.add(o)
                session.add(o)

                product = all_products.get(row["product1"])
                if product is None:
                    product = await session.scalar(
                        db.select(Product).filter_by(name=row["product1"])
                    )
                    all_products[row["product1"]] = product
                o.order_items.append(
                    OrderItem(
                        product=product,
                        unit_price=float(row["unit_price1"]),
                        quantity=int(row["quantity1"]),
                    )
                )

                if row["product2"]:
                    product = all_products.get(row["product2"])
                    if product is None:
                        product = await session.scalar(
                            db.select(Product).filter_by(name=row["product2"])
                        )
                        all_products[row["product2"]] = product
                    o.order_items.append(
                        OrderItem(
                            product=product,
                            unit_price=float(row["unit_price2"]),
                            quantity=int(row["quantity2"]),
                        )
                    )

                if row["product3"]:
                    product = all_products.get(row["product3"])
                    if product is None:
                        product = await session.scalar(
                            db.select(Product).filter_by(name=row["product3"])
                        )
                        all_products[row["product3"]] = product
                    o.order_items.append(
                        OrderItem(
                            product=product,
                            unit_price=float(row["unit_price3"]),
                            quantity=int(row["quantity3"]),
                        )
                    )

            await session.commit()
    print("Orders data created.")


@fake.command()
@async_command
async def reviews():
    """Generate reviews data."""
    async with db.Session() as session:
        with open("./data/reviews.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                c = await session.scalar(
                    db.select(Customer).filter_by(name=row["customer"])
                )
                p = await session.scalar(
                    db.select(Product).filter_by(name=row["product"])
                )
                r = ProductReview(
                    customer=c,
                    product=p,
                    timestamp=datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
                    rating=int(row["rating"]),
                    comment=row["comment"] or None,
                )
                session.add(r)
            await session.commit()
    print("Reviews data created.")


@fake.command()
@async_command
async def articles():
    """Generate articles data."""
    async with db.Session() as session:
        await session.execute(delete(BlogView))
        await session.execute(delete(BlogSession))
        await session.execute(delete(BlogUser))
        await session.execute(delete(BlogArticle))
        await session.execute(delete(BlogAuthor))

        all_authors = {}
        all_products = {}

        with open("./data/articles.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                author = all_authors.get(row["author"])
                if author is None:
                    author = BlogAuthor(name=row["author"])
                    all_authors[author.name] = author
                product = None
                if row["product"]:
                    product = all_products.get(row["product"])
                    if product is None:
                        product = await session.scalar(
                            db.select(Product).filter_by(name=row["product"])
                        )
                        all_products[product.name] = product
                article = BlogArticle(
                    title=row["title"],
                    author=author,
                    product=product,
                    timestamp=datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
                )
                session.add(article)
            await session.commit()
    print("Articles data created.")


@fake.command()
@async_command
async def views():
    """Generate views data."""
    async with db.Session() as session:
        await session.execute(delete(BlogView))
        await session.execute(delete(BlogSession))
        await session.execute(delete(BlogUser))

        all_articles = {}
        all_customers = {}
        all_blog_users = {}
        all_blog_sessions = {}

        with open("./data/views.csv") as f:
            reader = csv.DictReader(f)
            i = 0
            for row in reader:
                user = all_blog_users.get(row["user"])
                if user is None:
                    customer = None
                    if row["customer"]:
                        customer = all_customers.get(row["customer"])
                        if customer is None:
                            customer = await session.scalar(
                                db.select(Customer).filter_by(name=row["customer"])
                            )
                        all_customers[customer.name] = customer

                    user_id = UUID(row["user"])
                    user = BlogUser(id=user_id, customer=customer)
                    session.add(user)
                    all_blog_users[row["user"]] = user

                blog_session = all_blog_sessions.get(row["session"])
                if blog_session is None:
                    session_id = UUID(row["session"])
                    blog_session = BlogSession(id=session_id, user=user)
                    session.add(blog_session)
                    all_blog_sessions[row["session"]] = blog_session

                article = all_articles.get(row["title"])
                if article is None:
                    article = await session.scalar(
                        db.select(BlogArticle).filter_by(title=row["title"])
                    )
                all_articles[article.title] = article

                view = BlogView(
                    article=article,
                    session=blog_session,
                    timestamp=datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"),
                )
                session.add(view)

                i += 1
                if i % 100 == 0:
                    print(i)
                    await session.commit()
            print(i)
            await session.commit()
    print("Views data created.")


@fake.command()
@async_command
async def languages():
    """Generate languages data."""
    async with db.Session() as session:
        all_articles = {}
        all_languages = {}

        with open("./data/articles.csv") as f:
            reader = csv.DictReader(f)

            for row in reader:
                article = all_articles.get(row["title"])
                if article is None:
                    article = await session.scalar(
                        db.select(BlogArticle).filter_by(title=row["title"])
                    )
                    all_articles[article.title] = article

                language = all_languages.get(row["language"])
                if language is None:
                    language = await session.scalar(
                        db.select(Language).filter_by(name=row["language"])
                    )
                    if language is None:
                        language = Language(name=row["language"])
                        session.add(language)
                    all_languages[language.name] = language
                article.language = language

                if row["translation_of"]:
                    translation_of = all_articles.get(row["translation_of"])
                    if translation_of is None:
                        translation_of = await session.scalar(
                            db.select(BlogArticle).filter_by(
                                title=row["translation_of"]
                            )
                        )
                        all_articles[article.title] = article
                    article.translation_of = translation_of
            await session.commit()
    print("Languages data created.")
