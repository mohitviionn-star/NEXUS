# The monitoring worker: repeatedly checks every registered service's health
# at the same time (not one by one), records what happened, and updates
# each service's current status. Runs forever until you press Ctrl+C.
import asyncio
import signal
import time

import httpx
from sqlalchemy import select

from database import async_session
from models import HealthCheck, Service

CHECK_INTERVAL_SECONDS = 10   # how often to run a full round of checks
MAX_CONCURRENT_CHECKS = 5     # the "bouncer" limit - don't check more than 5 at once
REQUEST_TIMEOUT_SECONDS = 3   # give up waiting on one service after this long
MAX_RETRIES = 2               # retry a failed check this many times before giving up

shutdown_requested = False


def request_shutdown(signum, frame):
    global shutdown_requested
    print("Shutdown requested - finishing current round, then stopping...")
    shutdown_requested = True


async def check_one_service(service: Service, client: httpx.AsyncClient, semaphore: asyncio.Semaphore):
    async with semaphore:  # wait here if 5 other checks are already running
        for attempt in range(1, MAX_RETRIES + 2):  # first try, plus retries
            start = time.monotonic()
            try:
                response = await client.get(service.health_check_url, timeout=REQUEST_TIMEOUT_SECONDS)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                state = "healthy" if response.status_code == 200 else "unhealthy"
                return service, response.status_code, elapsed_ms, state
            except (httpx.TimeoutException, httpx.ConnectError):
                elapsed_ms = int((time.monotonic() - start) * 1000)
                if attempt <= MAX_RETRIES:
                    continue  # transient failure - try again
                return service, None, elapsed_ms, "unhealthy"


async def run_one_round():
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)

    async with async_session() as session:
        result = await session.execute(select(Service))
        services = result.scalars().all()

        if not services:
            print("No services registered yet.")
            return

        async with httpx.AsyncClient() as client:
            # Kick off every service's check at once - the semaphore keeps
            # only 5 actually "in flight" at any given moment.
            tasks = [check_one_service(service, client, semaphore) for service in services]
            results = await asyncio.gather(*tasks)

        for service, status_code, elapsed_ms, state in results:
            session.add(HealthCheck(
                service_id=service.id,
                status_code=status_code,
                response_time_ms=elapsed_ms,
                state=state,
            ))
            service.status = state
            print(f"{service.name}: {state} ({status_code}, {elapsed_ms}ms)")

        await session.commit()


async def sleep_with_shutdown_check(seconds: int):
    # Sleep 1 second at a time so Ctrl+C is noticed quickly, instead of
    # being stuck waiting out the full interval.
    for _ in range(seconds):
        if shutdown_requested:
            return
        await asyncio.sleep(1)


async def main():
    signal.signal(signal.SIGINT, request_shutdown)   # Ctrl+C
    signal.signal(signal.SIGTERM, request_shutdown)   # e.g. "stop this program" from Docker

    print("Monitoring worker started.")
    while not shutdown_requested:
        await run_one_round()
        await sleep_with_shutdown_check(CHECK_INTERVAL_SECONDS)

    print("Monitoring worker stopped gracefully.")


if __name__ == "__main__":
    asyncio.run(main())
