#!/bin/bash
echo "=== Xray ==="
if [ -f /tmp/xray.pid ] && kill -0 $(cat /tmp/xray.pid) 2>/dev/null; then
    echo "Status: RUNNING"
else
    echo "Status: STOPPED"
fi
echo "=== Flask ==="
if [ -f /tmp/flask.pid ] && kill -0 $(cat /tmp/flask.pid) 2>/dev/null; then
    echo "Status: RUNNING"
else
    echo "Status: STOPPED"
fi
IP=$(curl -s --max-time 5 ifconfig.me)
echo "=== Panel: http://$IP:5000 ==="
