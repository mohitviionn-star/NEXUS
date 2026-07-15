# The monitoring worker: repeatedly checks every registered service's health
# at the same time (not one by one), records what happened, updates
# each service's current status, and opens/resolves incidents based on
# repeated failures or successes. Runs forever until you press Ctrl+C.
import asyncio
import signal
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session
from models import HealthCheck, Incident, IncidentEvent, Service

CHECK_INTERVAL_SECONDS = 10   # how often to run a full round of checks
MAX_CONCURRENT_CHECKS = 5     # the "bouncer" limit - don't check more than 5 at once
REQUEST_TIMEOUT_SECONDS = 3   # give up waiting on one service after this long
MAX_RETRIES = 2               # retry a failed check this many times before giving up
FAILURE_THRESHOLD = 3         # this many failures in a row -> open an incident
RECOVERY_THRESHOLD = 3        # this many successes in a row -> resolve the incident

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


async def apply_incident_rules(session: AsyncSession, service: Service, state: str):
    if state == "healthy":
        service.consecutive_successes += 1
        service.consecutive_failures = 0

        if service.consecutive_successes >= RECOVERY_THRESHOLD:
            result = await session.execute(
                select(Incident).where(Incident.service_id == service.id, Incident.status == "open")
            )
            open_incident = result.scalar_one_or_none()
            if open_incident is not None:
                open_incident.status = "resolved"
                open_incident.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
                session.add(IncidentEvent(
                    incident_id=open_incident.id,
                    event_type="resolved",
                    message=f"{service.name} had {service.consecutive_successes} consecutive successful checks.",
                ))
                print(f"  -> Incident #{open_incident.id} resolved.")
    else:
        service.consecutive_failures += 1
        service.consecutive_successes = 0

        if service.consecutive_failures >= FAILURE_THRESHOLD:
            result = await session.execute(
                select(Incident).where(Incident.service_id == service.id, Incident.status == "open")
            )
            open_incident = result.scalar_one_or_none()
            if open_incident is None:  # don't open a second incident for the same problem
                incident = Incident(service_id=service.id, severity="high")
                session.add(incident)
                await session.flush()  # fills in incident.id before we use it below
                session.add(IncidentEvent(
                    incident_id=incident.id,
                    event_type="opened",
                    message=f"{service.name} failed {service.consecutive_failures} checks in a row.",
                ))
                print(f"  -> Incident #{incident.id} opened for {service.name}.")


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
            await apply_incident_rules(session, service, state)
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
