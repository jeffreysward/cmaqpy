"""
Functions that support other cmaqpy modules.

Known Issues/Wishlist:

"""
import datetime


def format_date(in_date):
    """
    Formats an input date so that it can be correctly written to the namelist.

    :param in_date : string
        string specifying the date
    :return: datetime64 array specifying the date

    """
    for fmt in ('%b %d %Y', '%B %d %Y', '%b %d, %Y', '%B %d, %Y',
                '%m-%d-%Y', '%m.%d.%Y', '%m/%d/%Y',
                '%Y-%m-%d', '%Y.%m.%d', '%Y/%m/%d',
                '%b %d %Y %H', '%B %d %Y %H', '%b %d, %Y %H', '%B %d, %Y %H',
                '%m-%d-%Y %H', '%m.%d.%Y %H', '%m/%d/%Y %H'):
        try:
            return datetime.datetime.strptime(in_date, fmt)
        except ValueError:
            pass
    raise ValueError('No valid date format found; please use a common US format (e.g., Jan 01, 2011 00)')


def read_script(file):
    """
    Opens a namelist file within a context manager.

    :param file: string
        Path to the namelist file you wish to open.
    :return: file object

    """
    with open(file, 'r') as script:
        return script.read()


def read_last(file_name, n_lines=1):
    """
    Reads the last line of a file.

    :param file_name: string
        Complete path of the file that you would like read.
    :return last_line: string
        Last line of the input file.

    """
    try:
        with open(file_name, mode='r') as infile:
            lines = infile.readlines()
    except IOError:
        last_line = 'IOEror in read_last_line: this file does not exist.'
        return last_line
    try:
        last_line = lines[-n_lines:]
    except IndexError:
        last_line = 'IndexError in read_last_line: no last line appears to exist in this file.'
    return last_line
