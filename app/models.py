from datetime import UTC, datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Text,
    distinct,
    event,
    func,
    inspect,
    or_,
)
from sqlalchemy.orm import Mapped, WriteOnlyMapped, mapped_column, relationship

from app.extensions import db

ProductCountry = db.Table(
    "product_country",
    Column("product_id", ForeignKey("product.id"), primary_key=True, nullable=False),
    Column("country_id", ForeignKey("country.id"), primary_key=True, nullable=False),
)


class Product(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturer.id"), index=True
    )
    manufacturer: Mapped["Manufacturer"] = relationship(
        back_populates="products", lazy="joined", innerjoin=True
    )
    year: Mapped[int] = mapped_column(index=True)
    cpu: Mapped[Optional[str]] = mapped_column(String(32))
    countries: Mapped[list["Country"]] = relationship(
        back_populates="products", secondary=ProductCountry, lazy="selectin"
    )
    order_items: WriteOnlyMapped["OrderItem"] = relationship(back_populates="product")
    reviews: WriteOnlyMapped["ProductReview"] = relationship(back_populates="product")
    blog_articles: WriteOnlyMapped["BlogArticle"] = relationship(
        back_populates="product"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "manufacturer": self.manufacturer.to_dict(),
            "year": self.year,
            "cpu": self.cpu,
            "countries": [country.to_dict() for country in self.countries],
        }


class Country(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), index=True, unique=True)
    products: Mapped[list["Product"]] = relationship(
        back_populates="countries", secondary=ProductCountry, lazy="selectin"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
        }


class Manufacturer(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    products: Mapped[list["Product"]] = relationship(
        back_populates="manufacturer", cascade="all, delete-orphan", lazy="selectin"
    )

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class Order(db.Model):
    id: Mapped[UUID] = mapped_column(default=uuid4, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), index=True
    )
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customer.id"), index=True)
    customer: Mapped["Customer"] = relationship(
        back_populates="orders", lazy="joined", innerjoin=True
    )
    order_items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", lazy="selectin"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "customer": self.customer.to_dict(),
            "order_items": [item.to_dict() for item in self.order_items],
        }

    @staticmethod
    def total_orders(search):
        if not search:
            return db.select(func.count(Order.id))
        return (
            db.select(func.count(distinct(Order.id)))
            .join(Order.customer)
            .join(Order.order_items)
            .join(OrderItem.product)
            .where(
                or_(
                    Customer.name.ilike(f"%{search}%"),
                    Product.name.ilike(f"%{search}%"),
                )
            )
        )

    @staticmethod
    def paginated_orders(start, length, sort, search):
        total = func.sum(OrderItem.quantity * OrderItem.unit_price).label(None)
        q = (
            db.select(Order, total)
            .join(Order.customer)
            .join(Order.order_items)
            .join(OrderItem.product)
            .group_by(Order)
            .distinct()
        )

        if search:
            q = q.where(
                or_(
                    Customer.name.ilike(f"%{search}%"),
                    Product.name.ilike(f"%{search}%"),
                )
            )

        if sort:
            order = []
            for s in sort.split(","):
                direction = s[0]
                name = s[1:]
                if name == "customer":
                    column = Customer.name
                elif name == "total":
                    column = total
                else:
                    column = getattr(Order, name)
                if direction == "-":
                    column = column.desc()
                order.append(column)
            q = q.order_by(*order)

        q = q.offset(start).limit(length)

        return q


class Customer(db.Model):
    id: Mapped[UUID] = mapped_column(default=uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    address: Mapped[Optional[str]] = mapped_column(String(128))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    orders: WriteOnlyMapped["Order"] = relationship(back_populates="customer")
    product_reviews: WriteOnlyMapped["ProductReview"] = relationship(
        back_populates="customer"
    )
    blog_users: WriteOnlyMapped["BlogUser"] = relationship(back_populates="customer")

    def to_dict(self):
        return {
            "id": self.id.hex,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
        }


class OrderItem(db.Model):
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), primary_key=True)
    product: Mapped["Product"] = relationship(
        back_populates="order_items", lazy="joined", innerjoin=True
    )
    order_id: Mapped[UUID] = mapped_column(ForeignKey("order.id"), primary_key=True)
    order: Mapped["Order"] = relationship(
        back_populates="order_items", lazy="joined", innerjoin=True
    )
    unit_price: Mapped[float]
    quantity: Mapped[int]

    def to_dict(self):
        return {
            "product": self.product.to_dict(),
            "quantity": self.quantity,
            "unit_price": self.unit_price,
        }


class ProductReview(db.Model):
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer.id"), primary_key=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), index=True
    )
    rating: Mapped[int]
    comment: Mapped[Optional[str]] = mapped_column(Text)
    product: Mapped["Product"] = relationship(
        back_populates="reviews", lazy="joined", innerjoin=True
    )
    customer: Mapped["Customer"] = relationship(
        back_populates="product_reviews", lazy="joined", innerjoin=True
    )


class BlogArticle(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("blog_author.id"), index=True)
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("product.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), index=True
    )
    author: Mapped["BlogAuthor"] = relationship(
        back_populates="articles", lazy="joined", innerjoin=True
    )
    product: Mapped[Optional["Product"]] = relationship(
        back_populates="blog_articles", lazy="joined"
    )
    views: WriteOnlyMapped["BlogView"] = relationship(back_populates="article")
    language_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("language.id"), index=True
    )
    language: Mapped[Optional["Language"]] = relationship(
        back_populates="blog_articles", lazy="joined"
    )
    translation_of_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("blog_article.id"), index=True
    )
    translation_of: Mapped[Optional["BlogArticle"]] = relationship(
        remote_side=id, back_populates="translations", lazy="joined"
    )
    translations: Mapped[list["BlogArticle"]] = relationship(
        back_populates="translation_of", lazy="selectin"
    )


class BlogAuthor(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    articles: WriteOnlyMapped["BlogArticle"] = relationship(back_populates="author")


class BlogUser(db.Model):
    id: Mapped[UUID] = mapped_column(default=uuid4, primary_key=True)
    customer_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("customer.id"), index=True
    )
    customer: Mapped[Optional["Customer"]] = relationship(
        back_populates="blog_users", lazy="joined"
    )
    sessions: WriteOnlyMapped["BlogSession"] = relationship(back_populates="user")


class BlogSession(db.Model):
    id: Mapped[UUID] = mapped_column(default=uuid4, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("blog_user.id"), index=True)
    user: Mapped["BlogUser"] = relationship(
        back_populates="sessions", lazy="joined", innerjoin=True
    )
    views: WriteOnlyMapped["BlogView"] = relationship(back_populates="session")


class BlogView(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("blog_article.id"))
    session_id: Mapped[UUID] = mapped_column(ForeignKey("blog_session.id"))
    timestamp: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), index=True
    )
    article: Mapped["BlogArticle"] = relationship(
        back_populates="views", lazy="joined", innerjoin=True
    )
    session: Mapped["BlogSession"] = relationship(
        back_populates="views", lazy="joined", innerjoin=True
    )


class Language(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), index=True, unique=True)
    blog_articles: WriteOnlyMapped["BlogArticle"] = relationship(
        back_populates="language"
    )


@event.listens_for(db.Model, "init", propagate=True)
def init_relationships(tgt, arg, kw):
    mapper = inspect(tgt.__class__)
    for arg in mapper.relationships:
        if arg.collection_class is None and arg.uselist:
            continue  # skip write-only and similar relationships
        if arg.key not in kw:
            kw.setdefault(arg.key, None if not arg.uselist else arg.collection_class())
