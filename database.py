"""Small PostgreSQL adapter for the store's parameterized SQL.

SQLite remains available for local use. PostgreSQL serializes each application
transaction with one advisory lock, preserving stock/idempotency guarantees
across serverless instances. This deliberately favors correctness over scale.
"""
import hashlib
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row

INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg.IntegrityError)
PostgresError = psycopg.Error


class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


class Cursor:
    def __init__(self, cursor, lastrowid=None):
        self.cursor, self.lastrowid = cursor, lastrowid
        self.rowcount = cursor.rowcount

    def fetchone(self):
        row = self.cursor.fetchone()
        return Row(row) if row is not None else None

    def fetchall(self):
        return [Row(row) for row in self.cursor.fetchall()]


class PostgresDatabase:
    dialect = 'postgres'

    def __init__(self, url, schema='anredseller'):
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', schema):
            raise ValueError('Nama schema database tidak valid.')
        self.schema = schema
        # Transaction poolers require prepared statements to be disabled.
        # Supabase's pooler uses a private CA that is not in the OS trust store.
        # Verify both its certificate chain AND the pooler hostname.
        hostname = urlsplit(url).hostname
        if hostname in {'127.0.0.1', 'localhost', '::1'}:
            tls = {}
        elif hostname and hostname.endswith('.pooler.supabase.com'):
            root_ca = Path(__file__).resolve().parent / 'certs' / 'supabase-root-2021.crt'
            tls = {'sslmode': 'verify-full', 'sslrootcert': str(root_ca)}
        else:
            tls = {'sslmode': 'verify-full', 'sslrootcert': 'system'}
        self.connection = psycopg.connect(url, row_factory=dict_row, prepare_threshold=None, connect_timeout=10, **tls)
        self.lock = int.from_bytes(hashlib.sha256(schema.encode()).digest()[:8], 'big') & ((1 << 63) - 1)

    def begin(self):
        if self.connection.info.transaction_status == TransactionStatus.IDLE:
            self.connection.execute("SET LOCAL lock_timeout = '10s'")
            self.connection.execute("SET LOCAL statement_timeout = '15s'")
            self.connection.execute('SELECT pg_advisory_xact_lock(%s)', (self.lock,))
            self.connection.execute(f'SET LOCAL search_path TO "{self.schema}", pg_catalog')

    def execute(self, query, parameters=()):
        self.begin()
        if query.strip().upper() == 'BEGIN IMMEDIATE':
            return Cursor(self.connection.execute('SELECT 1'))
        query = query.replace('?', '%s')
        generated_id = bool(re.match(r'\s*INSERT INTO (products|customers|customer_addresses)\b', query, re.I))
        if generated_id:
            query += ' RETURNING id'
        cursor = self.connection.execute(query, tuple(int(value) if isinstance(value, bool) else value for value in parameters))
        lastrowid = cursor.fetchone()['id'] if generated_id else None
        return Cursor(cursor, lastrowid)

    def initialize(self):
        self.begin()
        source = '\n'.join((Path(__file__).resolve().parent / 'migrations' / name).read_text()
                           for name in ('001_supabase.sql', '003_google_login.sql'))
        self.connection.execute(source.replace('anredseller', self.schema), prepare=False)
        self.commit()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()
