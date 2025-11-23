from flask import Flask, request, jsonify
import subprocess
import tempfile
import os

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
        full_cmd.extend(cmd_args.split())
        if cookies_path:
            full_cmd.append('--cookies')
            full_cmd.append(cookies_path)
        
        # EJS solver (משתמש ב-Deno)
        full_cmd.append('--remote-components')
        full_cmd.append('ejs:github')
        
        # Data Sync ID
        if data_sync_id:
            full_cmd.append('--extractor-args')
            full_cmd.append(f'youtube:data_sync_id={data_sync_id}')
        
        # Throttle מוגבר ל-429
        full_cmd.append('--sleep-interval')
        full_cmd.append('10')
        full_cmd.append('--max-sleep-interval')
        full_cmd.append('30')
        
        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                cwd=tmpdir,
                timeout=900  # 15 דקות
            )
            
            output_files = []
            if result.returncode == 0 and os.listdir(tmpdir):
                output_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if not f.startswith('.')]
            
            return jsonify({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "output_files": output_files
            })
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Command timed out"}), 408
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
