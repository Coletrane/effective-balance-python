from __future__ import print_function

import httplib2
import os
import re
import json
import datetime
from apiclient import discovery
from apscheduler.schedulers.blocking import BlockingScheduler
from oauth2client.client import GoogleCredentials
from oauth2client import tools
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Parse cli arguments
try:
    import argparse

    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# Google API configs
APPLICATION_NAME = 'Effective Balance'
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'

# AWS SES configs
AWS_REGION = 'us-east-1'
EMAIL = 'eloc49@gmail.com'

# Load environment variables
env_file = './.env'
if os.path.exists(env_file):
    load_dotenv(env_file)
    environment = 'dev'
    print('.env file found, environment is: ' + environment)
else:
    environment = 'prod'
    print('No .env file found, environment is: ' + environment)

CREDENTIALS_JSON = os.environ.get('CREDENTIALS_JSON')
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')


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

    balance_str = 'Effective Balance: $' + str(balance)

    client = boto3.client('ses', region_name=AWS_REGION)

    try:
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    EMAIL
                ]
            },
            Message={
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': balance_str
                },
                'Body': {
                    'Text': {
                        'Charset': 'UTF-8',
                        'Data': balance_str
                    }
                }
            },
            Source=EMAIL)
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print('Email sent!')

    # gmail = json.loads(GMAIL_LOGIN_JSON)
    #
    # username = json.dumps(gmail['username']).replace('\"', '')
    # password = json.dumps(gmail['password']).replace('\"', '')
    #
    # balance_str = 'Effective Balance: $' + str(balance)
    # msg = MIMEText(balance_str, 'plain')
    # msg['Subject'] = balance_str
    #
    # try:
    #     server = smtplib.SMTP('smtp.gmail.com', 587)
    #     server.ehlo()
    #     server.starttls()
    #     server.login(username, password)
    #     server.sendmail(username, username, msg.as_string())
    #     print('Email sent!')
    # except Exception as e:
    #     print('Could not send email!')
    #     print(e)


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
