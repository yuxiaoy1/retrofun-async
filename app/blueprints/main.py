from flask import Blueprint, render_template, request

from app.extensions import db
from app.models import Order

main = Blueprint("main", __name__)


@main.get("/")
async def index():
    return render_template("index.html")


@main.get("/api/orders")
async def get_orders():
    start = request.args.get("start")
    length = request.args.get("length")
    sort = request.args.get("sort")
    search = request.args.get("search")

    total_query = Order.total_orders(search)
    order_query = Order.paginated_orders(start, length, sort, search)

    async with db.Session() as session:
        total = await session.scalar(total_query)
        orders = await session.stream(order_query)
        data = [{**order[0].to_dict(), "total": order[1]} async for order in orders]

        return {"data": data, "total": total}
