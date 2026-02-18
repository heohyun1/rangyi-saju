# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip()

load_env()

from saju_engine import analyze_saju
from ai_interpreter import get_ai_interpretation, get_category_interpretation

app = Flask(__name__, static_folder='static')
CORS(app, origins=['*'])  # 티스토리에서 호출 허용

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/saju', methods=['POST'])
def get_saju():
    try:
        data = request.get_json()
        result = analyze_saju(
            int(data['year']), int(data['month']), int(data['day']),
            int(data['hour']), data['gender'], data.get('is_lunar', False)
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/saju/full', methods=['POST'])
def get_saju_full():
    try:
        data = request.get_json()
        saju_result = analyze_saju(
            int(data['year']), int(data['month']), int(data['day']),
            int(data['hour']), data['gender'], data.get('is_lunar', False)
        )
        ai_res = get_ai_interpretation(saju_result)
        saju_result['ai_interpretation'] = {
            'available': ai_res['success'],
            'text': ai_res.get('interpretation', '') or '',
            'message': ai_res.get('error', '') or ''
        }
        if ai_res['success']:
            print(f"[OK] AI {len(ai_res.get('interpretation',''))}자")
        else:
            print(f"[FAIL] AI: {ai_res.get('error','')}")
        return jsonify(saju_result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/saju/detail', methods=['POST'])
def get_saju_detail():
    try:
        data = request.get_json()
        saju_result = analyze_saju(
            int(data['year']), int(data['month']), int(data['day']),
            int(data['hour']), data['gender'], data.get('is_lunar', False)
        )
        ai_res = get_category_interpretation(saju_result, data.get('category', 'love'))
        return jsonify({
            'category': data.get('category', 'love'),
            'available': ai_res['success'],
            'interpretation': ai_res.get('interpretation', '') or '',
            'message': ai_res.get('error', '') or ''
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    key = os.environ.get('GEMINI_API_KEY', '')
    return jsonify({'status': 'ok', 'ai_enabled': bool(key)})

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
