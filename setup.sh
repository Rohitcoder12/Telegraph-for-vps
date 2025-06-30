#!/bin/bash

# A script to automate the deployment of the Telegraph Bot on a new Ubuntu server.

echo "--- Starting Telegraph Bot Setup ---"

# --- Step 1: Install Dependencies ---
echo "--> Updating and installing system packages (python, git, nginx)..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git nginx

# --- Step 2: Configure Firewall ---
echo "--> Configuring firewall (UFW)..."
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw --force enable

# --- Step 3: Set up Python Environment ---
echo "--> Setting up Python virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
fi
source venv/bin/activate
echo "--> Installing Python libraries from requirements.txt..."
pip install -r requirements.txt

# --- Step 4: .env Configuration ---
echo "--> Checking for .env file..."
if [ ! -f .env ]; then
    echo ".env file not found. Creating from .env.example."
    cp .env.example .env
    echo "IMPORTANT: Please edit the .env file now with your secrets!"
    nano .env
fi

# --- Step 5: Telethon Session ---
echo "--> Checking for Telethon session file..."
if [ ! -f "bot_session.session" ]; then
    echo "Telethon session file not found. Running login script..."
    python login.py
else
    echo "Telethon session file already exists. Skipping login."
fi

# --- Step 6: Configure and Start Gunicorn Service ---
echo "--> Configuring Gunicorn systemd service..."

# Get current user and project path automatically
CURRENT_USER=$(whoami)
PROJECT_PATH=$(pwd)

# Create the service file from a template
sudo tee /etc/systemd/system/telegraphbot.service > /dev/null <<EOF
[Unit]
Description=Gunicorn for Telegraph Bot
After=network.target

[Service]
User=$CURRENT_USER
Group=www-data
WorkingDirectory=$PROJECT_PATH
EnvironmentFile=$PROJECT_PATH/.env
ExecStart=$PROJECT_PATH/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:8080 bot:application

[Install]
WantedBy=multi-user.target
EOF

echo "--> Starting Gunicorn service..."
sudo systemctl daemon-reload
sudo systemctl restart telegraphbot
sudo systemctl enable telegraphbot

# --- Step 7: Configure Nginx ---
echo "--> Configuring Nginx reverse proxy..."

# Create the Nginx config file
sudo tee /etc/nginx/sites-available/telegraphbot > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

# Enable the site and restart Nginx
if [ -L /etc/nginx/sites-enabled/telegraphbot ]; then
    echo "Nginx site already enabled."
else
    sudo ln -s /etc/nginx/sites-available/telegraphbot /etc/nginx/sites-enabled/
fi

# Remove default site if it exists to avoid conflicts
if [ -L /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
fi

sudo nginx -t
sudo systemctl restart nginx

# --- Final ---
echo ""
echo "✅ --- Setup Complete! --- ✅"
echo "Your bot is now running in the background."
echo "The final step is to set the webhook with Telegram."
echo "Please visit the following URL in your browser (replace with your bot token and IP):"
echo "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=<YOUR_WEBHOOK_URL>/<YOUR_TOKEN>"
echo ""