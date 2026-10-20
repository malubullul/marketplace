"""Validated product photos on local disk or private Supabase Storage."""
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class StorageError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LocalStorage:
    def __init__(self, directory):
        self.directory = Path(directory) / 'uploads'
        self.directory.mkdir(parents=True, exist_ok=True)

    def exists(self, name):
        return (self.directory / name).is_file()

    def put(self, name, data):
        (self.directory / name).write_bytes(data)

    def get(self, name):
        path = self.directory / name
        return path.read_bytes() if path.is_file() else None


class SupabaseStorage:
    def __init__(self, url, key, bucket='product-photos', testing=False):
        parsed = urlsplit(url)
        local = testing and parsed.scheme == 'http' and parsed.hostname in {'localhost','127.0.0.1'}
        if (not parsed.netloc or (parsed.scheme != 'https' and not local) or parsed.username
                or parsed.password or parsed.path not in {'','/'} or parsed.query or parsed.fragment or not key):
            raise ValueError('Lengkapi SUPABASE_URL dan SUPABASE_SECRET_KEY yang valid di server.')
        self.base = url.rstrip('/') + '/storage/v1/object/' + quote(bucket, safe='') + '/'
        self.key = key
        self.http = build_opener(NoRedirect())

    def request(self, method, name, data=None):
        headers = {'apikey':self.key}
        # Supabase's new secret keys are not JWTs. Its API gateway maps the
        # apikey header to the service role; Bearer is only for legacy JWT keys.
        if not self.key.startswith('sb_secret_'):
            headers['Authorization'] = 'Bearer ' + self.key
        if data is not None:
            headers.update({'Content-Type':'image/webp','x-upsert':'false'})
        try:
            with self.http.open(Request(self.base+quote(name,safe=''), data=data, headers=headers, method=method), timeout=15) as response:
                payload = response.read(4*1024*1024+1)
                if len(payload)>4*1024*1024:
                    raise StorageError('Foto melebihi batas penyimpanan.')
                return payload
        except HTTPError as error:
            if error.code == 404:
                return None
            raise StorageError('Penyimpanan foto belum dapat diakses. Periksa pengaturan hosting.') from None
        except (URLError, TimeoutError, OSError):
            raise StorageError('Penyimpanan foto belum dapat dihubungi. Coba lagi nanti.') from None

    def exists(self, name):
        return self.request('HEAD',name) is not None

    def put(self, name, data):
        if self.request('POST',name,data) is None:
            raise StorageError('Bucket foto belum tersedia. Jalankan pengaturan Supabase terlebih dahulu.')

    def get(self, name):
        return self.request('GET',name)
