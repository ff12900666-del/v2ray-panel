import os
import json
import uuid
import qrcode
import io
import base64
import time
import urllib.request
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'v2ray-panel-secret-key-2024')

PASSWORD = os.environ.get('PANEL_PASSWORD', 'abol666k')
DB_FILE = 'configs.json'
SERVER_PORT = int(os.environ.get('SERVER_PORT', 8080))
SERVER_PATH = os.environ.get('SERVER_PATH', '/v2ray')
SERVER_UUID = os.environ.get('SERVER_UUID', 'ba4eb3e6-9a3d-426e-bc7b-a5dc0c0c6b5f')


def get_current_ip():
    try:
        with urllib.request.urlopen('https://ifconfig.me', timeout=5) as r:
            return r.read().decode().strip()
    except:
        try:
            with urllib.request.urlopen('https://ipinfo.io/ip', timeout=5) as r:
                return r.read().decode().strip()
        except:
            return 'YOUR_SERVER_IP'


def load_configs():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return []


def save_configs(configs):
    with open(DB_FILE, 'w') as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def generate_uuid():
    return str(uuid.uuid4())


def generate_vmess_link(config):
    vmess_obj = {
        "v": "2",
        "ps": config['remark'],
        "add": config['server_address'],
        "port": str(config['server_port']),
        "id": config['uuid'],
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": config.get('host', ''),
        "path": config.get('path', '/'),
        "tls": "tls",
        "sni": config.get('sni', config['server_address']),
        "alpn": "http/1.1",
        "fp": "chrome"
    }
    return "vmess://" + base64.b64encode(json.dumps(vmess_obj).encode()).decode()


def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='رمز عبور اشتباه است')
    return render_template('login.html', error=None)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    configs = load_configs()
    now = datetime.now()
    for c in configs:
        if c.get('expire_date'):
            expire = datetime.fromisoformat(c['expire_date'])
            c['days_left'] = (expire - now).days
            c['is_expired'] = c['days_left'] < 0
        else:
            c['days_left'] = None
            c['is_expired'] = False
        if c.get('traffic_limit', 0) > 0:
            c['traffic_used_gb'] = round(c.get('traffic_used', 0) / (1024**3), 2)
            c['traffic_limit_gb'] = round(c['traffic_limit'] / (1024**3), 2)
            c['traffic_percent'] = min(100, round((c['traffic_used'] / c['traffic_limit']) * 100, 1))
        else:
            c['traffic_used_gb'] = 0
            c['traffic_limit_gb'] = 0
            c['traffic_percent'] = 0
    return render_template('dashboard.html', configs=configs)


@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_config():
    current_ip = get_current_ip()
    if request.method == 'POST':
        configs = load_configs()
        data = request.form

        config = {
            'id': str(int(time.time() * 1000)),
            'remark': data.get('remark', 'Config'),
            'server_address': data.get('server_address', current_ip),
            'server_port': int(data.get('server_port', SERVER_PORT)),
            'uuid': data.get('uuid', SERVER_UUID),
            'host': data.get('host', ''),
            'sni': data.get('sni', ''),
            'path': data.get('path', SERVER_PATH),
            'created_at': datetime.now().isoformat(),
            'active': True,
            'traffic_limit': int(data.get('traffic_limit', 0)) * (1024**3) if data.get('traffic_limit') and data.get('traffic_limit') != '0' else 0,
            'traffic_used': 0,
            'max_users': int(data.get('max_users', 0)) if data.get('max_users') and data.get('max_users') != '0' else 0,
            'connected_users': 0,
            'expire_days': int(data.get('expire_days', 0)) if data.get('expire_days') and data.get('expire_days') != '0' else 0,
            'expire_date': (datetime.now() + timedelta(days=int(data.get('expire_days', 0)))).isoformat() if data.get('expire_days') and data.get('expire_days') != '0' else None,
            'unlimited_traffic': data.get('unlimited_traffic') == 'on',
            'unlimited_users': data.get('unlimited_users') == 'on',
            'unlimited_days': data.get('unlimited_days') == 'on',
        }

        if config['unlimited_traffic']:
            config['traffic_limit'] = 0
        if config['unlimited_users']:
            config['max_users'] = 0
        if config['unlimited_days']:
            config['expire_date'] = None
            config['expire_days'] = 0

        vmess_link = generate_vmess_link(config)
        config['vmess_link'] = vmess_link
        config['qr_code'] = generate_qr_code(vmess_link)

        sub_link = f"{request.host_url}sub/{config['id']}"
        config['sub_link'] = sub_link

        configs.append(config)
        save_configs(configs)

        return redirect(url_for('config_detail', config_id=config['id']))

    return render_template('create.html', uuid=SERVER_UUID, current_ip=get_current_ip(), server_port=SERVER_PORT)


@app.route('/config/<config_id>')
@login_required
def config_detail(config_id):
    configs = load_configs()
    config = next((c for c in configs if c['id'] == config_id), None)
    if not config:
        return redirect(url_for('dashboard'))

    vmess_link = config.get('vmess_link') or generate_vmess_link(config)
    qr_code = config.get('qr_code') or generate_qr_code(vmess_link)
    sub_link = config.get('sub_link') or f"{request.host_url}sub/{config['id']}"

    now = datetime.now()
    if config.get('expire_date'):
        expire = datetime.fromisoformat(config['expire_date'])
        config['days_left'] = (expire - now).days
        config['is_expired'] = config['days_left'] < 0
    else:
        config['days_left'] = None
        config['is_expired'] = False

    if config.get('traffic_limit', 0) > 0:
        config['traffic_used_gb'] = round(config.get('traffic_used', 0) / (1024**3), 2)
        config['traffic_limit_gb'] = round(config['traffic_limit'] / (1024**3), 2)
        config['traffic_percent'] = min(100, round((config['traffic_used'] / config['traffic_limit']) * 100, 1))
    else:
        config['traffic_used_gb'] = 0
        config['traffic_limit_gb'] = 0
        config['traffic_percent'] = 0

    return render_template('detail.html', config=config, vmess_link=vmess_link, qr_code=qr_code, sub_link=sub_link)


@app.route('/edit/<config_id>', methods=['GET', 'POST'])
@login_required
def edit_config(config_id):
    configs = load_configs()
    config = next((c for c in configs if c['id'] == config_id), None)
    if not config:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        data = request.form
        config['remark'] = data.get('remark', config['remark'])
        config['server_address'] = data.get('server_address', config['server_address'])
        config['server_port'] = int(data.get('server_port', config['server_port']))
        config['host'] = data.get('host', config.get('host', ''))
        config['sni'] = data.get('sni', config.get('sni', ''))
        config['path'] = data.get('path', config.get('path', '/'))
        config['unlimited_traffic'] = data.get('unlimited_traffic') == 'on'
        config['unlimited_users'] = data.get('unlimited_users') == 'on'
        config['unlimited_days'] = data.get('unlimited_days') == 'on'

        if config['unlimited_traffic']:
            config['traffic_limit'] = 0
        else:
            config['traffic_limit'] = int(data.get('traffic_limit', 0)) * (1024**3) if data.get('traffic_limit') and data.get('traffic_limit') != '0' else 0

        if config['unlimited_users']:
            config['max_users'] = 0
        else:
            config['max_users'] = int(data.get('max_users', 0)) if data.get('max_users') and data.get('max_users') != '0' else 0

        if config['unlimited_days']:
            config['expire_date'] = None
            config['expire_days'] = 0
        else:
            days = int(data.get('expire_days', 0)) if data.get('expire_days') and data.get('expire_days') != '0' else 0
            config['expire_days'] = days
            if days > 0:
                config['expire_date'] = (datetime.now() + timedelta(days=days)).isoformat()

        vmess_link = generate_vmess_link(config)
        config['vmess_link'] = vmess_link
        config['qr_code'] = generate_qr_code(vmess_link)
        config['sub_link'] = f"{request.host_url}sub/{config['id']}"

        save_configs(configs)
        return redirect(url_for('config_detail', config_id=config['id']))

    return render_template('edit.html', config=config)


@app.route('/delete/<config_id>', methods=['POST'])
@login_required
def delete_config(config_id):
    configs = load_configs()
    configs = [c for c in configs if c['id'] != config_id]
    save_configs(configs)
    return redirect(url_for('dashboard'))


@app.route('/toggle/<config_id>', methods=['POST'])
@login_required
def toggle_config(config_id):
    configs = load_configs()
    for c in configs:
        if c['id'] == config_id:
            c['active'] = not c['active']
            break
    save_configs(configs)
    return jsonify({'success': True})


@app.route('/sub/<config_id>')
def subscription(config_id):
    configs = load_configs()
    config = next((c for c in configs if c['id'] == config_id), None)
    if not config or not config.get('active'):
        return Response("Not Found", status=404)

    vmess_link = config.get('vmess_link') or generate_vmess_link(config)
    return Response(vmess_link, mimetype='text/plain', headers={
        'Content-Disposition': f'attachment; filename="{config["remark"]}.txt"'
    })


@app.route('/api/configs')
@login_required
def api_configs():
    configs = load_configs()
    for c in configs:
        c.pop('qr_code', None)
    return jsonify(configs)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
