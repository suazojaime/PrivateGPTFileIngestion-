def df(drives = 'C'):
    import os
    for drive in drives:
        drive = drive.upper()
        d = os.popen('dir/w ' + drive + ':\\').readlines()
        if not d:
            continue
        print '%s: (%-12s %12s bytes free ' %(
            drive,
            d[0].strip().split(' is ', 1)[-1]+')',
            d[-1].strip().split(' bytes ')[0].replace('.', '').replace(',', '')
        )

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        df()
    else:
        df(sys.argv[1])
