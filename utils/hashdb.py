import hashlib

def readdb(fn):
    db = {}
    try:
        with open(fn) as fh:
            for entry in fh:
                # Skip empty lines
                if len(entry) <= 1:
                    continue
                hash, name = entry.split(None, 1)
                db[hash] = name[:-1]
    except IOError:
        pass
    return db

def writedb(fn, db):
    with open(fn, 'w') as fh:
        for hash, name in db.items():
            fh.write(hash + " " + name + "\n")

def get_hash(fn):
    hash = hashlib.sha256()
    with open(fn) as fh:
        for chunk in iter((lambda:fh.read(16*256)),''):
            hash.update(chunk)
    return hash.hexdigest()

