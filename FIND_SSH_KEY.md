# How to Find SSH Key Locally

## Quick Commands

```bash
# Find all .pem files in home directory
find ~ -name "*.pem" 2>/dev/null

# Check Downloads folder
ls ~/Downloads/*.pem

# Check .ssh folder
ls ~/.ssh/*.pem

# List all files in .ssh directory
ls -la ~/.ssh/
```

## Common Locations

```
~/Downloads/your-key.pem          # Usually downloaded here
~/.ssh/your-key.pem               # Recommended location
~/Documents/aws/your-key.pem      # Custom location
~/Desktop/your-key.pem            # Sometimes saved here
```

## Example Output

```bash
$ find ~ -name "*.pem" 2>/dev/null
/Users/ruiping/Downloads/datahack-key.pem
/Users/ruiping/.ssh/my-aws-key.pem
```

## Move Key to .ssh Folder (Recommended)

```bash
# Move from Downloads to .ssh
mv ~/Downloads/your-key.pem ~/.ssh/

# Set correct permissions
chmod 400 ~/.ssh/your-key.pem

# Verify
ls -l ~/.ssh/your-key.pem
# Should show: -r-------- (read-only for you)
```

## Find EC2 IP Address

**AWS Console:**
1. Go to: https://console.aws.amazon.com/ec2/
2. Click **Instances**
3. Find **Public IPv4 address** column

**AWS CLI:**
```bash
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,PublicIpAddress,Tags[?Key==`Name`].Value|[0]]' --output table
```

## Connect

```bash
# Replace with your actual key path and IP
ssh -i ~/.ssh/your-key.pem ec2-user@YOUR_EC2_IP
```
