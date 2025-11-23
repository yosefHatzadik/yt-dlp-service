from flask import Flask, request, jsonify
import subprocess
import tempfile
import os

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def run():
    try:
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form.to_dict()
        else:
            data = request.args.to_dict()

        cmd = data.get('cmd') or data.get('command')
        cookies_txt = data.get('cookies', '')

        if not cmd:
            return jsonify({'error': 'Missing cmd'}), 400

        # בניית הפקודה
        full_cmd = ['yt-dlp'] + cmd.split()

        # הוספת cookies.txt זמני אם שלחת
        cookies_file = None
        if cookies_txt.strip():
            temp_dir = tempfile.mkdtemp()
            cookies_file = os.path.join(temp_dir, 'cookies.txt')
            with open(cookies_file, 'w', encoding='utf-8') as f:
                if not cookies_txt.startswith('# Netscape'):
                    f.write('# Netscape HTTP Cookie File\n\n')
                f.write(cookies_txt)
            full_cmd += ['--cookies', cookies_file]

        # הרצה
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=90)

        # ניקוי
        if cookies_file and os.path.exists(cookies_file):
            os.remove(cookies_file)
            os.rmdir(temp_dir)

        if result.returncode != 0:
            return jsonify({'error': result.stderr}), 500

        out = result.stdout.strip()
        if out.startswith('https://'):
            return jsonify({'url': out})
        else:
            try:
                return jsonify(json.loads(out))
            except:
                return jsonify({'stdout': out})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
