#!/usr/bin/env bash
set -e

# Number of pretend GPU rails (default 8 for 8-GPU servers like HGX / MI300X)
NUM_RAILS=${NUM_RAILS:-8}
START_PORT=${START_PORT:-5201}

echo "========================================================"
echo " Starting Pretend GPU Server: $(hostname) "
echo " Primary IP: $(hostname -i)"
echo " Initializing $NUM_RAILS GPU Rail iPerf3 server daemons..."
echo "========================================================"

for i in $(seq 0 $((NUM_RAILS - 1))); do
    port=$((START_PORT + i))
    iperf3 -s -p $port -D --logfile /var/log/iperf3-port-${port}.log
    echo "  -> Rail $i daemon listening on port $port"
done

echo "All $NUM_RAILS GPU rail daemons started successfully."
echo "Pretend GPU server is ready for fabric traffic injection."

# Keep container running and forward signals
trap 'echo "Stopping all daemons..."; killall iperf3 2>/dev/null; exit 0' SIGTERM SIGINT

tail -f /dev/null &
wait $!
