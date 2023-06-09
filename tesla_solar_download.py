"""
Copyright 2023 Ziga Mahkovec

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import csv
import os
import time
from datetime import datetime, timedelta

import pytz
import teslapy
from dateutil.parser import parse
from retry import retry


def _get_csv_name(date, site_id, partial_day=False):
    str_date = date.strftime('%Y-%m-%d')
    suffix = '.partial.csv' if partial_day else '.csv'
    return f'download/{site_id}/{str_date}{suffix}'


def _write_csv(timeseries, date, site_id, partial_day=False):
    if not timeseries:
        raise ValueError(f'No timeseries for {date}')

    csv_filename = _get_csv_name(date, site_id, partial_day=partial_day)
    os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
    fieldnames = list(timeseries[0].keys()) + ['load_power']
    with open(csv_filename, 'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for ts in timeseries:
            ts['timestamp'] = parse(ts['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            ts['load_power'] = (
                ts['solar_power']
                + ts['battery_power']
                + ts['grid_power']
                + ts['generator_power']
            )
            writer.writerow(ts)


@retry(tries=2, delay=5)
def _download_day(tesla, site_id, timezone, date, partial_day=True):
    start_date = (
        pytz.timezone(timezone)
        .localize(date.replace(hour=0, minute=0, second=0, tzinfo=None))
        .isoformat()
    )
    end_date = (
        pytz.timezone(timezone)
        .localize(date.replace(hour=23, minute=59, second=59, tzinfo=None))
        .isoformat()
    )
    response = tesla.api(
        'CALENDAR_HISTORY_DATA',
        path_vars={'site_id': site_id},
        kind='power',
        period='day',
        start_date=start_date,
        end_date=end_date,
        time_zone=timezone,
        fill_telemetry=0,
    )['response']

    _write_csv(response['time_series'], date, site_id, partial_day=partial_day)


def _download_data(tesla, site_id, debug=False):
    site_config = tesla.api('SITE_CONFIG', path_vars={'site_id': site_id})['response']
    installation_date = parse(site_config['installation_date'])
    timezone = site_config['installation_time_zone']

    date = pytz.timezone(timezone).localize(
        datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    )
    if debug:
        print(f'Timezone: {timezone}')
        print(f'Start date: {date}')

    # The first day (today) will be partial.
    partial_day = True

    while date > installation_date:
        if partial_day or not os.path.exists(_get_csv_name(date, site_id)):
            print(date.isoformat())
            _download_day(tesla, site_id, timezone, date, partial_day=partial_day)
            time.sleep(3)
        date -= timedelta(days=1)
        partial_day = False
        # Re-localize the date based on the timezone.  This is important because we maybe have
        # crossed a daylight saving change so the timezone offset will be different.
        date = pytz.timezone(timezone).localize(date.replace(tzinfo=None))


def _delete_partial_files(site_id):
    dir = os.path.join('download', str(site_id))
    for fname in os.listdir(dir):
        if '.partial.csv' in fname:
            os.remove(os.path.join(dir, fname))


def main():
    parser = argparse.ArgumentParser(
        description='Download Tesla Solar/Powerwall power data'
    )
    parser.add_argument(
        '--email', type=str, required=True, help='Tesla account email address'
    )
    parser.add_argument('--debug', action='store_true', help='Print debug info')
    args = parser.parse_args()

    tesla = teslapy.Tesla(args.email, retry=2, timeout=10)
    if not tesla.authorized:
        print('STEP 1: Log in to Tesla.  Open this page in your browser:\n')
        print(tesla.authorization_url())
        print()
        print(
            'After successful login, you will get a Page Not Found error.  That\'s expected.'
        )
        print('Just copy the url of that page and paste it here:')
        tesla.fetch_token(authorization_response=input('URL after authentication: '))
        print('\nSuccess!')

    for product in tesla.api('PRODUCT_LIST')['response']:
        resource_type = product.get('resource_type')
        if resource_type in ('battery', 'solar'):
            site_id = product['energy_site_id']
            print(f'Downloading data for {resource_type} site ***{str(site_id)[-4:]}')
            _delete_partial_files(site_id)
            _download_data(tesla, site_id, debug=args.debug)


if __name__ == '__main__':
    main()
