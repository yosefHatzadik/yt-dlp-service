from flask import Flask, request, jsonify
import subprocess
import tempfile
import os

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def run():
    try:
        # קבלת פרמטרים
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form.to_dict()
        else:
            data = request.args.to_dict()

        cmd = data.get('cmd') or data.get('command')
        if not cmd:
            return jsonify({'error': 'Missing cmd parameter'}), 400

        # בניית הפקודה הבסיסית
        command = ['yt-dlp'] + cmd.split()

        # אופציה 1 (מומלצת ביותר): cookies ישירות מהדפדפן בשרת Render
        browser = data.get('browser', '').lower()
        if browser in ['chrome', 'firefox', 'edge', 'brave', 'opera', 'safari']:
            command.extend(['--cookies-from-browser', browser])

        # אופציה 2 (גיבוי): אם שלחת קובץ cookies.txt כטקסט
        elif 'cookies' in data and data['cookies'].strip():
            cookies = data['cookies']
            temp_dir = tempfile.mkdtemp()
            cookies_file = os.path.join(temp_dir, 'cookies.txt')
            with open(cookies_file, 'w', encoding='utf-8') as f:
                if not cookies.strip().startswith('# Netscape'):
                    f.write('# Netscape HTTP Cookie File\n\n')
                f.write(cookies)
            command.extend(['--cookies', cookies_file])

        # הרצה
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=90  # קצת יותר זמן לבטיחות
        )

        # ניקוי קובץ עוגיות זמני אם היה
        if 'cookies_file' in locals() and os.path.exists(cookies_file):
            os.remove(cookies_file)
            os.rmdir(temp_dir)

        # תגובה
        if result.returncode != 0:
            return jsonify({
                'error': result.stderr.strip(),
                'stdout': result.stdout.strip(),
                'returncode': result.returncode
            }), 500

        # אם זה קישור ישיר – נחזיר אותו יפה
        stdout = result.stdout.strip()
        if stdout.startswith('https://'):
            return jsonify({'url': stdout})

        # אחרת נחזיר JSON של yt-dlp
        try:
            return jsonify(json.loads(stdout))
        except:
            return jsonify({'stdout': stdout, 'stderr': result.stderr.strip()})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
