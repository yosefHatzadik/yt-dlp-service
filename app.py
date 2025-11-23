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
        <h1>🎥 שירות YouTube מלא</h1>
        
        <h3>1️⃣ קבלת רשימת פורמטים:</h3>
        <code>POST /formats</code>
        <pre>{"url": "...", "cookies": "..."}</pre>
        
        <h3>2️⃣ קבלת קישור הורדה ישיר:</h3>
        <code>POST /get-download-url</code>
        <pre>{"url": "...", "cookies": "...", "format": "best"}</pre>
        
        <h3>3️⃣ הורדה דרך השרת (לאיטיות):</h3>
        <code>POST /download</code>
        <pre>{"url": "...", "cookies": "...", "format": "best"}</pre>
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
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
    except Exception as e:
        logging.warning(f"שגיאה בניקוי: {e}")

def handle_yt_dlp_error(e):
    """מטפל בשגיאות yt-dlp ומחזיר תגובה מתאימה"""
    error_msg = str(e)
    logging.error(f"שגיאת yt-dlp: {error_msg}")
    
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
    elif 'Video unavailable' in error_msg:
        return jsonify({
            'success': False,
            'error': 'הסרטון לא זמין',
            'error_type': 'unavailable'
        }), 404
    else:
        return jsonify({
            'success': False,
            'error': f'שגיאה: {error_msg}',
            'error_type': 'download_error'
        }), 500


@app.route('/formats', methods=['POST', 'GET'])
def get_formats():
    """מחזיר רשימת כל הפורמטים הזמינים"""
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            youtube_url = data.get('url') or request.args.get('url')
            cookies_data = data.get('cookies', '')
        else:
            youtube_url = request.args.get('url')
            cookies_data = request.args.get('cookies', '')
        
        if not youtube_url:
            return jsonify({'success': False, 'error': 'חסר פרמטר url'}), 400
        
        logging.info(f"מבקש פורמטים: {youtube_url}")
        
        cookies_file = get_cookies_file(cookies_data)
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            
            if cookies_file:
                ydl_opts['cookiefile'] = cookies_file
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
            
            formats = []
            for f in info.get('formats', []):
                formats.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'resolution': f.get('resolution') or f'{f.get("width")}x{f.get("height")}' if f.get('width') else 'audio only',
                    'filesize': f.get('filesize'),
                    'filesize_mb': round(f.get('filesize') / 1024 / 1024, 2) if f.get('filesize') else None,
                    'vcodec': f.get('vcodec'),
                    'acodec': f.get('acodec'),
                    'fps': f.get('fps'),
                    'format_note': f.get('format_note'),
                    'quality': f.get('quality')
                })
            
            return jsonify({
                'success': True,
                'title': info.get('title'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'formats': formats,
                'best_video': info.get('format_id')
            })
            
        finally:
            cleanup_file(cookies_file)
    
    except yt_dlp.utils.DownloadError as e:
        return handle_yt_dlp_error(e)
    except Exception as e:
        logging.error(f"שגיאה: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/get-download-url', methods=['POST', 'GET'])
def get_download_url():
    """מחזיר קישור הורדה ישיר (מומלץ!)"""
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            youtube_url = data.get('url') or request.args.get('url')
            cookies_data = data.get('cookies', '')
            format_id = data.get('format', 'best[ext=mp4]/best')
        else:
            youtube_url = request.args.get('url')
            cookies_data = request.args.get('cookies', '')
            format_id = request.args.get('format', 'best[ext=mp4]/best')
        
        if not youtube_url:
            return jsonify({'success': False, 'error': 'חסר פרמטר url'}), 400
        
        logging.info(f"מחלץ קישור: {youtube_url} | פורמט: {format_id}")
        
        cookies_file = get_cookies_file(cookies_data)
        
        try:
            ydl_opts = {
                'format': format_id,
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            
            if cookies_file:
                ydl_opts['cookiefile'] = cookies_file
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
            
            download_url = info.get('url')
            
            if not download_url:
                return jsonify({
                    'success': False, 
                    'error': 'לא נמצא קישור הורדה'
                }), 500
            
            logging.info(f"✅ קישור נמצא")
            
            return jsonify({
                'success': True,
                'download_url': download_url,
                'title': info.get('title'),
                'ext': info.get('ext', 'mp4'),
                'filesize': info.get('filesize') or info.get('filesize_approx'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'format_id': info.get('format_id'),
                'resolution': info.get('resolution')
            })
            
        finally:
            cleanup_file(cookies_file)
    
    except yt_dlp.utils.DownloadError as e:
        return handle_yt_dlp_error(e)
    except Exception as e:
        logging.error(f"שגיאה: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download', methods=['POST', 'GET'])
def download_video():
    """מוריד דרך השרת ושולח לקליינט (לא מומלץ לקבצים גדולים)"""
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            youtube_url = data.get('url') or request.args.get('url')
            cookies_data = data.get('cookies', '')
            format_id = data.get('format', 'best[ext=mp4]/best')
        else:
            youtube_url = request.args.get('url')
            cookies_data = request.args.get('cookies', '')
            format_id = request.args.get('format', 'best[ext=mp4]/best')
        
        if not youtube_url:
            return jsonify({'error': 'חסר פרמטר url'}), 400
        
        logging.info(f"מוריד: {youtube_url}")
        
        temp_dir = tempfile.mkdtemp()
        cookies_file = get_cookies_file(cookies_data)
        
        try:
            ydl_opts = {
                'format': format_id,
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
            }
            
            if cookies_file:
                ydl_opts['cookiefile'] = cookies_file
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                filename = ydl.prepare_filename(info)
            
            if not os.path.exists(filename):
                return jsonify({'error': 'הקובץ לא נוצר'}), 500
            
            logging.info(f"✅ הורדה הושלמה: {filename}")
            
            return send_file(
                filename,
                as_attachment=True,
                download_name=os.path.basename(filename),
                mimetype='video/mp4'
            )
            
        finally:
            cleanup_file(cookies_file)
            # ניקוי תיקיית temp אחרי שליחה
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
        error_response, code = handle_yt_dlp_error(e)
        return error_response, code
    except Exception as e:
        logging.error(f"שגיאה: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
