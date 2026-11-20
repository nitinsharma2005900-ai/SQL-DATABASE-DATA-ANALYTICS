"""Database Initialization and Realistic Business Seed Data Script."""

import random
from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    text,
)

from config.settings import settings
from .connection import DatabaseManager, get_db_manager


def create_schema(engine) -> MetaData:
    """Define database schema using SQLAlchemy MetaData."""
    metadata = MetaData()

    # 1. Customers Table
    Table(
        "customers",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(100), nullable=False),
        Column("email", String(150), nullable=False, unique=True),
        Column("city", String(80), nullable=False),
        Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    )

    # 2. Products Table
    Table(
        "products",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("product_name", String(150), nullable=False),
        Column("category", String(80), nullable=False),
        Column("price", Float, nullable=False),
    )

    # 3. Orders Table (Notice: order_date column; NO created_at column here by design!)
    Table(
        "orders",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False),
        Column("order_date", Date, nullable=False),
        Column("total_amount", Float, nullable=False),
        Column("status", String(50), nullable=False),
    )

    # 4. Order Items Table
    Table(
        "order_items",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("order_id", Integer, ForeignKey("orders.id"), nullable=False),
        Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
        Column("quantity", Integer, nullable=False),
        Column("unit_price", Float, nullable=False),
    )

    metadata.create_all(engine)
    return metadata


def seed_database(db_manager: DatabaseManager, force: bool = False) -> None:
    """Seed the database with rich, realistic business sample data."""
    engine = db_manager.engine
    metadata = MetaData()
    metadata.reflect(bind=engine)

    # If tables already exist and not forcing, check if data is populated
    if not force and "customers" in metadata.tables:
        with engine.connect() as conn:
            cust_count = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar() or 0
            if cust_count > 0:
                return

    # Drop existing tables if force is specified
    if force:
        metadata.drop_all(bind=engine)

    metadata = create_schema(engine)

    random.seed(42)

    # Realistic Seed Data
    customers_data = [
        {"name": "Alice Johnson", "email": "alice.johnson@example.com", "city": "New York", "created_at": datetime(2024, 1, 15, 10, 30)},
        {"name": "Bob Smith", "email": "bob.smith@example.com", "city": "San Francisco", "created_at": datetime(2024, 2, 1, 14, 15)},
        {"name": "Carol Williams", "email": "carol.w@example.com", "city": "Chicago", "created_at": datetime(2024, 2, 18, 9, 0)},
        {"name": "David Brown", "email": "david.b@example.com", "city": "Austin", "created_at": datetime(2024, 3, 5, 16, 45)},
        {"name": "Emma Davis", "email": "emma.davis@example.com", "city": "Seattle", "created_at": datetime(2024, 3, 22, 11, 20)},
        {"name": "Frank Miller", "email": "frank.m@example.com", "city": "Boston", "created_at": datetime(2024, 4, 10, 15, 30)},
        {"name": "Grace Wilson", "email": "grace.w@example.com", "city": "Denver", "created_at": datetime(2024, 4, 28, 8, 45)},
        {"name": "Henry Moore", "email": "henry.m@example.com", "city": "Los Angeles", "created_at": datetime(2024, 5, 12, 13, 10)},
        {"name": "Isabella Taylor", "email": "isabella.t@example.com", "city": "Miami", "created_at": datetime(2024, 5, 30, 17, 0)},
        {"name": "Jack Anderson", "email": "jack.a@example.com", "city": "Dallas", "created_at": datetime(2024, 6, 14, 12, 15)},
        {"name": "Karen Thomas", "email": "karen.t@example.com", "city": "Atlanta", "created_at": datetime(2024, 6, 25, 10, 0)},
        {"name": "Liam Jackson", "email": "liam.j@example.com", "city": "Portland", "created_at": datetime(2024, 7, 8, 14, 40)},
        {"name": "Mia White", "email": "mia.white@example.com", "city": "New York", "created_at": datetime(2024, 7, 21, 9, 30)},
        {"name": "Noah Harris", "email": "noah.h@example.com", "city": "Chicago", "created_at": datetime(2024, 8, 4, 16, 20)},
        {"name": "Olivia Martin", "email": "olivia.m@example.com", "city": "San Francisco", "created_at": datetime(2024, 8, 19, 11, 50)},
        {"name": "Paul Clark", "email": "paul.c@example.com", "city": "Seattle", "created_at": datetime(2024, 9, 2, 13, 15)},
        {"name": "Quinn Lewis", "email": "quinn.l@example.com", "city": "Austin", "created_at": datetime(2024, 9, 15, 15, 45)},
        {"name": "Rachel Lee", "email": "rachel.lee@example.com", "city": "Boston", "created_at": datetime(2024, 10, 1, 10, 10)},
        {"name": "Samuel Walker", "email": "samuel.w@example.com", "city": "Denver", "created_at": datetime(2024, 10, 18, 12, 0)},
        {"name": "Tina Hall", "email": "tina.hall@example.com", "city": "Miami", "created_at": datetime(2024, 11, 5, 14, 30)},
    ]

    products_data = [
        {"product_name": "Pro Wireless Keyboard", "category": "Accessories", "price": 89.99},
        {"product_name": "Ergonomic Optical Mouse", "category": "Accessories", "price": 49.99},
        {"product_name": "4K Ultra HD Monitor 27-inch", "category": "Electronics", "price": 349.99},
        {"product_name": "Noise Cancelling Headphones", "category": "Electronics", "price": 199.99},
        {"product_name": "USB-C Multiport Dock", "category": "Accessories", "price": 79.99},
        {"product_name": "Standing Desk Converter", "category": "Furniture", "price": 279.99},
        {"product_name": "Executive Mesh Chair", "category": "Furniture", "price": 329.99},
        {"product_name": "Aluminum Laptop Stand", "category": "Accessories", "price": 39.99},
        {"product_name": "Analytics Pro Annual License", "category": "Software", "price": 499.99},
        {"product_name": "Cloud Storage 2TB Plan", "category": "Software", "price": 119.99},
        {"product_name": "Mechanical Gaming Keyboard", "category": "Accessories", "price": 129.99},
        {"product_name": "Webcam 1080p HD with Mic", "category": "Electronics", "price": 69.99},
        {"product_name": "Desk LED Lamp with Dimmer", "category": "Furniture", "price": 45.99},
        {"product_name": "Security Suite 1-Year", "category": "Software", "price": 89.99},
        {"product_name": "Curved Ultrawide Monitor 34-inch", "category": "Electronics", "price": 599.99},
    ]

    orders_data = []
    order_items_data = []

    statuses = ["Completed", "Completed", "Completed", "Shipped", "Shipped", "Pending", "Cancelled"]
    base_date = datetime(2024, 1, 1).date()

    order_id_counter = 1
    item_id_counter = 1

    for customer_id in range(1, len(customers_data) + 1):
        # Each customer has between 2 to 6 orders
        num_orders = random.randint(2, 6)
        for _ in range(num_orders):
            day_offset = random.randint(10, 320)
            order_date = base_date + timedelta(days=day_offset)
            status = random.choice(statuses)

            # 1 to 4 items per order
            num_items = random.randint(1, 4)
            chosen_products = random.sample(range(1, len(products_data) + 1), num_items)
            order_total = 0.0

            order_items_for_this_order = []
            for prod_id in chosen_products:
                prod = products_data[prod_id - 1]
                qty = random.randint(1, 3)
                unit_price = prod["price"]
                subtotal = qty * unit_price
                order_total += subtotal

                order_items_for_this_order.append(
                    {
                        "id": item_id_counter,
                        "order_id": order_id_counter,
                        "product_id": prod_id,
                        "quantity": qty,
                        "unit_price": unit_price,
                    }
                )
                item_id_counter += 1

            orders_data.append(
                {
                    "id": order_id_counter,
                    "customer_id": customer_id,
                    "order_date": order_date,
                    "total_amount": round(order_total, 2),
                    "status": status,
                }
            )
            order_items_data.extend(order_items_for_this_order)
            order_id_counter += 1

    # Insert data
    customers_table = metadata.tables["customers"]
    products_table = metadata.tables["products"]
    orders_table = metadata.tables["orders"]
    order_items_table = metadata.tables["order_items"]

    with engine.begin() as conn:
        conn.execute(customers_table.insert(), customers_data)
        conn.execute(products_table.insert(), products_data)
        conn.execute(orders_table.insert(), orders_data)
        conn.execute(order_items_table.insert(), order_items_data)


if __name__ == "__main__":
    db = get_db_manager()
    print(f"Initializing database at: {db.database_url}")
    seed_database(db, force=True)
    inspector = DatabaseManager(db.database_url)
    res = inspector.execute_query("SELECT COUNT(*) as total_orders FROM orders")
    print(f"Database initialized successfully! Total orders created: {res.rows[0]['total_orders']}")
