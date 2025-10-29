from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import shutil

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>YouTube Downloader Pro</h1>
    <p>Use: /download?url=YOUTUBE_URL</p>
    <p>Status: Online</p>
    '''

def try_download_with_strategy(video_url, output_path, strategy_name, ydl_opts):
    """מנסה להוריד עם אסטרטגיה ספציפית"""
    print(f"[{strategy_name}] Trying...")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"[{strategy_name}] SUCCESS!")
                return filename, info
            else:
                print(f"[{strategy_name}] File not found or empty")
                return None, None
                
    except Exception as e:
        print(f"[{strategy_name}] Failed: {str(e)}")
        return None, None

@app.route('/download')
def download():
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, '%(title)s.%(ext)s')
    
    downloaded_file = None
    video_info = None
    
    # אסטרטגיה 1: Android client (הכי יציב)
    strategy1_opts = {
        'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
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
    
    downloaded_file, video_info = try_download_with_strategy(
        video_url, output_path, "Strategy 1: Android", strategy1_opts
    )
    
    # אסטרטגיה 2: iOS client
    if not downloaded_file:
        strategy2_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios'],
                    'skip': ['hls', 'dash']
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.ios.youtube/17.36.4 (iPhone; U; CPU iPhone OS 15_0 like Mac OS X)',
            },
        }
        
        downloaded_file, video_info = try_download_with_strategy(
            video_url, output_path, "Strategy 2: iOS", strategy2_opts
        )
    
    # אסטרטגיה 3: Web client עם bypass
    if not downloaded_file:
        strategy3_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'android'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }
        
        downloaded_file, video_info = try_download_with_strategy(
            video_url, output_path, "Strategy 3: Web+Android", strategy3_opts
        )
    
    # אסטרטגיה 4: TV client (אחרון)
    if not downloaded_file:
        strategy4_opts = {
            'format': 'best[height<=720]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv'],
                }
            },
        }
        
        downloaded_file, video_info = try_download_with_strategy(
            video_url, output_path, "Strategy 4: TV", strategy4_opts
        )
    
    # אסטרטגיה 5: ללא הגבלות (ניסיון אחרון)
    if not downloaded_file:
        strategy5_opts = {
            'format': 'best',
            'outtmpl': output_path,
            'quiet': True,
        }
        
        downloaded_file, video_info = try_download_with_strategy(
            video_url, output_path, "Strategy 5: Basic", strategy5_opts
        )
    
    # ניקוי ושליחה
    try:
        if downloaded_file and os.path.exists(downloaded_file):
            response = send_file(
                downloaded_file,
                as_attachment=True,
                download_name=os.path.basename(downloaded_file),
                mimetype='video/mp4'
            )
            
            # ניקוי אחרי שליחה
            @response.call_on_close
            def cleanup():
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            
            return response
        else:
            # ניקוי במקרה של כשלון
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
                
            return jsonify({
                'error': 'Unable to download video',
                'message': 'All strategies failed. The video might be private, region-locked, or require sign-in.',
                'url': video_url
            }), 500
            
    except Exception as e:
        # ניקוי במקרה של שגיאה
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
            
        return jsonify({
            'error': 'Download failed',
            'details': str(e)
        }), 500

@app.route('/info')
def info():
    """מחזיר מידע על סרטון בלי להוריד"""
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
                'success': True,
                'title': info.get('title'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'thumbnail': info.get('thumbnail'),
                'view_count': info.get('view_count')
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'yt-dlp-downloader'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
