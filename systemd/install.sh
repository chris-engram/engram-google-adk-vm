#!/bin/bash

# Install systemd services for Google ADK

echo "Installing Google ADK systemd services..."

# Copy service files
sudo cp adk-api.service /etc/systemd/system/
sudo cp scalar-docs.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable adk-api.service
sudo systemctl enable scalar-docs.service

echo "Services installed!"
echo ""
echo "To start the services:"
echo "  sudo systemctl start adk-api"
echo "  sudo systemctl start scalar-docs"
echo ""
echo "To check status:"
echo "  sudo systemctl status adk-api"
echo "  sudo systemctl status scalar-docs"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u adk-api -f"
echo "  sudo journalctl -u scalar-docs -f"