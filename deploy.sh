#!/bin/bash
# EC2 Deployment Script for PGV Prediction App

echo "=== Starting Deployment ==="

# 1. Update system
echo "Updating system packages..."
sudo yum update -y || sudo apt update -y

# 2. Install Python3 and dependencies
echo "Installing Python and tools..."
sudo yum install -y python3 python3-pip git || sudo apt install -y python3 python3-pip git

# 3. Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# 4. Check required files
if [ ! -f "loh_rom.joblib" ]; then
    echo "⚠️  Warning: Model file loh_rom.joblib not found!"
    echo "Please upload the model file or run training"
fi

if [ ! -f "loh.hdf5" ]; then
    echo "⚠️  Warning: Dataset file loh.hdf5 not found!"
fi

# 5. Configure firewall (open port 5001)
echo "Configuring firewall..."
sudo firewall-cmd --permanent --add-port=5001/tcp 2>/dev/null || echo "firewall-cmd not available, skipping"
sudo firewall-cmd --reload 2>/dev/null || echo "Skipping firewall reload"

echo "=== Deployment Complete ==="
echo ""
echo "To run the app:"
echo "  python3 app.py"
echo ""
echo "To run in background:"
echo "  nohup python3 app.py > app.log 2>&1 &"
echo ""
echo "Access at: http://$(curl -s ifconfig.me):5001"
