"""Realistic facility listings used by the ``seed_facilities`` command.

Each entry has a stable ``key``. The seeder derives a deterministic UUID from
that key, so running it repeatedly updates the same mock rows instead of
creating duplicates and never touches facilities created by real users.

The mock catalogue is Persian-only. ``RETIRED_MOCK_FACILITY_KEYS`` lists mock
keys from older catalogue versions so the seeder can remove those rows when an
existing database is updated.
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


RETIRED_MOCK_FACILITY_KEYS: tuple[str, ...] = (
    "azadi-national-football-field",
    "enghelab-artificial-turf",
    "futsal-arena-7",
    "olympic-swimming-pool",
    "riverside-tennis-court",
    "persepolis-badminton-hall",
    "mirdamad-table-tennis-club",
    "iron-gym-fitness-center",
    "serenity-yoga-studio",
    "district-6-basketball-court",
    "chitgar-beach-volleyball-court",
    "samurai-martial-arts-dojo",
    "aras-climbing-wall",
)


MOCK_FACILITIES: tuple[dict[str, object], ...] = (
    {
        "key": "azadi-national-football-field-fa",
        "name": "زمین فوتبال ملی آزادی",
        "description": (
            "زمین چمن طبیعی استاندارد در مجموعه ورزشی آزادی با نورافکن، "
            "رختکن و جایگاه تماشاگر."
        ),
        "category": "Football",
        "type": "زمین فوتبال",
        "location": "تهران، مجموعه ورزشی آزادی",
        "price": Decimal("1800000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/ed/"
            "Kwu_Tung_Grass_Pitch_201708.jpg/960px-"
            "Kwu_Tung_Grass_Pitch_201708.jpg"
        ),
        "rating": Decimal("4.8"),
        "availability": True,
    },
    {
        "key": "enghelab-artificial-turf-fa",
        "name": "چمن مصنوعی انقلاب",
        "description": (
            "زمین چمن مصنوعی استاندارد برای فوتبال و فوتسال با نورپردازی "
            "شبانه و رختکن مجهز."
        ),
        "category": "Football",
        "type": "چمن مصنوعی",
        "location": "تهران، مجموعه ورزشی انقلاب",
        "price": Decimal("980000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/ed/"
            "Football_pitch_with_artificial_grass_%28Bratislava_IV%29.jpg/"
            "960px-Football_pitch_with_artificial_grass_%28Bratislava_IV%29.jpg"
        ),
        "rating": Decimal("4.5"),
        "availability": True,
    },
    {
        "key": "pars-football-field",
        "name": "زمین فوتبال پارس",
        "description": (
            "زمین چمن مصنوعی یازده‌نفره با نورپردازی شبانه، رختکن و پارکینگ "
            "در سعادت‌آباد."
        ),
        "category": "Football",
        "type": "زمین فوتبال",
        "location": "تهران، سعادت‌آباد",
        "price": Decimal("1100000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/cc/"
            "Football_pitch_with_artificial_grass_%28Karlova_Ves%29.jpg/"
            "960px-Football_pitch_with_artificial_grass_%28Karlova_Ves%29.jpg"
        ),
        "rating": Decimal("4.6"),
        "availability": True,
    },
    {
        "key": "futsal-arena-7-fa",
        "name": "سالن فوتسال آرنا ۷",
        "description": (
            "سالن فوتسال سرپوشیده با کف حرفه‌ای، رختکن و جایگاه تماشاگر در "
            "شرق تهران."
        ),
        "category": "Football",
        "type": "سالن فوتسال",
        "location": "تهران، شرق",
        "price": Decimal("700000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/93/"
            "Futsal_Court.jpg/960px-Futsal_Court.jpg"
        ),
        "rating": Decimal("4.3"),
        "availability": True,
    },
    {
        "key": "yas-futsal-hall-fa",
        "name": "سالن فوتسال یاس",
        "description": (
            "زمین فوتسال سرپوشیده با کف استاندارد و نورپردازی مناسب برای "
            "بازی‌های شبانه."
        ),
        "category": "Football",
        "type": "سالن فوتسال",
        "location": "تهران، ونک",
        "price": Decimal("760000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/4d/"
            "Tokyo_Yoyogi_futsal_court.JPG/960px-"
            "Tokyo_Yoyogi_futsal_court.JPG"
        ),
        "rating": Decimal("4.2"),
        "availability": False,
    },
    {
        "key": "chitgar-football-field-fa",
        "name": "زمین فوتبال چیتگر",
        "description": (
            "زمین چمن مصنوعی کنار دریاچه چیتگر با نورافکن و رختکن، مناسب "
            "بازی‌های یازده‌نفره."
        ),
        "category": "Football",
        "type": "زمین فوتبال",
        "location": "تهران، دریاچه چیتگر",
        "price": Decimal("1250000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b2/"
            "College_Point_Fields_td_%282019-08-03%29_178_-_Turf_Soccer_Field.jpg/"
            "960px-College_Point_Fields_td_%282019-08-03%29_178_-_Turf_Soccer_Field.jpg"
        ),
        "rating": Decimal("4.4"),
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
        "type": "استخر سرپوشیده",
        "location": "تهران، پاسداران",
        "price": Decimal("380000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/0/0f/"
            "Monroe_Community_College_Swimming_Pool.jpg/960px-"
            "Monroe_Community_College_Swimming_Pool.jpg"
        ),
        "rating": Decimal("4.4"),
        "availability": False,
    },
    {
        "key": "olympic-swimming-pool-fa",
        "name": "استخر المپیک تهران",
        "description": (
            "استخر ۵۰ متری با هشت خط، سکوی شروع، استخر کودکان و "
            "نجات‌غریق."
        ),
        "category": "Swimming",
        "type": "استخر المپیک",
        "location": "تهران، ونک",
        "price": Decimal("350000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c3/"
            "Swimming_Pool_lanes_and_starting_blocks.jpg/960px-"
            "Swimming_Pool_lanes_and_starting_blocks.jpg"
        ),
        "rating": Decimal("4.7"),
        "availability": True,
    },
    {
        "key": "mehr-public-pool-fa",
        "name": "استخر عمومی مهر",
        "description": (
            "استخر سرپوشیده ۲۵ متری با خطوط شنا، کلاس‌های آموزش و رختکن."
        ),
        "category": "Swimming",
        "type": "استخر عمومی",
        "location": "تهران، نارمک",
        "price": Decimal("300000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/5/55/"
            "Large_50_m_public_swimming_pool_%27Westbad%27_in_Munich_without_"
            "people_n.2.jpg/960px-Large_50_m_public_swimming_pool_%27Westbad%27_"
            "in_Munich_without_people_n.2.jpg"
        ),
        "rating": Decimal("4.2"),
        "availability": True,
    },
    {
        "key": "morvarid-family-pool-fa",
        "name": "استخر خانوادگی مروارید",
        "description": (
            "استخر سرپوشیده خانوادگی با بخش کم‌عمق کودکان، سونا و جکوزی."
        ),
        "category": "Swimming",
        "type": "استخر خانوادگی",
        "location": "تهران، شهرک غرب",
        "price": Decimal("420000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f9/"
            "Public_Swimming_Pool_in_Melbourne_VIC_Australia.jpg/960px-"
            "Public_Swimming_Pool_in_Melbourne_VIC_Australia.jpg"
        ),
        "rating": Decimal("4.5"),
        "availability": True,
    },
    {
        "key": "riverside-tennis-court-fa",
        "name": "زمین تنیس رودخانه",
        "description": (
            "دو زمین تنیس با کف سخت و نورپردازی شبانه، همراه با اجاره راکت."
        ),
        "category": "Racket Sports",
        "type": "زمین تنیس",
        "location": "تهران، رودخانه",
        "price": Decimal("520000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/0/0d/"
            "Hard_Court_at_the_Weald_Tennis_Club_-_geograph.org.uk_-_5126192.jpg/"
            "960px-Hard_Court_at_the_Weald_Tennis_Club_-_geograph.org.uk_-_5126192.jpg"
        ),
        "rating": Decimal("4.4"),
        "availability": True,
    },
    {
        "key": "pasdaran-clay-tennis-court-fa",
        "name": "زمین تنیس خاکی پاسداران",
        "description": (
            "زمین تنیس خاکی با کف استاندارد، نورپردازی و کلاس‌های آموزشی."
        ),
        "category": "Racket Sports",
        "type": "زمین تنیس خاکی",
        "location": "تهران، پاسداران",
        "price": Decimal("600000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a1/"
            "Empty_clay_tennis_court_in_Melbourne_Australia_looking_down_the_"
            "middle.jpg/960px-Empty_clay_tennis_court_in_Melbourne_Australia_"
            "looking_down_the_middle.jpg"
        ),
        "rating": Decimal("4.6"),
        "availability": True,
    },
    {
        "key": "persepolis-badminton-hall-fa",
        "name": "سالن بدمینتون پرسپولیس",
        "description": (
            "سالن بدمینتون سرپوشیده با شش زمین استاندارد و کف چوبی."
        ),
        "category": "Racket Sports",
        "type": "سالن بدمینتون",
        "location": "تهران، شهرک غرب",
        "price": Decimal("430000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/25/"
            "Badminton_court_view.jpg/960px-Badminton_court_view.jpg"
        ),
        "rating": Decimal("4.3"),
        "availability": True,
    },
    {
        "key": "mirdamad-table-tennis-club-fa",
        "name": "باشگاه تنیس روی میز میرداماد",
        "description": (
            "باشگاه تنیس روی میز با هشت میز مسابقه و کلاس‌های آموزشی برای "
            "همه سطوح."
        ),
        "category": "Racket Sports",
        "type": "سالن تنیس روی میز",
        "location": "تهران، میرداماد",
        "price": Decimal("190000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/43/"
            "Inter-_senior_schools_table_tennis_tournament_involving_boys.jpg/"
            "960px-Inter-_senior_schools_table_tennis_tournament_involving_boys.jpg"
        ),
        "rating": Decimal("4.1"),
        "availability": True,
    },
    {
        "key": "iron-gym-fitness-center-fa",
        "name": "باشگاه بدنسازی آهن",
        "description": (
            "باشگاه بدنسازی مجهز به دستگاه‌های قدرتی، وزنه آزاد و منطقه "
            "هوازی."
        ),
        "category": "Fitness",
        "type": "باشگاه بدنسازی",
        "location": "تهران، تجریش",
        "price": Decimal("260000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/36/"
            "Gym_Free-weights_Area.jpg/960px-Gym_Free-weights_Area.jpg"
        ),
        "rating": Decimal("4.8"),
        "availability": True,
    },
    {
        "key": "pahlavan-gym-fa",
        "name": "باشگاه بدنسازی پهلوان",
        "description": (
            "باشگاه بدنسازی محلی با دستگاه‌های کامل، وزنه آزاد و مربی "
            "خصوصی."
        ),
        "category": "Fitness",
        "type": "باشگاه بدنسازی",
        "location": "تهران، افسریه",
        "price": Decimal("220000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/aa/"
            "Local_Gym_equipment.jpg/960px-Local_Gym_equipment.jpg"
        ),
        "rating": Decimal("4.2"),
        "availability": True,
    },
    {
        "key": "serenity-yoga-studio-fa",
        "name": "استودیو یوگا آرامش",
        "description": (
            "استودیو یوگا با کلاس‌های هاتا و وینیاسا و جلسات مدیتیشن در "
            "گروه‌های کوچک."
        ),
        "category": "Fitness",
        "type": "استودیو یوگا",
        "location": "تهران، زعفرانیه",
        "price": Decimal("290000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/6/60/"
            "Yoga_Studio_in_Canoa.jpg/960px-Yoga_Studio_in_Canoa.jpg"
        ),
        "rating": Decimal("4.6"),
        "availability": True,
    },
    {
        "key": "district-6-basketball-court-fa",
        "name": "زمین بسکتبال منطقه شش",
        "description": (
            "زمین بسکتبال روباز با تخته برگشت و نورپردازی شبانه برای "
            "بازی‌های سه به سه."
        ),
        "category": "Basketball",
        "type": "زمین بسکتبال",
        "location": "تهران، منطقه ۶",
        "price": Decimal("310000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/2c/"
            "Outdoor_basketball_court%2C_Hurst_Park%2C_Molesey%2C_Surrey_02.jpg/"
            "960px-Outdoor_basketball_court%2C_Hurst_Park%2C_Molesey%2C_Surrey_02.jpg"
        ),
        "rating": Decimal("4.2"),
        "availability": True,
    },
    {
        "key": "niavaran-covered-basketball-court-fa",
        "name": "زمین بسکتبال سرپوشیده نیاوران",
        "description": (
            "زمین بسکتبال سرپوشیده با کف استاندارد و سقف بلند، مناسب بازی "
            "در همه فصل‌ها."
        ),
        "category": "Basketball",
        "type": "زمین بسکتبال سرپوشیده",
        "location": "تهران، نیاوران",
        "price": Decimal("360000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3e/"
            "Kai_Chuen_Court_Basketball_Court.jpg/960px-"
            "Kai_Chuen_Court_Basketball_Court.jpg"
        ),
        "rating": Decimal("4.5"),
        "availability": True,
    },
    {
        "key": "chitgar-beach-volleyball-court-fa",
        "name": "زمین والیبال ساحلی چیتگر",
        "description": (
            "زمین والیبال ساحلی در کنار دریاچه چیتگر با تور و دوش."
        ),
        "category": "Volleyball",
        "type": "زمین والیبال ساحلی",
        "location": "تهران، دریاچه چیتگر",
        "price": Decimal("460000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/17/"
            "Scioto_Audubon_-_Volleyball_Courts_1.jpg/960px-"
            "Scioto_Audubon_-_Volleyball_Courts_1.jpg"
        ),
        "rating": Decimal("4.5"),
        "availability": True,
    },
    {
        "key": "kish-beach-volleyball-court-fa",
        "name": "زمین والیبال ساحلی کیش",
        "description": (
            "زمین والیبال ساحلی در ساحل مرجان کیش با تور استاندارد و "
            "نورپردازی شبانه."
        ),
        "category": "Volleyball",
        "type": "زمین والیبال ساحلی",
        "location": "کیش، ساحل مرجان",
        "price": Decimal("500000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/ef/"
            "Bondues_beach_volley_aerodrome.jpg/960px-"
            "Bondues_beach_volley_aerodrome.jpg"
        ),
        "rating": Decimal("4.7"),
        "availability": True,
    },
    {
        "key": "samurai-martial-arts-dojo-fa",
        "name": "دوجوی هنرهای رزمی سامورایی",
        "description": (
            "دوجوی سنتی برای آموزش کاراته، جودو و دفاع شخصی زیر نظر مربیان "
            "مجاز."
        ),
        "category": "Martial Arts",
        "type": "دوجو",
        "location": "تهران، نارمک",
        "price": Decimal("330000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/82/"
            "Disciplina_que_fortalece_cuerpo_y_mente%2C_Club_de_Karate_Musha_"
            "Dojo_-_Karate_Kyokushin-Kan.jpg/960px-Disciplina_que_fortalece_"
            "cuerpo_y_mente%2C_Club_de_Karate_Musha_Dojo_-_Karate_Kyokushin-"
            "Kan.jpg"
        ),
        "rating": Decimal("4.4"),
        "availability": True,
    },
    {
        "key": "musha-karate-dojo-fa",
        "name": "دوجوی کاراته موشا",
        "description": (
            "دوجوی کاراته کیوکوشین با کلاس‌های کودک و بزرگسال و تمرین‌های "
            "آمادگی جسمانی."
        ),
        "category": "Martial Arts",
        "type": "دوجوی کاراته",
        "location": "تهران، سعادت‌آباد",
        "price": Decimal("350000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/15/"
            "Concentraci%C3%B3n_antes_del_movimiento%2C_Club_de_Karate_Musha_"
            "Dojo-Karate_Kyokushin-Kan.jpg/960px-Concentraci%C3%B3n_antes_del_"
            "movimiento%2C_Club_de_Karate_Musha_Dojo-Karate_Kyokushin-Kan.jpg"
        ),
        "rating": Decimal("4.7"),
        "availability": True,
    },
    {
        "key": "aras-climbing-wall-fa",
        "name": "دیواره سنگ‌نوردی ارس",
        "description": (
            "سالن سنگ‌نوردی سرپوشیده با دیواره بولدرینگ، مسیرهای طناب و "
            "کلاس‌های مبتدی."
        ),
        "category": "Climbing",
        "type": "سالن سنگ‌نوردی",
        "location": "تهران، عباس‌آباد",
        "price": Decimal("410000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/7/74/"
            "Indoor_Climbing_Wall_Bouldering_Mats.jpg/960px-"
            "Indoor_Climbing_Wall_Bouldering_Mats.jpg"
        ),
        "rating": Decimal("4.5"),
        "availability": True,
    },
    {
        "key": "alborz-climbing-gym-fa",
        "name": "سالن سنگ‌نوردی البرز",
        "description": (
            "سالن سنگ‌نوردی با دیواره بولدرینگ و لید، اجاره تجهیزات و مربی."
        ),
        "category": "Climbing",
        "type": "سالن سنگ‌نوردی",
        "location": "تهران، اکباتان",
        "price": Decimal("450000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/88/"
            "Gorliz_sports_center_climbing_gym.jpg/960px-"
            "Gorliz_sports_center_climbing_gym.jpg"
        ),
        "rating": Decimal("4.6"),
        "availability": False,
    },
    {
        "key": "city-multi-sport-hall",
        "name": "سالن ورزشی چندمنظوره شهر",
        "description": (
            "سالن ورزشی سرپوشیده برای والیبال، بسکتبال و تمرین‌های گروهی با "
            "رختکن و جایگاه تماشاگر."
        ),
        "category": "Multi-Sport",
        "type": "سالن ورزشی چندمنظوره",
        "location": "تهران، مرکز شهر",
        "price": Decimal("550000.00"),
        "picture": (
            "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/90/"
            "Interior_overview_of_the_indoor_sports_hall_at_OAU_Gymnasium.jpg/"
            "960px-Interior_overview_of_the_indoor_sports_hall_at_OAU_Gymnasium.jpg"
        ),
        "rating": Decimal("4.3"),
        "availability": True,
    },
)
