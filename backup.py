import datetime
import os
import json
import time
import sys
import pysftp

#from apiclient.discovery import build
#from apiclient.http import MediaFileUpload
from traceback import format_exc


from misc import (
    error_and_exit,
    execute_command,
    format_subprocess_error,
    get_credentials,
    send_notif
)

config = {}

#TOKEN = 'IM6PzWRtUPoAAAAAAAJJGKJLKAVx9uP-ES6qp59Kat9edgm_OxRQkBe9u2A_ml7C'

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



def delete_backups():
    execute_command('rm {0} {1}.tar.gz'.format(config['dump_file'], config['timestamp']))



LOCALFILE = '{0}.tar.gz'.format(config['timestamp'])
BACKUPPATH = '/{0}.tar.gz'.format(config['timestamp']) # Keep the forward slash before destination filename


def ftp_files():
    srv = pysftp.Connection(host=config['ftp_server'], username=config['ftp_user'],password=config['ftp_password'])
    srv.put(LOCALFILE)
    srv.close()
    
if __name__ == '__main__':
    try:
        read_config()
        #dump_db()
        #pack_files()
        ftp_files()
        
        #delete_backups()

    except Exception as e:
        error_and_exit("\nFollowing error occured:\n{0}\n\n"
                       "More info about the error:\n{1}".format(e, format_exc()),
                       config.get('telegram_user_id')
        )