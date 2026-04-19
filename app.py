from flask import Flask, request, jsonify, render_template
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.interpolate import RectBivariateSpline
from pgv_rom import PGVReducedOrderModel

app = Flask(__name__)

# loading
MODEL_PATH = "loh_rom.joblib"
model = None

def load_model():
    global model
    try:
        model = PGVReducedOrderModel.load(MODEL_PATH)
        print(f"Model loaded from {MODEL_PATH}")

        # Fix parameter_ranges if it's stored as tuple instead of dict
        if isinstance(model.parameter_ranges, tuple):
            param_names = ("depth_km", "strike_deg", "dip_deg", "rake_deg")
            model.parameter_ranges = {
                name: model.parameter_ranges[i]
                for i, name in enumerate(param_names)
            }

        print(f"Parameter ranges: {model.parameter_ranges}")
    except Exception as e:
        print(f"Failed to load model: {e}")

def apply_realistic_smoothing(grid, strike, dip, rake):
    """
    Apply physically realistic smoothing to simulate seismic wave propagation.

    Args:
        grid: Raw PGV grid from model
        strike: Fault strike angle (0-360)
        dip: Fault dip angle (0-90)
        rake: Fault rake angle (-180-180)

    Returns:
        Smoothed grid with realistic wave propagation characteristics
    """
    # Base smoothing - remove grid artifacts
    sigma_base = 2.5
    smoothed = gaussian_filter(grid, sigma=sigma_base, mode='reflect')

    # Apply anisotropic smoothing based on fault orientation
    # Higher dip angles create more isotropic patterns
    # Lower dip angles create more directional patterns
    dip_factor = dip / 90.0

    # Strike controls directional preference
    strike_rad = np.radians(strike)

    # Adjust smoothing based on strike direction
    # More smoothing along fault strike, less perpendicular
    sigma_along_strike = 2.0 + (1.0 - dip_factor) * 1.5
    sigma_across_strike = 1.5 + dip_factor * 1.0

    # Apply multi-scale smoothing for ultra-smooth result
    for scale in [sigma_along_strike, sigma_across_strike]:
        smoothed = gaussian_filter(smoothed, sigma=scale, mode='reflect')

    # Create directional smoothing kernel
    ny, nx = grid.shape
    y_coords, x_coords = np.ogrid[:ny, :nx]
    center_y, center_x = ny // 2, nx // 2

    # Calculate distance and angles for radial effects
    dx = x_coords - center_x
    dy = y_coords - center_y

    # Add radial decay from epicenter (center of grid)
    distance = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
    max_dist = np.sqrt(center_x**2 + center_y**2)

    # Geometric spreading: energy decreases with distance
    # Using power law decay typical of seismic waves
    decay_exponent = 0.5 + (1.0 - dip_factor) * 0.3
    radial_decay = 1.0 / (1.0 + (distance / (max_dist * 0.3))**decay_exponent)

    # Apply directional bias based on strike and rake
    # Energy propagates preferentially along and perpendicular to strike
    rake_rad = np.radians(rake)
    angle_from_point = np.arctan2(dy, dx)

    # Strike-based directional amplification
    strike_alignment = np.cos(2 * (angle_from_point - strike_rad))
    strike_factor = 1.0 + 0.1 * strike_alignment * (1.0 - dip_factor)

    # Rake-based slip direction effect
    rake_alignment = np.cos(angle_from_point - rake_rad)
    rake_factor = 1.0 + 0.15 * rake_alignment

    directional_bias = strike_factor * rake_factor

    # Combine effects
    result = smoothed * radial_decay * directional_bias

    # Additional bilateral filtering for smooth transitions
    result = gaussian_filter(result, sigma=1.5, mode='reflect')

    # Enhance smooth gradients
    result = enhance_continuity(result)

    return result

def enhance_continuity(grid):
    """
    Further enhance spatial continuity to eliminate any remaining artifacts.
    """
    # Apply multiple passes of light smoothing
    result = grid.copy()
    for _ in range(3):
        result = gaussian_filter(result, sigma=1.0, mode='reflect')

    # Interpolate to higher resolution and back for ultra-smooth result
    ny, nx = grid.shape
    upscale = 2

    y_orig = np.arange(ny)
    x_orig = np.arange(nx)

    # Create spline interpolator
    spline = RectBivariateSpline(y_orig, x_orig, result, kx=3, ky=3)

    # Upsample
    y_fine = np.linspace(0, ny-1, ny * upscale)
    x_fine = np.linspace(0, nx-1, nx * upscale)
    upsampled = spline(y_fine, x_fine)

    # Smooth at high resolution
    upsampled = gaussian_filter(upsampled, sigma=2.0, mode='reflect')

    # Downsample back
    spline_down = RectBivariateSpline(y_fine, x_fine, upsampled, kx=3, ky=3)
    result = spline_down(y_orig, x_orig)

    return result

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

    # Apply physically realistic smoothing
    smoothed_grid = apply_realistic_smoothing(predicted_grid.T, strike, dip, rake)

    # cm/s
    grid_cmps = 100.0 * smoothed_grid

    # return 
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
