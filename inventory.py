"""Available stock per size; legacy products keep their explicitly pooled stock."""
import json


def size_name(value):
    if not isinstance(value, str):
        raise ValueError('Pilih satu ukuran untuk setiap baris stok.')
    value = value.strip().upper()
    parts = value.split()
    common = {'XXS','XS','S','M','L','XL','XXL','2XL','3XL','4XL'}
    if (not value or len(value) > 30 or any(ord(c) < 32 for c in value)
            or ',' in value or ';' in value or (len(parts) > 1 and all(p in common for p in parts))):
        raise ValueError('Pisahkan ukuran: gunakan satu baris untuk S, satu untuk M, dan seterusnya.')
    return value


def validate_stock(data, previous=None):
    rows = data.get('stokUkuran')
    if rows is None:
        if previous and previous.get('stokUkuran') is not None:
            raise ValueError('Produk ini memakai stok per ukuran. Sertakan rincian stok ukuran saat menyimpan.')
        return None
    if not isinstance(rows, list) or not 1 <= len(rows) <= 20:
        raise ValueError('Tambahkan 1–20 ukuran beserta stoknya.')
    result = []; names = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'ukuran','stok'}:
            raise ValueError('Setiap ukuran harus memiliki nama ukuran dan stok.')
        name = size_name(row['ukuran']); stock = row['stok']
        if name in names:
            raise ValueError('Ukuran tidak boleh duplikat. Tambah stok pada baris ukuran yang sama.')
        if type(stock) is not int or not 0 <= stock <= 1_000_000:
            raise ValueError('Stok ukuran harus bilangan bulat 0–1.000.000.')
        names.add(name); result.append({'ukuran':name,'stok':stock})
    if sum(r['stok'] for r in result) > 1_000_000:
        raise ValueError('Total stok maksimal 1.000.000.')
    if previous and previous.get('stokUkuran') is None and previous['stok'] > 0 and sum(r['stok'] for r in result) != previous['stok']:
        raise ValueError(f"Bagikan stok lama ({previous['stok']}) ke ukuran dengan total yang sama terlebih dahulu. Setelah disimpan, stok setiap ukuran dapat ditambah.")
    return result


def bucket(product, size):
    return size if product.get('stokUkuran') is not None else ''


def stock_key(product_id, product, size):
    return f'{product_id}:{bucket(product, size)}'


def available(product, size='', color=''):
    if not product or size not in (product.get('ukuran') or ['']) or color not in (product.get('warna') or ['']):
        return 0
    rows = product.get('stokUkuran')
    if rows is None:
        return product['stok']
    return next((row['stok'] for row in rows if row['ukuran'] == size), 0)


def adjust(product, size, quantity):
    rows = product.get('stokUkuran')
    if rows is None:
        product['stok'] += quantity
    else:
        row = next((row for row in rows if row['ukuran'] == size), None)
        if row is None:
            raise ValueError('Ukuran pesanan tidak ditemukan. Muat ulang produk sebelum melanjutkan.')
        row['stok'] += quantity
        product['stok'] = sum(row['stok'] for row in rows)


def validate_edit(db, product_id, previous, product):
    """Never lose the reservation bucket needed by an active order's cancellation."""
    old = previous.get('stokUkuran'); new = product.get('stokUkuran')
    converting = old is None and new is not None
    removed = {r['ukuran'] for r in (old or [])} - {r['ukuran'] for r in (new or [])}
    if not converting and not removed:
        return
    orders = db.execute("SELECT document FROM orders WHERE status IN ('baru','diproses','dikirim')").fetchall()
    for order in orders:
        for line in json.loads(order['document'])['items']:
            if line['id'] == product_id and (converting or line['ukuran'] in removed):
                raise ValueError('Ukuran masih terkait pesanan aktif. Selesaikan atau batalkan pesanan tersebut sebelum mengubah pembagian/menghapus ukuran. Stok ukuran lain tetap bisa ditambah.')
