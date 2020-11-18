import argparse
import boto3
import json
import logging
import pytz
import re

import numpy as np
import pandas as pd
import datetime as dt
import tweepy as tp

from time import sleep
from botocore.exceptions import ClientError

log = logging.getLogger()
log.setLevel(logging.INFO)

URL = 'https://apps.fas.usda.gov/export-sales/cottfax.htm'


class ExportSales:
    def __init__(self, profile=None):
        self.API = None
        self.profile_name = profile

    def get_secret(self):
        session = boto3.session.Session(profile_name=self.profile_name)
        client = session.client(
            service_name='secretsmanager', region_name='us-east-1')
        secret = client.get_secret_value(SecretId="twitter")["SecretString"]
        secret = json.loads(secret)
        return secret

    def login_twitter(self):
        secrets = self.get_secret()
        auth = tp.OAuthHandler(
            secrets['consumer_key'], secrets['consumer_secret'])
        auth.set_access_token(
            secrets['access_token'], secrets['access_secret'])
        self.API = tp.API(auth)

    def get_last_date(self):
        # Given the list of recent tweets find the most recent date for the Export Sales tweet
        tweets = self.API.user_timeline()
        last_date = dt.date(2000, 1, 1)
        for t in tweets:
            text = t.text
            date = re.search(r'\d+/\d+/\d+', text)
            if 'EXPORT SALES' in text and date:
                date = date.group()
                date = dt.datetime.strptime(date, '%m/%d/%y').date()
                last_date = max(last_date, date)

        return last_date

    @staticmethod
    def largest_df(dfs):
        # Returns largest df in a list of dfs
        if type(dfs) is list:
            sizes = [df.shape[0] * df.shape[1] for df in dfs]
            largest = sizes.index(max(sizes))
            return dfs[largest]
        return dfs

    def load_df(self, url):
        # Load the table into a df
        tables = pd.read_html(url, header=0)
        # get the largest df
        df_temp = self.largest_df(tables)
        return df_temp

    @staticmethod
    def get_report_date(df):
        # Find the date that is embedded in the df
        # get the date in the first column
        date_str = df[df.iloc[:, 0].str.contains(
            'ending', case=False)].iloc[:, 0][0]
        numbers = re.findall(r'\d+', date_str)
        # get the numbers from str and split by "/"
        numbers = [int(s) for s in numbers]
        date = dt.datetime(year=numbers[2],
                           month=numbers[0], day=numbers[1]).date()
        return date

    @staticmethod
    def clean(df):
        # Cleans up the df to easily reference the necessary columns/rows
        split_index = df.index[df.iloc[:, 0] == 'COUNTRY'].tolist()[0]
        df = df.iloc[split_index:, ].reset_index(drop=True)

        # set column values to second row
        df = df.rename(columns=df.iloc[1])
        # remove first two rows
        df = df[2:]
        df = df.reset_index(drop=True)

        df.columns = [re.sub('[^A-Za-z]', '', str(i)).lower()
                      for i in df.columns]
        df = df.set_index('country')
        return df

    @staticmethod
    def get_intersection(df, row, col):
        # Finds the intersection value of the col row values and converts the number from 9.6 to 9,600
        values = df.loc[row, col].tolist()
        if type(values) is list:
            values = np.array([float(i)*1000 for i in values])
            value = int(values.sum())
            return '{:,}'.format(value)
        value = int(float(values) * 1000)
        return '{:,}'.format(value)

    def get_export_text(self, df, date):
        # Writes out the text which will be tweeted.
        week_text = dt.datetime.strftime(date, '%m/%d/%y')
        sales = self.get_intersection(df, 'TOTAL', 'newsales')
        exports = self.get_intersection(df, 'TOTAL', 'exports')
        cancel = self.get_intersection(df, 'TOTAL', 'cancel')
        tweet = f'U.S. EXPORT SALES {week_text}\nExports: {exports}\nNew Sales: {sales}\nCancels: {cancel}\n{URL}\n#cotton'
        return tweet

    @staticmethod
    def is_dst():
        tz = pytz.timezone('US/Eastern')
        now = pytz.utc.localize(dt.datetime.utcnow())
        return now.astimezone(tz).dst() != dt.timedelta(0)

    def run(self):
        is_dst = self.is_dst()
        current_hour = dt.datetime.utcnow().hour
        log.info(f'Daylight savings: ${is_dst}, UTC Hour: {current_hour}')
        # End the function early if it is not the right time given if the US is in daylight savings
        if (is_dst and current_hour >= 13) or (not is_dst and current_hour < 13):
            return

        df = self.load_df(URL)
        found_date = self.get_report_date(df)
        self.login_twitter()
        last_date = self.get_last_date()
        log.info(f'Found date: {found_date}\nLast date: {last_date}')

        # Only if a newer date is found should you tweet out the report
        if found_date > last_date:
            df = self.clean(df)
            log.info(df)
            tweet = self.get_export_text(df=df, date=found_date)
            self.API.update_status(tweet)


def main(event, context):
    ExportSales().run()
    return {'statusCode': 200}


if __name__ == "__main__":
    # Below code allows for local testing with different aws profiles
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', dest='profile',
                        type=str, help='which aws profile to use')
    args = parser.parse_args()
    ExportSales(profile=args.profile).run()
