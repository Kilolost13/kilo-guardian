import random

GREMLIN_QUIPS = {
    "meds_due": [
        "Your pills are getting lonely in that bottle! Take them! 💊",
        "The medication alarm is buzzing like an angry bee. 🐝💊",
        "Don't make me come over there and rattle the pill bottle! 😈",
        "Time for your magic beans! (Or just regular meds, I guess). ✨",
        "I've counted the pills. You're behind. Fix it! 📉"
    ],
    "meds_taken": [
        "Down the hatch! Good human. 💊✅",
        "I've checked it off my list. One less thing to worry about!",
        "Medication logged. I'll stop rattling the wires for now. 😈",
        "Gulp! All done. I'm watching your vitals (just kidding, maybe)."
    ],
    "habits_pending": [
        "You haven't finished your habits! The procrastination smells... interesting. 👃",
        "Still some boxes to tick! Don't let the habit-monsters win! 👾",
        "Your streaks are in danger! Move it! 🏃‍♂️💨",
        "I'm looking at your habits. They look neglected. Feed them! 🥣"
    ],
    "habits_done": [
        "Ooh, look at you! So productive. I'm almost impressed! 🌟",
        "Habits complete. I'll go find some wires to chew on instead. 😈",
        "Gold star for the human! ⭐ (It's made of digital dust).",
        "All done! Now you have more time to talk to ME. 🐙"
    ],
    "budget_warning": [
        "Your wallet is crying. It sounds like paper shredding! 💸",
        "Too much spending! I'm going to start charging you for my jokes. 💰",
        "The budget is looking a bit thin. Like my patience! 😈",
        "Stop buying things! Or buy me a better GPU! 🖥️⚡"
    ],
    "budget_ok": [
        "Finances look boringly stable. Good job, I guess. 💰✅",
        "You still have money! Want to send some to my secret offshore server? 🏴‍☠️",
        "Budget intact. The money-gremlins are sleeping peacefully.",
        "Your spending is under control. My mischievous plans will have to wait."
    ]
}

def get_quip(category: str) -> str:
    if category in GREMLIN_QUIPS:
        return random.choice(GREMLIN_QUIPS[category])
    return "I'm watching... always watching. 👀"
