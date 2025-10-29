from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import shutil

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>YouTube Downloader Pro v2</h1>
    <p>Use: /download?url=YOUTUBE_URL</p>
    <p>Supports: Age-restricted, Private (with cookies)</p>
    '''

def try_download_with_strategy(video_url, output_path, strategy_name, ydl_opts):
    """מנסה להוריד עם אסטרטגיה ספציפית"""
    print(f"[{strategy_name}] Trying...")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"[{strategy_name}] SUCCESS! Size: {os.path.getsize(filename)} bytes")
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
    
    # אסטרטגיה 1: Android Embedded Player (עוקף age restrictions)
    strategy1_opts = {
        'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'age_limit': None,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_embedded', 'android'],
                'skip': ['hls', 'dash']
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12)',
        },
    }
    
    downloaded_file, video_info = try_download_with_strategy(
        video_url, output_path, "Strategy 1: Android Embedded", strategy1_opts
    )
    
    # אסטרטגיה 2: Android Music Player
    if not downloaded_file:
        strategy2_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'age_limit': None,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_music', 'android'],
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.android.apps.youtube.music/5.16.51 (Linux; U; Android 12)',
            },
        }
        
        downloaded_file, video_info = try_download_with_strategy(
            video_url, output_path, "Strategy 2: Android Music", strategy2_opts
        )
    
    # אסטרטגיה 3: iOS עם bypass מלא
    if not downloaded_file:
        strategy3_opts = {
            'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'age_limit': None,
            'geo_bypass': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android'],
                    'skip': ['dash', 'hls']
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.ios.youtube/17.36.4 (iPhone; CPU iPhone OS 15_0 like Mac OS X)',
                'X-YouTube-Client-Name': '5',
                'X-YouTube-Client-Version': '17.36.4'
            },
        }
        
        downloaded_file, video_info = try_download_with_strategy(
            video_url, output_path, "Strategy 3: iOS", strategy3_opts
        )
    
    # אסטרטגיה 4: Web עם headers מורחבים
    if not downloaded_file:
        strategy4_opts = {
            'format': 'best[height<=720]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'age_limit': None,
            'geo_bypass': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Origin': 'https://www.youtube.com',
                'Referer': 'https://www.youtube.com/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            },
        }
        
        downloaded_file, video_info = try_download_with_strategy(
            video_url, output_path, "Strategy 4: Web Extended", strategy4_opts
        )
    
    # אסטרטגיה 5: TV client
    if not downloaded_file:
        strategy5_opts = {
            'format': 'best[height<=720]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv_embedded', 'tv'],
                }
            },
        }
        
        downloaded_file, video_info = try_download_with_strategy(
            video_url, output_path, "Strategy 5: TV", strategy5_opts
        )
    
    # אסטרטגיה 6: Basic fallback
    if not downloaded_file:
        strategy6_opts = {
            'format': 'worst[ext=mp4]/worst',  # נסה איכות נמוכה
            'outtmpl': output_path,
            'quiet': False,
            'verbose': True,
            'age_limit': None,
        }
        
        downloaded_file, video_info = try_download_with_strategy(
            video_url, output_path, "Strategy 6: Low Quality", strategy6_opts
        )
    
    # ניקוי ושליחה
    try:
        if downloaded_file and os.path.exists(downloaded_file):
            print(f"SUCCESS! Sending file: {downloaded_file}")
            
            response = send_file(
                downloaded_file,
                as_attachment=True,
                download_name=os.path.basename(downloaded_file),
                mimetype='video/mp4'
            )
            
            @response.call_on_close
            def cleanup():
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            
            return response
        else:
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
                
            return jsonify({
                'error': 'Unable to download video after 6 strategies',
                'message': 'The video might be: 1) Private/Unlisted, 2) Requires sign-in, 3) Region-locked, 4) Age-restricted beyond bypass, 5) Live stream',
                'url': video_url,
                'suggestion': 'Try opening the video in your browser first to check if it plays normally'
            }), 500
            
    except Exception as e:
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
    """מחזיר מידע על סרטון"""
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({'error': 'No URL'}), 400
    
    strategies = [
        {'name': 'android_embedded', 'client': ['android_embedded']},
        {'name': 'android', 'client': ['android']},
        {'name': 'ios', 'client': ['ios']},
        {'name': 'web', 'client': ['web']},
    ]
    
    for strategy in strategies:
        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'age_limit': None,
                'extractor_args': {
                    'youtube': {
                        'player_client': strategy['client'],
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
                    'view_count': info.get('view_count'),
                    'strategy_used': strategy['name']
                })
        except:
            continue
    
    return jsonify({
        'success': False,
        'error': 'Could not get video info'
    }), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'strategies': 6})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
