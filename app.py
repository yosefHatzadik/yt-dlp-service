from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import time

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>YouTube Downloader</h1>
    <p>Use: /download?url=YOUTUBE_URL</p>
    '''

@app.route('/download')
def download():
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, '%(title)s.%(ext)s')
    
    try:
        # הגדרות אגרסיביות
        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            # עוקף חסימות
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                    'skip': ['hls', 'dash']
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12)',
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            
            # מחפש את הקובץ שהורד
            filename = ydl.prepare_filename(info)
            
            if not os.path.exists(filename):
                return jsonify({'error': 'File not downloaded'}), 500
            
            # שולח את הקובץ ישירות
            return send_file(
                filename,
                as_attachment=True,
                download_name=os.path.basename(filename),
                mimetype='video/mp4'
            )
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Try a different video or try again later'
        }), 500

@app.route('/info')
def info():
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({'error': 'No URL'}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            return jsonify({
                'title': info.get('title'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'thumbnail': info.get('thumbnail')
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
