"""Standalone owner portal. Browser requests stay on the admin domain.

Only this server knows the gateway key. Product data, photos and accounts stay
in the store backend; this deployment does not create another database.
"""
import os
from pathlib import Path
import re
from http.cookies import SimpleCookie
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from flask import Flask, abort, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent
COOKIE_NAME = 'anredseller_admin'
API_ROUTES = [
    ('GET', r'/api/session'), ('POST', r'/api/login'), ('POST', r'/api/logout'),
    ('GET', r'/api/admin/products'), ('POST', r'/api/admin/products'),
    ('PUT', r'/api/admin/products/\d+'), ('DELETE', r'/api/admin/products/\d+'),
    ('POST', r'/api/admin/uploads'), ('GET', r'/api/admin/orders'),
    ('PATCH', r'/api/admin/orders/[A-Za-z0-9-]{1,80}'),
    ('POST', r'/api/admin/orders/[A-Za-z0-9-]{1,80}/payment'),
    ('GET', r'/api/admin/orders/[A-Za-z0-9-]{1,80}/history'),
    ('GET', r'/api/admin/transaction-settings'), ('PUT', r'/api/admin/transaction-settings'),
    ('GET', r'/api/admin/activity'),
    ('GET', r'/api/admin/contacts'), ('PUT', r'/api/admin/contacts'),
    ('GET', r'/api/admin/content'), ('PUT', r'/api/admin/content'),
    ('GET', r'/api/admin/promos'), ('POST', r'/api/admin/promos'),
    ('PUT', r'/api/admin/promos/[A-Z0-9][A-Z0-9_-]{2,31}'),
]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def origin(value, setting):
    """Configuration must name a single trusted server, never a browser URL."""
    value = value.rstrip('/')
    parsed = urlsplit(value)
    local = parsed.scheme == 'http' and parsed.hostname in {'127.0.0.1', 'localhost', '::1'}
    if value and (not parsed.netloc or (parsed.scheme != 'https' and not local)
                  or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise ValueError(f'{setting} harus berupa origin HTTPS tanpa path.')
    return value


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        BACKEND_URL=os.environ.get('ANREDSELLER_BACKEND_URL', ''),
        SHOP_URL=os.environ.get('ANREDSELLER_SHOP_URL', ''),
        ADMIN_GATEWAY_KEY=os.environ.get('ANREDSELLER_ADMIN_GATEWAY_KEY', ''),
        SECURE_COOKIES=os.environ.get('ANREDSELLER_SECURE_COOKIES', '1') == '1',
        MAX_CONTENT_LENGTH=4 * 1024 * 1024 + 64 * 1024,
        UPSTREAM_TIMEOUT=20,
    )
    app.config.update(config or {})
    app.config['BACKEND_URL'] = origin(app.config['BACKEND_URL'], 'BACKEND_URL')
    app.config['SHOP_URL'] = origin(app.config['SHOP_URL'] or app.config['BACKEND_URL'], 'SHOP_URL')
    key = app.config['ADMIN_GATEWAY_KEY']
    if key and len(key) < 32:
        raise ValueError('ADMIN_GATEWAY_KEY harus minimal 32 karakter.')
    upstream = build_opener(NoRedirect())

    def configured():
        return bool(app.config['BACKEND_URL'] and app.config['SHOP_URL'] and key)

    @app.after_request
    def response_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        return response

    def proxy(path, method='GET'):
        if not configured():
            return jsonify(error='Portal admin belum terhubung ke server toko. Lengkapi pengaturan hosting.'), 503
        headers = {'X-Anredseller-Admin-Key': key, 'Accept': request.headers.get('Accept', 'application/json')}
        if request.headers.get('X-CSRF-Token'):
            headers['X-CSRF-Token'] = request.headers['X-CSRF-Token']
        cookie = request.cookies.get(COOKIE_NAME, '')
        if re.fullmatch(r'[A-Za-z0-9_.-]{1,4096}', cookie):
            headers['Cookie'] = 'session=' + cookie
        if request.content_type:
            headers['Content-Type'] = request.content_type
        data = request.get_data() if method in {'POST', 'PUT', 'PATCH', 'DELETE'} else None
        outgoing = Request(app.config['BACKEND_URL'] + path, data=data, headers=headers, method=method)
        try:
            try:
                response = upstream.open(outgoing, timeout=app.config['UPSTREAM_TIMEOUT'])
            except HTTPError as error:
                response = error
            with response:
                # Redirects are rejected, so the gateway key cannot reach a
                # destination chosen by a Location header from upstream.
                if 300 <= response.code < 400:
                    return jsonify(error='Alamat server toko berubah. Periksa pengaturan hosting.'), 502
                payload = response.read(32 * 1024 * 1024 + 1)
                if len(payload) > 32 * 1024 * 1024:
                    return jsonify(error='Respons server toko terlalu besar.'), 502
                result = app.response_class(payload, status=response.code,
                                            content_type=response.headers.get('Content-Type', 'application/json'))
                for header in response.headers.get_all('Set-Cookie', []):
                    cookies = SimpleCookie()
                    cookies.load(header)
                    if 'session' in cookies:
                        session = cookies['session']
                        result.set_cookie(COOKIE_NAME, session.value,
                                          max_age=int(session['max-age']) if session['max-age'] else None,
                                          expires=session['expires'] or None,
                                          secure=app.config['SECURE_COOKIES'], httponly=True,
                                          samesite='Lax', path='/')
                return result
        except (URLError, TimeoutError, OSError):
            return jsonify(error='Server toko belum dapat dihubungi. Coba lagi nanti.'), 502

    @app.get('/')
    @app.get('/admin')
    @app.get('/admin.html')
    @app.get('/index.html')
    def index():
        return send_from_directory(ROOT / 'templates', 'index.html')

    @app.get('/portal-config')
    def portal_config():
        return jsonify(shop_url=app.config['SHOP_URL'])

    @app.get('/api/health')
    def health():
        return proxy('/api/health')

    @app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
    def admin_api(path):
        target = '/api/' + path
        if not any(request.method == method and re.fullmatch(pattern, target) for method, pattern in API_ROUTES):
            return jsonify(error='Endpoint tidak tersedia di portal admin.'), 404
        # Defense in depth in addition to the store's per-session CSRF token.
        source = request.headers.get('Origin')
        if request.method != 'GET' and source:
            parsed = urlsplit(source)
            if parsed.scheme not in {'http', 'https'} or parsed.netloc.lower() != request.host.lower():
                return jsonify(error='Asal permintaan tidak diizinkan.'), 403
        if request.query_string:
            target += '?' + request.query_string.decode('ascii', errors='strict')
        return proxy(target, request.method)

    @app.get('/css/admin.css')
    @app.get('/js/admin.js')
    def ui_asset():
        return send_from_directory(ROOT / 'static', request.path.lstrip('/'))

    @app.get('/fonts/<filename>')
    def brand_font(filename):
        if not re.fullmatch(r'switzer-latin-(?:400|500|600)-normal\.woff2', filename):
            abort(404)
        return send_from_directory(ROOT / 'static' / 'fonts', filename)

    @app.get('/assets/<filename>')
    def catalog_asset(filename):
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.(?:png|jpe?g|webp|svg)', filename):
            abort(404)
        return proxy('/assets/' + filename)

    @app.get('/uploads/<filename>')
    def uploaded_asset(filename):
        if not re.fullmatch(r'[a-f0-9]{32}\.webp', filename):
            abort(404)
        return proxy('/uploads/' + filename)

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8001)
