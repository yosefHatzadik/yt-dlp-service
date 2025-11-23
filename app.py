from flask import Flask, request, jsonify
import subprocess
import tempfile
import os
import json

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
        cookies = data.get('cookies', '')
        
        if not cmd:
            return jsonify({'error': 'Missing cmd parameter'}), 400
        
        # הכנת פקודה
        command = ['yt-dlp'] + cmd.split()
        
        # הוספת עוגיות אם יש
        cookies_file = None
        if cookies.strip():
            temp_dir = tempfile.mkdtemp()
            cookies_file = os.path.join(temp_dir, 'cookies.txt')
            with open(cookies_file, 'w', encoding='utf-8') as f:
                if not cookies.strip().startswith('# Netscape'):
                    f.write('# Netscape HTTP Cookie File\n')
                    f.write('# This is a generated file! Do not edit.\n\n')
                f.write(cookies)
            command.extend(['--cookies', cookies_file])
        
        # הוספת --dump-json אוטומטית אם לא ביקשו הורדה
        if '--dump-json' not in command and '-J' not in command and '-o' not in command:
            command.append('--dump-json')
        
        # הרצת הפקודה
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # ניקוי עוגיות
        if cookies_file and os.path.exists(cookies_file):
            os.remove(cookies_file)
            os.rmdir(os.path.dirname(cookies_file))
        
        # החזרת התוצאה
        if result.returncode != 0:
            return jsonify({
                'error': result.stderr,
                'stdout': result.stdout,
                'returncode': result.returncode
            }), 500
        
        # ניסיון לפרסר JSON אם יש
        try:
            return jsonify(json.loads(result.stdout))
        except:
            # אם לא JSON, החזר טקסט
            return jsonify({
                'stdout': result.stdout,
                'stderr': result.stderr
            })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Command timeout'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
