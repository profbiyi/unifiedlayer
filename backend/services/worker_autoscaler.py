"""
Prefect Worker Auto-Scaler.

Monitors Prefect work queue and dynamically scales workers based on load.
"""

import os
import logging
import subprocess
from typing import Dict, Optional
from datetime import datetime, timezone

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class WorkerAutoScaler:
    """
    Auto-scales Prefect workers based on work queue depth.

    Scaling Logic:
    - Scale UP: When queue depth > threshold for consecutive checks
    - Scale DOWN: When queue depth < threshold and workers are idle
    - Minimum workers: 1 (always keep one running)
    - Maximum workers: Configurable (default: 10)
    """

    def __init__(
        self,
        prefect_api_url: str = "http://prefect-server:4200/api",
        work_pool_name: str = "default",
        compose_file: str = "/app/docker/docker-compose.yml",
        min_workers: int = 1,
        max_workers: int = 10,
        scale_up_threshold: int = 5,
        scale_down_threshold: int = 2,
        check_interval_seconds: int = 30,
        scale_up_consecutive_checks: int = 2,
        scale_down_consecutive_checks: int = 3,
    ):
        """
        Initialize auto-scaler.

        Args:
            prefect_api_url: Prefect server API URL
            work_pool_name: Name of work pool to monitor
            compose_file: Path to docker-compose.yml
            min_workers: Minimum number of workers (never scale below this)
            max_workers: Maximum number of workers
            scale_up_threshold: Queue depth to trigger scale up
            scale_down_threshold: Queue depth to trigger scale down
            check_interval_seconds: How often to check queue (seconds)
            scale_up_consecutive_checks: How many checks before scaling up
            scale_down_consecutive_checks: How many checks before scaling down
        """
        self.prefect_api_url = prefect_api_url
        self.work_pool_name = work_pool_name
        self.compose_file = compose_file
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.check_interval = check_interval_seconds
        self.scale_up_consecutive = scale_up_consecutive_checks
        self.scale_down_consecutive = scale_down_consecutive_checks

        self.current_workers = min_workers
        self.consecutive_high = 0
        self.consecutive_low = 0
        self.running = False

        logger.info(
            f"AutoScaler initialized: min={min_workers}, max={max_workers}, "
            f"scale_up_threshold={scale_up_threshold}, scale_down_threshold={scale_down_threshold}"
        )

    async def get_work_queue_depth(self) -> Optional[int]:
        """
        Get number of pending flow runs in work pool.

        Returns:
            Number of pending runs, or None on error
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get work queue stats from Prefect API
                response = await client.post(
                    f"{self.prefect_api_url}/work_pools/{self.work_pool_name}/get_scheduled_flow_runs",
                    json={"limit": 1000},  # Get up to 1000 scheduled runs
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    queue_depth = len(data)
                    logger.debug(f"Queue depth: {queue_depth}")
                    return queue_depth
                else:
                    logger.warning(f"Failed to get queue depth: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error getting queue depth: {e}")
            return None

    def scale_workers(self, target_count: int) -> bool:
        """
        Scale Prefect workers to target count.

        Args:
            target_count: Desired number of workers

        Returns:
            True if successful, False otherwise
        """
        if target_count < self.min_workers:
            target_count = self.min_workers
        elif target_count > self.max_workers:
            target_count = self.max_workers

        if target_count == self.current_workers:
            return True

        try:
            logger.info(f"Scaling workers from {self.current_workers} to {target_count}")

            # Use docker compose to scale
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    self.compose_file,
                    "up",
                    "-d",
                    "--scale",
                    f"prefect-worker={target_count}",
                    "--no-recreate",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self.current_workers = target_count
                logger.info(f"✅ Successfully scaled to {target_count} workers")
                return True
            else:
                logger.error(f"Failed to scale workers: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error scaling workers: {e}")
            return False

    async def check_and_scale(self) -> Dict:
        """
        Check queue depth and scale if needed.

        Returns:
            Dict with scaling decision info
        """
        queue_depth = await self.get_work_queue_depth()

        if queue_depth is None:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "queue_depth": None,
                "current_workers": self.current_workers,
                "action": "error",
                "message": "Failed to get queue depth",
            }

        # Determine scaling action
        action = "none"
        message = f"Queue depth: {queue_depth}, Workers: {self.current_workers}"

        # Check if we should scale UP
        if queue_depth > self.scale_up_threshold:
            self.consecutive_high += 1
            self.consecutive_low = 0

            if self.consecutive_high >= self.scale_up_consecutive:
                if self.current_workers < self.max_workers:
                    # Scale up by 1 or more based on queue depth
                    target = min(
                        self.current_workers + max(1, queue_depth // 5),
                        self.max_workers
                    )
                    if self.scale_workers(target):
                        action = "scale_up"
                        message = f"Scaled up to {target} workers (queue: {queue_depth})"
                        self.consecutive_high = 0
                else:
                    action = "at_max"
                    message = f"At maximum workers ({self.max_workers}), queue: {queue_depth}"

        # Check if we should scale DOWN
        elif queue_depth < self.scale_down_threshold:
            self.consecutive_low += 1
            self.consecutive_high = 0

            if self.consecutive_low >= self.scale_down_consecutive:
                if self.current_workers > self.min_workers:
                    # Scale down by 1
                    target = max(self.current_workers - 1, self.min_workers)
                    if self.scale_workers(target):
                        action = "scale_down"
                        message = f"Scaled down to {target} workers (queue: {queue_depth})"
                        self.consecutive_low = 0
                else:
                    action = "at_min"
                    message = f"At minimum workers ({self.min_workers})"

        # Middle ground - reset counters
        else:
            self.consecutive_high = 0
            self.consecutive_low = 0
            action = "stable"

        logger.info(message)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "queue_depth": queue_depth,
            "current_workers": self.current_workers,
            "action": action,
            "message": message,
            "consecutive_high": self.consecutive_high,
            "consecutive_low": self.consecutive_low,
        }

    async def run(self):
        """
        Run auto-scaler loop.
        """
        self.running = True
        logger.info("🚀 Worker AutoScaler started")

        while self.running:
            try:
                await self.check_and_scale()
            except Exception as e:
                logger.error(f"Error in auto-scaler loop: {e}")

            # Wait before next check
            await asyncio.sleep(self.check_interval)

        logger.info("AutoScaler stopped")

    def stop(self):
        """Stop the auto-scaler."""
        self.running = False


async def main():
    """Main entry point."""

    # Get config from environment
    prefect_api_url = os.getenv("PREFECT_API_URL", "http://prefect-server:4200/api")
    compose_file = os.getenv("COMPOSE_FILE", "/app/docker/docker-compose.yml")
    min_workers = int(os.getenv("AUTOSCALER_MIN_WORKERS", "1"))
    max_workers = int(os.getenv("AUTOSCALER_MAX_WORKERS", "10"))
    scale_up_threshold = int(os.getenv("AUTOSCALER_SCALE_UP_THRESHOLD", "5"))
    scale_down_threshold = int(os.getenv("AUTOSCALER_SCALE_DOWN_THRESHOLD", "2"))
    check_interval = int(os.getenv("AUTOSCALER_CHECK_INTERVAL", "30"))

    scaler = WorkerAutoScaler(
        prefect_api_url=prefect_api_url,
        compose_file=compose_file,
        min_workers=min_workers,
        max_workers=max_workers,
        scale_up_threshold=scale_up_threshold,
        scale_down_threshold=scale_down_threshold,
        check_interval_seconds=check_interval,
    )

    # Handle shutdown gracefully
    import signal

    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        scaler.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await scaler.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
