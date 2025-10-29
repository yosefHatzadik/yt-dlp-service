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
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if 'url' in info:
                download_url = info['url']
            elif 'formats' in info:
                formats = [f for f in info['formats'] if f.get('url')]
                if formats:
                    download_url = formats[-1]['url']
                else:
                    return jsonify({'error': 'לא נמצא קישור הורדה'}), 400
            else:
                return jsonify({'error': 'לא ניתן לחלץ קישור'}), 400
            
            return jsonify({
                'title': info.get('title', 'לא ידוע'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'download_url': download_url,
                'uploader': info.get('uploader', 'לא ידוע')
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
