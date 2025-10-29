from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>yt-dlp Download Service</h1>
    <p>שימוש: הוסף ?url=קישור_יוטיוב לסוף הכתובת</p>
    <form action="/download" method="get">
        <input type="text" name="url" placeholder="https://www.youtube.com/watch?v=..." style="width: 400px; padding: 8px;">
        <button type="submit" style="padding: 8px 16px;">קבל קישור הורדה</button>
    </form>
    '''

@app.route('/download')
def download():
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({'error': 'לא סופק קישור'}), 400
    
    try:
        # הגדרות אגרסיביות לעקיפת חסימות
        ydl_opts = {
            'format': 'best[ext=mp4][height<=720]/best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'geo_bypass': True,
            'nocheckcertificate': True,
            # פרמטרים נוספים לעקיפת זיהוי בוט
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['configs', 'webpage'],
                    'skip': ['hls', 'dash']
                }
            },
            # cookies ו-headers מותאמים
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            download_url = None
            
            # חיפוש URL
            if info.get('url'):
                download_url = info['url']
            elif info.get('formats'):
                # מעדיף mp4 עד 720p
                for fmt in reversed(info['formats']):
                    if (fmt.get('url') and 
                        fmt.get('ext') == 'mp4' and 
                        fmt.get('vcodec') != 'none' and
                        fmt.get('acodec') != 'none'):
                        if not fmt.get('height') or fmt.get('height') <= 720:
                            download_url = fmt['url']
                            break
                
                # אם לא מצאנו, ניקח כל mp4
                if not download_url:
                    for fmt in reversed(info['formats']):
                        if fmt.get('url') and fmt.get('ext') == 'mp4':
                            download_url = fmt['url']
                            break
                
                # אחרון - כל פורמט עם URL
                if not download_url:
                    for fmt in reversed(info['formats']):
                        if fmt.get('url'):
                            download_url = fmt['url']
                            break
            
            if not download_url:
                return jsonify({
                    'error': 'לא נמצא קישור הורדה',
                    'help': 'הסרטון עשוי להיות פרטי או מוגבל גיאוגרפית'
                }), 404
            
            return jsonify({
                'success': True,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'download_url': download_url,
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'filesize': info.get('filesize') or info.get('filesize_approx', 0)
            })
    
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'error': 'שגיאה בעיבוד הסרטון',
            'details': error_msg,
            'video_url': video_url
        }), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
