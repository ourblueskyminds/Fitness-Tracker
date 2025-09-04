import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date, timedelta
import calendar
import random
import streamlit.components.v1 as components

QUOTES = [
    "Strength is Earned, Not Given",
    "Lift Heavy, Live Bold",
    "Push Through, Power Up",
    "No Excuses, Just Results",
    "Grind Now, Glory Later",
    "Dominate the Bar, Conquer the Mats",
    "Grind Hard, Win Easy",
    "Power Through, PR Awaits"
]

WARM_UPS = {
    "Strength": [
        {"name": "Leg Swings", "description": "2x10/leg, swing leg forward-backward to improve hip mobility for squats and deadlifts. Keep core braced."},
        {"name": "Arm Circles", "description": "2x10/arm, forward and backward, to warm up shoulders for pull-ups or cleans. Controlled motion."},
        {"name": "Bodyweight Squats", "description": "2x15, slow tempo to activate quads, glutes, hamstrings. Focus on depth and form."},
        {"name": "Dynamic Hamstring Stretch", "description": "2x10/leg, lunge forward and straighten leg to stretch hamstrings. Preps for deadlifts."},
        {"name": "Scapular Push-Ups", "description": "2x12, on hands and knees, retract/protract shoulders to prime upper back for pulls."}
    ],
    "Conditioning": [
        {"name": "Shrimping", "description": "2x10/side, BJJ-specific hip escape movement to warm up hips and core for sprints or ropes."},
        {"name": "High Knees", "description": "2x20 sec, fast-paced to elevate heart rate and prep for conditioning. Keep arms pumping."},
        {"name": "Butt Kicks", "description": "2x20 sec, jog while kicking heels to glutes to warm up hamstrings for sprints."},
        {"name": "Lateral Lunges", "description": "2x10/side, step side-to-side to activate hips and adductors for agility drills."},
        {"name": "Mountain Climbers", "description": "2x20 sec, fast-paced to warm up core and shoulders for conditioning intensity."}
    ],
    "Rest": [
        {"name": "Cat-Cow Stretch", "description": "2x10, flow between arched and rounded spine to improve spinal mobility and recovery."},
        {"name": "Foam Rolling", "description": "5 min, target quads, hamstrings, or back to release tightness. Slow, controlled pressure."},
        {"name": "Child’s Pose", "description": "2x30 sec, stretch hips and lower back for recovery. Breathe deeply."},
        {"name": "Seated Forward Fold", "description": "2x30 sec, stretch hamstrings and lower back. Keep spine long, avoid rounding."},
        {"name": "Neck Rolls", "description": "2x10/side, gentle circles to release neck tension. Move slowly to avoid strain."}
    ]
}

ACHIEVEMENTS = [
    {"name": "Iron Novice", "emoji": "🏅", "condition": lambda data: len(data[data["Type"] == "Workout"]) >= 10, "description": "Log 10 workouts"},
    {"name": "Grip Titan", "emoji": "💪", "condition": lambda data: sum(1 for _, row in data.iterrows() if row["Exercise/Note"] in ["Deadlifts", "Farmer’s Carry", "Weighted Pull-Ups"] and "Success" in row["Notes"]) >= 50, "description": "50 successful grip exercise sets"},
    {"name": "Strength Beast", "emoji": "🏋️‍♂️", "condition": lambda data, onerms: any(new > old for ex, new in onerms.items() for _, row in data.iterrows() if ex in row["Exercise/Note"] and "1RM" in row["Notes"] and float(row["Notes"].split("1RM: ")[1].split()[0]) < new), "description": "Hit a 1RM PR"},
    {"name": "Sprint King", "emoji": "🏃", "condition": lambda data: sum(1 for _, row in data.iterrows() if row["Exercise/Note"] in ["Sprints", "Sprint Drills"] and "Success" in row["Notes"]) >= 50, "description": "50 successful sprint/conditioning sets"},
    {"name": "Recovery Pro", "emoji": "🥗", "condition": lambda data: len(data[data["Type"] == "Other"]) >= 7, "description": "7 consecutive recovery logs"},
    {"name": "Consistency Champ", "emoji": "🔥", "condition": lambda data: any((pd.to_datetime(data["Date"]).diff().dt.days <= 1).rolling(5).sum() >= 5), "description": "Log workouts 5 days in a row"},
    {"name": "BJJ Grinder", "emoji": "🥋", "condition": lambda data: sum(1 for _, row in data.iterrows() if row["Day"] in ["Day 1: Strength & Power", "Day 2: Conditioning & Core", "Day 3: Strength & Explosive Power"] and "Success" in row["Notes"]) >= 20, "description": "20 BJJ program sets"},
    {"name": "Power Surge", "emoji": "⚡", "condition": lambda data: sum(1 for _, row in data.iterrows() if "Success" in row["Notes"] and any(rpe in row["Details"] for rpe in ["RPE 8", "RPE 8-9", "RPE 9"])) >= 10, "description": "10 successful RPE 8+ sets"}
]

ACHIEVEMENTS_FILE = "achievements.json"
def save_achievements(achievements):
    with open(ACHIEVEMENTS_FILE, 'w') as f:
        json.dump(achievements, f, indent=4)

def load_achievements():
    if os.path.exists(ACHIEVEMENTS_FILE):
        with open(ACHIEVEMENTS_FILE, 'r') as f:
            return json.load(f)
    return {ach["name"]: False for ach in ACHIEVEMENTS}

def check_achievements():
    df = load_progress()
    onerms = load_1rms()
    achievements = load_achievements()
    new_achievements = []
    for ach in ACHIEVEMENTS:
        if not achievements.get(ach["name"], False):
            try:
                if ach["condition"](df, onerms) if "onerms" in ach["condition"].__code__.co_varnames else ach["condition"](df):
                    achievements[ach["name"]] = True
                    new_achievements.append(ach)
            except Exception as e:
                print(f"Error checking achievement {ach['name']}: {str(e)}")
    save_achievements(achievements)
    return new_achievements

DEFAULT_PROGRAM = {
    "name": "12-Week Strength & Running",
    "duration_weeks": 12,
    "description": "Weeks 1-4 Base, 5-8 Intensity, 9-12 Peaking. 4 days/week, 60-90 min. Focus: squats, 5k, sprints.",
    "days": {
        "Day 1: Leg Strength/Hypertrophy A": {
            "description": "Build lower body strength with compound lifts. Warm up 5-10 min, rest 2-3 min.",
            "exercises": ["SSB Back Squat", "Leg Press", "Bulgarian Split Squats", "Lying Leg Curls", "Calf Raises"],
            "schedule": [0]
        },
        "Day 2: Running/Endurance": {
            "description": "Develop aerobic capacity for 5k. Warm up 5 min, RPE 6-7.",
            "exercises": ["Walk/Run Intervals", "Core (Planks, etc.)"],
            "schedule": [1]
        },
        "Day 3: Leg Strength/Hypertrophy B": {
            "description": "Focus on posterior chain/unilateral lifts. Warm up 5-10 min, rest 2-3 min.",
            "exercises": ["Hack Squat", "Romanian Deadlifts", "Step-Ups", "Glute-Ham Raises", "Seated Calf Raises"],
            "schedule": [3]
        },
        "Day 4: Speed/Plyo": {
            "description": "Build explosive power/speed. Warm up 10-15 min, rest 60-90s.",
            "exercises": ["Sprint Drills", "Box Jumps", "Long Jumps", "Bounding", "Sled Pushes"],
            "schedule": [4]
        }
    },
    "prescriptions": {
        "Day 1: Leg Strength/Hypertrophy A": {
            "Base": {
                "SSB Back Squat": {"sets": "3-4", "reps": "6-10", "percent_1rm": (0.65, 0.75), "rpe": "7-8", "rest": 120},
                "Leg Press": {"sets": "3", "reps": "10-12", "percent_1rm": (0.65, 0.75), "rpe": "8", "rest": 90},
                "Bulgarian Split Squats": {"sets": "3", "reps": "8-10/leg", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Lying Leg Curls": {"sets": "3", "reps": "12-15", "percent_1rm": (0.65, 0.75), "rpe": "8", "rest": 60},
                "Calf Raises": {"sets": "3", "reps": "15-20", "percent_1rm": (0.65, 0.75), "rpe": "7-8", "rest": 60}
            },
            "Intensity": {
                "SSB Back Squat": {"sets": "3", "reps": "4-8", "percent_1rm": (0.75, 0.85), "rpe": "7-8", "rest": 120},
                "Leg Press": {"sets": "3", "reps": "8-10", "percent_1rm": (0.75, 0.85), "rpe": "8", "rest": 90},
                "Bulgarian Split Squats": {"sets": "3", "reps": "8-10/leg", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Lying Leg Curls": {"sets": "3", "reps": "10-12", "percent_1rm": (0.75, 0.85), "rpe": "8", "rest": 60},
                "Calf Raises": {"sets": "3", "reps": "12-15", "percent_1rm": (0.75, 0.85), "rpe": "7-8", "rest": 60}
            },
            "Peaking": {
                "SSB Back Squat": {"sets": "2-3", "reps": "3-6", "percent_1rm": (0.85, 0.95), "rpe": "7-8", "rest": 120},
                "Leg Press": {"sets": "2-3", "reps": "6-8", "percent_1rm": (0.85, 0.95), "rpe": "8", "rest": 90},
                "Bulgarian Split Squats": {"sets": "3", "reps": "6-8/leg", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Lying Leg Curls": {"sets": "2-3", "reps": "8-10", "percent_1rm": (0.85, 0.95), "rpe": "8", "rest": 60},
                "Calf Raises": {"sets": "2-3", "reps": "10-12", "percent_1rm": (0.85, 0.95), "rpe": "7-8", "rest": 60}
            }
        },
        "Day 2: Running/Endurance": {
            "Base": {
                "Walk/Run Intervals": {"duration": "30-40 min", "distance": "3-5 km", "pace": "6-7 min/km", "rpe": "6-7", "rest": 60},
                "Core (Planks, etc.)": {"sets": "3", "reps": "30-60 sec", "percent_1rm": (0, 0), "rpe": "6-7", "rest": 60}
            },
            "Intensity": {
                "Walk/Run Intervals": {"duration": "40-50 min", "distance": "5-8 km", "pace": "5.5-6.5 min/km", "rpe": "6-7", "rest": 60},
                "Core (Planks, etc.)": {"sets": "3", "reps": "45-60 sec", "percent_1rm": (0, 0), "rpe": "6-7", "rest": 60}
            },
            "Peaking": {
                "Walk/Run Intervals": {"duration": "50-60 min", "distance": "8-10 km, aim 5k in 25 min", "pace": "~5 min/km", "rpe": "6-7", "rest": 60},
                "Core (Planks, etc.)": {"sets": "3", "reps": "60 sec", "percent_1rm": (0, 0), "rpe": "6-7", "rest": 60}
            }
        },
        "Day 3: Leg Strength/Hypertrophy B": {
            "Base": {
                "Hack Squat": {"sets": "3-4", "reps": "8-12", "percent_1rm": (0.65, 0.75), "rpe": "7-8", "rest": 120},
                "Romanian Deadlifts": {"sets": "3", "reps": "8-10", "percent_1rm": (0.65, 0.75), "rpe": "8", "rest": 90},
                "Step-Ups": {"sets": "3", "reps": "10/leg", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Glute-Ham Raises": {"sets": "3", "reps": "6-8", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Seated Calf Raises": {"sets": "3", "reps": "12-15", "percent_1rm": (0.65, 0.75), "rpe": "7-8", "rest": 60}
            },
            "Intensity": {
                "Hack Squat": {"sets": "3", "reps": "6-10", "percent_1rm": (0.75, 0.85), "rpe": "7-8", "rest": 120},
                "Romanian Deadlifts": {"sets": "3", "reps": "6-8", "percent_1rm": (0.75, 0.85), "rpe": "8", "rest": 90},
                "Step-Ups": {"sets": "3", "reps": "8-10/leg", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Glute-Ham Raises": {"sets": "3", "reps": "6-8", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Seated Calf Raises": {"sets": "3", "reps": "10-12", "percent_1rm": (0.75, 0.85), "rpe": "7-8", "rest": 60}
            },
            "Peaking": {
                "Hack Squat": {"sets": "2-3", "reps": "4-8", "percent_1rm": (0.85, 0.95), "rpe": "7-8", "rest": 120},
                "Romanian Deadlifts": {"sets": "2-3", "reps": "4-6", "percent_1rm": (0.85, 0.95), "rpe": "8", "rest": 90},
                "Step-Ups": {"sets": "2-3", "reps": "6-8/leg", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Glute-Ham Raises": {"sets": "2-3", "reps": "6-8", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Seated Calf Raises": {"sets": "2-3", "reps": "8-10", "percent_1rm": (0.85, 0.95), "rpe": "7-8", "rest": 60}
            }
        },
        "Day 4: Speed/Plyo": {
            "Base": {
                "Sprint Drills": {"sets": "4-6", "reps": "50-100m", "effort": "80%", "rpe": "7-8", "rest": 90},
                "Box Jumps": {"sets": "3-4", "reps": "4-6", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 90},
                "Long Jumps": {"sets": "3", "reps": "4-6", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 90},
                "Bounding": {"sets": "3", "reps": "20-30m", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 90},
                "Sled Pushes": {"sets": "3-4", "reps": "20-30m", "percent_1rm": (0.5, 0.75), "rpe": "7-8", "rest": 90}
            },
            "Intensity": {
                "Sprint Drills": {"sets": "6-8", "reps": "50-100m", "effort": "85%", "rpe": "7-8", "rest": 90},
                "Box Jumps": {"sets": "3", "reps": "4-6", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 90},
                "Long Jumps": {"sets": "3", "reps": "4-6", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 90},
                "Bounding": {"sets": "3", "reps": "25-35m", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 90},
                "Sled Pushes": {"sets": "3-4", "reps": "20-30m", "percent_1rm": (0.75, 1.0), "rpe": "7-8", "rest": 90}
            },
            "Peaking": {
                "Sprint Drills": {"sets": "8", "reps": "50-100m", "effort": "near-max", "rpe": "7-8", "rest": 90},
                "Box Jumps": {"sets": "3", "reps": "3-5", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 90},
                "Long Jumps": {"sets": "3", "reps": "3-5", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 90},
                "Bounding": {"sets": "3", "reps": "30-40m", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 90},
                "Sled Pushes": {"sets": "3-4", "reps": "20-30m", "percent_1rm": (1.0, 1.0), "rpe": "7-8", "rest": 90}
            }
        }
    }
}

BJJ_PROGRAM = {
    "name": "8-Week BJJ Strength & Conditioning",
    "duration_weeks": 8,
    "description": "Build strength, power, and conditioning for BJJ. Weeks 1-3 Base, 4-6 Intensity, 7-8 Peaking. 3 days/week, 60-90 min.",
    "days": {
        "Day 1: Strength & Power": {
            "description": "Compound lifts for grip, pulling, lower body strength. Warm up 5-10 min, rest 2-3 min for lifts.",
            "exercises": ["Deadlifts", "Weighted Pull-Ups", "Farmer’s Carry", "Hanging Leg Raises"],
            "schedule": [0]
        },
        "Day 2: Conditioning & Core": {
            "description": "High-intensity conditioning to mimic BJJ anaerobic demands, plus core work. Warm up 5 min, rest 60-90s.",
            "exercises": ["Sprints", "Battle Ropes", "Plank Variations"],
            "schedule": [2]
        },
        "Day 3: Strength & Explosive Power": {
            "description": "Build explosive power and strength for takedowns and scrambles. Warm up 10 min, rest 2-3 min for lifts.",
            "exercises": ["Power Cleans", "Sled Pushes", "Bulgarian Split Squats", "Russian Twists"],
            "schedule": [4]
        }
    },
    "prescriptions": {
        "Day 1: Strength & Power": {
            "Base": {
                "Deadlifts": {"sets": "3-4", "reps": "6-8", "percent_1rm": (0.65, 0.75), "rpe": "7-8", "rest": 120},
                "Weighted Pull-Ups": {"sets": "3", "reps": "8-10", "percent_1rm": (0.65, 0.75), "rpe": "7-8", "rest": 90},
                "Farmer’s Carry": {"sets": "3", "reps": "30-45 sec", "percent_1rm": (0.5, 0.6), "rpe": "7-8", "rest": 60},
                "Hanging Leg Raises": {"sets": "3", "reps": "12-15", "percent_1rm": (0, 0), "rpe": "6-7", "rest": 60}
            },
            "Intensity": {
                "Deadlifts": {"sets": "3", "reps": "4-6", "percent_1rm": (0.75, 0.85), "rpe": "8", "rest": 120},
                "Weighted Pull-Ups": {"sets": "3", "reps": "6-8", "percent_1rm": (0.75, 0.85), "rpe": "8", "rest": 90},
                "Farmer’s Carry": {"sets": "3", "reps": "45-60 sec", "percent_1rm": (0.6, 0.7), "rpe": "8", "rest": 60},
                "Hanging Leg Raises": {"sets": "3", "reps": "15-20", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60}
            },
            "Peaking": {
                "Deadlifts": {"sets": "2-3", "reps": "3-5", "percent_1rm": (0.85, 0.95), "rpe": "8-9", "rest": 150},
                "Weighted Pull-Ups": {"sets": "2-3", "reps": "5-7", "percent_1rm": (0.85, 0.95), "rpe": "8-9", "rest": 90},
                "Farmer’s Carry": {"sets": "3", "reps": "60 sec", "percent_1rm": (0.7, 0.8), "rpe": "8-9", "rest": 60},
                "Hanging Leg Raises": {"sets": "3", "reps": "20", "percent_1rm": (0, 0), "rpe": "8", "rest": 60}
            }
        },
        "Day 2: Conditioning & Core": {
            "Base": {
                "Sprints": {"sets": "6", "reps": "30 sec", "effort": "80%", "rpe": "7-8", "rest": 60},
                "Battle Ropes": {"sets": "4", "reps": "30 sec", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Plank Variations": {"sets": "3", "reps": "30-45 sec", "percent_1rm": (0, 0), "rpe": "6-7", "rest": 60}
            },
            "Intensity": {
                "Sprints": {"sets": "8", "reps": "30 sec", "effort": "85%", "rpe": "8", "rest": 60},
                "Battle Ropes": {"sets": "4", "reps": "45 sec", "percent_1rm": (0, 0), "rpe": "8", "rest": 60},
                "Plank Variations": {"sets": "3", "reps": "45-60 sec", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60}
            },
            "Peaking": {
                "Sprints": {"sets": "10", "reps": "30 sec", "effort": "90%", "rpe": "8-9", "rest": 60},
                "Battle Ropes": {"sets": "4", "reps": "60 sec", "percent_1rm": (0, 0), "rpe": "8-9", "rest": 60},
                "Plank Variations": {"sets": "3", "reps": "60 sec", "percent_1rm": (0, 0), "rpe": "8", "rest": 60}
            }
        },
        "Day 3: Strength & Explosive Power": {
            "Base": {
                "Power Cleans": {"sets": "3-4", "reps": "5-7", "percent_1rm": (0.65, 0.75), "rpe": "7-8", "rest": 120},
                "Sled Pushes": {"sets": "4", "reps": "20-30m", "percent_1rm": (0.5, 0.75), "rpe": "7-8", "rest": 90},
                "Bulgarian Split Squats": {"sets": "3", "reps": "8-10/leg", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60},
                "Russian Twists": {"sets": "3", "reps": "15-20/side", "percent_1rm": (0, 0), "rpe": "6-7", "rest": 60}
            },
            "Intensity": {
                "Power Cleans": {"sets": "3", "reps": "4-6", "percent_1rm": (0.75, 0.85), "rpe": "8", "rest": 120},
                "Sled Pushes": {"sets": "4", "reps": "30-40m", "percent_1rm": (0.75, 1.0), "rpe": "8", "rest": 90},
                "Bulgarian Split Squats": {"sets": "3", "reps": "6-8/leg", "percent_1rm": (0, 0), "rpe": "8", "rest": 60},
                "Russian Twists": {"sets": "3", "reps": "20-25/side", "percent_1rm": (0, 0), "rpe": "7-8", "rest": 60}
            },
            "Peaking": {
                "Power Cleans": {"sets": "2-3", "reps": "3-5", "percent_1rm": (0.85, 0.95), "rpe": "8-9", "rest": 150},
                "Sled Pushes": {"sets": "4", "reps": "40m", "percent_1rm": (1.0, 1.0), "rpe": "8-9", "rest": 90},
                "Bulgarian Split Squats": {"sets": "3", "reps": "5-6/leg", "percent_1rm": (0, 0), "rpe": "8-9", "rest": 60},
                "Russian Twists": {"sets": "3", "reps": "25/side", "percent_1rm": (0, 0), "rpe": "8", "rest": 60}
            }
        }
    }
}

RECOVERY_BEHAVIORS = [
    {"Behavior": "Active Recovery Walk", "Reason": "Reduces soreness, improves mood.", "Mechanism": "Low-intensity movement aids lactate clearance.", "Barrier": "Lack of time; schedule 15-min walk with podcast."},
    {"Behavior": "Foam Rolling", "Reason": "Relieves tightness, enhances flexibility.", "Mechanism": "Myofascial release improves range of motion.", "Barrier": "Discomfort; start with soft rollers, 5-min sessions."},
    {"Behavior": "Hydration Focus", "Reason": "Prevents fatigue, supports repair.", "Mechanism": "Water maintains cellular function.", "Barrier": "Forgetting to drink; keep water bottle nearby."},
    {"Behavior": "Sleep Optimization", "Reason": "Accelerates recovery, hormonal balance.", "Mechanism": "Deep sleep triggers growth hormone.", "Barrier": "Busy schedule; avoid screens before bed."},
    {"Behavior": "Static Stretching", "Reason": "Improves flexibility, reduces injury risk.", "Mechanism": "Lengthens muscle fibers.", "Barrier": "Boredom; pair with music, 10-min sessions."}
]

PROGRAM_LIBRARY_FILE = "program_library.json"
def save_program(program):
    if os.path.exists(PROGRAM_LIBRARY_FILE):
        with open(PROGRAM_LIBRARY_FILE, 'r') as f:
            library = json.load(f)
    else:
        library = [DEFAULT_PROGRAM, BJJ_PROGRAM]
    if program["name"] not in [p["name"] for p in library]:
        library.append(program)
        with open(PROGRAM_LIBRARY_FILE, 'w') as f:
            json.dump(library, f, indent=4)
        return True
    return False

def load_programs():
    if os.path.exists(PROGRAM_LIBRARY_FILE):
        with open(PROGRAM_LIBRARY_FILE, 'r') as f:
            return json.load(f)
    return [DEFAULT_PROGRAM, BJJ_PROGRAM]

def validate_program(program):
    required_keys = ["name", "duration_weeks", "description", "days", "prescriptions"]
    for key in required_keys:
        if key not in program:
            return False, f"Missing key: {key}"
    for day, details in program["days"].items():
        if "description" not in details or "exercises" not in details or "schedule" not in details:
            return False, f"Invalid day structure for {day}"
        if not all(isinstance(day, int) and 0 <= day <= 6 for day in details["schedule"]):
            return False, f"Invalid schedule days for {day}"
    for day in program["prescriptions"]:
        if day not in program["days"]:
            return False, f"Prescription day {day} not in days"
        for phase in ["Base", "Intensity", "Peaking"]:
            if phase not in program["prescriptions"][day]:
                return False, f"Missing phase {phase} for {day}"
            for exercise in program["prescriptions"][day][phase]:
                if exercise not in program["days"][day]["exercises"]:
                    return False, f"Exercise {exercise} not in {day} exercises"
                if "sets" not in program["prescriptions"][day][phase][exercise]:
                    return False, f"Missing sets for {exercise} in {day}"
                if "rest" not in program["prescriptions"][day][phase][exercise]:
                    return False, f"Missing rest for {exercise} in {day}"
    return True, "Valid program"

ONERM_FILE = "1rm.json"
def save_1rm(exercise, onerm):
    if os.path.exists(ONERM_FILE):
        with open(ONERM_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {}
    data[exercise] = float(onerm) if onerm else 0
    with open(ONERM_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_1rms():
    if os.path.exists(ONERM_FILE):
        with open(ONERM_FILE, 'r') as f:
            return json.load(f)
    return {}

PERFORMANCE_FILE = "performance_history.json"
def save_performance(exercise, date, success, set_number):
    if os.path.exists(PERFORMANCE_FILE):
        with open(PERFORMANCE_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {}
    if exercise not in data:
        data[exercise] = []
    data[exercise].append({"date": date, "success": success, "set": set_number})
    with open(PERFORMANCE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_performance(exercise):
    if os.path.exists(PERFORMANCE_FILE):
        with open(PERFORMANCE_FILE, 'r') as f:
            data = json.load(f)
        return data.get(exercise, [])
    return []

def get_recovery_metrics():
    df = load_progress()
    weights = df[df['Exercise/Note'].str.contains("Weight:")]['Exercise/Note'].apply(
        lambda x: float(x.split("Weight: ")[1].split(",")[0]) if "Weight: " in x else None
    ).dropna()
    calories = df[df['Exercise/Note'].str.contains("Nutrition:")]['Exercise/Note'].apply(
        lambda x: float(x.split("Nutrition: ")[1]) if "Nutrition: " in x else None
    ).dropna()
    return weights.mean() if not weights.empty else None, calories.mean() if not calories.empty else None

def update_prescription(exercise, success, set_number, workout_day, phase, sensitivity="Moderate", program=DEFAULT_PROGRAM):
    history = load_performance(exercise)
    current_date = datetime.now().strftime("%Y-%m-%d")
    if success is not None and set_number is not None:
        save_performance(exercise, current_date, success, set_number)
    
    session_counts = {"Conservative": 5, "Moderate": 4, "Aggressive": 3}
    n = session_counts.get(sensitivity, 4)
    recent = [entry for entry in history if entry['date'] >= (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")][-n:]
    score = sum(1 if entry['success'] else -1 for entry in recent)
    
    prescription = program["prescriptions"].get(workout_day, {}).get(phase, {}).get(exercise, {})
    adjusted = prescription.copy()
    
    workout_fails = sum(1 for entry in history if entry['date'] == current_date and not entry['success'])
    if workout_fails >= 2 and adjusted.get('rpe'):
        rpe_nums = [float(x) for x in adjusted['rpe'].split('-')]
        adjusted['rpe'] = f"{rpe_nums[0]-1}-{rpe_nums[1]-1}" if len(rpe_nums) == 2 else str(float(adjusted['rpe'])-1)
    
    weight_avg, calorie_avg = get_recovery_metrics()
    recovery_modifier = 0
    if weight_avg and 'Weight' in st.session_state and st.session_state['Weight']:
        try:
            if float(st.session_state['Weight']) < 0.95 * weight_avg:
                recovery_modifier -= 0.05
        except ValueError:
            pass
    if calorie_avg and 'Calories' in st.session_state and st.session_state['Calories']:
        try:
            if float(st.session_state['Calories']) < 0.95 * calorie_avg:
                recovery_modifier -= 0.05
        except ValueError:
            pass
    
    if score <= -3:
        st.warning(f"Consistent failures for {exercise}—consider a deload week.")
        if adjusted.get('percent_1rm'):
            adjusted['percent_1rm'] = (max(0.5, adjusted['percent_1rm'][0] - 0.05 + recovery_modifier),
                                      max(0.5, adjusted['percent_1rm'][1] - 0.05 + recovery_modifier))
        if adjusted.get('sets'):
            sets_nums = adjusted['sets'].split('-')
            if len(sets_nums) == 2:
                adjusted['sets'] = f"{int(sets_nums[0])}-{min(5, int(sets_nums[1])+1)}"
            else:
                adjusted['sets'] = str(min(5, int(sets_nums[0]) + 1))
        if exercise in program["prescriptions"].get(workout_day, {}).get(phase, {}):
            program["prescriptions"][workout_day][phase][exercise]["rest"] = min(180, program["prescriptions"][workout_day][phase][exercise]["rest"] + 30)
    elif score >= 3:
        if adjusted.get('percent_1rm'):
            adjusted['percent_1rm'] = (min(0.95, adjusted['percent_1rm'][0] + 0.05),
                                      min(1.0, adjusted['percent_1rm'][1] + 0.05))
        if adjusted.get('sets'):
            sets_nums = adjusted['sets'].split('-')
            if len(sets_nums) == 2:
                adjusted['sets'] = f"{max(2, int(sets_nums[0])-1)}-{max(2, int(sets_nums[1])-1)}"
            else:
                adjusted['sets'] = str(max(2, int(sets_nums[0]) - 1))
        if exercise in program["prescriptions"].get(workout_day, {}).get(phase, {}):
            program["prescriptions"][workout_day][phase][exercise]["rest"] = max(30, program["prescriptions"][workout_day][phase][exercise]["rest"] - 15)
    
    return adjusted, score

def suggest_weight(exercise, onerm, phase, percent_1rm):
    if onerm <= 0 or percent_1rm == (0, 0):
        return "Bodyweight/Non-weighted"
    low = round(onerm * percent_1rm[0] / 5) * 5
    high = round(onerm * percent_1rm[1] / 5) * 5
    return f"{low}-{high} lbs"

LOG_FILE = "progress_log.csv"

def save_log(entry_type, data):
    df = pd.DataFrame([data])
    if os.path.exists(LOG_FILE):
        existing = pd.read_csv(LOG_FILE)
        df = pd.concat([existing, df], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)
    new_achievements = check_achievements()
    for ach in new_achievements:
        st.success(f"{ach['emoji']} {ach['name']} Unlocked! {ach['description']}")

def load_progress(filter_by=""):
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
        if filter_by:
            df = df[df['Exercise/Note'].str.contains(filter_by, case=False, na=False)]
        return df
    return pd.DataFrame(columns=["Date", "Type", "Day", "Exercise/Note", "Details", "Notes"])

def generate_calendar(year, month, program):
    cal = calendar.monthcalendar(year, month)[:4]
    workout_days = {}
    for day_name, details in program["days"].items():
        for weekday in details["schedule"]:
            workout_days[weekday] = day_name
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return cal, workout_days, days

def get_workout_day_and_week(current_date, program):
    program_start = date(2025, 9, 1)
    days_since_start = (current_date - program_start).days
    print(f"Debug: current_date={current_date}, program_start={program_start}, days_since_start={days_since_start}")
    if days_since_start < 0 or days_since_start >= program["duration_weeks"] * 7:
        return None, None, None
    week = (days_since_start // 7) + 1
    phase = "Base" if week <= 4 else "Intensity" if week <= 8 else "Peaking"
    weekday = current_date.weekday()
    workout_day = None
    for day_name, details in program["days"].items():
        if weekday in details["schedule"]:
            workout_day = day_name
            break
    print(f"Debug: week={week}, phase={phase}, workout_day={workout_day}")
    return workout_day, week, phase

def format_time(ms):
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    milliseconds = ms % 1000
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def format_prescription(prescription, exercise, onerm):
    if "duration" in prescription:
        duration = prescription.get('duration', '')
        distance = prescription.get('distance', '')
        pace = prescription.get('pace', '')
        rpe = prescription.get('rpe', '')
        return f"{duration}, {distance}, {pace}, RPE {rpe}"
    sets = prescription.get('sets', '')
    reps = prescription.get('reps', '')
    percent_1rm = prescription.get('percent_1rm', (0, 0))
    rpe = prescription.get('rpe', '')
    weight = suggest_weight(exercise, onerm, None, percent_1rm)
    return f"{sets}x{reps} @ {weight}, RPE {rpe}"

def render_stopwatch(suggested_rest_ms):
    stopwatch_html = f"""
    <style>
        .stopwatch-container {{ background-color: #4A4A4A; padding: 15px; border-radius: 10px; border: 2px solid #8B0000; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3); margin-bottom: 20px; text-align: center; }}
        .stopwatch-display {{ font-family: 'Courier New', monospace; font-size: 36px; font-weight: bold; color: #FFFFFF; background-color: #333333; padding: 10px; border-radius: 5px; border: 1px solid #C0C0C0; display: inline-block; margin-bottom: 15px; }}
        .stopwatch-btn {{ background-color: #8B0000; color: #FFFFFF; font-family: 'Impact', sans-serif; font-size: 16px; padding: 8px 16px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
        .stopwatch-btn:hover {{ background-color: #A52A2A; transform: scale(1.05); box-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
        .lap-list {{ color: #C0C0C0; font-family: 'Courier New', monospace; font-size: 14px; text-align: left; margin-top: 10px; max-height: 150px; overflow-y: auto; }}
        .progress-bar {{ width: 100px; height: 10px; background-color: #4A4A4A; border-radius: 5px; display: inline-block; margin-left: 10px; overflow: hidden; }}
        .progress-fill {{ height: 100%; border-radius: 5px; background-color: #90EE90; transition: width 0.3s ease; }}
    </style>
    <div class="stopwatch-container">
        <div id="stopwatch-display" class="stopwatch-display">{format_time(suggested_rest_ms)}</div>
        <div>
            <button id="start-btn" class="stopwatch-btn">Start</button>
            <button id="stop-btn" class="stopwatch-btn">Stop</button>
            <button id="reset-btn" class="stopwatch-btn">Reset</button>
            <button id="lap-btn" class="stopwatch-btn">Lap</button>
        </div>
        <div id="lap-list" class="lap-list"></div>
    </div>
    <script>
        let stopwatchInterval = null;
        let elapsedTime = 0;
        let startTime = 0;
        let isRunning = false;
        let isCountdown = true;
        let countdownTime = {suggested_rest_ms};
        let laps = [];

        const display = document.getElementById('stopwatch-display');
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        const resetBtn = document.getElementById('reset-btn');
        const lapBtn = document.getElementById('lap-btn');
        const lapList = document.getElementById('lap-list');

        function formatTime(ms) {{
            const minutes = Math.floor(ms / 60000);
            const seconds = Math.floor((ms % 60000) / 1000);
            const milliseconds = ms % 1000;
            return `${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}.${{milliseconds.toString().padStart(3, '0')}}`;
        }}

        function updateDisplay() {{
            if (isCountdown && countdownTime > 0) {{
                display.innerText = formatTime(countdownTime);
            }} else {{
                isCountdown = false;
                display.innerText = formatTime(elapsedTime);
            }}
        }}

        function resetCountdown(newTime) {{
            isRunning = false;
            clearInterval(stopwatchInterval);
            elapsedTime = 0;
            countdownTime = newTime;
            isCountdown = true;
            updateDisplay();
            laps = [];
            lapList.innerHTML = '';
        }}

        function startStopwatch() {{
            if (!isRunning) {{
                isRunning = true;
                startBtn.innerText = 'Resume';
                if (isCountdown) {{
                    startTime = Date.now();
                    stopwatchInterval = setInterval(() => {{
                        const elapsed = Date.now() - startTime;
                        countdownTime = Math.max(0, countdownTime - elapsed);
                        if (countdownTime <= 0) {{
                            isCountdown = false;
                            elapsedTime = 0;
                            startTime = Date.now();
                        }}
                        updateDisplay();
                    }}, 10);
                }} else {{
                    startTime = Date.now() - elapsedTime;
                    stopwatchInterval = setInterval(() => {{
                        elapsedTime = Date.now() - startTime;
                        updateDisplay();
                    }}, 10);
                }}
            }}
        }}

        function stopStopwatch() {{
            if (isRunning) {{
                isRunning = false;
                clearInterval(stopwatchInterval);
                if (isCountdown) {{
                    countdownTime = Math.max(0, countdownTime - (Date.now() - startTime));
                }} else {{
                    elapsedTime = Date.now() - startTime;
                }}
                updateDisplay();
            }}
        }}

        function resetStopwatch() {{
            resetCountdown(countdownTime);
        }}

        function recordLap() {{
            if (isRunning) {{
                const time = isCountdown ? countdownTime : elapsedTime;
                laps.push(formatTime(time));
                const lapItem = document.createElement('div');
                lapItem.innerText = `Lap ${{laps.length}}: ${{formatTime(time)}}`;
                lapList.appendChild(lapItem);
            }}
        }}

        startBtn.addEventListener('click', startStopwatch);
        stopBtn.addEventListener('click', stopStopwatch);
        resetBtn.addEventListener('click', resetStopwatch);
        lapBtn.addEventListener('click', recordLap);

        window.addEventListener('message', function(event) {{
            if (event.data && event.data.type === 'updateRestTime') {{
                resetCountdown(event.data.newTime);
            }}
        }});

        updateDisplay();
    </script>
    """
    components.html(stopwatch_html, height=300)

def render_interval_timer(run_time_ms, walk_time_ms):
    interval_timer_html = f"""
    <style>
        .interval-timer-container {{ background-color: #4A4A4A; padding: 15px; border-radius: 10px; border: 2px solid #8B0000; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3); margin-bottom: 20px; text-align: center; }}
        .interval-timer-display {{ font-family: 'Courier New', monospace; font-size: 36px; font-weight: bold; color: #FFFFFF; background-color: #333333; padding: 10px; border-radius: 5px; border: 1px solid #C0C0C0; display: inline-block; margin-bottom: 15px; }}
        .interval-timer-btn {{ background-color: #8B0000; color: #FFFFFF; font-family: 'Impact', sans-serif; font-size: 16px; padding: 8px 16px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; transition: all 0.3s ease; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
        .interval-timer-btn:hover {{ background-color: #A52A2A; transform: scale(1.05); box-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
        .phase-label {{ font-family: 'Courier New', monospace; font-size: 18px; color: #90EE90; margin-bottom: 10px; }}
    </style>
    <div class="interval-timer-container">
        <div id="phase-label" class="phase-label">Run</div>
        <div id="interval-timer-display" class="interval-timer-display">{format_time(run_time_ms)}</div>
        <div>
            <button id="start-btn" class="interval-timer-btn">Start</button>
            <button id="stop-btn" class="interval-timer-btn">Stop</button>
            <button id="reset-btn" class="interval-timer-btn">Reset</button>
        </div>
        <div id="cycle-count" style="color: #C0C0C0; font-family: 'Courier New', monospace; font-size: 14px; margin-top: 10px;">Cycle: 1</div>
    </div>
    <script>
        let timerInterval = null;
        let elapsedTime = 0;
        let startTime = 0;
        let isRunning = false;
        let isRunPhase = true;
        let runTime = {run_time_ms};
        let walkTime = {walk_time_ms};
        let currentTime = runTime;
        let cycleCount = 1;

        const display = document.getElementById('interval-timer-display');
        const phaseLabel = document.getElementById('phase-label');
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        const resetBtn = document.getElementById('reset-btn');
        const cycleCountDisplay = document.getElementById('cycle-count');

        function formatTime(ms) {{
            const minutes = Math.floor(ms / 60000);
            const seconds = Math.floor((ms % 60000) / 1000);
            const milliseconds = ms % 1000;
            return `${{minutes.toString().padStart(2, '0')}}:${{seconds.toString().padStart(2, '0')}}.${{milliseconds.toString().padStart(3, '0')}}`;
        }}

        function updateDisplay() {{
            phaseLabel.innerText = isRunPhase ? 'Run' : 'Walk';
            display.innerText = formatTime(currentTime);
            cycleCountDisplay.innerText = `Cycle: ${{cycleCount}}`;
        }}

        function resetTimer() {{
            isRunning = false;
            clearInterval(timerInterval);
            isRunPhase = true;
            currentTime = runTime;
            cycleCount = 1;
            elapsedTime = 0;
            updateDisplay();
        }}

        function startTimer() {{
            if (!isRunning) {{
                isRunning = true;
                startBtn.innerText = 'Resume';
                startTime = Date.now();
                timerInterval = setInterval(() => {{
                    const elapsed = Date.now() - startTime;
                    currentTime = Math.max(0, currentTime - elapsed);
                    if (currentTime <= 0) {{
                        isRunPhase = !isRunPhase;
                        currentTime = isRunPhase ? runTime : walkTime;
                        if (!isRunPhase) cycleCount++;
                        startTime = Date.now();
                    }}
                    updateDisplay();
                }}, 10);
            }}
        }}

        function stopTimer() {{
            if (isRunning) {{
                isRunning = false;
                clearInterval(timerInterval);
                currentTime = Math.max(0, currentTime - (Date.now() - startTime));
                updateDisplay();
            }}
        }}

        startBtn.addEventListener('click', startTimer);
        stopBtn.addEventListener('click', stopTimer);
        resetBtn.addEventListener('click', resetTimer);

        window.addEventListener('message', function(event) {{
            if (event.data && event.data.type === 'updateRestTime') {{
                resetTimer();
            }}
        }});

        updateDisplay();
    </script>
    """
    components.html(interval_timer_html, height=300)

st.set_page_config(page_title="PR Machine", layout="centered")
st.markdown("""
<style>
    .main { background-color: #333333; color: white; font-family: 'Helvetica', sans-serif; }
    .stButton>button { background-color: #8B0000; color: white; font-family: 'Impact', sans-serif; font-size: 16px; padding: 10px 20px; border-radius: 8px; border: none; transition: all 0.3s ease; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    .stButton>button:hover { background-color: #A52A2A; transform: scale(1.05); box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .stSelectbox, .stTextInput, .stNumberInput, .stTextArea { background-color: #4A4A4A; color: white; border-radius: 8px; border: 1px solid #C0C0C0; }
    h1, h2, h3 { font-family: 'Impact', sans-serif; color: #C0C0C0; letter-spacing: 1px; }
    .stExpander { background-color: #3A3A3A; border-radius: 8px; border: 1px solid #C0C0C0; }
    .calendar-header { background-color: #8B0000; color: white; font-weight: bold; font-size: 16px; padding: 8px; text-align: center; border: 3px solid #C0C0C0; border-radius: 5px; box-sizing: border-box; width: 120px; height: 40px; margin: 0; }
    .calendar-day { background-color: #4A4A4A; color: white; border: 3px solid #C0C0C0; padding: 8px; text-align: center; width: 120px; height: 120px; font-size: 14px; white-space: normal; word-wrap: break-word; overflow: hidden; border-radius: 5px; box-sizing: border-box; margin: 0; }
    .calendar-day button { background-color: #90EE90; color: black; border: none; width: 100%; height: 100%; font-size: 14px; font-family: 'Helvetica', sans-serif; transition: all 0.3s ease; }
    .calendar-day button:hover { background-color: #98FB98; transform: scale(1.02); }
    .workout-day { background-color: #90EE90; color: black; }
    .non-workout-day { background-color: #4A4A4A; color: white; }
    .achievement-card { background-color: #4A4A4A; padding: 10px; border-radius: 8px; border: 1px solid #C0C0C0; text-align: center; margin: 5px; }
    .achievement-card-unlocked { background-color: #90EE90; color: black; }
    .quote-container { text-align: center; font-size: 18px; color: #90EE90; font-family: 'Impact', sans-serif; margin-bottom: 20px; }
    .warm-up-container { background-color: #3A3A3A; padding: 10px; border-radius: 8px; border: 1px solid #C0C0C0; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

if os.path.exists("gym_header.jpg"):
    st.image("gym_header.jpg", use_container_width=True)
else:
    st.markdown("### Add gym_header.jpg for full effect")
st.title("PR Machine")
if 'quote_index' not in st.session_state:
    st.session_state.quote_index = 0
st.markdown(f"<div class='quote-container'>{QUOTES[st.session_state.quote_index]}</div>", unsafe_allow_html=True)
if st.button("New Quote"):
    st.session_state.quote_index = (st.session_state.quote_index + 1) % len(QUOTES)
    st.rerun()

st.sidebar.header("Navigation")
if 'page' not in st.session_state:
    st.session_state.page = "View Program"
st.session_state.page = st.sidebar.selectbox("Select Page", ["View Program", "Workout of the Day", "Progress Dashboard", "View Progress", "Recovery Metrics", "Create Program"], index=["View Program", "Workout of the Day", "Progress Dashboard", "View Progress", "Recovery Metrics", "Create Program"].index(st.session_state.page))
page = st.session_state.page

onerms = load_1rms()

if 'display_date' not in st.session_state:
    st.session_state.display_date = date.today()
if 'sensitivity' not in st.session_state:
    st.session_state.sensitivity = "Moderate"
if 'Weight' not in st.session_state:
    st.session_state.Weight = ""
if 'Calories' not in st.session_state:
    st.session_state.Calories = ""
if 'selected_program' not in st.session_state:
    st.session_state.selected_program = "12-Week Strength & Running"

program_library = load_programs()
program_names = [p["name"] for p in program_library]
st.session_state.selected_program = st.sidebar.selectbox("Select Program", program_names, index=program_names.index(st.session_state.selected_program))
selected_program = next(p for p in program_library if p["name"] == st.session_state.selected_program)

if page == "View Program":
    with st.expander("Training Program Overview", expanded=True):
        st.markdown(selected_program["description"])
        st.subheader("Adjustment Sensitivity")
        st.write("Select how responsive the program adapts to your performance. 'Conservative' uses 5 sessions, 'Moderate' uses 4, 'Aggressive' uses 3.")
        st.session_state.sensitivity = st.selectbox(
            "Sensitivity",
            ["Conservative", "Moderate", "Aggressive"],
            index=["Conservative", "Moderate", "Aggressive"].index(st.session_state.sensitivity),
            key="sensitivity_select"
        )
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            current_month = st.session_state.get('calendar_month', 9)
            current_year = st.session_state.get('calendar_year', 2025)
            if st.button("Previous Month"):
                if current_month == 1:
                    current_month = 12
                    current_year -= 1
                else:
                    current_month -= 1
                st.session_state.calendar_month = current_month
                st.session_state.calendar_year = current_year
                st.rerun()
            st.markdown(f"**{calendar.month_name[current_month]} {current_year}**", unsafe_allow_html=True)
            if st.button("Next Month"):
                if current_month == 12:
                    current_month = 1
                    current_year += 1
                else:
                    current_month += 1
                st.session_state.calendar_month = current_month
                st.session_state.calendar_year = current_year
                st.rerun()
        cal, workout_days, days = generate_calendar(current_year, current_month, selected_program)
        cols = st.columns(7, gap="small")
        for i, day in enumerate(days):
            cols[i].markdown(f"<div class='calendar-header'>{day}</div>", unsafe_allow_html=True)
        for week in cal:
            cols = st.columns(7, gap="small")
            for i, day in enumerate(week):
                if day == 0:
                    cols[i].markdown("<div class='calendar-day'></div>", unsafe_allow_html=True)
                else:
                    workout = workout_days.get(i, "")
                    workout_display = workout or "Rest day"
                    class_name = "workout-day" if workout else "non-workout-day"
                    if workout:
                        program_start = date(2025, 9, 1)
                        clicked_date = date(current_year, current_month, day)
                        if program_start <= clicked_date < program_start + timedelta(days=selected_program["duration_weeks"] * 7):
                            if cols[i].button(f"{day}\n{workout_display}", key=f"day_workout_{day}_{i}_{current_month}_{current_year}", help=f"Go to {workout} on Workout of the Day"):
                                st.session_state.display_date = clicked_date
                                st.session_state.page = "Workout of the Day"
                                st.rerun()
                        else:
                            cols[i].markdown(f"<div class='{class_name}'><strong>{day}</strong><br>{workout_display}</div>", unsafe_allow_html=True)
                    else:
                        cols[i].markdown(f"<div class='{class_name}'><strong>{day}</strong><br>{workout_display}</div>", unsafe_allow_html=True)
    for day in selected_program["days"]:
        with st.expander(f"{day} Details"):
            st.markdown(selected_program["days"][day]["description"])

elif page == "Workout of the Day":
    st.header("Workout of the Day")
    program_start = date(2025, 9, 1)
    program_end = program_start + timedelta(days=(selected_program["duration_weeks"] * 7 - 1))
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.session_state.display_date > program_start:
            if st.button("Previous Day"):
                st.session_state.display_date -= timedelta(days=1)
                for day in selected_program["days"]:
                    for ex in selected_program["days"][day]["exercises"]:
                        if f"set_results_{day}_{ex}" in st.session_state:
                            del st.session_state[f"set_results_{day}_{ex}"]
                st.rerun()
    with col2:
        st.write("")
    with col3:
        if st.session_state.display_date < program_end:
            if st.button("Next Day"):
                st.session_state.display_date += timedelta(days=1)
                for day in selected_program["days"]:
                    for ex in selected_program["days"][day]["exercises"]:
                        if f"set_results_{day}_{ex}" in st.session_state:
                            del st.session_state[f"set_results_{day}_{ex}"]
                st.rerun()
    
    workout_day, week, phase = get_workout_day_and_week(st.session_state.display_date, selected_program)
    
    if workout_day is None and (0 <= (st.session_state.display_date - program_start).days < selected_program["duration_weeks"] * 7):
        with st.expander("Rest Day", expanded=True):
            st.markdown(f"**{st.session_state.display_date.strftime('%B %d, %Y')}: Rest Day**")
            st.markdown("### Warm-Up Suggestions")
            with st.container():
                if st.button("Generate Warm-Ups"):
                    st.session_state.warm_ups = random.sample(WARM_UPS["Rest"], 3)
                if 'warm_ups' in st.session_state and st.session_state.warm_ups:
                    st.markdown("**Your Warm-Ups**")
                    for warm_up in st.session_state.warm_ups:
                        st.markdown(f"- **{warm_up['name']}**: {warm_up['description']}")
            st.write("Today is a rest day. Here are some recovery activities:")
            for behavior in random.sample(RECOVERY_BEHAVIORS, 3):
                st.markdown(f"- **{behavior['Behavior']}**: {behavior['Reason']} {behavior['Mechanism']} {behavior['Barrier']}")
    elif workout_day in selected_program["days"]:
        with st.expander("Warm-Up", expanded=True):
            warm_up_type = "Conditioning" if "running" in workout_day.lower() or "speed" in workout_day.lower() or "conditioning" in workout_day.lower() else "Strength"
            if st.button("Generate Warm-Ups"):
                st.session_state.warm_ups = random.sample(WARM_UPS[warm_up_type], 3)
            if 'warm_ups' in st.session_state and st.session_state.warm_ups:
                st.markdown("**Your Warm-Ups**")
                for warm_up in st.session_state.warm_ups:
                    st.markdown(f"- **{warm_up['name']}**: {warm_up['description']}")
        
        st.markdown(f"**{st.session_state.display_date.strftime('%B %d, %Y')}: {workout_day}, Week {week} - {phase} Phase**")
        st.markdown(selected_program["days"][workout_day]["description"])
        exercises = selected_program["days"][workout_day]["exercises"]
        
        st.markdown("### Exercise Details")
        with st.container():
            exercise = st.selectbox("Exercise", exercises, key=f"exercise_{workout_day}")
            
            if f"last_exercise_{workout_day}" in st.session_state and st.session_state[f"last_exercise_{workout_day}"] != exercise:
                if f"set_results_{workout_day}_{exercise}" in st.session_state:
                    del st.session_state[f"set_results_{workout_day}_{exercise}"]
            st.session_state[f"last_exercise_{workout_day}"] = exercise
            
            history = load_performance(exercise)
            recent = [entry for entry in history if entry['date'] >= (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")][-4:]
            score = sum(1 if entry['success'] else -1 for entry in recent)
            progress_width = min(100, max(0, (score + 3) * 100 / 6))
            emoji = "🔥" if score >= 3 else "⚠️" if score <= -3 else "💪"
            st.markdown(f"Progress: {emoji} <div class='progress-bar'><div class='progress-fill' style='width: {progress_width}%'></div></div>", unsafe_allow_html=True)
            
            suggested_rest_time = selected_program["prescriptions"][workout_day][phase][exercise]["rest"]
            st.text_input("Suggested Rest Time (seconds)", value=str(suggested_rest_time), disabled=True)
            
            if "running" in workout_day.lower() or "speed" in workout_day.lower() or "conditioning" in workout_day.lower():
                st.subheader("Interval Timer")
                default_ratios = {
                    "Base": (120000, 60000),
                    "Intensity": (180000, 60000),
                    "Peaking": (240000, 60000)
                }
                run_time_ms, walk_time_ms = default_ratios.get(phase, (120000, 60000))
                run_time_key = f"run_time_{workout_day}_{exercise}"
                walk_time_key = f"walk_time_{workout_day}_{exercise}"
                if run_time_key not in st.session_state:
                    st.session_state[run_time_key] = run_time_ms / 1000
                if walk_time_key not in st.session_state:
                    st.session_state[walk_time_key] = walk_time_ms / 1000
                st.session_state[run_time_key] = st.number_input("Run Duration (seconds)", min_value=1.0, value=float(st.session_state[run_time_key]), step=1.0)
                st.session_state[walk_time_key] = st.number_input("Walk Duration (seconds)", min_value=1.0, value=float(st.session_state[walk_time_key]), step=1.0)
                render_interval_timer(int(st.session_state[run_time_key] * 1000), int(st.session_state[walk_time_key] * 1000))
                
                st.subheader("Conditioning Metrics")
                adjusted, _ = update_prescription(exercise, None, None, workout_day, phase, st.session_state.sensitivity, selected_program)
                prescribed = format_prescription(adjusted, exercise, onerms.get(exercise, 0))
                st.text_input("Prescribed", value=prescribed, disabled=True)
                target_duration = st.text_input("Target Duration (min)", value="30")
                target_distance = st.text_input("Target Distance (km)", value="5")
                target_pace = st.text_input("Target Pace (min/km)", value="5:00")
                details = st.text_input("Total Work", value=prescribed)
            else:
                st.subheader("Stopwatch")
                render_stopwatch(suggested_rest_time * 1000)
                
                onerm = st.number_input("1RM (lbs, enter to update)", min_value=0.0, value=float(onerms.get(exercise, 0)), step=5.0)
                if onerm and onerm > 0:
                    save_1rm(exercise, onerm)
                    onerms[exercise] = onerm
                adjusted, _ = update_prescription(exercise, None, None, workout_day, phase, st.session_state.sensitivity, selected_program)
                prescribed = format_prescription(adjusted, exercise, onerms.get(exercise, 0))
                st.write(f"Suggested Weight: {suggest_weight(exercise, onerms.get(exercise, 0), phase, adjusted.get('percent_1rm', (0.65, 0.75)))}")
                st.text_input("Prescribed", value=prescribed, disabled=True)
                details = st.text_input("Total Work", value=prescribed)
        
        st.markdown("### Log Sets")
        with st.container():
            st.write("Mark 'Success' if completed with good form at target RPE; 'Fail' if not.")
            num_sets = int(adjusted['sets'].split('-')[-1]) if '-' in adjusted.get('sets', '3') else int(adjusted.get('sets', '3'))
            set_results_key = f"set_results_{workout_day}_{exercise}"
            if set_results_key not in st.session_state or len(st.session_state[set_results_key]) != num_sets:
                st.session_state[set_results_key] = [None] * num_sets
            set_results = st.session_state[set_results_key]
            for i in range(num_sets):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"Set {i+1}")
                with col2:
                    if st.button("Success", key=f"success_{workout_day}_{exercise}_{i}"):
                        set_results[i] = True
                        adjusted, score = update_prescription(exercise, True, i+1, workout_day, phase, st.session_state.sensitivity, selected_program)
                        st.session_state[set_results_key] = set_results
                        if exercise in selected_program["prescriptions"][workout_day][phase]:
                            components.html(f"<script>window.parent.postMessage({{'type': 'updateRestTime', 'newTime': {selected_program['prescriptions'][workout_day][phase][exercise]['rest'] * 1000}}}, '*')</script>", height=0)
                        st.rerun()
                with col3:
                    if st.button("Fail", key=f"fail_{workout_day}_{exercise}_{i}"):
                        set_results[i] = False
                        adjusted, score = update_prescription(exercise, False, i+1, workout_day, phase, st.session_state.sensitivity, selected_program)
                        st.session_state[set_results_key] = set_results
                        if exercise in selected_program["prescriptions"][workout_day][phase]:
                            components.html(f"<script>window.parent.postMessage({{'type': 'updateRestTime', 'newTime': {selected_program['prescriptions'][workout_day][phase][exercise]['rest'] * 1000}}}, '*')</script>", height=0)
                        st.rerun()
                if i < len(set_results) and set_results[i] is not None:
                    st.write(f"Set {i+1}: {'Success' if set_results[i] else 'Fail'}")
            
            notes = st.text_area("Notes", height=150, value=f"{sum(1 for r in set_results if r is True)}/{num_sets} sets successful" if any(r is not None for r in set_results) else "")
            if st.button("Finish Workout"):
                if not workout_day or not exercise:
                    st.error("Please select an exercise.")
                else:
                    data = {
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Type": "Workout",
                        "Day": workout_day,
                        "Exercise/Note": exercise,
                        "Details": details,
                        "Notes": notes + (f" 1RM: {onerms.get(exercise, 0)}" if onerms.get(exercise, 0) > 0 else "")
                    }
                    save_log("Workout", data)
                    st.session_state[set_results_key] = [None] * num_sets
                    st.success("Workout logged!")
                    st.rerun()
    else:
        with st.expander("Program Not Active", expanded=True):
            st.markdown(f"**{st.session_state.display_date.strftime('%B %d, %Y')}: Program not active**")
            st.write(f"The {selected_program['name']} program runs from September 1, 2025, for {selected_program['duration_weeks']} weeks.")

elif page == "Progress Dashboard":
    with st.expander("Achievements", expanded=True):
        st.write("Unlock badges by hitting your goals!")
        achievements = load_achievements()
        cols = st.columns(4)
        for i, ach in enumerate(ACHIEVEMENTS):
            with cols[i % 4]:
                class_name = "achievement-card-unlocked" if achievements.get(ach["name"], False) else "achievement-card"
                st.markdown(f"<div class='{class_name}'><h3>{ach['emoji']} {ach['name']}</h3><p>{ach['description']}</p></div>", unsafe_allow_html=True)
    
    with st.expander("Performance Metrics", expanded=True):
        st.write("Track your 1RM trends and set success rates.")
        df = load_progress()
        all_exercises = []
        for program in program_library:
            for day in program["days"]:
                all_exercises.extend(program["days"][day]["exercises"])
        all_exercises = sorted(set(all_exercises))
        
        selected_exercise = st.selectbox("Select Exercise for 1RM Trend", all_exercises)
        onerm_data = load_1rms()
        history = load_performance(selected_exercise)
        
        if selected_exercise in onerm_data:
            dates = [datetime.now().strftime("%Y-%m-%d")]
            values = [onerm_data[selected_exercise]]
            st.write("1RM Trend")
            components.html(f"""
            <canvas id="onermChart" style="max-height: 300px;"></canvas>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script>
                const ctx = document.getElementById('onermChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: {json.dumps(dates)},
                        datasets: [{{
                            label: '1RM (lbs)',
                            data: {json.dumps(values)},
                            borderColor: '#90EE90',
                            backgroundColor: '#90EE9040',
                            fill: true
                        }}]
                    }},
                    options: {{
                        scales: {{
                            x: {{title: {{display: true, text: 'Date'}}}},
                            y: {{title: {{display: true, text: '1RM (lbs)'}}, beginAtZero: false}}
                        }}
                    }}
                }});
            </script>
            """, height=350)
        
        success_data = []
        for ex in all_exercises:
            history = load_performance(ex)
            total_sets = len(history)
            successes = sum(1 for entry in history if entry["success"])
            success_rate = (successes / total_sets * 100) if total_sets > 0 else 0
            success_data.append(success_rate)
        
        st.write("Set Success Rates")
        components.html(f"""
        <canvas id="successChart" style="max-height: 300px;"></canvas>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            const ctx2 = document.getElementById('successChart').getContext('2d');
            new Chart(ctx2, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(all_exercises)},
                    datasets: [{{
                        label: 'Success Rate (%)',
                        data: {json.dumps(success_data)},
                        backgroundColor: '#8B0000',
                        borderColor: '#C0C0C0',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    scales: {{
                        x: {{title: {{display: true, text: 'Exercise'}}}},
                        y: {{title: {{display: true, text: 'Success Rate (%)'}}, beginAtZero: true, max: 100}}
                    }}
                }}
            }});
        </script>
        """, height=350)

elif page == "View Progress":
    with st.expander("Workout History", expanded=True):
        st.write("View your logged workouts and filter by exercise.")
        all_exercises = []
        for program in program_library:
            for day in program["days"]:
                all_exercises.extend(program["days"][day]["exercises"])
        all_exercises = sorted(set(all_exercises))
        filter_by = st.selectbox("Filter by", [""] + all_exercises)
        df = load_progress(filter_by)
        st.dataframe(df, use_container_width=True)

elif page == "Recovery Metrics":
    with st.expander("Recovery Tracking", expanded=True):
        st.write("Log body weight and nutrition to optimize recovery.")
        weight = st.text_input("Body Weight (lbs)", value=st.session_state.get('Weight', ""))
        nutrition = st.text_input("Calories/Protein", value=st.session_state.get('Calories', ""))
        notes = st.text_area("General Notes", height=150)
        if st.button("Save"):
            st.session_state.Weight = weight
            st.session_state.Calories = nutrition
            data = {
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Type": "Other",
                "Day": "",
                "Exercise/Note": f"Weight: {weight}, Nutrition: {nutrition}",
                "Details": "",
                "Notes": notes
            }
            save_log("Other", data)
            st.success("Info logged!")
            st.rerun()

elif page == "Create Program":
    EXERCISE_LIBRARY = {
        "Strength": [
            {"name": "SSB Back Squat", "description": "Safety squat bar for quads, glutes, hamstrings."},
            {"name": "Deadlifts", "description": "Compound lift for posterior chain, grip strength."},
            {"name": "Hack Squat", "description": "Machine-based squat for quad focus."},
            {"name": "Leg Press", "description": "Quad and glute hypertrophy with controlled range."},
            {"name": "Romanian Deadlifts", "description": "Hamstring and glute-focused deadlift variation."},
            {"name": "Weighted Pull-Ups", "description": "Upper body pulling strength, BJJ grip."},
            {"name": "Power Cleans", "description": "Explosive lift for power and athleticism."},
            {"name": "Bulgarian Split Squats", "description": "Unilateral leg strength, stability."},
            {"name": "Lying Leg Curls", "description": "Hamstring isolation for hypertrophy."},
            {"name": "Calf Raises", "description": "Calf strength and endurance."},
            {"name": "Glute-Ham Raises", "description": "Posterior chain strength, BJJ-specific."},
            {"name": "Seated Calf Raises", "description": "Calf hypertrophy with seated variation."},
            {"name": "Step-Ups", "description": "Unilateral leg strength, functional movement."}
        ],
        "Conditioning": [
            {"name": "Sprints", "description": "High-intensity running for anaerobic capacity."},
            {"name": "Sprint Drills", "description": "Short bursts to improve speed and agility."},
            {"name": "Battle Ropes", "description": "Full-body conditioning, BJJ endurance."},
            {"name": "Box Jumps", "description": "Plyometric exercise for explosive power."},
            {"name": "Long Jumps", "description": "Plyometric movement for leg power."},
            {"name": "Bounding", "description": "Exaggerated strides for power and coordination."},
            {"name": "Sled Pushes", "description": "Full-body conditioning, strength endurance."},
            {"name": "Walk/Run Intervals", "description": "Aerobic conditioning for 5k prep."}
        ],
        "BJJ Drill": [
            {"name": "Hanging Leg Raises", "description": "Core strength for BJJ guard work."},
            {"name": "Plank Variations", "description": "Core stability for grappling."},
            {"name": "Russian Twists", "description": "Rotational core strength for BJJ sweeps."},
            {"name": "Farmer’s Carry", "description": "Grip and core endurance for BJJ control."}
        ]
    }

    def generate_periodized_program(base_week):
        program = {"days": {}, "prescriptions": {}}
        for day_name, day_data in base_week["days"].items():
            program["days"][day_name] = day_data.copy()
            program["prescriptions"][day_name] = {
                "Base": base_week["prescriptions"][day_name]["Base"].copy(),
                "Intensity": {},
                "Peaking": {}
            }
            for ex in day_data["exercises"]:
                base_prescription = base_week["prescriptions"][day_name]["Base"].get(ex, {})
                if "duration" in base_prescription:
                    intensity = base_prescription.copy()
                    peaking = base_prescription.copy()
                    intensity["duration"] = f"{int(base_prescription['duration'].split('-')[0]) + 10}-{int(base_prescription['duration'].split('-')[1]) + 10} min"
                    peaking["duration"] = f"{int(base_prescription['duration'].split('-')[0]) + 20}-{int(base_prescription['duration'].split('-')[1]) + 20} min"
                    intensity["rpe"] = f"{float(base_prescription['rpe'].split('-')[0]) + 1}-{float(base_prescription['rpe'].split('-')[1]) + 1}"
                    peaking["rpe"] = f"{float(base_prescription['rpe'].split('-')[0]) + 1.5}-{float(base_prescription['rpe'].split('-')[1]) + 1.5}"
                    intensity["rest"] = max(30, base_prescription["rest"] - 15)
                    peaking["rest"] = max(30, base_prescription["rest"] - 15)
                    program["prescriptions"][day_name]["Intensity"][ex] = intensity
                    program["prescriptions"][day_name]["Peaking"][ex] = peaking
                else:
                    intensity = base_prescription.copy()
                    peaking = base_prescription.copy()
                    intensity["sets"] = f"{max(2, int(base_prescription['sets'].split('-')[0]) - 1)}-{max(3, int(base_prescription['sets'].split('-')[-1]) - 1)}"
                    peaking["sets"] = f"{max(2, int(base_prescription['sets'].split('-')[0]) - 1)}-{max(2, int(base_prescription['sets'].split('-')[-1]) - 1)}"
                    intensity_reps = base_prescription["reps"].split('-')
                    peaking_reps = base_prescription["reps"].split('-')
                    intensity["reps"] = f"{max(1, int(intensity_reps[0]) - round(int(intensity_reps[0]) * 0.25))}-{max(1, int(intensity_reps[-1]) - round(int(intensity_reps[-1]) * 0.25))}"
                    peaking["reps"] = f"{max(1, int(peaking_reps[0]) - round(int(peaking_reps[0]) * 0.5))}-{max(1, int(peaking_reps[-1]) - round(int(peaking_reps[-1]) * 0.5))}"
                    intensity["percent_1rm"] = (min(0.95, base_prescription["percent_1rm"][0] + 0.1), min(1.0, base_prescription["percent_1rm"][1] + 0.1))
                    peaking["percent_1rm"] = (min(0.95, base_prescription["percent_1rm"][0] + 0.2), min(1.0, base_prescription["percent_1rm"][1] + 0.2))
                    intensity["rpe"] = f"{float(base_prescription['rpe'].split('-')[0]) + 1}-{float(base_prescription['rpe'].split('-')[1]) + 1}"
                    peaking["rpe"] = f"{float(base_prescription['rpe'].split('-')[0]) + 1.5}-{float(base_prescription['rpe'].split('-')[1]) + 1.5}"
                    intensity["rest"] = base_prescription["rest"] + 30
                    peaking["rest"] = base_prescription["rest"] + 60
                    program["prescriptions"][day_name]["Intensity"][ex] = intensity
                    program["prescriptions"][day_name]["Peaking"][ex] = peaking
        return program

    with st.expander("Create or Import Program", expanded=True):
        st.subheader("Create New Program")
        with st.form(key="create_program_form"):
            st.markdown("### Step 1: Program Details")
            program_name = st.text_input("Program Name", key="program_name")
            duration_weeks = st.number_input("Duration (weeks)", min_value=1, max_value=52, value=12, key="duration_weeks")
            program_description = st.text_area("Program Description", height=150, key="program_description")
            
            st.markdown("### Step 2: Weekly Structure")
            if 'num_days' not in st.session_state:
                st.session_state.num_days = 0
            if 'days' not in st.session_state:
                st.session_state.days = []
            
            num_days = st.number_input("Number of Days per Week", min_value=0, max_value=7, key="num_days")
            
            # Initialize temp_days with default structure
            temp_days = [{"type": "Workout", "name": f"Day {i+1}", "description": "", "exercises": [], "schedule": [], "prescriptions": {"Base": {}}} for i in range(num_days)]
            # Copy existing days if they exist, up to num_days
            for i in range(min(len(st.session_state.days), num_days)):
                temp_days[i] = st.session_state.days[i].copy()
            
            for i in range(num_days):
                st.markdown(f"#### Day {i+1}")
                with st.container():
                    temp_days[i]["type"] = st.selectbox(f"Day Type", ["Workout", "Rest"], key=f"day_type_{i}")
                    if temp_days[i]["type"] == "Workout":
                        temp_days[i]["name"] = st.text_input(f"Day Name", value=temp_days[i]["name"], key=f"day_name_{i}")
                        temp_days[i]["description"] = st.text_area(f"Day Description", value=temp_days[i]["description"], key=f"day_desc_{i}")
                        temp_days[i]["schedule"] = st.multiselect(f"Schedule (days of week)", options=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], default=temp_days[i]["schedule"], key=f"day_schedule_{i}")
                        
                        st.markdown(f"##### Exercises for {temp_days[i]['name']}")
                        exercise_category = st.selectbox(f"Select Exercise Category", ["Strength", "Conditioning", "BJJ Drill"], key=f"exercise_category_{i}")
                        available_exercises = [ex["name"] for ex in EXERCISE_LIBRARY[exercise_category]]
                        selected_exercises = st.multiselect(f"Select Exercises", available_exercises, default=temp_days[i]["exercises"], key=f"exercises_{i}")
                        temp_days[i]["exercises"] = selected_exercises
                        
                        for ex in temp_days[i]["exercises"]:
                            st.markdown(f"###### Prescriptions for {ex}")
                            with st.container():
                                exercise_type = st.selectbox(f"Exercise Type ({ex})", ["Strength", "Running/Speed", "BJJ Drill"], key=f"type_{i}_{ex}")
                                st.markdown("**Base Phase**")
                                sets = st.text_input(f"Sets ({ex})", value="3-4", key=f"sets_{i}_{ex}_Base")
                                if exercise_type == "Running/Speed":
                                    duration = st.text_input(f"Duration ({ex})", value="30-40 min", key=f"duration_{i}_{ex}_Base")
                                    distance = st.text_input(f"Distance ({ex})", value="3-5 km", key=f"distance_{i}_{ex}_Base")
                                    pace = st.text_input(f"Pace ({ex})", value="6-7 min/km", key=f"pace_{i}_{ex}_Base")
                                    rpe = st.text_input(f"RPE ({ex})", value="6-7", key=f"rpe_{i}_{ex}_Base")
                                    rest = st.number_input(f"Rest (seconds, {ex})", min_value=0, value=60, key=f"rest_{i}_{ex}_Base")
                                    temp_days[i]["prescriptions"]["Base"][ex] = {
                                        "duration": duration, "distance": distance, "pace": pace, "rpe": rpe, "rest": rest
                                    }
                                else:
                                    reps = st.text_input(f"Reps or Duration ({ex})", value="8-12" if exercise_type == "Strength" else "30-45 sec", key=f"reps_{i}_{ex}_Base")
                                    percent_1rm = st.text_input(f"%1RM ({ex})", value="0.65-0.75" if exercise_type == "Strength" else "0-0", key=f"percent_1rm_{i}_{ex}_Base")
                                    rpe = st.text_input(f"RPE ({ex})", value="7-8", key=f"rpe_{i}_{ex}_Base")
                                    rest = st.number_input(f"Rest (seconds, {ex})", min_value=0, value=120 if exercise_type == "Strength" else 60, key=f"rest_{i}_{ex}_Base")
                                    try:
                                        low, high = map(float, percent_1rm.split('-'))
                                        if low < 0 or high > 1.0:
                                            st.error(f"Invalid %1RM for {ex} in Base phase: must be between 0 and 1.0.")
                                            continue
                                        temp_days[i]["prescriptions"]["Base"][ex] = {
                                            "sets": sets, "reps": reps, "percent_1rm": (low, high), "rpe": rpe, "rest": rest
                                        }
                                    except ValueError:
                                        st.error(f"Invalid %1RM format for {ex} in Base phase. Use 'low-high' (e.g., 0.65-0.75).")
                    else:
                        temp_days[i]["name"] = f"Rest Day {i+1}"
                        temp_days[i]["description"] = st.text_area(f"Rest Day Description", value=temp_days[i]["description"], key=f"rest_desc_{i}")
                        temp_days[i]["schedule"] = st.multiselect(f"Schedule (days of week)", options=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], default=temp_days[i]["schedule"], key=f"rest_schedule_{i}")
                        temp_days[i]["exercises"] = []
                        temp_days[i]["prescriptions"] = {"Base": {}, "Intensity": {}, "Peaking": {}}
            
            st.markdown("### Step 3: Review & Save")
            if num_days > 0:
                st.write("**Weekly Structure Preview**")
                for i, day in enumerate(temp_days):
                    st.markdown(f"- **{day['name']}** ({', '.join(day['schedule'])}): {day['description']}")
                    if day["type"] == "Workout":
                        st.markdown("  Exercises: " + (", ".join(day["exercises"]) if day["exercises"] else "None"))
            
            if st.form_submit_button("Update Program"):
                if not program_name:
                    st.error("Program name is required.")
                else:
                    # Update session state with form data
                    st.session_state.num_days = num_days
                    st.session_state.days = temp_days
                    base_week = {
                        "name": program_name,
                        "duration_weeks": 1,
                        "description": program_description,
                        "days": {day["name"]: {"description": day["description"], "exercises": day["exercises"], "schedule": [ ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].index(s) for s in day["schedule"] ]} for day in temp_days},
                        "prescriptions": {day["name"]: {"Base": day["prescriptions"]["Base"]} for day in temp_days}
                    }
                    valid, message = validate_program(base_week)
                    if valid:
                        st.session_state.base_week = base_week
                        st.success("Base week saved! You can now generate a full program or save as is.")
                    else:
                        st.error(f"Failed to save base week: {message}")
        
        if 'base_week' in st.session_state and st.session_state.num_days > 0:
            with st.form(key="generate_program_form"):
                if st.form_submit_button("Generate Autoregulated Program"):
                    program = st.session_state.base_week.copy()
                    program["duration_weeks"] = duration_weeks
                    periodized = generate_periodized_program(st.session_state.base_week)
                    program["prescriptions"] = periodized["prescriptions"]
                    valid, message = validate_program(program)
                    if valid:
                        if save_program(program):
                            st.success("Full program generated and saved successfully!")
                            st.session_state.num_days = 0
                            st.session_state.days = []
                            if 'base_week' in st.session_state:
                                del st.session_state.base_week
                            st.rerun()
                        else:
                            st.error("Program name already exists. Please choose a unique name.")
                    else:
                        st.error(f"Failed to generate program: {message}")
        
        st.subheader("Import Program")
        st.write("Upload JSON or CSV. JSON should match default program structure. CSV needs: day, day_description, exercise, schedule (comma-separated), Base_sets, Base_reps, Base_percent_1rm, Base_rpe, Base_rest, etc.")
        uploaded_file = st.file_uploader("Upload JSON or CSV Program File", type=["json", "csv"])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".json"):
                    program = json.load(uploaded_file)
                else:
                    df = pd.read_csv(uploaded_file)
                    program = {
                        "name": uploaded_file.name.split(".")[0],
                        "duration_weeks": int(df["duration_weeks"].iloc[0]),
                        "description": df["description"].iloc[0],
                        "days": {},
                        "prescriptions": {}
                    }
                    for day in df["day"].unique():
                        day_df = df[df["day"] == day]
                        program["days"][day] = {
                            "description": day_df["day_description"].iloc[0],
                            "exercises": day_df["exercise"].tolist(),
                            "schedule": [int(x) for x in day_df["schedule"].iloc[0].split(",")]
                        }
                        program["prescriptions"][day] = {}
                        for phase in ["Base", "Intensity", "Peaking"]:
                            program["prescriptions"][day][phase] = {}
                            for _, row in day_df.iterrows():
                                ex = row["exercise"]
                                if "running" in day.lower() or "speed" in day.lower() or "conditioning" in day.lower():
                                    program["prescriptions"][day][phase][ex] = {
                                        "duration": row[f"{phase}_duration"],
                                        "distance": row[f"{phase}_distance"],
                                        "pace": row[f"{phase}_pace"],
                                        "rpe": row[f"{phase}_rpe"],
                                        "rest": int(row[f"{phase}_rest"])
                                    }
                                else:
                                    percent_1rm = tuple(map(float, row[f"{phase}_percent_1rm"].split("-")))
                                    program["prescriptions"][day][phase][ex] = {
                                        "sets": row[f"{phase}_sets"],
                                        "reps": row[f"{phase}_reps"],
                                        "percent_1rm": percent_1rm,
                                        "rpe": row[f"{phase}_rpe"],
                                        "rest": int(row[f"{phase}_rest"])
                                    }
                valid, message = validate_program(program)
                if valid:
                    if save_program(program):
                        st.success("Program imported successfully!")
                        st.rerun()
                    else:
                        st.error("Program name already exists. Please choose a unique name.")
                else:
                    st.error(f"Failed to import program: {message}")
            except Exception as e:
                st.error(f"Error importing program: {str(e)}")