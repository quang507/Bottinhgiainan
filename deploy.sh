#!/usr/bin/env bash
# Deploy lên VPS: chạy test trước, fail thì không đẩy. Dùng: bash deploy.sh "commit message"
set -e
cd "$(dirname "$0")"
VPS=root@103.126.162.93
python -X utf8 -m py_compile bot.py goi/engine.py goi/extract.py
python -X utf8 -m goi.engine | tail -1 | grep -q "KHỚP EXCEL"
[ -n "$SKIP_SMOKE" ] || python -X utf8 tests/smoke.py
ssh $VPS 'mkdir -p /opt/goi-bot/goi /opt/goi-bot/deploy'
scp -q bot.py requirements.txt .env $VPS:/opt/goi-bot/
scp -q goi/*.py goi/prices.json $VPS:/opt/goi-bot/goi/
scp -q deploy/goi-bot.service $VPS:/opt/goi-bot/deploy/
ssh $VPS 'systemctl restart goi-bot; sleep 4; systemctl is-active goi-bot; journalctl -u goi-bot -n 2 --no-pager -o cat'
if [ -n "$1" ]; then
  git add -A
  git -c user.name="Le Quang" -c user.email="explore@nhadat.company" commit -q -m "$1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q 2>&1 | grep -v warning || true
  git log --oneline -1
fi
