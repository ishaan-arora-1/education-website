#!/bin/bash

VPS_IP="45.76.4.171"
VPS_USER="root"
MAX_ATTEMPTS=20
WAIT_TIME=30

echo "🔍 Waiting for VPS $VPS_IP to come back online..."
echo "⏰ Will check every $WAIT_TIME seconds for up to $(($MAX_ATTEMPTS * $WAIT_TIME / 60)) minutes"

for i in $(seq 1 $MAX_ATTEMPTS); do
    echo "📡 Attempt $i/$MAX_ATTEMPTS..."
    
    if ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=no "$VPS_USER@$VPS_IP" 'echo "✅ VPS is back online!"' 2>/dev/null; then
        echo "🎉 SUCCESS! VPS is reachable again!"
        echo "🚀 You can now run the cleanup and redeployment."
        exit 0
    else
        echo "❌ Still unreachable. Waiting $WAIT_TIME seconds..."
        sleep $WAIT_TIME
    fi
done

echo "⚠️  VPS still unreachable after $(($MAX_ATTEMPTS * $WAIT_TIME / 60)) minutes."
echo "🔧 This might indicate a more serious issue. Consider:"
echo "   1. Contacting your VPS provider"
echo "   2. Checking the VPS console/dashboard"
echo "   3. Verifying the IP address is correct" 