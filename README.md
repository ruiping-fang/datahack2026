# Instant PGV Map Predictor

This project is a reduced-order model that predicts a full peak ground velocity (PGV) map from earthquake source parameters in milliseconds once trained.

The dataset used is publicly available [here](https://zenodo.org/records/8170242).

The interactable website with the model is available at https://datahack2026.fangruiping.com/.

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

## Predict

```bash
python pgv_rom.py predict --model loh_rom.joblib --depth 10 --strike 120 --dip 60 --rake 90 --png predicted_pgv.png
```

This writes:

- a `60 x 60` NumPy grid as `.npy`
- an optional heatmap `predicted_pgv.png`
