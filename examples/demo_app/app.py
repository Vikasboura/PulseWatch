"""
PulseWatch Demo Traffic & Error Generator
------------------------------------------
Simulates a live e-commerce application processing requests, generating
telemetry logs, sending time-series metrics, and triggering periodic error spikes.

Usage:
  python app.py --api-key pw_live_YOUR_KEY --url http://localhost:8000/api/v1
"""

import argparse
import logging
import os
import random
import sys
import time

# Add sdk to path if running directly from repo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../sdk")))

try:
    from pulsewatch import PulseWatchClient, PulseWatchHandler
except ImportError:
    print("Error: PulseWatch SDK not found. Install it with: pip install -e ../../sdk")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="PulseWatch Live Demo Generator")
    parser.add_argument(
        "--api-key",
        default=os.getenv("PULSEWATCH_API_KEY", ""),
        help="PulseWatch Project Ingest API Key (pw_live_...)",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("PULSEWATCH_URL", "http://localhost:8001/api/v1"),
        help="PulseWatch Backend Base API URL",
    )
    parser.add_argument(
        "--burst",
        action="store_true",
        help="Simulate an immediate severe error spike to trigger alert rules",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=0,
        help="Number of iterations to run (0 for continuous loop)",
    )
    args = parser.parse_args()

    api_key = args.api_key.strip()
    if not api_key:
        print("\n[PulseWatch Demo Generator]")
        api_key = input("Enter your PulseWatch Project API Key (e.g. pw_live_...): ").strip()
        if not api_key:
            print("API Key required. Exiting.")
            sys.exit(1)

    print(f"\n[*] Initializing PulseWatch Client...")
    print(f"Target URL: {args.url}")
    print(f"API Key:    {api_key[:12]}...")

    client = PulseWatchClient(api_key=api_key, base_url=args.url, batch_size=20, flush_interval=1.5)

    # Setup standard logger
    app_logger = logging.getLogger("demo_store")
    app_logger.setLevel(logging.DEBUG)
    pw_handler = PulseWatchHandler(client)
    app_logger.addHandler(pw_handler)

    # Console output handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    app_logger.addHandler(console)

    if args.burst:
        print("\n[!] Triggering instant error burst (15 error events)...")
        for i in range(15):
            app_logger.error(
                f"PaymentGatewayError: Stripe charge failed for cart_#{1000 + i}",
                extra={"cart_id": f"cart_{1000 + i}", "error_code": "card_declined_gateway_timeout", "attempt": 3},
            )
            client.send_metric("error_burst_rate", value=15.0, labels={"env": "prod"})
        client.flush()
        print("Burst completed. Check your PulseWatch alerts page!\n")
        return

    print("\n[+] Simulating continuous realistic production traffic...")
    print("Press Ctrl+C to stop.\n")

    endpoints = [
        ("GET", "/api/v1/products", 20, 60),
        ("GET", "/api/v1/search", 35, 120),
        ("POST", "/api/v1/cart/items", 40, 90),
        ("POST", "/api/v1/checkout", 120, 380),
        ("GET", "/api/v1/users/profile", 15, 45),
    ]

    iteration = 0
    try:
        while True:
            iteration += 1
            method, path, min_lat, max_lat = random.choice(endpoints)
            latency = round(random.uniform(min_lat, max_lat), 2)
            user_id = f"usr_{random.randint(100, 999)}"

            # 90% normal requests, 10% errors/warnings
            dice = random.random()
            if dice > 0.95:
                # Critical / Error
                err_msg = random.choice([
                    "DatabaseConnectionError: Postgres pool exhausted (active=20, max=20)",
                    "PaymentGatewayTimeout: upstream 504 Gateway Timeout from Stripe",
                    "RedisConnectionRefused: Cache cluster node redis-02 unreachable",
                    "DeadlockDetected: Transaction aborted on table 'order_inventory'",
                ])
                app_logger.error(
                    err_msg,
                    extra={"endpoint": path, "user_id": user_id, "status_code": 500, "latency_ms": latency},
                )
                client.send_metric("http_latency_ms", value=latency * 2.5, labels={"path": path, "status": "500"})
                client.send_metric("failed_requests_count", value=1.0)
            elif dice > 0.88:
                # Warning
                warn_msg = random.choice([
                    "HighMemoryUsage: Pod memory reached 84% threshold",
                    "SlowQueryWarning: Query took 284ms on table 'search_index'",
                    "RateLimitWarning: Client approaching quota (92/100 requests)",
                ])
                app_logger.warning(
                    warn_msg,
                    extra={"endpoint": path, "user_id": user_id, "status_code": 429 if "RateLimit" in warn_msg else 200},
                )
                client.send_metric("http_latency_ms", value=latency, labels={"path": path, "status": "warning"})
            else:
                # Info
                app_logger.info(
                    f"{method} {path} completed in {latency}ms",
                    extra={"endpoint": path, "user_id": user_id, "status_code": 200, "latency_ms": latency},
                )
                client.send_metric("http_latency_ms", value=latency, labels={"path": path, "status": "200"})

            # Periodic system metrics
            cpu_val = round(random.uniform(25.0, 75.0), 1)
            active_sessions = random.randint(140, 260)
            client.send_metric("cpu_utilization", value=cpu_val, labels={"node": "worker-1"})
            client.send_metric("active_sessions", value=float(active_sessions))

            time.sleep(random.uniform(0.3, 0.8))

            if args.rounds > 0 and iteration >= args.rounds:
                break

    except KeyboardInterrupt:
        print("\nStopping demo generator...")
    finally:
        client.close()
        print("Flushed remaining logs and metrics. Goodbye!")


if __name__ == "__main__":
    main()
