# ebilab

Utility python library for lab experiment (for me)

- `ebilab.experiment` : utility to control Experimental instruments
- `ebilab.analysis` : utility for analyzing data

## Installation

### Normal install (Recommended)

Please execute the command below in this directory.

```
pip install ebilab
```

### Development install

clone this repository and run 

```
pip install -e .
```

## (For experiment) Driver setup

This repository requires VISA driver.
Please install Keysight-VISA or NI-VISA.


# translation

Translation is conducted under transifex: https://www.transifex.com/ebilab/ebilab/


(To maintainer)

```bash
cd doc
make tx-push
# translate
make tx-pull
```

