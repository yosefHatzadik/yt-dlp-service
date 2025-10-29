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
        # הגדרות משופרות כדי לעקוף את זיהוי הבוטים של YouTube
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': False,
            # הוספת User-Agent כדי להתחזות לדפדפן רגיל
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # הוספת headers נוספים
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            # עוקף age restriction
            'age_limit': None,
            # משתמש ב-extractor מותאם
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_client': ['android', 'web'],
                }
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # חיפוש URL להורדה
            download_url = None
            
            # אופציה 1: URL ישיר
            if info.get('url'):
                download_url = info['url']
            
            # אופציה 2: חיפוש בפורמטים
            elif info.get('formats'):
                # מחפש פורמט עם URL וסיומת mp4
                for fmt in reversed(info['formats']):
                    if fmt.get('url') and fmt.get('ext') == 'mp4' and not fmt.get('acodec') == 'none':
                        download_url = fmt['url']
                        break
                
                # אם לא מצאנו mp4 מלא, ניקח כל פורמט עם URL
                if not download_url:
                    for fmt in reversed(info['formats']):
                        if fmt.get('url'):
                            download_url = fmt['url']
                            break
            
            # אופציה 3: requested_formats
            elif info.get('requested_formats'):
                for fmt in info['requested_formats']:
                    if fmt.get('url'):
                        download_url = fmt['url']
                        break
            
            if not download_url:
                return jsonify({
                    'error': 'לא נמצא קישור הורדה ישיר',
                    'info': 'הסרטון עשוי לדרוש עיבוד נוסף'
                }), 400
            
            return jsonify({
                'success': True,
                'title': info.get('title', 'לא ידוע'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'download_url': download_url,
                'uploader': info.get('uploader', 'לא ידוע'),
                'ext': info.get('ext', 'mp4'),
                'filesize': info.get('filesize') or info.get('filesize_approx', 0)
            })
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        # אם זו שגיאת בוט, תן הודעה ברורה יותר
        if 'Sign in to confirm' in error_msg or 'bot' in error_msg.lower():
            return jsonify({
                'error': 'YouTube חוסם את הבקשה',
                'details': 'נסה שוב בעוד מספר שניות, או השתמש בסרטון אחר',
                'technical': error_msg
            }), 429
        return jsonify({
            'error': 'שגיאת הורדה',
            'details': error_msg
        }), 500
    
    except Exception as e:
        return jsonify({
            'error': 'שגיאה כללית',
            'details': str(e),
            'type': type(e).__name__
        }), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'yt-dlp-downloader'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
