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
import traceback
from datetime import datetime, timedelta

import pytz
import teslapy
from dateutil.parser import parse
from retry import retry

# Exclude columns that are not relevant (and generally not set).
EXCLUDED_COLUMNS = (
    'grid_services_power',
    'generator_power',
    'generator_energy_exported',
    'grid_services_energy_imported',
    'grid_services_energy_exported',
    'grid_energy_exported_from_generator',
    'battery_energy_imported_from_generator',
    'consumer_energy_imported_from_generator',
)


def _remove_excluded_columns(timeseries):
    for col in EXCLUDED_COLUMNS:
        if col in timeseries:
            del timeseries[col]


def _get_energy_csv_name(date, site_id, partial_month=False):
    str_date = date.strftime('%Y-%m')
    suffix = '.partial.csv' if partial_month else '.csv'
    return f'download/{site_id}/energy/{str_date}{suffix}'


def _get_fieldnames_from_series(timeseries):
    keys = dict()
    for series in timeseries:
        for k in series.keys():
            keys[k] = True
    return list(keys.keys())


def _write_energy_csv(timeseries, date, site_id, partial_month=False):
    if not timeseries:
        raise ValueError('No timeseries')

    csv_filename = _get_energy_csv_name(date, site_id, partial_month=partial_month)
    os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
    fieldnames = _get_fieldnames_from_series(timeseries)
    fieldnames = [n for n in fieldnames if n not in EXCLUDED_COLUMNS]
    with open(csv_filename, 'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for ts in timeseries:
            ts['timestamp'] = parse(ts['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            _remove_excluded_columns(ts)
            writer.writerow(ts)


@retry(tries=2, delay=5)
def _download_energy_month(
    tesla, site_id, timezone, start_date, end_date, partial_month=False
):
    response = tesla.api(
        'CALENDAR_HISTORY_DATA',
        path_vars={'site_id': site_id},
        kind='energy',
        period='month',
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        time_zone=timezone,
    )['response']

    if not response or 'time_series' not in response:
        raise ValueError(f'No timeseries for {start_date}')
    _write_energy_csv(
        response['time_series'], start_date, site_id, partial_month=partial_month
    )


def _get_timezone(site_config, installation_date):
    if 'installation_time_zone' in site_config:
        return site_config['installation_time_zone']
    offset = installation_date.strftime('%z')
    for tz in pytz.country_timezones('us'):
        if datetime.now(pytz.timezone(tz)).strftime('%z') == offset:
            return tz
    for tz in pytz.common_timezones:
        if datetime.now(pytz.timezone(tz)).strftime('%z') == offset:
            return tz
    for tz in pytz.all_timezones:
        if datetime.now(pytz.timezone(tz)).strftime('%z') == offset:
            return tz


def _download_energy_data(tesla, site_id, debug=False):
    site_config = tesla.api('SITE_CONFIG', path_vars={'site_id': site_id})['response']
    installation_date = parse(site_config['installation_date'])
    timezone = _get_timezone(site_config, installation_date)

    now = datetime.now(pytz.timezone(timezone)).replace(microsecond=0)
    start_date = now.replace(hour=0, minute=0, second=0)
    end_date = now.replace(hour=23, minute=59, second=59)

    # Beginning of the month.
    start_date = start_date - timedelta(days=start_date.day - 1)
    if debug:
        print(f'Timezone: {timezone}')
        print(f'Start date: {start_date}')

    # The latest month will be partial.
    partial_month = True

    while end_date > installation_date:
        csv_name = _get_energy_csv_name(start_date, site_id)
        if partial_month or not os.path.exists(
            _get_energy_csv_name(start_date, site_id)
        ):
            print(f'  {os.path.basename(csv_name)}')
            try:
                _download_energy_month(
                    tesla,
                    site_id,
                    timezone,
                    start_date,
                    end_date,
                    partial_month=partial_month,
                )
            except Exception:
                traceback.print_exc()
            time.sleep(1)
        partial_month = False
        end_date = start_date - timedelta(seconds=1)
        start_date = end_date.replace(hour=0, minute=0, second=0) - timedelta(
            days=end_date.day - 1
        )
        start_date = pytz.timezone(timezone).localize(start_date.replace(tzinfo=None))


def _delete_partial_energy_files(site_id):
    dir = os.path.join('download', str(site_id), 'energy')
    if not os.path.exists(dir):
        return
    for fname in os.listdir(dir):
        if '.partial.csv' in fname:
            os.remove(os.path.join(dir, fname))


def _get_power_csv_name(date, site_id, partial_day=False):
    str_date = date.strftime('%Y-%m-%d')
    suffix = '.partial.csv' if partial_day else '.csv'
    return f'download/{site_id}/power/{str_date}{suffix}'


def _get_soe_csv_name(date, site_id, partial_day=False):
    str_date = date.strftime('%Y-%m-%d')
    suffix = '.partial.csv' if partial_day else '.csv'
    return f'download/{site_id}/soe/{str_date}{suffix}'


def _write_power_csv(timeseries, date, site_id, partial_day=False):
    if not timeseries:
        raise ValueError(f'No timeseries for {date}')

    csv_filename = _get_power_csv_name(date, site_id, partial_day=partial_day)
    os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
    fieldnames = _get_fieldnames_from_series(timeseries) + ['load_power']
    fieldnames = [n for n in fieldnames if n not in EXCLUDED_COLUMNS]
    with open(csv_filename, 'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for ts in timeseries:
            ts['timestamp'] = parse(ts['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            ts['load_power'] = (
                ts['solar_power']
                + ts['battery_power']
                + ts['grid_power']
                + ts['generator_power']
            )
            _remove_excluded_columns(ts)
            writer.writerow(ts)


def _write_soe_csv(timeseries, date, site_id, partial_day=False):
    if not timeseries:
        raise ValueError(f'No timeseries for {date}')

    csv_filename = _get_soe_csv_name(date, site_id, partial_day=partial_day)
    os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
    fieldnames = _get_fieldnames_from_series(timeseries)
    fieldnames = [n for n in fieldnames if n not in EXCLUDED_COLUMNS]
    with open(csv_filename, 'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for ts in timeseries:
            ts['timestamp'] = parse(ts['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            _remove_excluded_columns(ts)
            writer.writerow(ts)


@retry(tries=2, delay=5)
def _download_power_day(tesla, site_id, timezone, date, partial_day=True):
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
    )['response']

    if not response or 'time_series' not in response:
        raise ValueError(f'No timeseries for {date}')
    _write_power_csv(response['time_series'], date, site_id, partial_day=partial_day)


@retry(tries=2, delay=5)
def _download_soe_day(tesla, site_id, timezone, date, partial_day=True):
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
        kind='soe',
        period='day',
        start_date=start_date,
        end_date=end_date,
        time_zone=timezone,
    )['response']

    if response and 'time_series' in response:
        _write_soe_csv(response['time_series'], date, site_id, partial_day=partial_day)


def _download_power_data(tesla, site_id, debug=False):
    site_config = tesla.api('SITE_CONFIG', path_vars={'site_id': site_id})['response']
    installation_date = parse(site_config['installation_date'])
    timezone = _get_timezone(site_config, installation_date)

    date = datetime.now(pytz.timezone(timezone)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    if debug:
        print(f'Timezone: {timezone}')
        print(f'Start date: {date}')

    # The first day (today) will be partial.
    partial_day = True

    while date > installation_date:
        csv_name = _get_power_csv_name(date, site_id)
        if partial_day or not os.path.exists(csv_name):
            print(f'  {os.path.basename(csv_name)}')
            try:
                _download_power_day(tesla, site_id, timezone, date, partial_day=partial_day)
                _download_soe_day(tesla, site_id, timezone, date, partial_day=partial_day)
            except Exception:
                traceback.print_exc()
            time.sleep(1)
        date -= timedelta(days=1)
        partial_day = False
        # Re-localize the date based on the timezone.  This is important because we maybe have
        # crossed a daylight saving change so the timezone offset will be different.
        date = pytz.timezone(timezone).localize(date.replace(tzinfo=None))


def _delete_partial_power_files(site_id):
    dir = os.path.join('download', str(site_id), 'power')
    if not os.path.exists(dir):
        return
    for fname in os.listdir(dir):
        if '.partial.csv' in fname:
            os.remove(os.path.join(dir, fname))


def _delete_partial_soe_files(site_id):
    dir = os.path.join('download', str(site_id), 'soe')
    if not os.path.exists(dir):
        return
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
            obfuscated_site_it = f'***{str(site_id)[-4:]}'
            print(
                f'Downloading energy data for {resource_type} site {obfuscated_site_it} to download/energy/'
            )
            try:
                _delete_partial_energy_files(site_id)
                _download_energy_data(tesla, site_id, debug=args.debug)
            except Exception:
                traceback.print_exc()
            print()

            print(
                f'Downloading power data for {resource_type} site {obfuscated_site_it} to download/power/'
            )
            try:
                _delete_partial_power_files(site_id)
                _delete_partial_soe_files(site_id)
                _download_power_data(tesla, site_id, debug=args.debug)
            except Exception:
                traceback.print_exc()


if __name__ == '__main__':
    main()
