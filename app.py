from flask import Flask, request, jsonify
import yt_dlp
import tempfile
import os

app = Flask(__name__)

def get_cookies(cookies_str):
    """פונקציה קבועה ליצירת קובץ עוגיות"""
    if not cookies_str or not cookies_str.strip():
        return None
    temp_dir = tempfile.mkdtemp()
    cookies_file = os.path.join(temp_dir, 'cookies.txt')
    with open(cookies_file, 'w') as f:
        if not cookies_str.strip().startswith('# Netscape'):
            f.write('# Netscape HTTP Cookie File\n')
            f.write('# This is a generated file! Do not edit.\n\n')
        f.write(cookies_str)
    return cookies_file

@app.route('/', methods=['POST', 'GET'])
def run():
    try:
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form.to_dict()
        else:
            data = request.args.to_dict()
        
        url = data.get('url')
        cookies_str = data.get('cookies', '')
        yt_dlp_opts = data.get('opts', {})
        
        if not url:
            return jsonify({'error': 'Missing url'}), 400
        
        # הכנת עוגיות
        cookies_file = get_cookies(cookies_str)
        if cookies_file:
            yt_dlp_opts['cookiefile'] = cookies_file
        
        # הרצת yt-dlp
        with yt_dlp.YoutubeDL(yt_dlp_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        # ניקוי
        if cookies_file and os.path.exists(cookies_file):
            os.remove(cookies_file)
            os.rmdir(os.path.dirname(cookies_file))
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
