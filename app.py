from flask import Flask, render_template, request
import os, json, hashlib, random, string, requests, urllib.parse, uuid

app = Flask(__name__)
app.config['DATA_FILE'] = 'data.json'
HANCOM_SERVER = 'http://210.95.181.17:8101'  # 문서뷰어 서버 주소

SUPPORTED_EXTENSIONS = {
    'hwp', 'hwpx', 'doc', 'docx', 'ppt', 'pptx',
    'xls', 'xlsx', 'pdf', 'txt', 'odt',
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'svg', 'html'
}

# --- 유틸리티 함수 ---

def load_data():
    if os.path.exists(app.config['DATA_FILE']):
        try:
            with open(app.config['DATA_FILE'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_data(data):
    with open(app.config['DATA_FILE'], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_password():
    return str(random.randint(1000, 9999))

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()[:10]

def generate_id(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_file_hash(file):
    file.seek(0)
    content = file.read()
    file.seek(0)
    return hashlib.sha256(content).hexdigest()[:16]

def upload_to_hancom(file):
    ext = file.filename.rsplit('.', 1)[-1]
    short_uuid = uuid.uuid4().hex[:32].upper()
    safe_filename = f"{short_uuid}.{ext}"
    url = f"{HANCOM_SERVER}/rest/upload_file"
    files = {'file': (safe_filename, file.stream, file.mimetype)}

    try:
        res = requests.post(url, files=files)
        res.raise_for_status()
        result = res.json()
        if result.get("code") == "0000":
            return result.get("upload_file_path")
    except Exception as e:
        print("[한컴 업로드 실패]", e)
    return None

# --- 라우트 ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return 'No file uploaded', 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return f'{ext.upper()} 형식은 지원하지 않습니다.', 400

    filehash = get_file_hash(file)
    data = load_data()

    for sid, entry in data.items():
        if entry.get('filehash') == filehash:
            return {
                'short_url': f'/doc/{sid}',
                'password': entry['pw']
            }

    hancom_path = upload_to_hancom(file)
    if not hancom_path:
        return '한컴 서버 업로드 실패', 500

    password = generate_password()
    short_id = generate_id()
    encoded_path = urllib.parse.quote(hancom_path, safe='')
    viewer_url = f"{HANCOM_SERVER}/hdv/view/?file_path={encoded_path}&ext_to=jpg"

    data[short_id] = {
        'pw': password,
        'hash': hash_password(password),
        'filehash': filehash,
        'viewer_url': viewer_url
    }
    save_data(data)

    return {
        'short_url': f'/doc/{short_id}',
        'password': password
    }

@app.route('/doc/<short_id>')
def doc(short_id):
    data = load_data()
    entry = data.get(short_id)
    if not entry:
        return '유효하지 않은 문서입니다.', 404
    return render_template('passcheck.html', doc_id=short_id, error='')

@app.route('/view/<short_id>', methods=['POST'])
def view(short_id):
    input_pw = request.form.get('password', '').strip()
    data = load_data()
    entry = data.get(short_id)
    if not entry:
        return '존재하지 않는 문서입니다.', 404

    if hash_password(input_pw) == entry['hash']:
        return f"""
        <script>
          sessionStorage.setItem("auth_{short_id}", "ok");
          const win = window.open("{entry['viewer_url']}", "_blank");
          if (win) {{
            window.close();
          }} else {{
            location.href = "{entry['viewer_url']}";
          }}
        </script>
        """
    else:
        return render_template("passcheck.html", doc_id=short_id, error="비밀번호가 틀렸습니다.")

@app.route('/reset', methods=['POST'])
def reset():
    data = request.get_json()
    pw = data.get('password', '')

    # 안전하게 비교할 실제 관리자 비밀번호 해시값
    ADMIN_HASH = hash_password("3702")  # 실제 비밀번호는 환경변수로 관리하면 더 안전함

    if hash_password(pw) != ADMIN_HASH:
        print("❌ 관리자 인증 실패")
        return { 'success': False, 'message': '잘못된 관리자 비밀번호입니다.' }

    # 👉 초기화 작업들 수행 (data.json, 캐시, 로그 삭제 등)
    try:
        open(app.config['DATA_FILE'], 'w', encoding='utf-8').write('{}')
        print("🧼 data.json 초기화 완료")

        requests.get(f"{HANCOM_SERVER}/host/delete/cache")
        requests.get(f"{HANCOM_SERVER}/rest/delete/log")
        print("🧹 캐시 및 로그 삭제 완료")

        return { 'success': True }
    except Exception as e:
        print("❌ 초기화 오류:", e)
        return { 'success': False, 'message': '초기화 중 오류 발생' }
    
@app.before_request
def restrict_ip_access():
    ip = request.remote_addr
    path = request.path

    # IP 제한이 필요한 경로만 설정
    IP_RESTRICTED_PATHS = ['/upload']

    if any(path.startswith(p) for p in IP_RESTRICTED_PATHS):
        ALLOWED_IP_PREFIXES = ['108.']
        if not any(ip.startswith(prefix) for prefix in ALLOWED_IP_PREFIXES):
            print(f"🚫 접근 제한: {ip} → {path}")
            abort(403)

@app.route('/check-ip')
def check_ip():
    remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    print(f"접속 IP: {remote_ip}")

    allowed_prefixes = ['108.']
    is_internal = any(remote_ip.startswith(prefix) for prefix in allowed_prefixes)

    return {'internal': is_internal}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)


