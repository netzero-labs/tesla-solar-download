# Tesla Solar Data Downloader

## Introduction

This script will download your entire history of Tesla Solar power and energy data:
solar/battery/grid power data in 5 minute intervals and daily totals for solar/home/battery/grid
energy.  The script is using the [unofficial Tesla API](https://tesla-api.timdorr.com/)
and [TeslaPy](https://github.com/tdorssers/TeslaPy) library.  Data is stored in CSV files by day for
power and a single `energy.csv` file for energy.

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

Power data downloads take ~1.5 seconds per day (~10 minutes per year of data).  This is mostly due
to delays used to slow down the rate of API requests.  You may interrupt and restart the process
-- any CSV files that already exist will be skipped during the next run.

Energy downloads are faster (less than 30s per year) so they're done in entirety every time.


## Data

Power data is formatted as follows:
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

Energy data:
`download/<site_id>/energy.csv`
```CSV
timestamp,solar_energy_exported,generator_energy_exported,grid_energy_imported,grid_services_energy_imported,grid_services_energy_exported,grid_energy_exported_from_solar,grid_energy_exported_from_generator,grid_energy_exported_from_battery,battery_energy_exported,battery_energy_imported_from_grid,battery_energy_imported_from_solar,battery_energy_imported_from_generator,consumer_energy_imported_from_grid,consumer_energy_imported_from_solar,consumer_energy_imported_from_battery,consumer_energy_imported_from_generator
2022-03-20 01:00:00,19900,0,16020.54954135904,0,0,0,0,31.6434716614458,6920,373.8292054498161,12196.170794550184,0,15646.720335909224,7703.829205449816,6888.356528338554,0
2022-03-21 01:00:00,18880,0,7672.932049195355,0,0,0,0,49.019242481099354,12540,274.12727761318456,9405.872722386815,0,7398.80477158217,9474.127277613185,12490.9807575189,0
2022-03-22 01:00:00,18510,0,32628.105420033753,0,0,0,0,38.805653165723925,8180,365.48287811766204,12714.517121882338,0,32262.62254191609,5795.482878117662,8141.194346834276,0
[...]
```
