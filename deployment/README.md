# Deployment Guide for Metalized Background Detector API

This guide explains how to deploy the Metalized Background Detector API on a VPS.

## Prerequisites

1. **VPS Requirements**:
   - Ubuntu 20.04/22.04 LTS (recommended)
   - At least 1GB RAM (2GB recommended)
   - At least 10GB disk space
   - Root or sudo access

2. **Domain Name (Optional but recommended)**
   - Point your domain to the VPS IP address

## Step 1: Server Setup

### 1.1 Connect to your VPS
```bash
ssh root@your_server_ip
```

### 1.2 Create a non-root user (recommended)
```bash
adduser deploy
usermod -aG sudo deploy
```

### 1.3 Update system packages
```bash
sudo apt update && sudo apt upgrade -y
```

## Step 2: Install Dependencies

### 2.1 Install system dependencies
```bash
sudo apt install -y python3-pip python3-venv nginx supervisor
```

### 2.2 Install OpenCV dependencies
```bash
sudo apt install -y libgl1-mesa-glx libsm6 libxext6 libxrender-dev
```

## Step 3: Deploy the Application

### 3.1 Clone the repository
```bash
sudo apt install -y git
mkdir -p /opt/apps
cd /opt/apps
git clone https://your-repository-url.git metalized-detector
cd metalized-detector/app
```

### 3.2 Create and activate virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3.3 Install Python dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.4 Create uploads directory
```bash
mkdir -p uploads
chmod 755 uploads
```

## Step 4: Configure Gunicorn

### 4.1 Install Gunicorn
```bash
pip install gunicorn
```

### 4.2 Create Gunicorn service file
Create `/etc/systemd/system/metalized-detector.service`:

```ini
[Unit]
Description=Metalized Background Detector API
After=network.target

[Service]
User=deploy
Group=www-data
WorkingDirectory=/opt/apps/metalized-detector/app
Environment="PATH=/opt/apps/metalized-detector/app/venv/bin"
ExecStart=/opt/apps/metalized-detector/app/venv/bin/gunicorn --workers 3 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

### 4.3 Start and enable the service
```bash
sudo systemctl daemon-reload
sudo systemctl start metalized-detector
sudo systemctl enable metalized-detector
```

## Step 5: Configure Nginx

### 5.1 Create Nginx configuration
Create `/etc/nginx/sites-available/metalized-detector`:

```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for file uploads
        client_max_body_size 10M;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Serve static files directly (if any)
    location /static/ {
        alias /opt/apps/metalized-detector/app/static/;
    }
}
```

### 5.2 Enable the site and restart Nginx
```bash
sudo ln -s /etc/nginx/sites-available/metalized-detector /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

## Step 6: Set Up SSL (Recommended)

### 6.1 Install Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 6.2 Obtain SSL certificate
```bash
sudo certbot --nginx -d your_domain.com
```

### 6.3 Set up automatic renewal
```bash
sudo systemctl status certbot.timer
```

## Step 7: Firewall Configuration

### 7.1 Allow necessary ports
```bash
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

## Step 8: Monitoring and Logs

### 8.1 Check application logs
```bash
sudo journalctl -u metalized-detector -f
```

### 8.2 Check Nginx logs
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

## Step 9: Automatic Updates (Optional)

### 9.1 Set up automatic security updates
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Environment Variables

Create a `.env` file in the app directory for environment-specific settings:

```bash
cd /opt/apps/metalized-detector/app
echo "UPLOAD_DIR=/opt/apps/metalized-detector/app/uploads" > .env
```

## Updating the Application

1. Pull the latest changes:
   ```bash
   cd /opt/apps/metalized-detector
   git pull origin main
   ```

2. Restart the service:
   ```bash
   sudo systemctl restart metalized-detector
   ```

## Troubleshooting

1. **Check service status**:
   ```bash
   sudo systemctl status metalized-detector
   ```

2. **Check logs**:
   ```bash
   sudo journalctl -u metalized-detector -f
   ```

3. **Check Nginx configuration**:
   ```bash
   sudo nginx -t
   ```

4. **Check open ports**:
   ```bash
   sudo netstat -tulpn | grep LISTEN
   ```

## Security Considerations

1. **Keep the system updated**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Use a firewall**:
   ```bash
   sudo ufw status
   ```

3. **Disable root login**:
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Set: PermitRootLogin no
   sudo systemctl restart sshd
   ```

4. **Use SSH keys**:
   ```bash
   ssh-copy-id deploy@your_server_ip
   ```

## Backup

1. **Backup your database** (if any)
2. **Backup your uploads directory**:
   ```bash
   tar -czvf metalized-detector-backup-$(date +%Y%m%d).tar.gz /opt/apps/metalized-detector/app/uploads
   ```

## Scaling

For higher traffic, consider:
1. Increasing the number of Gunicorn workers
2. Using a process manager like Supervisor
3. Setting up a load balancer
4. Using a CDN for static files
