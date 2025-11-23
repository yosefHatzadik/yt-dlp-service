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
        <h1>🎥 שירות הורדת YouTube</h1>
        <p>השתמש ב-API:</p>
        <code>GET /download?url=[youtube-url]&cookies=[cookies-string]</code>
        <br><br>
        <p><strong>cookies</strong> הוא פרמטר אופציונלי במבנה Netscape</p>
    </body>
    </html>
    '''

@app.route('/download')
def download_video():
    try:
        youtube_url = request.args.get('url')
        cookies_data = request.args.get('cookies', '')
        
        if not youtube_url:
            return jsonify({'error': 'חסר פרמטר url'}), 400
        
        logging.info(f"מעבד: {youtube_url}")
        logging.info(f"יש עוגיות: {'כן' if cookies_data else 'לא'}")
        
        # יצירת תיקיה זמנית
        temp_dir = tempfile.mkdtemp()
        cookies_file = None
        
        try:
            # אם יש עוגיות, שמור אותן בקובץ
            if cookies_data:
                cookies_file = os.path.join(temp_dir, 'cookies.txt')
                with open(cookies_file, 'w', encoding='utf-8') as f:
                    # אם העוגיות לא מתחילות בהדר Netscape, נוסיף אותו
                    if not cookies_data.strip().startswith('# Netscape HTTP Cookie File'):
                        f.write('# Netscape HTTP Cookie File\n')
                        f.write('# This is a generated file! Do not edit.\n\n')
                    f.write(cookies_data)
                logging.info(f"קובץ עוגיות נוצר: {cookies_file}")
            
            # הגדרות yt-dlp
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
            }
            
            # הוספת עוגיות אם קיימות
            if cookies_file and os.path.exists(cookies_file):
                ydl_opts['cookiefile'] = cookies_file
                logging.info("משתמש בעוגיות")
            
            # הורדת הסרטון
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                filename = ydl.prepare_filename(info)
            
            if not os.path.exists(filename):
                return jsonify({'error': 'הקובץ לא נוצר'}), 500
            
            logging.info(f"הורדה הושלמה: {filename}")
            
            # שליחת הקובץ
            return send_file(
                filename,
                as_attachment=True,
                download_name=os.path.basename(filename),
                mimetype='video/mp4'
            )
            
        finally:
            # ניקוי קבצים זמניים (יתבצע אחרי השליחה)
            try:
                if cookies_file and os.path.exists(cookies_file):
                    os.remove(cookies_file)
                for f in os.listdir(temp_dir):
                    try:
                        os.remove(os.path.join(temp_dir, f))
                    except:
                        pass
                os.rmdir(temp_dir)
            except Exception as e:
                logging.warning(f"שגיאה בניקוי: {e}")
    
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"שגיאת הורדה: {str(e)}")
        return jsonify({'error': f'שגיאת הורדה: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"שגיאה כללית: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
