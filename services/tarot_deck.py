TAROT_DECK = {
    # Major Arcana (Старшие Арканы) — 1–22
    1: "Шут (The Fool)",
    2: "Маг (The Magician)",
    3: "Верховная Жрица (The High Priestess)",
    4: "Императрица (The Empress)",
    5: "Император (The Emperor)",
    6: "Иерофант (The Hierophant)",
    7: "Влюблённые (The Lovers)",
    8: "Колесница (The Chariot)",
    9: "Сила (Strength)",
    10: "Отшельник (The Hermit)",
    11: "Колесо Фортуны (Wheel of Fortune)",
    12: "Справедливость (Justice)",
    13: "Повешенный (The Hanged Man)",
    14: "Смерть (Death)",
    15: "Умеренность (Temperance)",
    16: "Дьявол (The Devil)",
    17: "Башня (The Tower)",
    18: "Звезда (The Star)",
    19: "Луна (The Moon)",
    20: "Солнце (The Sun)",
    21: "Суд (Judgement)",
    22: "Мир (The World)",
    # Wands (Жезлы) — 23–36
    23: "Туз Жезлов (Ace of Wands)",
    24: "Двойка Жезлов (Two of Wands)",
    25: "Тройка Жезлов (Three of Wands)",
    26: "Четвёрка Жезлов (Four of Wands)",
    27: "Пятёрка Жезлов (Five of Wands)",
    28: "Шестёрка Жезлов (Six of Wands)",
    29: "Семёрка Жезлов (Seven of Wands)",
    30: "Восьмёрка Жезлов (Eight of Wands)",
    31: "Девятка Жезлов (Nine of Wands)",
    32: "Десятка Жезлов (Ten of Wands)",
    33: "Паж Жезлов (Page of Wands)",
    34: "Рыцарь Жезлов (Knight of Wands)",
    35: "Королева Жезлов (Queen of Wands)",
    36: "Король Жезлов (King of Wands)",
    # Cups (Кубки) — 37–50
    37: "Туз Кубков (Ace of Cups)",
    38: "Двойка Кубков (Two of Cups)",
    39: "Тройка Кубков (Three of Cups)",
    40: "Четвёрка Кубков (Four of Cups)",
    41: "Пятёрка Кубков (Five of Cups)",
    42: "Шестёрка Кубков (Six of Cups)",
    43: "Семёрка Кубков (Seven of Cups)",
    44: "Восьмёрка Кубков (Eight of Cups)",
    45: "Девятка Кубков (Nine of Cups)",
    46: "Десятка Кубков (Ten of Cups)",
    47: "Паж Кубков (Page of Cups)",
    48: "Рыцарь Кубков (Knight of Cups)",
    49: "Королева Кубков (Queen of Cups)",
    50: "Король Кубков (King of Cups)",
    # Swords (Мечи) — 51–64
    51: "Туз Мечей (Ace of Swords)",
    52: "Двойка Мечей (Two of Swords)",
    53: "Тройка Мечей (Three of Swords)",
    54: "Четвёрка Мечей (Four of Swords)",
    55: "Пятёрка Мечей (Five of Swords)",
    56: "Шестёрка Мечей (Six of Swords)",
    57: "Семёрка Мечей (Seven of Swords)",
    58: "Восьмёрка Мечей (Eight of Swords)",
    59: "Девятка Мечей (Nine of Swords)",
    60: "Десятка Мечей (Ten of Swords)",
    61: "Паж Мечей (Page of Swords)",
    62: "Рыцарь Мечей (Knight of Swords)",
    63: "Королева Мечей (Queen of Swords)",
    64: "Король Мечей (King of Swords)",
    # Pentacles (Пентакли) — 65–78
    65: "Туз Пентаклей (Ace of Pentacles)",
    66: "Двойка Пентаклей (Two of Pentacles)",
    67: "Тройка Пентаклей (Three of Pentacles)",
    68: "Четвёрка Пентаклей (Four of Pentacles)",
    69: "Пятёрка Пентаклей (Five of Pentacles)",
    70: "Шестёрка Пентаклей (Six of Pentacles)",
    71: "Семёрка Пентаклей (Seven of Pentacles)",
    72: "Восьмёрка Пентаклей (Eight of Pentacles)",
    73: "Девятка Пентаклей (Nine of Pentacles)",
    74: "Десятка Пентаклей (Ten of Pentacles)",
    75: "Паж Пентаклей (Page of Pentacles)",
    76: "Рыцарь Пентаклей (Knight of Pentacles)",
    77: "Королева Пентаклей (Queen of Pentacles)",
    78: "Король Пентаклей (King of Pentacles)",
}


FILE_TO_CARD = {
    "00-TheFool.png": 1,
    "01-TheMagician.png": 2,
    "02-TheHighPriestess.png": 3,
    "03-TheEmpress.png": 4,
    "04-TheEmperor.png": 5,
    "05-TheHierophant.png": 6,
    "06-TheLovers.png": 7,
    "07-TheChariot.png": 8,
    "08-Strength.png": 9,
    "09-TheHermit.png": 10,
    "10-WheelOfFortune.png": 11,
    "11-Justice.png": 12,
    "12-TheHangedMan.png": 13,
    "13-Death.png": 14,
    "14-Temperance.png": 15,
    "15-TheDevil.png": 16,
    "16-TheTower.png": 17,
    "17-TheStar.png": 18,
    "18-TheMoon.png": 19,
    "19-TheSun.png": 20,
    "20-Judgement.png": 21,
    "21-TheWorld.png": 22,
}

for suit in ("Wands", "Cups", "Swords", "Pentacles"):
    for num in range(1, 15):
        filename = f"{suit}{num:02d}.png"
        base_idx = {"Wands": 23, "Cups": 37, "Swords": 51, "Pentacles": 65}[suit]
        FILE_TO_CARD[filename] = base_idx + (num - 1)


def card_image_path(card_number: int) -> str:
    for filename, num in FILE_TO_CARD.items():
        if num == card_number:
            return f"assets/cards/{filename}"
    return ""


def random_card() -> tuple[int, str]:
    import random
    num = random.randint(1, 78)
    return num, TAROT_DECK[num]


def card_by_seed(seed: str) -> tuple[int, str]:
    import hashlib
    num = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % 78 + 1
    return num, TAROT_DECK[num]
