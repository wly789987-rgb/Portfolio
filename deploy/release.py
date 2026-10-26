#!/usr/bin/python3
"""Forced SSH command for atomic static-site releases; runs without sudo."""
import datetime as dt
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import uuid

BASE = Path('/srv/portfolio')
DOMAIN = 'wangliyan.wang'
REQUIRED = ('index.html', 'app.js', 'style.css')
MAX_TOTAL = 1024 * 1024 * 1024


def unpack(stream, destination):
    """Extract only regular site files, never links or archive metadata paths."""
    total, seen = 0, set()
    with tarfile.open(fileobj=stream, mode='r|gz') as archive:
        for member in archive:
            name = member.name.rstrip('/')
            path = PurePosixPath(name)
            if (not name or '\\' in name or path.is_absolute()
                    or any(p in ('', '.', '..') for p in name.split('/'))
                    or (name not in REQUIRED and path.parts[0] != 'assets')):
                raise ValueError('Unexpected archive path: ' + name)
            if name in seen or not (member.isfile() or member.isdir()):
                raise ValueError('Duplicate, link, or special file: ' + name)
            seen.add(name)
            target = destination.joinpath(*path.parts)
            if member.isdir():
                if path.parts[0] != 'assets':
                    raise ValueError('Required entry must be a file')
                target.mkdir(parents=True, exist_ok=True, mode=0o755)
                continue
            if member.size < 0 or member.size > 256 * 1024 * 1024:
                raise ValueError('File exceeds size limit')
            total += member.size
            if total > MAX_TOTAL:
                raise ValueError('Release exceeds size limit')
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            with archive.extractfile(member) as source, target.open('xb') as out:
                shutil.copyfileobj(source, out)
            target.chmod(0o644)
    for name in REQUIRED:
        if not (destination / name).is_file() or not (destination / name).stat().st_size:
            raise ValueError('Missing or empty file: ' + name)
    if not (destination / 'assets').is_dir():
        raise ValueError('Missing assets directory')


def release_target(base, link):
    entry = base / link
    if not entry.is_symlink():
        raise ValueError('Expected a release symlink: ' + link)
    resolved = entry.resolve(strict=True)
    if resolved.parent != (base / 'releases').resolve() or not resolved.is_dir():
        raise ValueError('Release target is outside releases directory')
    return resolved


def point(base, name, target):
    if target.resolve().parent != (base / 'releases').resolve():
        raise ValueError('Invalid release target')
    temporary = base / ('.' + name + '-' + uuid.uuid4().hex)
    try:
        temporary.symlink_to(target, target_is_directory=True)
        os.replace(temporary, base / name)
    finally:
        temporary.unlink(missing_ok=True)


def check_live(expected, base=BASE):
    url = 'https://' + DOMAIN
    common = ['curl', '--fail', '--silent', '--show-error', '--noproxy', '*',
              '--connect-timeout', '5', '--max-time', '20',
              '--resolve', DOMAIN + ':443:127.0.0.1']
    result = subprocess.run(common + [url + '/release.json'], check=True,
                            capture_output=True, text=True)
    actual = json.loads(result.stdout)
    if actual.get('release_id') != expected['release_id']:
        raise ValueError('Nginx did not serve the selected release')
    for path in ('/', '/app.js', '/style.css'):
        subprocess.run(common + ['--head', '--output', os.devnull, url + path],
                       check=True, capture_output=True)


def activate(base, target, health=check_live):
    old = release_target(base, 'current')
    record = json.loads((target / 'release.json').read_text(encoding='utf-8'))
    point(base, 'current', target)
    try:
        health(record, base)
    except BaseException:
        point(base, 'current', old)
        raise
    if target != old:
        point(base, 'previous', old)
    return record


def deploy(base, revision, stream, health=check_live):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Deployment requires a full Git commit SHA')
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    release_id = stamp + '-' + revision[:12] + '-' + uuid.uuid4().hex[:6]
    staging = base / ('incoming-' + uuid.uuid4().hex)
    staging.mkdir(mode=0o755)
    try:
        unpack(stream, staging)
        record = {'release_id': release_id, 'commit': revision,
                  'released_at': dt.datetime.now(dt.timezone.utc).isoformat()}
        (staging / 'release.json').write_text(json.dumps(record) + '\n', encoding='utf-8')
        (staging / 'release.json').chmod(0o644)
        target = base / 'releases' / release_id
        staging.rename(target)
        return activate(base, target, health)
    finally:
        # staging is always an internally generated child, never archive input.
        if staging.exists():
            shutil.rmtree(staging)


def rollback(base, revision='previous', health=check_live):
    if revision == 'previous':
        target = release_target(base, 'previous')
    elif re.fullmatch(r'[0-9a-f]{40}', revision):
        matches = []
        for entry in (base / 'releases').iterdir():
            if entry.is_dir() and not entry.is_symlink():
                record = entry / 'release.json'
                if record.is_file() and json.loads(record.read_text()).get('commit') == revision:
                    matches.append(entry)
        if not matches:
            raise ValueError('This commit has not been deployed on this server')
        target = sorted(matches)[-1]
    else:
        raise ValueError('Rollback requires previous or a full commit SHA')
    return activate(base, target, health)


def main():
    import fcntl
    os.umask(0o022)
    command = shlex.split(os.environ.get('SSH_ORIGINAL_COMMAND', ''))
    if len(command) != 2 or command[0] not in ('deploy', 'rollback'):
        raise ValueError('Only deploy <SHA> and rollback <SHA|previous> are allowed')
    with (BASE / '.deploy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if command[0] == 'deploy':
            record = deploy(BASE, command[1], sys.stdin.buffer)
        else:
            record = rollback(BASE, command[1])
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Release failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
