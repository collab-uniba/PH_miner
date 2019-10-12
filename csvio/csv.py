import csv
import sys


class CsvReader:
    """
    A CSV reader which will read rows from CSV file "f",
    which is encoded in the given encoding.
    """
    max_int = sys.maxsize
    while True:
        # decrease the max_int value by factor 10 as long as the OverflowError occurs.
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = int(max_int / 10)
    reader = None

    def __init__(self, csv_file, mode='r'):
        self.f = open(csv_file, mode, newline='\n', encoding='utf-8')
        self.reader = csv.reader(self.f, delimiter=';', dialect=csv.excel)

    def readrows(self):
        return self.reader

    def close(self):
        self.f.close()


class CsvWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """
    writer = None

    def __init__(self, csv_file, mode='w'):
        self.f = open(csv_file, mode, newline='\n', encoding='utf-8')
        self.writer = csv.writer(self.f, delimiter=';', dialect=csv.excel, quoting=csv.QUOTE_MINIMAL)

    def writerow(self, row):
        self.writer.writerow(row)

    def writerows(self, rows):
        for row in rows:
            self.writer.writerow(row)

    def close(self):
        self.f.close()

    def flush(self):
        self.f.flush()
