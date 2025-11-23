from flask import Flask, request, jsonify
import yt_dlp
import tempfile
import os

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def run():
    try:
        # קבלת הקוד להרצה
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form.to_dict()
        else:
            data = request.args.to_dict()
        
        code = data.get('run') or data.get('RUN')
        
        if not code:
            return jsonify({'error': 'Missing run parameter'}), 400
        
        # הרצת הקוד
        result = eval(code)
        
        # החזרת התוצאה כמו שהיא
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
