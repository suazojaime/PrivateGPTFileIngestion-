#!/usr/bin/env python
import os
import glob
import zipfile
import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='Input directory with customer data .zip snapshots')
    parser.add_argument('-o', '--output', help='Output directory for extracted messages')
    parser.add_argument('-m', '--match', help='Text for matching snapshots')
    parser.parse_args()
    args = parser.parse_args()

    inDir = args.input
    os.chdir(inDir)

    outDir = args.output
    if not os.path.exists(outDir): os.makedirs(outDir)

    match = args.match

    print '---> Reading snapshots from ' + inDir
    print '---> Writing extracted messages to ' + outDir
    print '---> Matching files with ' + match

    for file in glob.glob("*.zip"):

        if match not in file: continue
        if not zipfile.is_zipfile(file): continue

        done = outDir + '/' + 'done-' + file
        if os.path.exists(done):
            print 'Skipping ' + file + '...'
            continue
        else:
            print 'Processing ' + file + '...'

        zipf = zipfile.ZipFile(file, 'r')

        for filename in zipf.namelist():
            if filename.startswith('messages/') and filename.endswith('.gwm'):
                try:
                    gwmCopy = open(outDir + '/' + filename.replace('messages/', ''), 'wb')
                    gwmCopy.write(zipf.read(filename))
                except KeyError:
                    print 'ERROR: Did not find %s in zip file' % filename
                except ValueError:
                    print 'ERROR: Did not find %s in zip file' % filename

        doneFile = open(done, 'w').write('')
        zipf.close()
