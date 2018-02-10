from __future__ import print_function

import httplib2
import os
import re
import json
import smtplib
import datetime
from email.mime.text import MIMEText
from apiclient import discovery
from apscheduler.schedulers.blocking import BlockingScheduler
from oauth2client.client import GoogleCredentials
from oauth2client import tools
from os.path import join,dirname
from dotenv import load_dotenv

# Parse cli arguments
try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

APPLICATION_NAME = 'Effective Balance'
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'

# Load environment variables
try:
    load_dotenv(join(dirname(__file__), '.env'))
    environment = 'dev'
    print('.env file found, environment is: ' + environment)
except IOError as e:
    environment = 'prod'
    print('No .env file found, environment is: ' + environment)

CREDENTIALS_JSON = os.environ.get('CREDENTIALS_JSON')
GMAIL_LOGIN_JSON = os.environ.get('GMAIL_LOGIN_JSON')

def get_balance_from_inbox(bank, query):
    """Gets and returns the most current balance from SunTrust"""

    creds = json.loads(CREDENTIALS_JSON)
    credentials = GoogleCredentials(
        creds['access_token'],
        creds['client_id'],
        creds['client_secret'],
        creds['refresh_token'],
        creds['token_expiry'],
        creds['token_uri'],
        creds['user_agent'])
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)

    email_ids = service.users().messages().list(userId='me', q=query).execute()

    if not email_ids:
        print('No emails from ' + bank + ' found!')
    else:
        emails = []
        for email in email_ids['messages']:
            emails.append(service.users().messages().get(userId='me', id=email['id']).execute())

            if not emails:
                print('No email found with id' + email['id'])
            else:
                emails.sort(key=lambda email: email['internalDate'])
                balance = re.findall(r'(?:[$]{1}[,\d]+.?\d*)', emails[0]['snippet'])
                return balance[0]

def send_effective_balance_email(balance):
    """Logs into the gmail SMTPS server and sends an email with the current balance"""

    gmail = json.loads(GMAIL_LOGIN_JSON)

    username = json.dumps(gmail['username']).replace('\"', '')
    password = json.dumps(gmail['password']).replace('\"', '')

    balance_str = 'Effective Balance: $' + str(balance)
    msg = MIMEText(balance_str, 'plain')
    msg['Subject'] = balance_str

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(username, password)
        server.sendmail(username, username, msg.as_string())
        print('Email sent!')
    except Exception as e:
        print('Could not send email!')
        print(e)

def get_balance_and_send_email():
    additional_query = ' newer_than:2d'
    suntrust_query = 'from:alertnotification@suntrust.com' + additional_query
    citi_query = 'from:alerts@citibank.com' + additional_query

    suntrust_balance = get_balance_from_inbox("SunTrust", suntrust_query)
    citi_balance = get_balance_from_inbox('Citi', citi_query)

    # Take the $ out and make them real deal floats
    suntrust_balance = float(suntrust_balance.replace('$', ''))
    citi_balance = float(citi_balance.replace('$', ''))

    send_effective_balance_email(suntrust_balance - citi_balance)

def main():
    # Create and configure the scheduler to run every day
    scheduler = BlockingScheduler()

    scheduler.add_job(get_balance_and_send_email,
                      'interval',
                      hours=23)

    print("Testing: sending email now")
    get_balance_and_send_email()

    print('Scheduler started at ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    scheduler.start()

if __name__ == '__main__':
    main()
