#!/usr/bin/env bash
# Guest-only base setup. Does not start applications or touch databases.
set -euo pipefail
umask 077
APPLY=0
ROLE=''
PACKAGE_VERSION=''
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
while (($#)); do
  case "$1" in
    --check) APPLY=0; shift;;
    --apply) APPLY=1; shift;;
    --role) (($#>=2)) || die 'Missing role'; ROLE=$2; shift 2;;
    --package-version) (($#>=2)) || die 'Missing package version'; PACKAGE_VERSION=$2; shift 2;;
    -h|--help) printf 'Usage: sudo bash install-jdk21.sh --check|--apply --role java-test-01|java-prod-01|java-prod-02|java-prod-03|publish-service [--package-version VERSION]\n'; exit 0;;
    *) die 'Unknown argument';;
  esac
done
[[ $(id -u) == 0 && ! -d /etc/pve ]] || die 'Run as root on assigned guest; PVE host refused'
case "$ROLE" in java-test-01|java-prod-01|java-prod-02|java-prod-03|publish-service) ;; *) die 'Unapproved role';; esac
[[ $(hostname -s) == "$ROLE" ]] || die 'Hostname does not match assigned role'
# shellcheck disable=SC1091
. /etc/os-release
[[ ${ID:-} == debian && ${VERSION_ID:-} == 13 && $(dpkg --print-architecture) == amd64 ]] || die 'This base recipe supports Debian 13 amd64 only'
if (( APPLY )); then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  if [[ -n "$PACKAGE_VERSION" ]]; then
    [[ "$PACKAGE_VERSION" =~ ^21[.][A-Za-z0-9.+:~_-]+$ ]] || die 'Expected explicit OpenJDK21 version'
    apt-get install --yes --no-install-recommends "openjdk-21-jdk-headless=$PACKAGE_VERSION" python3 python3-yaml ca-certificates fonts-dejavu-core fontconfig libharfbuzz0b
  else
    apt-get install --yes --no-install-recommends openjdk-21-jdk-headless python3 python3-yaml ca-certificates fonts-dejavu-core fontconfig libharfbuzz0b
  fi
fi
JAVA=/usr/lib/jvm/java-21-openjdk-amd64/bin/java
[[ -x "$JAVA" ]] || die 'Java21 is not installed; apply is required'
DELL_JAVA_VERSION_OUT=$("$JAVA" -version 2>&1)
[[ "$DELL_JAVA_VERSION_OUT" == *'version "21.'* ]] || die 'Java version is not 21'
if (( APPLY )); then
  if [[ "$ROLE" != publish-service ]]; then
    getent group finger >/dev/null || groupadd --system finger
    if ! id finger >/dev/null 2>&1; then useradd --system --gid finger --home-dir /var/lib/finger --no-create-home --shell /usr/sbin/nologin finger; fi
    [[ $(id -u finger) != 0 ]] || die 'Runtime account must be non-root'
    install -d -m 755 /opt/finger /opt/finger/releases
    install -d -o root -g finger -m 750 /var/lib/finger /var/log/finger
    for service in finger-gateway-mobile finger-auth finger-service-system finger-service-coms finger-bff-system; do
      install -d -o finger -g finger -m 700 "/var/lib/finger/$service" "/var/log/finger/$service"
    done
    install -d -o finger -g finger -m 700 /var/lib/finger/finger-service-coms/uploads
  else
    install -d -m 755 /opt/finger
  fi
  if [[ -e /opt/finger/java && ! -L /opt/finger/java ]]; then die 'Refusing to replace an existing real Java directory'; fi
  ln -sfnT /usr/lib/jvm/java-21-openjdk-amd64 /opt/finger/java
fi
[[ -x /opt/finger/java/bin/java ]] || die 'Stable system-wide Java path is missing'
[[ $(dpkg-query -W -f='${db:Status-Status}' libharfbuzz0b 2>/dev/null || true) == installed ]] || die 'libharfbuzz0b is required for headless captcha font rendering'

python3 - "$ROLE" <<'PY'
import json,subprocess,sys
p=subprocess.run(['dpkg-query','-W','-f=${Version}','openjdk-21-jdk-headless'],capture_output=True,text=True,check=True)
print(json.dumps({'status':'base-ready-needs-runtime-verification','role':sys.argv[1],'jdk_package':'openjdk-21-jdk-headless','jdk_version':p.stdout,'java_path':'/opt/finger/java/bin/java','captcha_font_native_package':'libharfbuzz0b','captcha_font_native_package_installed':True,'applications_started':False,'sql_executed':False}))
PY
