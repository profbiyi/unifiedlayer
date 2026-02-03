#!/bin/bash
# Generate self-signed SSL certificates for local testing
# For production, use Let's Encrypt with certbot instead!

echo "Generating self-signed SSL certificates for local testing..."
echo "WARNING: These are NOT suitable for production use!"
echo ""

# Create ssl directory if it doesn't exist
mkdir -p ssl

# Generate private key and certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/privkey.pem \
    -out ssl/fullchain.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

chmod 600 ssl/privkey.pem
chmod 644 ssl/fullchain.pem

echo ""
echo "✅ Self-signed certificates generated in ssl/ directory"
echo ""
echo "To use these certificates:"
echo "1. Uncomment the HTTPS server block in nginx.conf"
echo "2. Update server_name to match your domain"
echo "3. Restart nginx: docker compose -f docker-compose.prod.yml restart nginx"
echo ""
echo "For production, use Let's Encrypt:"
echo "  docker run -it --rm -v ./ssl:/etc/letsencrypt certbot/certbot certonly --standalone -d your-domain.com"
