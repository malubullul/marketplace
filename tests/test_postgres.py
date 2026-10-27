"""Run the existing store/customer/gateway contracts against real PostgreSQL.

Set ANREDSELLER_TEST_DATABASE_URL to a disposable local PostgreSQL database.
Each test uses its own schema, removed afterwards. Never use a production URL.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import secrets
import time
import unittest
from unittest.mock import patch

import psycopg
from psycopg import sql
from server import create_app

TEST_URL = os.environ.get('ANREDSELLER_TEST_DATABASE_URL', '')


def postgres_case(module_name, class_name):
    module = importlib.import_module(module_name)

    class PostgreSQLCase(getattr(module, class_name)):
        def run(self, result=None):
            secret = secrets.token_urlsafe(40)
            schemas = set()

            def factory(config=None):
                config = dict(config or {})
                schema = 'test_' + hashlib.sha256(str(config.get('DATA_DIR')).encode()).hexdigest()[:24]
                config.update(DATABASE_URL=TEST_URL, DATABASE_SCHEMA=schema)
                config.setdefault('SESSION_SECRET', secret)
                app = create_app(config)
                with app.app_context():
                    db = app.get_db()
                    db.initialize()
                    if not db.execute("SELECT 1 FROM metadata WHERE key='seeded'").fetchone():
                        products = json.loads((Path(__file__).resolve().parents[1]/'data/products.seed.json').read_text())
                        for product in products:
                            product.update(ukuran=[],warna=[],published=True,demo=True)
                            db.execute('INSERT INTO products(id,document,published,updated_at) VALUES(?,?,1,?)', (product['id'],json.dumps(product),time.time_ns()))
                        db.execute("SELECT setval(pg_get_serial_sequence('products','id'), (SELECT MAX(id) FROM products))")
                        db.execute("INSERT INTO metadata VALUES('seeded','1')")
                        db.commit()
                schemas.add(schema)
                return app

            try:
                with patch.object(module, 'create_app', factory):
                    return super().run(result)
            finally:
                with psycopg.connect(TEST_URL, autocommit=True) as connection:
                    for schema in schemas:
                        connection.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))

    PostgreSQLCase.__name__ = 'Postgres' + class_name
    PostgreSQLCase.__qualname__ = PostgreSQLCase.__name__
    return PostgreSQLCase


if TEST_URL:
    PostgresStoreTests = postgres_case('test_server', 'StoreTests')
    PostgresCustomerTests = postgres_case('test_customers', 'CustomerTests')
    PostgresAdminPortalTests = postgres_case('test_admin_portal', 'AdminPortalTests')
    PostgresContactTests = postgres_case('test_contacts', 'ContactTests')
    PostgresStoreContentTests = postgres_case('test_store_content', 'StoreContentTests')
    PostgresReviewRecoveryTests = postgres_case('test_reviews_recovery', 'ReviewRecoveryTests')
    PostgresPromoTests = postgres_case('test_promos', 'PromoTests')
    PostgresOrderOperationTests = postgres_case('test_order_operations', 'OrderOperationTests')
    PostgresEmailVerificationTests = postgres_case('test_email_verification', 'EmailVerificationTests')
else:
    @unittest.skip('Set ANREDSELLER_TEST_DATABASE_URL to run real PostgreSQL contracts.')
    class PostgresNotConfigured(unittest.TestCase):
        def test_postgresql_contracts(self):
            pass
