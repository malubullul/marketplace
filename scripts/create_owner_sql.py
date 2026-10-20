"""Generate owner-creation SQL locally without sending a password to chat."""
import getpass
import re
from werkzeug.security import generate_password_hash


def owner_sql(email, password):
    email=email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or not 12<=len(password)<=128:
        raise ValueError('Gunakan email valid dan kata sandi 12–128 karakter.')
    quoted_email=email.replace("'","''")
    hashed=generate_password_hash(password).replace("'","''")
    return f"INSERT INTO anredseller.owners(email,password_hash) VALUES ('{quoted_email}','{hashed}') ON CONFLICT(email) DO NOTHING;"


if __name__=='__main__':
    email=input('Email pemilik: ')
    password=getpass.getpass('Kata sandi pemilik (12–128 karakter): ')
    if password!=getpass.getpass('Ulangi kata sandi: '):
        raise SystemExit('Kata sandi tidak sama.')
    try:
        result=owner_sql(email,password)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print('\nJalankan SQL berikut di Supabase SQL Editor. Jangan unggah hasilnya ke GitHub.\n')
    print(result)
