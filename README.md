# PrivateGPT File Ingestion Script
=====================================

This script manually loads many XML files from a local directory into a PrivateGPT instance.

## Requirements
---------------

* Python 3.x with `requests` and `os` libraries installed.
* A PrivateGPT server running at http://192.168.0.196:8001/v1/ingest/file (adjust the URL as needed).

## Usage
-----

### Step 1: Place XML files in a local directory

Create a new folder named "libraries" and place all your XML files inside.

### Step 2: Run the script

Run this Python script to ingest all XML files from the "libraries" directory into PrivateGPT. The script will display progress updates for each file uploaded.

## Code
-----

```python
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
```

## Notes
-----

* Make sure to replace the `url` variable with your actual PrivateGPT server URL.
* This script assumes all XML files are in a single directory named "libraries". Adjust the file path as needed if using a different structure.