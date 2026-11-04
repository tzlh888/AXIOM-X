"""Verify sealed public artifacts and saved-result reproduction; never generate models."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def main():
    manifest=ROOT/'SHA256SUMS'
    for line in manifest.read_text().splitlines():
        digest,name=line.split('  ',1)
        path=ROOT/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise SystemExit('Manifest mismatch: '+name)
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    for args in [
        ['-m','research_v3.controlled_development','verify'],
        ['-m','research_v4.v4_experiment','verify'],
        ['-m','research_v5.prepare_evidence','verify'],
        ['-m','pytest','-q','-ra','-p','no:cacheprovider'],
    ]:
        completed=subprocess.run([sys.executable,*args],cwd=ROOT,env=env,capture_output=True,text=True)
        print(completed.stdout,end='')
        if completed.stderr:print(completed.stderr,file=sys.stderr,end='')
        if completed.returncode:raise SystemExit(completed.returncode)
        if 'verify' in args and 'FAILED' in completed.stdout:
            raise SystemExit('Research verifier reported FAILED')
    print('PASS: sealed public files and deterministic saved-output verification; no model generation.')


if __name__=='__main__':main()
