# Tesla Solar Data Downloader

## Introduction

This script will download your entire history of Tesla Solar power and energy data:
solar/battery/grid power data in 5 minute intervals and daily totals for solar/home/battery/grid
energy.  The script is using the [unofficial Tesla API](https://tesla-api.timdorr.com/)
and [TeslaPy](https://github.com/tdorssers/TeslaPy) library.  Data is stored in CSV files: one file per
day for power, and one file per month for energy.  You can run the script repeatedly and it will only
download new data.

Note: if you're not comfortable running Python code and want better data exports from your Tesla solar/battery system,
consider the [Netzero app](https://www.netzeroapp.io).

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
    pip3 install --upgrade pip
    pip3 install -r requirements.txt
    ```

## Usage
```bash
source venv/bin/activate
python3 ./tesla_solar_download.py --email my_tesla_email@gmail.com
```

Follow the instructions to log in to Tesla with your web browser (this is needed to generate an API
token, the credentials are only sent to Tesla).  Once you've logged in, the token will be stored
locally so you can rerun the script if needed.

Data will start downloading to the `download` directory.  Starting with today and going back in time
all the way to the Tesla system's installation date.

Power data downloads take ~1.5 seconds per day (~10 minutes per year of data).  This is mostly due
to delays used to slow down the rate of API requests.  You may interrupt and restart the process
-- any CSV files that already exist will be skipped during the next run.

Energy downloads are faster (less than 30s per year).


## Data

Power data is formatted as follows:
`download/<site_id>/power/2022-07-19.csv`
```CSV
timestamp,solar_power,battery_power,grid_power,load_power
[...]
2023-07-19 10:40:00,7506.428571428572,-7401.224489795918,612.5714285714286,717.775510204082
2023-07-19 10:45:00,7576.836734693878,-3342.0408163265306,-3555.030612244898,679.7653061224487
2023-07-19 10:50:00,7616.666666666667,-3466.6666666666665,-3544.4,605.5999999999999
[...]
```

- One CSV file per day.
- Every file starts at midnight and ends at 11.55pm, in 5 minute increments.
- All power values are in Watts.
- load_power is simply a sum of solar+battery+grid+generator power and is what is shown as "house" load in the Tesla app.  (Note: this value is not included in API responses since it can be easily derived.)

Energy data:
`download/<site_id>/energy/2022-07.csv`
```CSV
timestamp,solar_energy_exported,grid_energy_imported,grid_energy_exported_from_solar,grid_energy_exported_from_battery,battery_energy_exported,battery_energy_imported_from_grid,battery_energy_imported_from_solar,consumer_energy_imported_from_grid,consumer_energy_imported_from_solar,consumer_energy_imported_from_battery
2023-07-01 01:00:00,66700,6493.5,43456,0,16760,249.5,15640.5,6244,7603.5,16760
2023-07-02 01:00:00,66780,6353,40874,0,14060,260,18510,6093,7396,14060
2023-07-03 01:00:00,67380,6282,45964.5,0,10030,230,15580,6052,5835.5,10030
[...]
```
