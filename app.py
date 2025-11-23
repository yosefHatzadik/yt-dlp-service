from flask import Flask, request, send_file, jsonify
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
        <h1>🎥 yt-dlp Wrapper API</h1>
        <p>API פשוט שמעביר פרמטרים ישירות ל-yt-dlp</p>
        
        <h3>POST /execute</h3>
        <p>מריץ yt-dlp עם פרמטרים שאתה שולח</p>
        <pre>{
  "url": "youtube_url",
  "yt_dlp_options": {
    "format": "best",
    "quiet": true,
    ...
  },
  "cookies": "optional_cookies_string",
  "action": "info|download"
}</pre>
        
        <p><strong>action:</strong></p>
        <ul>
            <li><code>info</code> - רק מידע (ברירת מחדל)</li>
            <li><code>download</code> - הורדה ושליחת קובץ</li>
        </ul>
    </body>
    </html>
    '''

def get_cookies_file(cookies_data):
    """יוצר קובץ עוגיות זמני"""
    if not cookies_data:
        return None
        
    temp_dir = tempfile.mkdtemp()
    cookies_file = os.path.join(temp_dir, 'cookies.txt')
    
    with open(cookies_file, 'w', encoding='utf-8') as f:
        if not cookies_data.strip().startswith('# Netscape HTTP Cookie File'):
            f.write('# Netscape HTTP Cookie File\n')
            f.write('# This is a generated file! Do not edit.\n\n')
        f.write(cookies_data)
    
    return cookies_file

def cleanup_file(filepath):
    """מנקה קובץ זמני"""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            temp_dir = os.path.dirname(filepath)
            if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)
    except Exception as e:
        logging.warning(f"שגיאה בניקוי: {e}")

@app.route('/execute', methods=['POST', 'GET'])
def execute():
    """מריץ yt-dlp עם הפרמטרים שהתקבלו"""
    try:
        # קבלת נתונים - תמיכה ב-POST (JSON) וגם ב-GET (query params)
        if request.method == 'POST':
            if request.is_json:
                data = request.get_json()
            else:
                # אם זה form data
                data = request.form.to_dict()
        else:
            data = request.args.to_dict()
        
        # פרמטרים בסיסיים
        youtube_url = data.get('url')
        cookies_data = data.get('cookies', '')
        action = data.get('action', 'info')  # info או download
        
        # אפשרויות yt-dlp - יכול לבוא כ-JSON או כ-string
        yt_dlp_options = data.get('yt_dlp_options', {})
        if isinstance(yt_dlp_options, str):
            import json
            try:
                yt_dlp_options = json.loads(yt_dlp_options)
            except:
                yt_dlp_options = {}
        
        if not youtube_url:
            return jsonify({'success': False, 'error': 'חסר פרמטר url'}), 400
        
        logging.info(f"מעבד: {youtube_url} | action: {action}")
        logging.info(f"אפשרויות: {yt_dlp_options}")
        
        # הכנת קובץ עוגיות
        cookies_file = get_cookies_file(cookies_data)
        temp_dir = None
        
        try:
            # הגדרות ברירת מחדל
            default_opts = {
                'quiet': False,
                'no_warnings': False,
            }
            
            # מיזוג עם האפשרויות שהתקבלו
            ydl_opts = {**default_opts, **yt_dlp_options}
            
            # הוספת עוגיות אם קיימות
            if cookies_file:
                ydl_opts['cookiefile'] = cookies_file
                logging.info("משתמש בעוגיות")
            
            # אם זו הורדה, הגדרת תיקיה זמנית
            if action == 'download':
                temp_dir = tempfile.mkdtemp()
                ydl_opts['outtmpl'] = os.path.join(temp_dir, '%(title)s.%(ext)s')
            
            # הרצת yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=(action == 'download'))
            
            # טיפול לפי סוג הפעולה
            if action == 'download':
                # מציאת הקובץ שהורד
                filename = ydl.prepare_filename(info)
                
                if not os.path.exists(filename):
                    return jsonify({'success': False, 'error': 'הקובץ לא נוצר'}), 500
                
                logging.info(f"✅ הורדה הושלמה: {filename}")
                
                # שליחת הקובץ
                return send_file(
                    filename,
                    as_attachment=True,
                    download_name=os.path.basename(filename),
                    mimetype='video/mp4'
                )
            else:
                # החזרת מידע בלבד
                # ניקוי מידע רגיש/מיותר
                safe_info = {
                    'success': True,
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'url': info.get('url'),
                    'ext': info.get('ext'),
                    'format': info.get('format'),
                    'format_id': info.get('format_id'),
                    'width': info.get('width'),
                    'height': info.get('height'),
                    'resolution': info.get('resolution'),
                    'fps': info.get('fps'),
                    'vcodec': info.get('vcodec'),
                    'acodec': info.get('acodec'),
                    'filesize': info.get('filesize'),
                    'filesize_approx': info.get('filesize_approx'),
                    'tbr': info.get('tbr'),
                    'duration': info.get('duration'),
                    'thumbnail': info.get('thumbnail'),
                    'description': info.get('description'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'protocol': info.get('protocol'),
                    'formats': info.get('formats', []) if data.get('include_formats') else None,
                }
                
                # הסרת ערכים ריקים
                safe_info = {k: v for k, v in safe_info.items() if v is not None}
                
                logging.info(f"✅ מידע נשלח")
                
                return jsonify(safe_info)
            
        finally:
            # ניקוי
            cleanup_file(cookies_file)
            if temp_dir and os.path.exists(temp_dir):
                try:
                    for f in os.listdir(temp_dir):
                        try:
                            os.remove(os.path.join(temp_dir, f))
                        except:
                            pass
                    os.rmdir(temp_dir)
                except:
                    pass
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logging.error(f"שגיאת yt-dlp: {error_msg}")
        return jsonify({
            'success': False,
            'error': error_msg,
            'error_type': 'yt_dlp_error'
        }), 500
        
    except Exception as e:
        logging.error(f"שגיאה כללית: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'general_error'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
