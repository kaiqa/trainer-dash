#!/usr/bin/env python3
"""Generate fake training session data for testing/demo purposes."""

import argparse
import json
import sys
from datetime import datetime, timedelta
from random import choice, randint, uniform

try:
    from faker import Faker
except ImportError:
    print("Faker library not installed. Install with: pip install faker")
    sys.exit(1)

fake = Faker()

# Training type options
TRAINING_TYPES = [
    "squats", "bench_press", "deadlift", "pull_ups", "push_ups", "lunges",
    "overhead_press", "barbell_row", "romanian_deadlift", "leg_press",
    "lat_pull_down", "chest_fly", "dumbbell_curl", "tricep_extension",
    "plank", "burpees", "jump_rope"
]

BODY_TYPES = ["legs", "chest", "back", "shoulders", "arms", "core"]

STATUSES = ["planned", "done", "skipped"]

INJURY_OPTIONS = ["yes", "no"]
PAIN_OPTIONS = ["yes", "no"]
PAIN_SOURCES = ["knees", "lower_back", "shoulders", "wrists", "neck", "ankles", None]


def generate_session(idx: int) -> dict:
    """Generate a single fake training session entry."""
    # Random date within last 90 days
    days_ago = randint(0, 90)
    session_date = (datetime.now() - timedelta(days=days_ago)).strftime("%d.%m.%Y")

    # Random time in HH:MM format
    hour = randint(6, 21)
    minute = choice([0, 15, 30, 45])
    session_time = f"{hour:02d}:{minute:02d}"

    # Random injuries / pain (with dependency)
    injuries = choice(INJURY_OPTIONS)
    pain = choice(PAIN_OPTIONS)
    pain_source = choice(PAIN_SOURCES) if pain == "yes" else None

    # Random body type and training type
    body_type = choice(BODY_TYPES)
    training_type = choice(TRAINING_TYPES)

    # Realistic sets/reps/weight
    sets = randint(2, 6)
    repetitions = randint(5, 20)
    weight = round(uniform(20, 150), 1)

    # Random rating 1-10
    rating = randint(1, 10)

    # Random session notes
    notes_pool = [
        "Great session, felt strong throughout.",
        "Hard training but completed all sets.",
        "Knees felt a bit sore during squats.",
        "New PR on bench press!",
        "Skipped warm-up, won't do again.",
        "Solid workout, maintained good form.",
        "Back felt tight, reduced weight.",
        "Excellent energy today.",
        "Struggled with last set.",
        "Quick session, felt good.",
        "Need more rest between sets.",
        "Perfect technique on all reps.",
        "Feeling tired but pushed through.",
        "Very satisfied with progress.",
        "Pain in shoulders during overhead press.",
    ]
    session_notes = choice(notes_pool)

    return {
        "user_name": fake.name(),
        "time_spend_minutes": randint(20, 120),
        "date": session_date,
        "time": session_time,
        "type": training_type,
        "sets": str(sets),
        "repetitions": str(repetitions),
        "weight": str(weight),
        "body_type": body_type,
        "injuries": injuries,
        "pain": pain,
        "pain_source": pain_source,
        "rating": str(rating),
        "session_notes": session_notes,
        "status": choice(STATUSES),
    }


import urllib.request

def main():
    parser = argparse.ArgumentParser(
        description="Generate fake training session data for Dogbrah AI webhook."
    )
    parser.add_argument(
        "count",
        type=int,
        nargs="?",
        default=10,
        help="Number of fake training sessions to generate (default: 10)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="fake_trainings.json",
        help="Output file path (default: fake_trainings.json)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "jsonl"],
        default="json",
        help="Output format: json (array) or jsonl (one JSON per line)",
    )
    parser.add_argument(
        "--host", "-H",
        type=str,
        default="localhost",
        help="Webhook server host/IP to send data to (default: localhost)",
    )
    parser.add_argument(
        "--port", "-P",
        type=int,
        default=5687,
        help="Webhook server port (default: 5687)",
    )
    parser.add_argument(
        "--send-to-webhook",
        action="store_true",
        help="Send generated sessions to webhook endpoint instead of writing file",
    )

    args = parser.parse_args()

    if args.count < 1 or args.count > 10000:
        print(f"Error: count must be between 1 and 10000. Got: {args.count}")
        sys.exit(1)

    sessions = [generate_session(i) for i in range(args.count)]

    if args.send_to_webhook:
        webhook_url = f"http://{args.host}:{args.port}/webhook/record-training"
        print(f"Sending {args.count} session(s) to {webhook_url} ...")
        for s in sessions:
            payload = json.dumps(s).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    print(f"  POST {s['user_name']} | status={resp.status} | {s['date']} {s['time']}")
            except Exception as exc:
                print(f"  POST {s['user_name']} | FAILED | {exc}")
    else:
        if args.format == "json":
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(sessions, f, indent=2, ensure_ascii=False)
        else:
            with open(args.output, "w", encoding="utf-8") as f:
                for session in sessions:
                    f.write(json.dumps(session, ensure_ascii=False) + "\n")

    print(f"Generated {args.count} fake training session(s)")
    if args.send_to_webhook:
        print(f"  -> sent to webhook at http://{args.host}:{args.port}/webhook/record-training")
    else:
        print(f"  -> {args.output}")
    if args.count <= 3:
        for s in sessions:
            print(f"  - {s['date']} | {s['user_name']} | {s['type']} | {s['sets']}x{s['repetitions']} reps | {s['body_type']} | status={s['status']}")


if __name__ == "__main__":
    main()
