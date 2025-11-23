from flask import Flask, request, jsonify
import subprocess
import tempfile
import os
import time

app = Flask(__name__)

@app.route('/', methods=['POST'])
def run_yt_dlp():
    data = request.get_json()
    cmd_args = data.get('cmd', '')
    cookies_content = data.get('cookies', None)
    data_sync_id = data.get('data_sync_id', None)
    
    if not cmd_args:
        return jsonify({"error": "Missing cmd parameter"}), 400
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cookies_path = None
        if cookies_content:
            cookies_path = os.path.join(tmpdir, 'cookies.txt')
            with open(cookies_path, 'w', encoding='utf-8') as f:
                f.write(cookies_content)
        
        full_cmd = ['yt-dlp']
        
        # הוסף cookies לפני הכל
        if cookies_path:
            full_cmd.extend(['--cookies', cookies_path])
        
        # אסטרטגיות עקיפת בוט
        full_cmd.extend([
            '--extractor-retries', '10',
            '--fragment-retries', '10',
            '--retry-sleep', '10',
            '--sleep-requests', '3',
            '--sleep-interval', '15',
            '--max-sleep-interval', '45',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--add-header', 'Accept-Language:en-US,en;q=0.9',
            '--add-header', 'Accept:text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '--no-check-certificates'
        ])
        
        # Data Sync ID
        if data_sync_id:
            full_cmd.extend(['--extractor-args', f'youtube:data_sync_id={data_sync_id}'])
        
        # הוסף את פקודות המשתמש בסוף
        full_cmd.extend(cmd_args.split())
        
        try:
            # המתן קצת לפני הבקשה
            time.sleep(2)
            
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=900
            )
            
            return jsonify({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "cmd": ' '.join(full_cmd)  # לדיבוג
            })
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Command timed out"}), 408
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
