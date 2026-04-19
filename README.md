# Instant PGV Map Predictor

This repo now includes a reduced-order model that predicts a full peak ground velocity (PGV) map from earthquake source parameters in milliseconds once trained.

The implementation follows the published Zenodo demo for record `8170242`:

1. Load simulated PGV maps from the HDF5 dataset.
2. Compute a POD/SVD basis over the maps.
3. Interpolate the modal coefficients from earthquake parameters using `scipy.interpolate.RBFInterpolator`.
4. Reconstruct the full PGV map instantly for new source parameters.

The current workflow is set up for the downloaded `loh.hdf5` dataset, whose inputs are:

- `depth_km`
- `strike_deg`
- `dip_deg`
- `rake_deg`

and whose output is a flattened `60 x 60` PGV map.

## Files

- `pgv_rom.py`: model class plus training and prediction CLIs
- `loh.hdf5`: downloaded Zenodo dataset bundle used below

## Install

```bash
python -m pip install numpy scipy scikit-learn matplotlib h5py joblib
```

## Train

This trains a ROM artifact and prints validation metrics.

```bash
python pgv_rom.py train --dataset loh.hdf5 --model-out loh_rom.joblib
```

Useful options:

- `--max-samples 2000` to limit training size for a faster demo
- `--energy-threshold 0.995` to keep enough POD modes to explain 99.5% of the variance
- `--test-size 0.1` for the holdout split

## Predict

```bash
python pgv_rom.py predict --model loh_rom.joblib --depth 10 --strike 120 --dip 60 --rake 90 --png predicted_pgv.png
```

This writes:

- a `60 x 60` NumPy grid as `.npy`
- an optional heatmap `.png`

## Notes

- Inference is fast because the expensive simulation is replaced by a precomputed basis plus an interpolator over modal coefficients.
- The script stores PGV internally in the same units as the Zenodo dataset. Plots are labeled in `cm/s`.
