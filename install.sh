#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: build_and_install.sh <main_file>"
    exit 1
fi

MAIN_FILE="$1"

python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Failed to create virtual environment."
    exit 1
fi

source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment."
    exit 1
fi

pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install requirements."
    deactivate
    exit 1
fi

python ./src/scripts/configure_keyring.py

deactivate
if [ $? -ne 0 ]; then
    echo "Failed to deactivate virtual environment."
    exit 1
fi

SERVICE_NAME="linkedin_assistant"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Linkedin Assistant service
After=network.target

[Service]
ExecStart=$(pwd)/venv/bin/python $(pwd)/$MAIN_FILE
Restart=always
User=$(whoami)
WorkingDirectory=$(pwd)
Environment="VIRTUAL_ENV=$(pwd)/venv"
Environment="PATH=$(pwd)/venv/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOL

# Step 8: Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

if [ $? -ne 0 ]; then
    echo "Failed to start the service."
    exit 1
fi

echo "Build and installation completed successfully. Service is running."
