#!/usr/bin/env bash
# Run once as root on the existing Alibaba Cloud server.
set -euo pipefail
BASE=/srv/portfolio
ACCOUNT=portfolio-deploy
CONFIG=/etc/nginx/conf.d/wangliyan.conf
OLD_ROOT=/usr/share/nginx/wangliyan
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PUBLIC_KEY=${1:?Usage: bash setup-server.sh /path/to/deployment-key.pub}

[[ $(id -u) == 0 ]] || { echo 'Run as root.' >&2; exit 1; }
[[ -f "$CONFIG" && -s "$OLD_ROOT/index.html" && -f "$PUBLIC_KEY" ]]
[[ -f "$SCRIPT_DIR/release.py" ]]
if [[ -e "$BASE" || -L "$BASE" ]]; then
  echo "$BASE already exists; do not rerun setup. Inspect the previous setup first." >&2
  exit 1
fi
if id "$ACCOUNT" >/dev/null 2>&1; then
  echo "$ACCOUNT already exists; inspect it before setup." >&2
  exit 1
fi
python3 - "$CONFIG" "$PUBLIC_KEY" <<'PY'
import pathlib, re, sys
config = pathlib.Path(sys.argv[1]).read_text()
assert len(re.findall(r'\broot\s+/usr/share/nginx/wangliyan\s*;', config)) == 1, 'Unexpected Nginx configuration'
key = pathlib.Path(sys.argv[2]).read_text().strip()
assert '\n' not in key and re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+(?: [^\r\n]*)?', key), 'Expected one Ed25519 public key'
PY
nginx -t
ssh-keygen -lf "$PUBLIC_KEY" >/dev/null
command -v curl >/dev/null
command -v sshd >/dev/null
command -v flock >/dev/null

# Permanent SELinux mapping, when enabled; deployment creates files in this tree.
if command -v selinuxenabled >/dev/null && selinuxenabled; then
  if ! command -v semanage >/dev/null; then
    dnf install -y policycoreutils-python-utils
  fi
  semanage fcontext -a -t httpd_sys_content_t '/srv/portfolio(/.*)?' ||
    semanage fcontext -m -t httpd_sys_content_t '/srv/portfolio(/.*)?'
fi

# An unusable password hash prevents password login without an account-lock
# marker that can also block public-key login on servers with UsePAM=no.
useradd --create-home --shell /bin/bash --password '*' "$ACCOUNT"
install -d -m 755 -o "$ACCOUNT" -g "$ACCOUNT" "$BASE" "$BASE/releases"
INITIAL="manual-$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 755 "$BASE/releases/$INITIAL"
cp -a "$OLD_ROOT/." "$BASE/releases/$INITIAL/"
find "$BASE/releases/$INITIAL" -type d -exec chmod 755 {} +
find "$BASE/releases/$INITIAL" -type f -exec chmod 644 {} +
python3 - "$BASE/releases/$INITIAL" "$INITIAL" <<'PY'
import datetime, json, pathlib, sys
record = {'release_id': sys.argv[2], 'commit': 'manual-import',
          'released_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
(pathlib.Path(sys.argv[1]) / 'release.json').write_text(json.dumps(record) + '\n')
PY
ln -s "$BASE/releases/$INITIAL" "$BASE/current"
chown -R "$ACCOUNT:$ACCOUNT" "$BASE"
if command -v selinuxenabled >/dev/null && selinuxenabled; then
  restorecon -RF "$BASE"
fi

# The key can invoke this root-owned gateway only; it has no root/sudo access.
install -m 755 -o root -g root "$SCRIPT_DIR/release.py" /usr/local/bin/portfolio-release
HOME_DIR=$(getent passwd "$ACCOUNT" | cut -d: -f6)
chown root:root "$HOME_DIR"
chmod 755 "$HOME_DIR"
install -d -m 755 -o root -g root "$HOME_DIR/.ssh"
printf 'restrict,command="/usr/local/bin/portfolio-release" %s\n' "$(cat "$PUBLIC_KEY")" > "$HOME_DIR/.ssh/authorized_keys"
chown root:root "$HOME_DIR/.ssh/authorized_keys"
chmod 644 "$HOME_DIR/.ssh/authorized_keys"
if command -v restorecon >/dev/null; then restorecon -RF "$HOME_DIR/.ssh"; fi
sshd -t

BACKUP="$CONFIG.before-oneclick-$(date -u +%Y%m%dT%H%M%SZ).bak"
cp -a "$CONFIG" "$BACKUP"
python3 - "$CONFIG" <<'PY'
import pathlib, re, sys
path = pathlib.Path(sys.argv[1])
content, count = re.subn(r'\broot\s+/usr/share/nginx/wangliyan\s*;', 'root /srv/portfolio/current;', path.read_text())
assert count == 1
path.write_text(content)
PY
if ! nginx -t || ! systemctl reload nginx; then
  cp -a "$BACKUP" "$CONFIG"
  nginx -t && systemctl reload nginx
  echo 'Setup failed; restored Nginx configuration.' >&2
  exit 1
fi
if ! curl --noproxy '*' --fail --silent --show-error --max-time 20 \
  --resolve wangliyan.wang:443:127.0.0.1 https://wangliyan.wang/release.json; then
  cp -a "$BACKUP" "$CONFIG"
  nginx -t && systemctl reload nginx
  echo 'Initial check failed; restored Nginx configuration.' >&2
  exit 1
fi
printf '\nSetup complete. Previous files remain in %s. Nginx backup: %s\n' "$OLD_ROOT" "$BACKUP"
echo 'Known-hosts value (public; copy the next line into DEPLOY_KNOWN_HOSTS):'
awk '{print "47.111.109.82 " $1 " " $2}' /etc/ssh/ssh_host_ed25519_key.pub
