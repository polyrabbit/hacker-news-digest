'''Recognize image file formats and size based on their first few bytes.

This module is a port of Image::Size Perl Module
see more http://search.cpan.org/author/RJRAY/Image-Size-3.01/lib/Image/Size.pm

ported by jigloo(phus@live.com)
add rgbsize rassize pcxsize function

New BSD license
'''
# see https://github.com/phuslu/imgsz

__version__ = '2.1'
__all__ = ['what', 'size', 'frombytes']

import io
import re
from struct import unpack

from PIL import Image


def _jpegsize(stream):
    '''gets the width and height (in pixels) of a JPEG file'''
    x, y = 0, 0
    # Dummy read to skip header ID
    stream.read(2)
    while 1:
        # Extract the segment header.
        (marker, code, length) = unpack('!BBH', stream.read(4))
        # Verify that it's a valid segment.
        if marker != 0xFF:
            # Was it there?
            raise ValueError('JPEG marker not found')
        elif code >= 0xC0 and code <= 0xC3:
            # Segments that contain size info
            (y, x) = unpack('!xHH', stream.read(5))
            break
        else:
            # Dummy read to skip over data
            stream.read(length - 2)
    if x == 0 or y == 0:
        raise ValueError('could not determine JPEG size')
    return 'JPEG', x, y


def _bmpsize(stream):
    '''size a Windows-ish BitMap image'''
    x, y = 0, 0
    # Dummy read to skip header data
    stream.read(18)
    (x, y) = unpack('<LL', stream.read(8))
    if x == 0 or y == 0:
        raise ValueError('Unable to determine size of BMP data')
    return 'BMP', x, y


def _pngsize(stream):
    '''gets the width & height (in pixels) of a png file
    cor this program is on the cutting edge of technology! (pity it's blunt!)'''
    x, y = 0, 0
    # Dummy read to skip header data
    stream.read(12)
    if stream.read(4) == b'IHDR':
        x, y = unpack('!LL', stream.read(8))
    else:
        raise ValueError('could not determine PNG size')
    return 'PNG', x, y


def _gifsize(stream):
    '''Subroutine gets the size of the specified GIF
    Default behavior for GIFs is to return the "screen" size'''
    # Skip over the identifying string, since we already know this is a GIF
    type = stream.read(6)
    buf = stream.read(5)
    if len(buf) != 5:
        raise ValueError('Invalid/Corrupted GIF (bad header)')
    (sw, sh, x) = unpack('<HHB', buf)
    return 'GIF', sw, sh


def _ppmsize(stream):
    '''gets data on the PPM/PGM/PBM family.'''
    MIME_MAP = {'P1': 'PBM', 'P2': 'PGM', 'P3': 'PPM',
                'P4': 'BPM', 'P5': 'PGM', 'P6': 'PPM'}
    mime, x, y = '', 0, 0
    header = stream.read(1024)
    # PPM file of some sort
    re.sub(rb'^\#.*', '', header, re.M)
    m = re.match(rb'^(P[1-6])\s+(\d+)\s+(\d+)', header, re.S)
    if m:
        (n, x, y) = m.group(1, 2, 3)
        if n == b'P7':
            mime = b'XV'
            m = re.match(rb'IMGINFO:(\d+)x(\d+)', header, re.S)
            if m:
                (x, y) = m.group(1, 2)
        elif n in MIME_MAP:
            mime = MIME_MAP[n]
        else:
            raise ValueError('Invalid/Corrupted PPM (bad header)')
        return mime, int(x), int(y)
    else:
        raise ValueError('Unable to determine size of PPM/PGM/PBM data')


def _xbmsize(stream):
    '''size a XBM image'''
    x, y = 0, 0
    header = stream.read(1024)
    m = re.match(rb'^\#define\s*\S*\s*(\d+)\s*\n\#define\s*\S*\s*(\d+)', header, re.S | re.I)
    if m:
        x, y = m.group(1, 2)
        return 'XBM', int(x), int(y)
    else:
        raise ValueError('could not determine XBM size')


def _xpmsize(stream):
    '''Size an XPM file by looking for the "X Y N W" line, where X and Y are
       dimensions, N is the total number of colors defined, and W is the width of
       a color in the ASCII representation, in characters. We only care about X & Y.'''
    x, y = 0, 0
    while True:
        line = stream.readline()
        if line == b'':
            break
        m = re.compile(rb'\s*(\d+)\s+(\d+)(\s+\d+\s+\d+){1,2}\s*', re.M).match(line, 1)
        if m:
            x, y = list(map(int, m.group(1, 2)))
            break
    else:
        raise ValueError('could not determine XPM size')
    return 'XPM', x, y


def _tiffsize(stream):
    '''size a TIFF image'''
    x, y = 0, 0

    be = '!'  # Default to big-endian; I like it better
    if stream.read(4) == b'II\x2a\x00':  # little-endian
        be = '<'

    # Set up an association between data types and their corresponding
    # pack/unpack specification.  Don't take any special pains to deal with
    # signed numbers; treat them as unsigned because none of the image
    # dimensions should ever be negative.  (I hope.)
    packspec = (None,  # nothing (shouldn't happen)
                'Bxxx',  # BYTE (8-bit unsigned integer)
                None,  # ASCII
                be + 'Hxx',  # SHORT (16-bit unsigned integer)
                be + 'L',  # LONG (32-bit unsigned integer)
                None,  # RATIONAL
                'bxxx',  # SBYTE (8-bit signed integer)
                None,  # UNDEFINED
                be + 'Hxx',  # SSHORT (16-bit unsigned integer)
                be + 'L'  # SLONG (32-bit unsigned integer)
                )

    offset = unpack(be + 'L', stream.read(4))[0]  # Get offset to IFD

    stream.seek(offset)
    ifd = stream.read(2)  # Get number of directory entries
    num_dirent = unpack(be + 'H', ifd)[0]  # Make it useful
    num_dirent = offset + (num_dirent * 12)  # Calc. maximum offset of IFD

    # Do all the work
    ifd = ''
    tag = 0
    type = 0
    while x == 0 or y == 0:
        ifd = stream.read(12)  # Get first directory entry
        if ifd == "" or stream.tell() > num_dirent:
            break
        tag = unpack(be + 'H', ifd[:2])[0]  # ...and decode its tag
        type = unpack(be + 'H', ifd[2:2 + 2])[0]  # ...and the data type
        # Check the type for sanity.
        if type > len(packspec) or packspec[type] is None:
            continue
        if tag == 0x0100:  # ImageWidth (x)
            # Decode the value
            x = unpack(packspec[type], ifd[8:4 + 8])[0]
        elif tag == 0x0101:  # ImageLength (y)
            # Decode the value
            y = unpack(packspec[type], ifd[8:4 + 8])[0]

    # Decide if we were successful or not

    if x == 0 or y == 0:
        error = '%s%s%s ' % ('ImageWidth ' if x == 0 else '',
                             ' and ' if x + y > 0 else '',
                             'ImageHeigth ' if y == 0 else '')
        error += 'tag(s) could not be found'
        raise ValueError(error)

    return 'TIFF', x, y


def _psdsize(stream):
    '''determine the size of a PhotoShop save-file (*.PSD)'''
    x, y = 0, 0
    stream.read(14)
    (y, x) = unpack('!LL', stream.read(8))
    if x == 0 or y == 0:
        raise ValueError('could not determine PSD size')
    return 'PSD', x, y


# pcdsize :
# Kodak photo-CDs are weird. Don't ask me why, you really don't want details.
PCD_MAP = {'base/16': (192, 128),
           'base/4': (384, 256),
           'base': (768, 512),
           'base4': (1536, 1024),
           'base16': (3072, 2048),
           'base64': (6144, 4096)}
# Default scale for PCD images
PCD_SCALE = 'base'


def _pcdsize(stream):
    '''determine the size of a file in Kodak photo-CDs'''
    x, y = 0, 0
    buff = stream.read(0xf00)
    if buff[0x800:3 + 0x800] != 'PCD':
        raise ValueError('Invalid/Corrupted PCD (bad header)')
    orient = ord(buff[0x0e02:1 + 0x0e02]) & 1  # Clear down to one bit
    if orient:
        (x, y) = PCD_MAP[PCD_SCALE]
    else:
        (y, x) = PCD_MAP[PCD_SCALE]
    return 'PCD', x, y


def _bin(n, count=32):
    '''returns the binary of integer n, using count number of digits'''
    return ''.join([str((n >> i) & 1) for i in range(count - 1, -1, -1)])


def _swfsize(stream):
    '''determine size of ShockWave/Flash files.'''
    x, y = 0, 0
    header = stream.read(33)
    bs = ''.join([_bin(c, 8) for c in unpack('B' * 17, header[8:17 + 8])])
    bits = int(bs[:5], 2)
    x = int(bs[(5 + bits):bits + (5 + bits)], 2) / 20
    y = int(bs[(5 + bits * 3):bits + (5 + bits * 3)], 2) / 20
    if x == 0 or y == 0:
        raise ValueError('could not determine SWF size')
    return 'SWF', x, y


def _swfmxsize(stream):
    '''determine size of Compressed ShockWave/Flash files.'''
    import zlib
    x, y = 0, 0
    stream.read(8)
    z = zlib.decompressobj()
    header = z.decompress(stream.read(1024))
    del z
    bs = ''.join([_bin(c, 8) for c in unpack('B' * 9, header[:9])])
    bits = int(bs[:5], 2)
    x = int(bs[(5 + bits):bits + (5 + bits)], 2) / 20
    y = int(bs[(5 + bits * 3):bits + (5 + bits * 3)], 2) / 20
    if x == 0 or y == 0:
        raise ValueError('could not determine CWS size')
    return 'CWS', x, y


def _mngsize(stream):
    '''gets the width and height (in pixels) of an MNG file.
       Basically a copy of pngsize.'''
    x, y = 0, 0
    stream.read(12)
    if stream.read(4) == b'MHDR':
        # MHDR = Image Header
        x, y = unpack('!LL', stream.read(8))
    else:
        raise ValueError('Invalid/Corrupted MNG (bad header)')
    return 'MNG', x, y


def _rgbsize(stream):
    '''gets the width and height (in pixels) of a SGI file.'''
    x, y = 0, 0
    stream.read(6)
    x, y = unpack('!HH', stream.read(4))
    if x == 0 or y == 0:
        raise ValueError('could not determine SGI size')
    return 'RGB', x, y


def _rassize(stream):
    '''gets the width and height (in pixels) of a Sun raster file.'''
    x, y = 0, 0
    stream.read(4)
    x, y = unpack('!LL', stream.read(8))
    if x == 0 or y == 0:
        raise ValueError('could not determine Sun raster size')
    return 'RAS', x, y


def _pcxsize(stream):
    '''gets the width and height (in pixels) of a ZSoft PCX File.'''
    x, y = 0, 0
    stream.read(4)
    (xmin, ymin, xmax, ymax) = unpack('<HHHH', stream.read(8))
    x, y = xmax - xmin + 1, ymax - ymin + 1
    if x == 0 or y == 0:
        raise ValueError('could not determine ZSoft PCX size')
    return 'PCX', x, y


def _svgsize(stream):
    '''gets the width and height (in pixels) of a SVG File.'''
    # TODO add support for other units like: "em", "ex", "px", "in", "cm", "mm", "pt", "pc", "%"
    header = stream.read(1024)
    m = re.search(rb'''width\s*=\s*(["\'])
            (\d*\.?\d+) # px maybe a floating-point
            (?:px)?  # unit maybe omitted too
            \1
            '''
                  , header, re.I | re.X)
    n = re.search(rb'''height\s*=\s*(["\'])
            (\d*\.?\d+) # px maybe a floating-point
            (?:px)?  # unit maybe omitted too
            \1
            '''
                  , header, re.I | re.X)
    if m and n:
        x = int(m.group(2).split(b'.')[0])
        y = int(n.group(2).split(b'.')[0])
        return 'SVG', x, y
    raise ValueError('Unable to determine size of SVG data')


# type_map used in function type_map_match
TYPE_MAP = {re.compile(rb'^\xFF\xD8'): ('JPEG', _jpegsize),
            re.compile(rb'^BM'): ('BMP', _bmpsize),
            re.compile(rb'^\x89PNG\x0d\x0a\x1a\x0a'): ('PNG', _pngsize),
            re.compile(rb'^GIF8[7,9]a'): ('GIF', _gifsize),
            re.compile(rb'^P[1-7]'): ('PPM', _ppmsize),
            re.compile(rb'^\#define\s+\S+\s+\d+'): ('XBM', _xbmsize),
            re.compile(rb'^\/\* XPM \*\/'): ('XPM', _xpmsize),
            re.compile(rb'^MM\x00\x2a'): ('TIFF', _tiffsize),
            re.compile(rb'^II\x2a\x00'): ('TIFF', _tiffsize),
            re.compile(rb'^8BPS'): ('PSD', _psdsize),
            re.compile(rb'^PCD_OPA'): ('PCD', _pcdsize),
            re.compile(rb'^FWS'): ('SWF', _swfsize),
            re.compile(rb'^CWS'): ('SWF', _swfmxsize),
            re.compile(rb'^\x8aMNG\x0d\x0a\x1a\x0a'): ('MNG', _mngsize),
            re.compile(rb'^\x01\xDA[\x01\x00]'): ('RGB', _rgbsize),
            re.compile(rb'^\x59\xA6\x6A\x95'): ('RAS', _rassize),
            re.compile(rb'^\x0A.\x01'): ('PCX', _pcxsize),
            re.compile(rb'<svg\s'): ('SVG', _svgsize)}


def _type_match(data):
    '''type_map_match to get MIME-TYPE and callback function'''
    for rx in TYPE_MAP:
        if rx.search(data):
            return TYPE_MAP[rx]
    else:
        # fail back to PIL
        with Image.open(io.BytesIO(data)) as im:
            return im.format, lambda d: (im.format, im.width, im.height)


def what(filename):
    '''Recognize image format from file header'''
    with open(filename, 'rb') as stream:
        data = stream.read(512)
        stream.seek(0, 0)
        mime, callback = _type_match(data)
        return mime


def size(filename):
    '''size image format'''
    with open(filename, 'rb') as stream:
        data = stream.read()
        stream.seek(0, 0)
        mime, callback = _type_match(data)
        mime, x, y = callback(stream)
        return mime, x, y


def frombytes(data):
    if not data:
        return '', 0, 0
    '''size image from string'''
    mime, callback = _type_match(data)
    mime, x, y = callback(io.BytesIO(data))
    return mime, x, y
