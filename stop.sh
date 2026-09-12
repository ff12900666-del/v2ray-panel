#!/bin/bash
kill $(cat /tmp/xray.pid) 2>/dev/null
kill $(cat /tmp/flask.pid) 2>/dev/null
rm -f /tmp/xray.pid /tmp/flask.pid
echo "Stopped!"
