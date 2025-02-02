import requests
import os

files = os.listdir('libraries')
url = "http://192.168.0.196:8001/v1/ingest/file"

totalFiles = len(files)
counter = 1


for library in files:
    print('=================')
    print(f'Ingesting {library} file number {counter} of {totalFiles}')    
    with open('libraries/'+library, 'rb') as file:
            upload_file = {'file': (library, file, 'application/xml')}
            response = requests.post(url, files=upload_file)

            print(response.status_code)
            print(response.text)
    counter +=1
