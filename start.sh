#!/bin/bash
pkill -f "xray run" 2>/dev/null
pkill -f "python3 app.py" 2>/dev/null
sleep 1
nohup xray run -c /usr/local/etc/xray/config.json > /tmp/xray.log 2>&1 &
echo $! > /tmp/xray.pid
cd /root/v2ray-panel
nohup python3 app.py > /tmp/flask.log 2>&1 &
echo $! > /tmp/flask.pid
IP=$(curl -s --max-time 5 ifconfig.me)
echo "Xray PID: $(cat /tmp/xray.pid)"
echo "Flask PID: $(cat /tmp/flask.pid)"
echo "Panel URL: http://$IP:5000"
