from __future__ import print_function
import httplib2
import os
import io
import threading
import time

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from apiclient.http import MediaFileUpload, MediaIoBaseDownload
from pathlib import Path
#SA
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import sys

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = ['https://www.googleapis.com/auth/drive']
CLIENT_SECRET_FILE = 'credentials.json'

SA_ACCOUNT = True
SA_SECRET_FILE = 'sa-account.json'
THREADS = int(open("cpu.txt","r").readline())
srt_file_list = {}

def get_credentials(CLIENT_SECRET_FILE):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)
    
def Create_Sa_Service(SA_SECRET_FILE):
    credentials = service_account.Credentials.from_service_account_file(SA_SECRET_FILE,scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials, cache_discovery=False)
    
    

def main():
    credentials = service_account.Credentials.from_service_account_file(SA_SECRET_FILE,scopes=SCOPES)
    service = Create_Sa_Service(SA_SECRET_FILE)
    
    # imgfile = 'image.jpeg'  # Image with texts (png, jpg, bmp, gif, pdf)
    # txtfile = 'text.txt'  # Text file outputted by OCR

    current_directory = Path(Path.cwd())
    images_dir = Path(f'{current_directory}/down')
    raw_texts_dir = Path(f'{current_directory}/raw_texts')
    texts_dir = Path(f'{current_directory}/texts')
    srt_file = open(Path(f'{current_directory}/down.srt'), 'a', encoding='utf-8')
    line = 1

    # check directory if exists
    if not images_dir.exists():
        images_dir.mkdir()
        print('Images folder is empty.')
        exit()

    if not raw_texts_dir.exists():
        raw_texts_dir.mkdir()
    if not texts_dir.exists():
        texts_dir.mkdir()
	
    images = Path(f'{current_directory}/up').rglob('*.jpg')
    images2 = []
    threads = []
    for image in images:
        images2.append(image)
    for image in Path(f'{current_directory}/up').rglob('*.png'):
        images2.append(image)	
    for image in images2:
        t = threading.Thread(target=ocr_image, args=[image, line, credentials, current_directory])
        line += 1
        while len(threads) > THREADS:

            for thread in range(len(threads), 0, -1):
                thread = thread - 1
                if not threads[thread].is_alive():
                    threads.pop(thread)
        t.start()
        time.sleep(0.25)
        threads.append(t)
        if image == images2[-1]:
            for thread in threads:
                thread.join()
    for i in sorted(srt_file_list):
        srt_file.writelines(srt_file_list[i])
    srt_file.close()



def ocr_image(image, line, credentials, current_directory):
    tries = 0
    while True:
        try:
            credentials = service_account.Credentials.from_service_account_file(SA_SECRET_FILE,scopes=SCOPES)
            service = Create_Sa_Service(SA_SECRET_FILE)
            # Get data
            imgfile = str(image.absolute())
            imgname = str(image.name)
            raw_txtfile = f'{current_directory}/raw_texts/{imgname[:-5]}.txt'
            txtfile = f'{current_directory}/texts/{imgname[:-5]}.txt'
        
            mime = 'application/vnd.google-apps.document'
            res = service.files().create(
                body={
                    'name': imgname,
                    'mimeType': mime
                },
                media_body=MediaFileUpload(imgfile, mimetype=mime, resumable=True)
            ).execute()
            try:
                res = service.files().create(
                    body={
                        'name': imgname,
                        'mimeType': mime
                    },
                    media_body=MediaFileUpload(imgfile, mimetype=mime, resumable=True)
                ).execute()
            except:
                time.sleep(1)
                try:
                    res = service.files().create(
                        body={
                            'name': imgname,
                            'mimeType': mime
                        },
                        media_body=MediaFileUpload(imgfile, mimetype=mime, resumable=True)
                    ).execute()
                except:
                    time.sleep(5)
                    try:
                        res = service.files().create(
                            body={
                                'name': imgname,
                                'mimeType': mime
                            },
                            media_body=MediaFileUpload(imgfile, mimetype=mime, resumable=True)
                        ).execute()
                    except:
                        raise
            downloader = MediaIoBaseDownload(
                io.FileIO(raw_txtfile, 'wb'),
                service.files().export_media(fileId=res['id'], mimeType="text/plain")
            )
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            try:
                service.files().delete(fileId=res['id']).execute()
            except:
                time.sleep(1)
                try:
                    service.files().delete(fileId=res['id']).execute()
                except:
                    time.sleep(5)
                    try:
                        service.files().delete(fileId=res['id']).execute()
                    except:
                        raise
        
            # Create clean text file
            raw_text_file = open(raw_txtfile, 'r', encoding='utf-8')
            text_content = raw_text_file.read()
            raw_text_file.close()
            text_content = text_content.split('\n')
            text_content = ''.join(text_content[2:])
            text_file = open(txtfile, 'w', encoding='utf-8')
            text_file.write(text_content)
            text_file.close()
        
            start_hour = imgname.split('_')[0][:2]
            start_min = imgname.split('_')[1][:2]
            start_sec = imgname.split('_')[2][:2]
            start_micro = imgname.split('_')[3][:3]
        
            end_hour = imgname.split('__')[1].split('_')[0][:2]
            end_min = imgname.split('__')[1].split('_')[1][:2]
            end_sec = imgname.split('__')[1].split('_')[2][:2]
            end_micro = imgname.split('__')[1].split('_')[3][:3]
        
            # Format start time
            start_time = f'{start_hour}:{start_min}:{start_sec},{start_micro}'
        
            # Format end time
            end_time = f'{end_hour}:{end_min}:{end_sec},{end_micro}'
            # Append the line to srt file
            srt_file_list[line] = [
                f'{line}\n',
                f'{start_time} --> {end_time}\n',
                f'{text_content}\n\n',
                ''
            ]
        
            print(f"{imgname} Done.")
            break
        except:
            tries +=1
            if tries > 5:
                raise
            continue

	
    
    
if __name__ == '__main__':
    main()
