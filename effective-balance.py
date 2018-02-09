from __future__ import print_function

import httplib2
import os
import re
import json
import smtplib
from email.mime.text import MIMEText
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
CREDS_FILE = 'credentials.json'
GMAIL_LOGIN_FILE = 'gmail-login.json'
APPLICATION_NAME = 'Effective Balance'

def get_credentials():
    """Gets valid user credentials from storage.

   If nothing has been stored, or if the stored credentials are invalid,
   the OAuth2 flow is completed to obtain the new credentials.

   Returns:
       Credentials, the obtained credential.
   """

    try:
        credentials_file = open(CREDS_FILE, 'r')
    except IOError:
        credentials_file = open(CREDS_FILE, 'w')
    finally:
        credentials_path = os.path.join(os.getcwd(), CREDS_FILE)

    store = Storage(credentials_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credentials_path)
    return credentials

def get_balance_from_inbox(bank, query):
    """Gets and returns the most current balance from SunTrust"""

    credentials = get_credentials()
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

    gmail = json.load(open('gmail-login.json'))

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

def main():
    additional_query = ' newer_than:2d'
    suntrust_query = 'from:alertnotification@suntrust.com' + additional_query
    citi_query = 'from:alerts@citibank.com' + additional_query

    suntrust_balance = get_balance_from_inbox("SunTrust", suntrust_query)
    citi_balance = get_balance_from_inbox('Citi', citi_query)

    # Take the $ out and make them real deal floats
    suntrust_balance = float(suntrust_balance.replace('$', ''))
    citi_balance = float(citi_balance.replace('$', ''))

    send_effective_balance_email(suntrust_balance - citi_balance)

if __name__ == '__main__':
    main()
