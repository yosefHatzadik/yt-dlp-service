from flask import Flask, request, jsonify
import subprocess
import tempfile
import os
import shutil  # להעתקת קבצים אם צריך (אופציונלי)

app = Flask(__name__)

@app.route('/', methods=['POST'])
def run_yt_dlp():
    data = request.get_json()
    cmd_args = data.get('cmd', '')
    cookies_content = data.get('cookies', None)
    
    if not cmd_args:
        return jsonify({"error": "Missing cmd parameter"}), 400
    
    # צור תיקייה זמנית להורדות ועוגיות
    with tempfile.TemporaryDirectory() as tmpdir:
        cookies_path = None
        if cookies_content:
            cookies_path = os.path.join(tmpdir, 'cookies.txt')
            with open(cookies_path, 'w', encoding='utf-8') as f:
                f.write(cookies_content)
        
        # בנה את הפקודה המלאה: yt-dlp + args + --cookies אם צריך
        full_cmd = ['yt-dlp']
        full_cmd.extend(cmd_args.split())  # פצל את cmd_args לרשימה (בטוח יותר מ-shell=True)
        if cookies_path:
            full_cmd.append('--cookies')
            full_cmd.append(cookies_path)
        
        # רץ את הפקודה בתיקייה זמנית
        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=600  # 10 דקות מקסימום, התאם אם צריך
            )
            
            # העתק קבצים שהורדו אם יש (אופציונלי: החזר paths)
            output_files = []
            if result.returncode == 0 and os.listdir(tmpdir):
                output_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if not f.startswith('.')]
                # אם צריך להחזיר קישורים, העלה ל-S3 או משהו – אבל כאן נשמור פשוט על טקסט
            
            return jsonify({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "output_files": output_files  # רשימת קבצים שהורדו (paths זמניים)
            })
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Command timed out"}), 408
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)  # Render משתמש בפורט 10000
