"""Create and verify a complete local snapshot; no uploads or git operations."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, io, json, tarfile
ROOT=Path(__file__).resolve().parent.parent
DEST=ROOT/'archive';DEST.mkdir(exist_ok=True)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
base='inline_four_2l_cad_reference_v1_'+stamp
files=sorted(p for p in ROOT.rglob('*') if p.is_file() and DEST not in p.parents and '__pycache__' not in p.parts)
def digest(stream):
    h=hashlib.sha256()
    for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
records={}
for p in files:
    with p.open('rb') as stream:records['inline_four_cad/'+str(p.relative_to(ROOT))]={'bytes':p.stat().st_size,'sha256':digest(stream)}
manifest=json.dumps(dict(created_utc=stamp,excluded=['archive/ (output directory)','__pycache__/ (regenerable Python cache)'],files=records),indent=2).encode()+b'\n'
(DEST/(base+'.contents.json')).write_bytes(manifest)
archive=DEST/(base+'.tar.gz')
with tarfile.open(archive,'w:gz',compresslevel=1) as tf:
    info=tarfile.TarInfo('ARCHIVE_CONTENTS.json');info.size=len(manifest);tf.addfile(info,io.BytesIO(manifest))
    for p in files:tf.add(p,arcname='inline_four_cad/'+str(p.relative_to(ROOT)),recursive=False)
verified=0
with tarfile.open(archive,'r:gz') as tf:
    for member in tf:
        if member.name=='ARCHIVE_CONTENTS.json':
            assert tf.extractfile(member).read()==manifest
            continue
        expected=records[member.name]
        assert member.size==expected['bytes']
        assert digest(tf.extractfile(member))==expected['sha256'],member.name
        verified+=1
assert verified==len(records)
with archive.open('rb') as stream:checksum=digest(stream)
(DEST/(base+'.sha256')).write_text(checksum+'  '+archive.name+'\n')
(DEST/(base+'.verification.json')).write_text(json.dumps(dict(passed=True,archive=archive.name,bytes=archive.stat().st_size,verified_files=verified,sha256=checksum),indent=2)+'\n')
print(json.dumps(dict(archive=str(archive),bytes=archive.stat().st_size,verified_files=verified)),flush=True)
