import datetime
import os
import json
import time
import sys
import dropbox

from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from traceback import format_exc


from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError


from misc import (
    error_and_exit,
    execute_command,
    format_subprocess_error,
    get_ecredentials,
    send_notif
)

config = {}

TOKEN = 'IM6PzWRtUPoAAAAAAAJJGKJLKAVx9uP-ES6qp59Kat9edgm_OxRQkBe9u2A_ml7C'

# LOCALFILE = '{0}.tar.gz'.format(config['timestamp'])
# BACKUPPATH = '/{0}.tar.gz'.format(config['timestamp']) # Keep the forward slash before destination filename


def read_config():
    config_file = open('/opt/ghost-backup/.config.json', 'r')
    config_file_json = json.loads(config_file.read())
    config_file_json['timestamp'] = datetime.datetime.fromtimestamp(
        time.time()).strftime('%Y%m%d%H%M%S')
    config.update(config_file_json)

def dump_db():
    if config['images'] and config['themes']:
        dump_path = config['images_dir'] if config['images'] else config['themes_dir']
        config['dump_path'] = os.path.normpath(dump_path + '/..')
    else:
        config['dump_path'] = os.getcwd()

    #print('dumping database {0}').format(config['timestamp'])
    config['dump_file'] = config['dump_path'] + '/{0}.sql'.format(config['timestamp'])
    dump_command = ("mysqldump -h{mysql_hostname} -u'{mysql_username}' "
                    "-p'{mysql_password}' {mysql_db_name} > {0}".format(
                        config['dump_file'],
                        **config
                    )
    )
    status = execute_command(dump_command)

    if status.returncode != 0:
        print("state code here %s " %status.returncode)
        error_and_exit(
            '\nError while taking DB dump\n\n{0}'.format(format_subprocess_error(status)),
            config.get('telegram_user_id')
        )

def pack_files():
    compress_command = 'tar -C {0} -cvzf {1}.tar.gz {1}.sql'.format(
        config['dump_path'], config['timestamp'])

    if config['images']:
        compress_command += ' images'

    if config['themes']:
        compress_command += ' themes'
    status = execute_command(compress_command)

    if status.returncode != 0:
        print("state code here %s " %status.returncode)
        error_and_exit(
            '\nError while packing backup files\n\n{0}'.format(format_subprocess_error(status)),
            config.get('telegram_user_id')
        )

def upload_files():
    oauth_config = config['oauth']

    credentials = Credentials(
        None,
        refresh_token=oauth_config['refresh_token'],
        token_uri=oauth_config['token_uri'],
        client_id=get_ecredentials('yatch'),
        client_secret=get_ecredentials('bakery')
    )
    drive = build('drive', 'v3', credentials=credentials)

    media = MediaFileUpload('{0}.tar.gz'.format(config['timestamp']))
    file_metadata = {
        'name': config['timestamp'] + '.tar.gz',
        'mimeType': 'application/gzip'
    }

    resp = drive.files().update(
        body=file_metadata,
        fileId=config['backup_file_id'],
        media_body=media
    ).execute()

def delete_backups():
    execute_command('rm {0} {1}.tar.gz'.format(config['dump_file'], config['timestamp']))






def main():
    #read_config()
    dump_db()
    pack_files()
    upload_files()
    delete_backups()
    send_notif(config.get('telegram_user_id'), 'Backup completed successfully!!!')

#LOCALFILE = '{0}.tar.gz'.format(config['timestamp'])
#BACKUPPATH = '/{0}.tar.gz'.format(config['timestamp']) # Keep the forward slash before destination filename


# Uploads contents of LOCALFILE to Dropbox
def dropbox_backup():
    #with open('{0}.tar.gz'.format(config['timestamp']), 'rb') as f:
    LOCALFILE = '{0}.tar.gz'.format(config['timestamp'])
    BACKUPPATH = '/{0}.tar.gz'.format(config['timestamp']) # Keep the forward slash before destination filename
    #LOCALFILE = '20190330124159.tar.gz'
    #BACKUPPATH = '/20190330124159.tar.gz'

    with open(LOCALFILE, 'rb') as f:
        # We use WriteMode=overwrite to make sure that the settings in the file
        # are changed on upload
        print("Uploading " + LOCALFILE + " to Dropbox as " + BACKUPPATH + "...")
        try:
            dbx.files_upload(f.read(), BACKUPPATH, mode=WriteMode('overwrite'))
        except ApiError as err:
            # This checks for the specific error where a user doesn't have enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().error.is_insufficient_space()):
                sys.exit("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
                sys.exit()
            else:
                print(err)
                sys.exit()


# Adding few functions to check file details
def checkFileDetails():
    print("Checking file details")

    for entry in dbx.files_list_folder('').entries:
        print("File list is : ")
        print(entry.name)



if __name__ == '__main__':
    try:
        #main()
        read_config()
        dump_db()
        pack_files()
        #upload_files()
        print(config['timestamp'])
        if (len(TOKEN) == 0):
            sys.exit("ERROR: Looks like you didn't add your access token. Open up backup-and-restore-example.py in a text editor and paste in your token in line 14.")

    # Create an instance of a Dropbox class, which can make requests to the API.
        print("Creating a Dropbox object...")
        dbx = dropbox.Dropbox(TOKEN)

    # Check that the access token is valid
        try:
            dbx.users_get_current_account()
        except AuthError as err:
            sys.exit(
                "ERROR: Invalid access token; try re-generating an access token from the app console on the web.")

        try:
            checkFileDetails()
        except Error as err:
            sys.exit("Error while checking file details")

        print("Creating backup...")
    # Create a backup of the current settings file
        dropbox_backup()

        print("Done!")
        #delete_backups()

    except Exception as e:
        error_and_exit("\nFollowing error occured:\n{0}\n\n"
                       "More info about the error:\n{1}".format(e, format_exc()),
                       config.get('telegram_user_id')
        )