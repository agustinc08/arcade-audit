#!/usr/bin/env python3
"""Per-test snapshot/restore with SHA-256 conflict guards; no historical restore."""
import argparse, hashlib, json, os, shutil, stat, tempfile, uuid
from datetime import datetime, timezone
from pathlib import Path
import sys

TOOLS = Path('/userdata/system/el_gordo_tools')
if str(TOOLS) not in sys.path: sys.path.insert(0, str(TOOLS))
from marker_ownership import MARKER, classify_marker, marker_lock, read_marker

RUNTIME = Path('/userdata/system/state/arcade_audit/runtime')
ALLOWED_EXACT = {Path('/userdata/system/batocera.conf'), Path('/userdata/system/state/boot_audit_once.json'),
                 Path('/userdata/roms/mame/gamelist.xml')}
ALLOWED_PREFIXES = (Path('/userdata/system/configs'), Path('/userdata/saves'), Path('/userdata/system/.local/share'), RUNTIME/'selftest-fixtures')
MAX_FILE = 20 * 1024 * 1024
MAX_TREE_BYTES = 50 * 1024 * 1024
MAX_TREE_ENTRIES = 5000

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()
def is_allowed(path):
    p=Path(os.path.realpath(path))
    # A gamelist is an exact, one-file runtime write target for its system.
    # Do not allow other content paths or recurse into a ROM directory.
    roms=Path('/userdata/roms')
    is_system_gamelist=(p.name=='gamelist.xml' and p.parent.parent==roms)
    return p in ALLOWED_EXACT or is_system_gamelist or any(p == root or root in p.parents for root in ALLOWED_PREFIXES)
def atomic_json(path,obj):
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.chmod(tmp,0o600); os.replace(tmp,path)
def state(path):
    if path.is_symlink(): raise RuntimeError('UNSUPPORTED_FILE_TYPE:'+str(path))
    if not path.exists(): return {'exists':False,'sha256':None}
    st=path.stat()
    if path.is_file():
        size=st.st_size
        if size > MAX_FILE: raise RuntimeError('FILE_TOO_LARGE:'+str(path))
        return {'exists':True,'type':'file','sha256':sha(path),'size':size,
                'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns}
    if not path.is_dir(): raise RuntimeError('UNSUPPORTED_FILE_TYPE:'+str(path))
    entries=[]; total=0
    for parent,dirs,files in os.walk(path,topdown=True,followlinks=False):
        base=Path(parent)
        for name in dirs:
            q=base/name
            if q.is_symlink(): raise RuntimeError('SYMLINK_IN_TREE:'+str(q))
            ds=q.stat(); entries.append({'path':q.relative_to(path).as_posix()+'/','type':'dir',
                    'mode':stat.S_IMODE(ds.st_mode),'uid':ds.st_uid,'gid':ds.st_gid,'mtime_ns':ds.st_mtime_ns})
        for name in files:
            q=base/name
            if q.is_symlink() or not q.is_file(): raise RuntimeError('NONREGULAR_FILE_IN_TREE:'+str(q))
            fs=q.stat(); total+=fs.st_size
            if fs.st_size>MAX_FILE: raise RuntimeError('FILE_TOO_LARGE:'+str(q))
            if total>MAX_TREE_BYTES: raise RuntimeError('TREE_TOO_LARGE:'+str(path))
            entries.append({'path':q.relative_to(path).as_posix(),'type':'file','size':fs.st_size,
                    'sha256':sha(q),'mode':stat.S_IMODE(fs.st_mode),'uid':fs.st_uid,
                    'gid':fs.st_gid,'mtime_ns':fs.st_mtime_ns})
            if len(entries)>MAX_TREE_ENTRIES: raise RuntimeError('TREE_TOO_MANY_ENTRIES:'+str(path))
    entries.sort(key=lambda x:x['path'])
    digest=hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'exists':True,'type':'dir','sha256':digest,'size':total,'entries':entries,
            'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns}

def remove_guarded(path):
    if path.is_symlink(): raise RuntimeError('RESTORE_CONFLICT_SYMLINK:'+str(path))
    if path.is_dir(): shutil.rmtree(path)
    elif path.exists(): path.unlink()

def apply_tree_metadata(root, meta):
    for item in sorted(meta.get('entries',[]),key=lambda x:x['path'].count('/'),reverse=True):
        p=root/item['path'].rstrip('/')
        if not p.exists(): raise RuntimeError('SNAPSHOT_TREE_ENTRY_MISSING:'+str(p))
        os.chown(p,item['uid'],item['gid']); os.chmod(p,item['mode'])
        os.utime(p,ns=(p.stat().st_atime_ns,item['mtime_ns']))
    os.chown(root,meta['uid'],meta['gid']); os.chmod(root,meta['mode'])
    os.utime(root,ns=(root.stat().st_atime_ns,meta['mtime_ns']))
def txdir(txid):
    if not txid or '/' in txid or txid in ('.','..'): raise RuntimeError('BAD_TRANSACTION_ID')
    p=RUNTIME/txid
    if p.parent != RUNTIME or not p.is_dir() or p.is_symlink(): raise RuntimeError('TRANSACTION_NOT_FOUND')
    return p
def begin(paths,label):
    RUNTIME.mkdir(parents=True,exist_ok=True,mode=0o700); os.chmod(RUNTIME,0o700)
    txid=datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:10]
    root=RUNTIME/txid; root.mkdir(mode=0o700)
    entries=[]
    try:
        for i,raw in enumerate(paths):
            p=Path(os.path.abspath(raw))
            if not is_allowed(p): raise RuntimeError('PATH_NOT_ALLOWLISTED:'+str(p))
            before=state(p); item={'path':str(p),'before':before,'snapshot':None,'mode':None,'uid':None,'gid':None}
            if before['exists']:
                st=p.stat(); item.update(mode=stat.S_IMODE(st.st_mode),uid=st.st_uid,gid=st.st_gid)
                snap=root/'snapshots'/f'{i:03d}'
                snap.parent.mkdir(mode=0o700,exist_ok=True)
                if before['type']=='dir':
                    shutil.copytree(p,snap,copy_function=shutil.copy2,symlinks=False)
                    apply_tree_metadata(snap,before)
                    if state(snap)!=before: raise RuntimeError('SNAPSHOT_TREE_HASH_MISMATCH:'+str(p))
                else:
                    shutil.copyfile(p,snap); os.chmod(snap,0o600)
                    if sha(snap)!=before['sha256']: raise RuntimeError('SNAPSHOT_HASH_MISMATCH:'+str(p))
                item['snapshot']=str(snap.relative_to(root))
            entries.append(item)
        obj={'schema_version':1,'transaction_id':txid,'label':label,'created_at':now(),'status':'PRE_STATE','entries':entries}
        atomic_json(root/'manifest.json',obj)
        return txid
    except Exception:
        shutil.rmtree(root,ignore_errors=True); raise
def seal(txid):
    root=txdir(txid); m=json.loads((root/'manifest.json').read_text())
    if m['status']!='PRE_STATE': raise RuntimeError('BAD_TRANSACTION_STATE:'+m['status'])
    for e in m['entries']: e['post']=state(Path(e['path']))
    m['sealed_at']=now(); m['status']='POST_STATE'; atomic_json(root/'manifest.json',m)
    print(json.dumps({'transaction_id':txid,'status':'POST_STATE','files':len(m['entries'])},indent=2)); return 0
def restore(txid):
    root=txdir(txid); m=json.loads((root/'manifest.json').read_text())
    if m['status']!='POST_STATE': raise RuntimeError('RESTORE_REQUIRES_SEALED_POST_STATE')
    if any(Path(e['path']) == MARKER for e in m['entries']):
        with marker_lock(): return _restore_locked(txid, root, m)
    return _restore_locked(txid, root, m)

def _restore_locked(txid, root, m):
    # Preflight every file before changing any file.
    actions=[]
    for e in m['entries']:
        p=Path(e['path']); current=state(p); before=e['before']; post=e['post']
        if not is_allowed(p): raise RuntimeError('RESTORE_PATH_NOT_ALLOWLISTED:'+str(p))
        if current==before: actions.append((e,'unchanged')); continue
        if p == MARKER:
            if before.get('exists') or current!=post:
                raise RuntimeError('FOREIGN_STATE_CONFLICT:'+str(p)+':FOREIGN_UNKNOWN')
            ownership=classify_marker(read_marker(p), txid)
            if ownership != 'OWNED_BY_CURRENT_TRANSACTION':
                raise RuntimeError('FOREIGN_STATE_CONFLICT:'+str(p)+':'+ownership)
        elif current!=post: raise RuntimeError('RESTORE_CONFLICT:'+str(p))
        actions.append((e,'restore'))
    for e,action in actions:
        if action=='unchanged': continue
        p=Path(e['path'])
        if e['before']['exists'] and e['before'].get('type')=='dir':
            snap=root/e['snapshot']; tmp=p.with_name(p.name+'.arcade-restore-'+m['transaction_id'])
            old=p.with_name(p.name+'.arcade-old-'+m['transaction_id'])
            if tmp.exists() or old.exists(): raise RuntimeError('RESTORE_TEMP_COLLISION:'+str(p))
            shutil.copytree(snap,tmp,copy_function=shutil.copy2,symlinks=False)
            apply_tree_metadata(tmp,e['before'])
            if state(tmp)!=e['before']: raise RuntimeError('RESTORE_STAGED_TREE_VERIFY_FAIL:'+str(p))
            os.replace(p,old)
            try:
                os.replace(tmp,p)
                if state(p)!=e['before']: raise RuntimeError('RESTORE_TREE_VERIFY_FAIL:'+str(p))
                shutil.rmtree(old)
            except Exception:
                if p.exists(): shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()
                os.replace(old,p)
                raise
        elif e['before']['exists']:
            snap=root/e['snapshot']; tmp=p.with_name(p.name+'.arcade-restore-'+m['transaction_id'])
            shutil.copyfile(snap,tmp); os.chmod(tmp,e['mode']); os.chown(tmp,e['uid'],e['gid'])
            os.utime(tmp,ns=(tmp.stat().st_atime_ns,e['before']['mtime_ns'])); os.replace(tmp,p)
        else:
            if p.exists() or p.is_symlink(): remove_guarded(p)
    verified=[]
    for e in m['entries']:
        if state(Path(e['path']))!=e['before']: raise RuntimeError('RESTORE_VERIFY_FAIL:'+e['path'])
        verified.append(e['path'])
    m['restored_at']=now(); m['status']='RESTORE_VERIFIED'; atomic_json(root/'manifest.json',m)
    print(json.dumps({'transaction_id':txid,'status':'RESTORE_VERIFIED','files':len(verified),'paths':verified},indent=2)); return 0
def self_test():
    base=RUNTIME/'selftest-fixtures'/uuid.uuid4().hex
    base.mkdir(parents=True,mode=0o700)
    target=base/'fixture.txt'; target.write_text('before\n')
    txids=[]
    try:
        original=sha(target); txid=begin([str(target)],'transaction-engine-self-test'); txids.append(txid)
        target.write_text('temporary test mutation\n'); during=sha(target)
        seal(txid)
        target.write_text('concurrent external change\n')
        try: restore(txid)
        except RuntimeError as e:
            if not str(e).startswith('RESTORE_CONFLICT:'): raise
        else: raise RuntimeError('SELF_TEST_CONFLICT_GUARD_FAIL')
        if target.read_text()!='concurrent external change\n': raise RuntimeError('SELF_TEST_CONFLICT_OVERWROTE_FILE')
        target.write_text('temporary test mutation\n')
        post=json.loads((RUNTIME/txid/'manifest.json').read_text())['entries'][0]['post']
        os.chmod(target,0o644); os.chown(target,0,0); os.utime(target,ns=(target.stat().st_atime_ns,post['mtime_ns']))
        restore(txid)
        if sha(target)!=original: raise RuntimeError('SELF_TEST_HASH_CHECK_FAIL')
        tree=base/'tree'; tree.mkdir(); (tree/'original.txt').write_text('tree before\n')
        tree_tx=begin([str(tree)],'transaction-engine-tree-self-test'); txids.append(tree_tx)
        (tree/'original.txt').write_text('tree mutation\n'); (tree/'new.txt').write_text('new file\n')
        seal(tree_tx); restore(tree_tx)
        if sorted(x.name for x in tree.iterdir())!=['original.txt'] or (tree/'original.txt').read_text()!='tree before\n': raise RuntimeError('SELF_TEST_TREE_RESTORE_FAIL')
        absent=base/'created-tree'; absent_tx=begin([str(absent)],'transaction-engine-created-tree-self-test'); txids.append(absent_tx)
        absent.mkdir(); (absent/'created.txt').write_text('temporary\n'); seal(absent_tx); restore(absent_tx)
        if absent.exists(): raise RuntimeError('SELF_TEST_ABSENT_TREE_NOT_REMOVED')
        print(json.dumps({'status':'TRANSACTION_ENGINE_SELF_TEST_PASS','pre_sha':original,'during_sha':during,'after_sha':sha(target),'conflict_guard':'PASS','existing_tree_restore':'PASS','created_tree_removal':'PASS','scope':'temporary fixture only'},indent=2)); return 0
    finally:
        for txid in txids:
            root=RUNTIME/txid
            if root.exists() and root.parent==RUNTIME: shutil.rmtree(root)
        if base.exists(): shutil.rmtree(base)
def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest='cmd',required=True)
    b=s.add_parser('begin'); b.add_argument('--label',required=True); b.add_argument('--path',action='append',required=True)
    q=s.add_parser('seal'); q.add_argument('--id',required=True)
    r=s.add_parser('restore'); r.add_argument('--id',required=True)
    s.add_parser('self-test')
    a=p.parse_args()
    try:
        if a.cmd=='begin':
            txid=begin(a.path,a.label)
            root=RUNTIME/txid; m=json.loads((root/'manifest.json').read_text())
            print(json.dumps({'transaction_id':txid,'status':m['status'],'files':len(m['entries'])},indent=2)); return 0
        if a.cmd=='seal': return seal(a.id)
        if a.cmd=='restore': return restore(a.id)
        return self_test()
    except Exception as e:
        print(type(e).__name__+': '+str(e)); return 2
if __name__=='__main__': raise SystemExit(main())
