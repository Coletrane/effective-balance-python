from __future__ import print_function
import httplib2
import os

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
APPLICATION_NAME = 'Effective Balance'

def get_credentials():
    """Gets valid user credentials from storage.

   If nothing has been stored, or if the stored credentials are invalid,
   the OAuth2 flow is completed to obtain the new credentials.

   Returns:
       Credentials, the obtained credential.
   """
    # home_dir = os.path.expanduser('~/Programs')
    # credential_dir = os.path.join(home_dir, '.credentials')
    # if not os.path.exists(credential_dir):
    #     os.makedirs(credential_dir)
    # credential_path = os.path.join(credential_dir,
    #                                'gmail.json')

    creds_file_name = 'credentials.json'
    try:
        credentials_file = open(creds_file_name, 'r')
    except:
        credentials_file = open(creds_file_name, 'w')
    finally:
        credentials_path = os.path.join(os.getcwd(), creds_file_name)

    store = Storage(credentials_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credentials_path)
    return credentials

def main():
    """Shows basic usage of the Gmail API.

   Creates a Gmail API service object and outputs a list of label names
   of the user's Gmail account.
   """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)

    suntrust_query = 'from:alertnotification@suntrust.com newer_than:2d'
    suntrust_email_ids = service.users().messages().list(userId='me', q=suntrust_query).execute()

    if not suntrust_email_ids:
        print('No emails from SunTrust found!')
    else:
        suntrust_emails = []
        for email in suntrust_email_ids['messages']:
            suntrust_emails.append(service.users().messages().get(userId='me', id=email['id']).excecute())

            if not suntrust_emails:
                print('No email found with id' + email['id'])
            else:
                for real_email in suntrust_emails:
                    print(real_email['snippet'])

if __name__ == '__main__':
    main()
