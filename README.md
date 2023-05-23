# Tesla Solar Data Downloader

## Introduction

This script will download your entire history of Tesla Solar power data: solar/battery/grid power
data in 5 minute intervals.  The script is using the [unofficial Tesla API](https://tesla-api.timdorr.com/)
and [TeslaPy](https://github.com/tdorssers/TeslaPy) library.  Data is stored in CSV files by day.

## Installation

1. If needed, install Python 3 and git.
2. Clone the repo:
    ```bash
    git clone https://github.com/zigam/tesla-solar-download.git
    cd tesla-solar-download
    ```

2. Install the package dependencies:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

## Usage
```bash
python ./tesla_solar_download.py --email <my_tesla_email@gmail.com>
```

Follow the instructions to log in to Tesla with your web browser (this is needed to generate an API
token, the credentials are only sent to Tesla).  Once you've logged in, the token will be stored
locally so you can rerun the script if needed.

Data will start downloading to the `download` directory.  Starting with today and going back in time
all the way to the Tesla system's installation date.

Downloads take ~3.5 seconds per day (~20 minutes per year of data).  This is mostly due to delays
used to slow down the rate of API requests.  You may interrupt and restart the process -- any CSV
files that already exist will be skipped during the next run.


## Data

The data is formatted as follows:
`download/<site_id>/2022-05-23.csv`
```CSV
timestamp,solar_power,battery_power,grid_power,grid_services_power,generator_power,load_power
2023-05-23 00:00:00,0,0,569.7448979591836,0,0,569.7448979591836
2023-05-23 00:05:00,0,0,494.8469387755102,0,0,494.8469387755102
[...]
2023-05-23 10:25:00,7691.632653061224,0,-7238.224489795918,0,0,453.408163265306
2023-05-23 10:30:00,7689.183673469388,0,-7211.2040816326535,0,0,477.979591836734
[...]
2023-05-23 23:50:00,0,826.6666666666666,0,0,0,826.6666666666666
2023-05-23 23:55:00,0,855.7142857142857,0,0,0,855.7142857142857
```

- One CSV file per day.
- Every file starts at midnight and ends at 11.55pm, in 5 minute increments.  There might be gaps.
- All power values are in Watts.
- load_power is simply a sum of solar+battery+grid+generator power and is what is shown as "house" load in the Tesla app.  (Note: this value is not included in API responses since it can be easily derived.)
- grid_services_power and generator_power will likely be 0 and can be ignored.
