#!/bin/bash
# Start Data Platform

echo "🚀 Starting Data Platform..."
echo ""

cd docker

# Start services
echo "Starting all services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 15

echo ""
echo "✅ Data Platform started!"
echo ""
echo "Access your services:"
echo "  Frontend:     http://localhost"
echo "  Backend API:  http://localhost/api"
echo "  Prefect UI:   http://localhost/prefect"
echo "  Grafana:      http://localhost/grafana"
echo "  Prometheus:   http://localhost/prometheus"
echo ""
echo "View logs: docker compose logs -f"
echo "Stop: docker compose down"
