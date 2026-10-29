"""Local SQLite records for synthetic cases and demonstration officer decisions."""
from pathlib import Path
import json, sqlite3, uuid
from contextlib import contextmanager
from datetime import datetime, timezone

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')

class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS cases
                (id TEXT PRIMARY KEY, owner TEXT NOT NULL, created TEXT NOT NULL, assessment TEXT NOT NULL,
                 generation TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending review')''')
            db.execute('''CREATE TABLE IF NOT EXISTS reviews
                (id INTEGER PRIMARY KEY, case_id TEXT NOT NULL, created TEXT NOT NULL,
                 decision TEXT NOT NULL, note TEXT NOT NULL, exception INTEGER NOT NULL)''')
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()
    def create(self,owner,assessment,generation):
        cid=uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO cases(id,owner,created,assessment,generation) VALUES (?,?,?,?,?)',
                       (cid,owner,now(),json.dumps(assessment),json.dumps(generation)))
        return cid
    def get(self,cid):
        with self.connect() as db:
            row=db.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone()
            if row is None:return None
            result=dict(row);result['assessment']=json.loads(row['assessment']);result['generation']=json.loads(row['generation'])
            result['reviews']=[dict(r) for r in db.execute('SELECT * FROM reviews WHERE case_id=? ORDER BY id',(cid,))]
            return result
    def list_cases(self,owner=None):
        with self.connect() as db:
            if owner is None:rows=db.execute('SELECT id,created,status FROM cases ORDER BY created DESC LIMIT 100').fetchall()
            else:rows=db.execute('SELECT id,created,status FROM cases WHERE owner=? ORDER BY created DESC LIMIT 100',(owner,)).fetchall()
            return [dict(r) for r in rows]
    def review(self,cid,decision,note,exception,policy_fingerprint):
        if decision not in ('Approved','Rejected','More information required'):raise ValueError('Choose a valid review decision.')
        if not 20<=len(note.strip())<=2000:raise ValueError('Write a review reason of 20 to 2,000 characters.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM cases WHERE id=?',(cid,)).fetchone()
            if row is None:raise ValueError('Case not found.')
            if row['status']!='Pending review':raise ValueError('This case already has a reviewer decision. Submit a new assessment for corrected inputs.')
            a=json.loads(row['assessment'])
            if a['policy_fingerprint']!=policy_fingerprint:raise ValueError('The policy changed. Reassess the case before signing off.')
            if decision=='Approved':
                if not a['scope_supported']:raise ValueError('Out-of-scope applications cannot be approved under this policy.')
                if a['flags'] and not exception:raise ValueError('Approval with review flags requires explicit exception acknowledgement.')
            db.execute('UPDATE cases SET status=? WHERE id=?',(decision,cid))
            db.execute('INSERT INTO reviews(case_id,created,decision,note,exception) VALUES (?,?,?,?,?)',(cid,now(),decision,note.strip(),int(exception)))
