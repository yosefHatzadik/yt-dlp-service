from flask import Flask, request, jsonify
import yt_dlp
import os
import tempfile
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return '''
    <html dir="rtl">
    <body style="font-family: Arial; padding: 20px;">
        <h1>🎥 שירות חילוץ קישורי YouTube</h1>
        <p>API מחזיר קישור הורדה ישיר במקום להוריד את הקובץ</p>
        <h3>POST:</h3>
        <code>POST /get-download-url</code>
        <pre>{"url": "...", "cookies": "..."}</pre>
        <h3>תגובה:</h3>
        <pre>{"success": true, "download_url": "...", "title": "...", "ext": "mp4"}</pre>
    </body>
    </html>
    '''

@app.route('/get-download-url', methods=['POST', 'GET'])
def get_download_url():
    try:
        # קבלת פרמטרים
        if request.method == 'POST':
            data = request.get_json() or {}
            youtube_url = data.get('url') or request.args.get('url')
            cookies_data = data.get('cookies', '')
        else:
            youtube_url = request.args.get('url')
            cookies_data = request.args.get('cookies', '')
        
        if not youtube_url:
            return jsonify({'success': False, 'error': 'חסר פרמטר url'}), 400
        
        logging.info(f"מחלץ מידע: {youtube_url}")
        logging.info(f"יש עוגיות: {'כן' if cookies_data else 'לא'}")
        
        # יצירת קובץ עוגיות זמני אם צריך
        temp_dir = tempfile.mkdtemp()
        cookies_file = None
        
        try:
            if cookies_data:
                cookies_file = os.path.join(temp_dir, 'cookies.txt')
                with open(cookies_file, 'w', encoding='utf-8') as f:
                    if not cookies_data.strip().startswith('# Netscape HTTP Cookie File'):
                        f.write('# Netscape HTTP Cookie File\n')
                        f.write('# This is a generated file! Do not edit.\n\n')
                    f.write(cookies_data)
                logging.info(f"קובץ עוגיות נוצר")
            
            # הגדרות yt-dlp - רק חילוץ מידע, בלי הורדה!
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,  # לא להוריד!
            }
            
            if cookies_file and os.path.exists(cookies_file):
                ydl_opts['cookiefile'] = cookies_file
                logging.info("משתמש בעוגיות")
            
            # חילוץ מידע על הסרטון
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
            
            # קישור ההורדה הישיר
            download_url = info.get('url')
            title = info.get('title', 'video')
            ext = info.get('ext', 'mp4')
            filesize = info.get('filesize') or info.get('filesize_approx', 0)
            
            if not download_url:
                return jsonify({
                    'success': False, 
                    'error': 'לא נמצא קישור הורדה'
                }), 500
            
            logging.info(f"✅ קישור נמצא: {title}.{ext}")
            
            return jsonify({
                'success': True,
                'download_url': download_url,
                'title': title,
                'ext': ext,
                'filesize': filesize,
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail')
            })
            
        finally:
            # ניקוי
            try:
                if cookies_file and os.path.exists(cookies_file):
                    os.remove(cookies_file)
                os.rmdir(temp_dir)
            except Exception as e:
                logging.warning(f"שגיאה בניקוי: {e}")
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logging.error(f"שגיאת yt-dlp: {error_msg}")
        
        # ניתוח השגיאה
        if 'Sign in' in error_msg or 'login' in error_msg.lower():
            return jsonify({
                'success': False,
                'error': 'הסרטון דורש התחברות - העוגיות לא תקפות או חסרות',
                'error_type': 'auth_required'
            }), 403
        elif 'bot' in error_msg.lower():
            return jsonify({
                'success': False,
                'error': 'YouTube חסם את הבקשה - נסה שוב מאוחר יותר',
                'error_type': 'bot_detected'
            }), 429
        elif 'Private video' in error_msg or 'private' in error_msg.lower():
            return jsonify({
                'success': False,
                'error': 'סרטון פרטי - העוגיות חייבות להיות מחשבון עם גישה',
                'error_type': 'private'
            }), 403
        else:
            return jsonify({
                'success': False,
                'error': f'שגיאה: {error_msg}',
                'error_type': 'download_error'
            }), 500
            
    except Exception as e:
        logging.error(f"שגיאה כללית: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'general'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
