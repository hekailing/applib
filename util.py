# coding: utf8
import logging
import hashlib
import random

import const


def gen_sha256(obj):
    '''
    Generate sha256 of an object.  The object can only be a string
    '''
    if getattr(obj, '__hash__'):
        sha256obj = hashlib.sha256()
        sha256obj.update(obj)
        return sha256obj.hexdigest()
    else:
        return None


def add_slash(path):
    if not path.endswith('/'):
        path += '/'
    return path


def to_unicode(data, encoding='utf-8'):
    import collections
    _encoding = encoding

    def _convert(data):
        if isinstance(data, unicode):
            return data
        elif isinstance(data, str):
            return unicode(data, _encoding)
        elif isinstance(data, collections.Mapping):
            return dict(map(_convert, data.iteritems()))
        elif isinstance(data, collections.Iterable):
            return type(data)(map(_convert, data))
        else:
            return data
    return _convert(data)


def is_float(datastr):
    try:
        float(datastr)
    except ValueError:
        return False
    return True


def get_picture_format(fh):
    '''
    Get picture file format according to file header
    '''
    import binascii
    saved_fp = fh.tell()
    hexheader = binascii.b2a_hex(fh.read(32)).upper()
    fh.seek(saved_fp)
    if hexheader.startswith('FFD8FF'):
        return 'jpg'
    elif hexheader.startswith('89504E47'):
        return 'png'
    elif hexheader.startswith('47494638'):
        return 'gif'
    elif hexheader.startswith('49492A00'):
        return 'tif'
    elif hexheader.startswith('424D'):
        return 'bmp'
    else:
        return ''


def gen_file_md5(file):
    '''Generate md5sum of a file.
    Each time read 8096 Bytes from the file, then update md5sum.
    '''
    def read_chunks(fh):
        saved_fp = fh.tell()
        chunk = fh.read(8096)
        while chunk:
            yield chunk
            chunk = fh.read(8096)
        else:
            fh.seek(saved_fp)
    md5obj = hashlib.md5()
    for chunk in read_chunks(file):
        md5obj.update(chunk)
    return md5obj.hexdigest()


def save_image(f, save_name):
    """Put file to cottom with key=save_name.
    Each time read 8096 Bytes from the tmpfile, then push to cottion.
    """
    from cotton import client
    cli = client.CottonClient(const.cotton['host'])
    bucket = cli.Bucket(const.cotton['bucket_id'], const.cotton['secret_key'])
    myfile = cli.File(bucket, save_name)
    try:
        f.seek(0)
        myfile.put(f.read())
        return True
    except client.ResponseError, e:
        logging.log('[Cotton Write Error](key:%s) %s' % (save_name, str(e)))
    return False


def generate_image_path(key):
    path = 'http://%s/buckets/%s/files/%s' % (const.cotton['host'],
                                              const.cotton['bucket_id'],
                                              key)
    return path


def gen_file_key(file):
    """Get file key for cotton.  Cal file md5 and get file_id from the
    prefix of file md5.  Call cotton.client.radix62encode() to generate
    file key for cotton.
    """
    from cotton import client
    file_id = int(gen_file_md5(file)[0:16], 16)/2 + 0x1fffffff
    return client.BaseFile.radix62encode(file_id)


def _gen_sig(message, encrt, pristr):
    if encrt == 'rsa':
        import rsa
        prikey = rsa.PrivateKey.load_pkcs1(pristr)
        return rsa.sign(message, prikey, 'SHA-1')
    return ''


def gen_signature(message, encrt='rsa'):
    """Read privary key from 'my.pem' and sign with the private key.
    """
    with open(const.keys['prikey'], 'r') as f:
        pristr = f.read()
    if pristr:
        signature = _gen_sig(message, encrt, pristr)
        if signature:
            import base64
            return base64.encodestring(signature)
    return ''


def _verify(message, signature, encrt, pubstr):
    if encrt == 'rsa':
        import rsa
        pubkey = rsa.PublicKey.load_pkcs1(pubstr)
        try:
            return rsa.verify(message, signature, pubkey)
        except rsa.VerificationError:
            return False
    return False


def verify(message, signature, pubfile, encrt='rsa'):
    """Read public key from pubfile and verify with the public key.
    If the pubfile is not existed, return False.
    """
    with open(pubfile, 'r') as f:
        pubstr = f.read()
    if pubstr:
        import base64
        signature = base64.decodestring(signature)
        return _verify(message, signature, encrt, pubstr)
    return False


def dict2str(d):
    items = ['%s: %s' % (str(item[0]), str(item[1])) for item in d.items()]
    items.sort()
    return ', '.join(items)
