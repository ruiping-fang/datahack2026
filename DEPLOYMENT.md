# EC2 Deployment Guide

## Prerequisites

1. **EC2 Instance**: Amazon Linux 2 or Ubuntu
2. **Security Group**: Allow inbound on port 5001
3. **SSH Key**: Your `.pem` file from AWS

## Step 1: SSH into EC2

```bash
# Set key permissions
chmod 400 your-key.pem

# Connect to EC2
ssh -i your-key.pem ec2-user@your-ec2-public-ip
```

For Ubuntu, use `ubuntu@` instead of `ec2-user@`.

## Step 2: Clone Repository

```bash
# Generate SSH key on EC2
ssh-keygen -t ed25519 -C "your-email@example.com"

# Display public key
cat ~/.ssh/id_ed25519.pub

# Add the key to GitHub: Settings > SSH and GPG keys > New SSH key

# Clone repository
git clone git@github.com:your-username/datahack2026.git
cd datahack2026
```

## Step 3: Deploy

```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

## Step 4: Run Application

### Option A: Direct Run (Development)
```bash
python3 app.py
```

### Option B: Background Process
```bash
# Run in background
nohup python3 app.py > app.log 2>&1 &

# Check logs
tail -f app.log

# Find process
ps aux | grep app.py

# Stop process
kill <PID>
```

### Option C: Systemd Service (Production)
```bash
# Copy service file
sudo cp pgv-app.service /etc/systemd/system/

# Edit paths if needed
sudo nano /etc/systemd/system/pgv-app.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable pgv-app
sudo systemctl start pgv-app

# Check status
sudo systemctl status pgv-app

# View logs
sudo journalctl -u pgv-app -f

# Restart service
sudo systemctl restart pgv-app
```

## Step 5: Configure AWS Security Group

In AWS Console:
1. Go to EC2 > Security Groups
2. Select your instance's security group
3. Add inbound rule:
   - Type: Custom TCP
   - Port: 5001
   - Source: 0.0.0.0/0 (or your IP for security)

## Step 6: Access Application

```
http://your-ec2-public-ip:5001
```

## Important Files

- **loh_rom.joblib**: Pre-trained model (137 MB) - Must be uploaded
- **loh.hdf5**: Training dataset (137 MB) - Optional for inference
- **templates/**: HTML templates for web interface

## Upload Large Files

If model files are too large for git:

```bash
# From local machine
scp -i your-key.pem loh_rom.joblib ec2-user@your-ec2-ip:~/datahack2026/
scp -i your-key.pem loh.hdf5 ec2-user@your-ec2-ip:~/datahack2026/
```

## Troubleshooting

### Port already in use
```bash
# Find process using port 5001
sudo lsof -i :5001

# Kill process
kill <PID>
```

### Missing dependencies
```bash
pip3 install --upgrade -r requirements.txt
```

### Permission denied
```bash
# Check file permissions
ls -la app.py

# Make executable if needed
chmod +x app.py
```

### Model not loading
```bash
# Check if model file exists
ls -lh loh_rom.joblib

# Verify file integrity
python3 -c "from pgv_rom import PGVReducedOrderModel; model = PGVReducedOrderModel.load('loh_rom.joblib'); print('Model loaded successfully')"
```

## Production Recommendations

1. **Use Nginx as reverse proxy**
2. **Enable HTTPS with Let's Encrypt**
3. **Set up monitoring (CloudWatch)**
4. **Configure auto-scaling**
5. **Use Elastic IP for static address**
6. **Set up automated backups**

## Quick SSH Config

Add to `~/.ssh/config` on your local machine:

```
Host pgv-ec2
    HostName your-ec2-public-ip
    User ec2-user
    IdentityFile ~/.ssh/your-key.pem
    ServerAliveInterval 60
```

Then connect with: `ssh pgv-ec2`
