from flask import Flask, request, jsonify, render_template
import numpy as np
from pgv_rom import PGVReducedOrderModel

app = Flask(__name__)

# 加载模型
MODEL_PATH = "loh_rom.joblib"
model = None

def load_model():
    global model
    try:
        model = PGVReducedOrderModel.load(MODEL_PATH)
        print(f"Model loaded from {MODEL_PATH}")
        print(f"Parameter ranges: {model.parameter_ranges}")
    except Exception as e:
        print(f"Failed to load model: {e}")

@app.route('/')
def index():
    return render_template('index.html',
                         ranges=model.parameter_ranges if model else None)

@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500

    data = request.json
    depth = float(data.get('depth', 10))
    strike = float(data.get('strike', 120))
    dip = float(data.get('dip', 60))
    rake = float(data.get('rake', 90))

    params = np.array([depth, strike, dip, rake], dtype=float)
    predicted_grid = model.predict_grid(params)

    # 转换为cm/s
    grid_cmps = 100.0 * predicted_grid.T

    # 返回原始数据而非图像
    return jsonify({
        'data': grid_cmps.tolist(),
        'stats': {
            'min': float(grid_cmps.min()),
            'max': float(grid_cmps.max()),
            'mean': float(grid_cmps.mean())
        },
        'params': {
            'depth': depth,
            'strike': strike,
            'dip': dip,
            'rake': rake
        }
    })

if __name__ == '__main__':
    load_model()
    app.run(debug=True, host='0.0.0.0', port=5001)
