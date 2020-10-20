import sys
from zimscan import Reader

with Reader(open(sys.argv[1], 'rb')) as reader:
    for record in reader:
        data = record.read()
        print(data)
