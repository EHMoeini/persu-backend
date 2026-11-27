"""Realistic facility listings used by the ``seed_facilities`` command.

Each entry has a stable ``key``. The seeder derives a deterministic UUID from
that key, so running it repeatedly updates the same mock rows instead of
creating duplicates and never touches facilities created by real users.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

MOCK_FACILITY_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL,
    "https://persu.fpna.ir/mock-facilities",
)


def mock_facility_id(key: str) -> uuid.UUID:
    """Return the stable primary key for a mock listing."""

    return uuid.uuid5(MOCK_FACILITY_NAMESPACE, key)


MOCK_FACILITIES: tuple[dict[str, object], ...] = (
    {
        "key": "azadi-national-football-field",
        "name": "Azadi National Football Field",
        "description": (
            "Full-size natural-grass football pitch inside the Azadi Sports "
            "Complex, with floodlights and covered seating."
        ),
        "category": "Football",
        "type": "Soccer Field",
        "location": "Azadi Sports Complex, Tehran",
        "price": Decimal("1800000.00"),
        "picture": "https://picsum.photos/seed/azadi-football/800/600",
        "rating": Decimal("4.8"),
        "availability": True,
    },
    {
        "key": "enghelab-artificial-turf",
        "name": "Enghelab Artificial Turf",
        "description": (
            "FIFA-standard artificial turf pitch for football and futsal, "
            "available for hourly bookings."
        ),
        "category": "Football",
        "type": "Artificial Turf",
        "location": "Enghelab Sports Complex, Tehran",
        "price": Decimal("950000.00"),
        "picture": "https://picsum.photos/seed/enghelab-turf/800/600",
        "rating": Decimal("4.4"),
        "availability": True,
    },
    {
        "key": "futsal-arena-7",
        "name": "Futsal Arena 7",
        "description": (
            "Indoor futsal court with professional flooring, changing rooms, "
            "and spectator seating."
        ),
        "category": "Football",
        "type": "Futsal Court",
        "location": "East Side, Tehran",
        "price": Decimal("700000.00"),
        "picture": "https://picsum.photos/seed/futsal-arena/800/600",
        "rating": Decimal("4.3"),
        "availability": True,
    },
    {
        "key": "pars-football-field",
        "name": "زمین فوتبال پارس",
        "description": (
            "زمین چمن مصنوعی استاندارد برای فوتبال و فوتسال با نورپردازی "
            "شبانه و رختکن مجهز."
        ),
        "category": "Football",
        "type": "Soccer Field",
        "location": "تهران، سعادت‌آباد",
        "price": Decimal("1100000.00"),
        "picture": "https://picsum.photos/seed/pars-football/800/600",
        "rating": Decimal("4.6"),
        "availability": True,
    },
    {
        "key": "olympic-swimming-pool",
        "name": "Olympic Swimming Pool",
        "description": (
            "Fifty-meter indoor swimming pool with eight lanes, a children's "
            "pool, and certified lifeguards."
        ),
        "category": "Swimming",
        "type": "Swimming Pool",
        "location": "Vanak, Tehran",
        "price": Decimal("350000.00"),
        "picture": "https://picsum.photos/seed/olympic-pool/800/600",
        "rating": Decimal("4.7"),
        "availability": True,
    },
    {
        "key": "pars-indoor-pool",
        "name": "استخر سرپوشیده پارس",
        "description": (
            "استخر سرپوشیده با آب گرم، سونا و جکوزی برای شنای تفریحی و "
            "تمرین حرفه‌ای."
        ),
        "category": "Swimming",
        "type": "Indoor Pool",
        "location": "تهران، پاسداران",
        "price": Decimal("380000.00"),
        "picture": "https://picsum.photos/seed/pars-pool/800/600",
        "rating": Decimal("4.4"),
        "availability": False,
    },
    {
        "key": "riverside-tennis-court",
        "name": "Riverside Tennis Court",
        "description": (
            "Two outdoor hard tennis courts with evening lighting and racket "
            "rental."
        ),
        "category": "Racket Sports",
        "type": "Tennis Court",
        "location": "Riverside, Tehran",
        "price": Decimal("500000.00"),
        "picture": "https://picsum.photos/seed/riverside-tennis/800/600",
        "rating": Decimal("4.5"),
        "availability": True,
    },
    {
        "key": "persepolis-badminton-hall",
        "name": "Persepolis Badminton Hall",
        "description": (
            "Six indoor badminton courts with wooden flooring and equipment "
            "rental."
        ),
        "category": "Racket Sports",
        "type": "Badminton Hall",
        "location": "Shahrak-e Gharb, Tehran",
        "price": Decimal("420000.00"),
        "picture": "https://picsum.photos/seed/badminton-hall/800/600",
        "rating": Decimal("4.2"),
        "availability": True,
    },
    {
        "key": "mirdamad-table-tennis-club",
        "name": "Mirdamad Table Tennis Club",
        "description": (
            "Table tennis club with eight competition tables and coaching "
            "sessions for all levels."
        ),
        "category": "Racket Sports",
        "type": "Table Tennis Hall",
        "location": "Mirdamad, Tehran",
        "price": Decimal("180000.00"),
        "picture": "https://picsum.photos/seed/table-tennis/800/600",
        "rating": Decimal("4.0"),
        "availability": True,
    },
    {
        "key": "iron-gym-fitness-center",
        "name": "Iron Gym Fitness Center",
        "description": (
            "Modern fitness center with strength machines, free weights, a "
            "cardio zone, and personal trainers."
        ),
        "category": "Fitness",
        "type": "Gym",
        "location": "Tajrish, Tehran",
        "price": Decimal("250000.00"),
        "picture": "https://picsum.photos/seed/iron-gym/800/600",
        "rating": Decimal("4.9"),
        "availability": True,
    },
    {
        "key": "serenity-yoga-studio",
        "name": "Serenity Yoga Studio",
        "description": (
            "Calm yoga studio offering hatha, vinyasa, and meditation classes "
            "in small groups."
        ),
        "category": "Fitness",
        "type": "Yoga Studio",
        "location": "Zafaraniyeh, Tehran",
        "price": Decimal("280000.00"),
        "picture": "https://picsum.photos/seed/serenity-yoga/800/600",
        "rating": Decimal("4.7"),
        "availability": True,
    },
    {
        "key": "district-6-basketball-court",
        "name": "District 6 Basketball Court",
        "description": (
            "Outdoor basketball court with a rebound board and evening "
            "lighting, suitable for 3x3 games."
        ),
        "category": "Basketball",
        "type": "Basketball Court",
        "location": "District 6, Tehran",
        "price": Decimal("300000.00"),
        "picture": "https://picsum.photos/seed/basketball-court/800/600",
        "rating": Decimal("4.1"),
        "availability": True,
    },
    {
        "key": "chitgar-beach-volleyball-court",
        "name": "Chitgar Beach Volleyball Court",
        "description": (
            "Sandy beach volleyball court beside Chitgar Lake with nets and "
            "showers."
        ),
        "category": "Volleyball",
        "type": "Beach Volleyball Court",
        "location": "Chitgar Lake, Tehran",
        "price": Decimal("450000.00"),
        "picture": "https://picsum.photos/seed/beach-volleyball/800/600",
        "rating": Decimal("4.6"),
        "availability": True,
    },
    {
        "key": "samurai-martial-arts-dojo",
        "name": "Samurai Martial Arts Dojo",
        "description": (
            "Traditional dojo for karate, judo, and self-defense classes led "
            "by certified coaches."
        ),
        "category": "Martial Arts",
        "type": "Dojo",
        "location": "Narmak, Tehran",
        "price": Decimal("320000.00"),
        "picture": "https://picsum.photos/seed/martial-arts-dojo/800/600",
        "rating": Decimal("4.5"),
        "availability": True,
    },
    {
        "key": "aras-climbing-wall",
        "name": "Aras Climbing Wall",
        "description": (
            "Indoor climbing gym with bouldering walls, top-rope routes, and "
            "beginner lessons."
        ),
        "category": "Climbing",
        "type": "Climbing Gym",
        "location": "Abbasabad, Tehran",
        "price": Decimal("400000.00"),
        "picture": "https://picsum.photos/seed/aras-climbing/800/600",
        "rating": Decimal("4.6"),
        "availability": True,
    },
    {
        "key": "city-multi-sport-hall",
        "name": "سالن ورزشی چندمنظوره شهر",
        "description": (
            "سالن ورزشی سرپوشیده برای والیبال، بسکتبال و تمرین‌های گروهی با "
            "رختکن و جایگاه تماشاگر."
        ),
        "category": "Multi-Sport",
        "type": "Sports Hall",
        "location": "تهران، مرکز شهر",
        "price": Decimal("550000.00"),
        "picture": "https://picsum.photos/seed/multi-sport-hall/800/600",
        "rating": Decimal("4.3"),
        "availability": True,
    },
)
