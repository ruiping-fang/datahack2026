import argparse
import math
import time
from dataclasses import dataclass
from pathlib import Path

import h5py
import joblib
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import RBFInterpolator
from sklearn.model_selection import train_test_split


PARAMETER_NAMES = ("depth_km", "strike_deg", "dip_deg", "rake_deg")


@dataclass
class EvaluationResult:
    mae_mps: float
    rmse_mps: float
    max_abs_mps: float
    mae_cmps: float
    rmse_cmps: float
    max_abs_cmps: float
    mean_inference_ms: float


class PGVReducedOrderModel:
    def __init__(
        self,
        energy_threshold: float = 0.995,
        smoothing: float = 0.0,
        kernel: str = "thin_plate_spline",
        epsilon: float | None = None,
    ) -> None:
        self.energy_threshold = energy_threshold
        self.smoothing = smoothing
        self.kernel = kernel
        self.epsilon = epsilon
        self.grid_shape: tuple[int, int] | None = None
        self.basis: np.ndarray | None = None
        self.interpolator: RBFInterpolator | None = None
        self.relative_information_content: np.ndarray | None = None
        self.n_modes: int | None = None
        self.parameter_ranges: dict[str, tuple[float, float]] | None = None

    def fit(self, params: np.ndarray, maps: np.ndarray, grid_shape: tuple[int, int]) -> "PGVReducedOrderModel":
        u, singular_values, _ = np.linalg.svd(maps.T, full_matrices=False)
        ric = np.cumsum(singular_values ** 2) / np.sum(singular_values ** 2)
        n_modes = int(np.searchsorted(ric, self.energy_threshold) + 1)

        basis = u[:, :n_modes]
        coefficients = maps @ basis
        interpolator = RBFInterpolator(
            params,
            coefficients,
            smoothing=self.smoothing,
            kernel=self.kernel,
            epsilon=self.epsilon,
        )

        self.grid_shape = grid_shape
        self.basis = basis
        self.interpolator = interpolator
        self.relative_information_content = ric
        self.n_modes = n_modes
        self.parameter_ranges = {
            name: (float(np.min(params[:, i])), float(np.max(params[:, i])))
            for i, name in enumerate(PARAMETER_NAMES)
        }
        return self

    def predict(self, params: np.ndarray) -> np.ndarray:
        if self.interpolator is None or self.basis is None:
            raise RuntimeError("Model is not fitted.")
        coeffs = self.interpolator(np.atleast_2d(params))
        return coeffs @ self.basis.T

    def predict_grid(self, params: np.ndarray) -> np.ndarray:
        if self.grid_shape is None:
            raise RuntimeError("Model is not fitted.")
        flat = self.predict(params)[0]
        return flat.reshape(self.grid_shape)

    def save(self, path: str | Path) -> None:
        joblib.dump(self, path)

    @staticmethod
    def load(path: str | Path) -> "PGVReducedOrderModel":
        return joblib.load(path)


def load_dataset(dataset_path: str | Path) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    with h5py.File(dataset_path, "r") as handle:
        params = handle["params"][:]
        maps = handle["data"][:]

    n_points = maps.shape[1]
    side = int(math.isqrt(n_points))
    if side * side != n_points:
        raise ValueError(f"Expected square output grid, got {n_points} points.")

    return params, maps, (side, side)


def evaluate(model: PGVReducedOrderModel, x_test: np.ndarray, y_test: np.ndarray) -> EvaluationResult:
    started = time.perf_counter()
    predictions = model.predict(x_test)
    elapsed = time.perf_counter() - started

    errors = y_test - predictions
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    max_abs = float(np.max(np.abs(errors)))
    mean_ms = 1000.0 * elapsed / len(x_test)

    return EvaluationResult(
        mae_mps=mae,
        rmse_mps=rmse,
        max_abs_mps=max_abs,
        mae_cmps=100.0 * mae,
        rmse_cmps=100.0 * rmse,
        max_abs_cmps=100.0 * max_abs,
        mean_inference_ms=mean_ms,
    )


def format_ranges(ranges: dict[str, tuple[float, float]]) -> str:
    lines = []
    for name, (low, high) in ranges.items():
        lines.append(f"  {name}: {low:.3f} to {high:.3f}")
    return "\n".join(lines)


def train_command(args: argparse.Namespace) -> int:
    params, maps, grid_shape = load_dataset(args.dataset)

    if args.max_samples is not None:
        params = params[: args.max_samples]
        maps = maps[: args.max_samples]

    x_train, x_test, y_train, y_test = train_test_split(
        params,
        maps,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    model = PGVReducedOrderModel(
        energy_threshold=args.energy_threshold,
        smoothing=args.smoothing,
        kernel=args.kernel,
        epsilon=args.epsilon,
    ).fit(x_train, y_train, grid_shape)

    metrics = evaluate(model, x_test, y_test)
    model.save(args.model_out)

    print(f"Dataset: {args.dataset}")
    print(f"Training maps: {len(x_train)}")
    print(f"Testing maps: {len(x_test)}")
    print(f"Grid shape: {grid_shape[0]} x {grid_shape[1]}")
    print(f"Retained POD modes: {model.n_modes}")
    print(f"Energy threshold: {args.energy_threshold}")
    print("Parameter ranges:")
    print(format_ranges(model.parameter_ranges or {}))
    print(f"MAE: {metrics.mae_mps:.6f} m/s ({metrics.mae_cmps:.3f} cm/s)")
    print(f"RMSE: {metrics.rmse_mps:.6f} m/s ({metrics.rmse_cmps:.3f} cm/s)")
    print(f"Max abs error: {metrics.max_abs_mps:.6f} m/s ({metrics.max_abs_cmps:.3f} cm/s)")
    print(f"Mean inference time: {metrics.mean_inference_ms:.4f} ms/map")
    print(f"Saved model: {args.model_out}")
    return 0


def predict_command(args: argparse.Namespace) -> int:
    model = PGVReducedOrderModel.load(args.model)
    params = np.array([args.depth, args.strike, args.dip, args.rake], dtype=float)
    predicted_grid = model.predict_grid(params)

    np.save(args.output, predicted_grid)
    print(f"Saved grid to {args.output}")
    print(f"Grid shape: {predicted_grid.shape[0]} x {predicted_grid.shape[1]}")
    print(f"PGV min/max: {predicted_grid.min():.6f} / {predicted_grid.max():.6f} m/s")

    if args.png:
        fig, ax = plt.subplots(figsize=(6, 5))
        image = ax.imshow(100.0 * predicted_grid.T, origin="lower", cmap="inferno")
        ax.set_title("Predicted PGV")
        ax.set_xlabel("Grid X")
        ax.set_ylabel("Grid Y")
        fig.colorbar(image, ax=ax, label="PGV (cm/s)")
        fig.tight_layout()
        fig.savefig(args.png, dpi=150)
        plt.close(fig)
        print(f"Saved preview image to {args.png}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train and use a reduced-order PGV map model.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="Train a reduced-order model from an HDF5 dataset.")
    train_parser.add_argument("--dataset", required=True, help="Path to the Zenodo HDF5 dataset.")
    train_parser.add_argument("--model-out", required=True, help="Path to save the trained model artifact.")
    train_parser.add_argument("--energy-threshold", type=float, default=0.995)
    train_parser.add_argument("--smoothing", type=float, default=0.0)
    train_parser.add_argument("--kernel", default="thin_plate_spline")
    train_parser.add_argument("--epsilon", type=float, default=None)
    train_parser.add_argument("--test-size", type=float, default=0.1)
    train_parser.add_argument("--random-state", type=int, default=0)
    train_parser.add_argument("--max-samples", type=int, default=None)
    train_parser.set_defaults(func=train_command)

    predict_parser = subparsers.add_parser("predict", help="Predict one PGV map from earthquake parameters.")
    predict_parser.add_argument("--model", required=True, help="Path to a trained model artifact.")
    predict_parser.add_argument("--depth", type=float, required=True, help="Hypocentral depth in km.")
    predict_parser.add_argument("--strike", type=float, required=True, help="Strike in degrees.")
    predict_parser.add_argument("--dip", type=float, required=True, help="Dip in degrees.")
    predict_parser.add_argument("--rake", type=float, required=True, help="Rake in degrees.")
    predict_parser.add_argument("--output", default="predicted_pgv.npy", help="Output .npy path.")
    predict_parser.add_argument("--png", default=None, help="Optional output image path.")
    predict_parser.set_defaults(func=predict_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
