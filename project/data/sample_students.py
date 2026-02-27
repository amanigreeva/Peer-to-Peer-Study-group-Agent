"""
Sample student data generator for testing and demonstration.
"""
import random
from typing import List
from models.student import Student, SUBJECTS, LEARNING_STYLES, AVAILABILITY_OPTIONS

FIRST_NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Ethan", "Fiona", "George", "Hannah",
    "Ivan", "Julia", "Kevin", "Laura", "Michael", "Nina", "Oscar", "Priya",
    "Quincy", "Rachel", "Samuel", "Tina", "Uma", "Victor", "Wendy", "Xavier",
    "Yara", "Zach", "Aisha", "Ben", "Carmen", "David"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Taylor", "Anderson", "Thomas", "Jackson", "White",
    "Harris", "Martin", "Thompson", "Martinez", "Robinson", "Clark"
]


def generate_sample_students(n: int = 30, seed: int = 42) -> List[Student]:
    """
    Generate n sample students with varied academic profiles.

    Profiles are intentionally varied to create interesting clustering:
    - STEM-focused: high Math/Physics/CS, lower English/Biology
    - Arts-focused: high English/Biology, lower Math/CS
    - Balanced: moderate scores across the board
    - Struggling: low scores needing support
    """
    random.seed(seed)
    students = []

    profiles = {
        "stem": {
            "Mathematics": (75, 99),
            "Physics": (70, 95),
            "Chemistry": (60, 90),
            "Biology": (40, 70),
            "English": (45, 75),
            "Computer Science": (75, 99),
        },
        "arts": {
            "Mathematics": (35, 65),
            "Physics": (30, 60),
            "Chemistry": (40, 70),
            "Biology": (65, 90),
            "English": (75, 99),
            "Computer Science": (35, 65),
        },
        "balanced": {
            "Mathematics": (55, 80),
            "Physics": (55, 80),
            "Chemistry": (55, 80),
            "Biology": (55, 80),
            "English": (55, 80),
            "Computer Science": (55, 80),
        },
        "struggling": {
            "Mathematics": (25, 55),
            "Physics": (20, 50),
            "Chemistry": (25, 55),
            "Biology": (30, 60),
            "English": (30, 60),
            "Computer Science": (20, 50),
        },
    }
    profile_weights = ["stem"] * 8 + ["arts"] * 8 + ["balanced"] * 8 + ["struggling"] * 6

    used_names = set()
    for i in range(n):
        # Generate unique name
        while True:
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            if name not in used_names:
                used_names.add(name)
                break

        profile_key = profile_weights[i % len(profile_weights)]
        profile = profiles[profile_key]

        subjects = {
            subj: round(random.uniform(*rng), 1)
            for subj, rng in profile.items()
        }

        availability_count = random.randint(1, 3)
        availability = random.sample(AVAILABILITY_OPTIONS, availability_count)

        first_name = name.split()[0].lower()
        last_name = name.split()[1].lower()
        email = f"{first_name}.{last_name}@university.edu"

        students.append(Student(
            id=i + 1,
            name=name,
            subjects=subjects,
            learning_style=random.choice(LEARNING_STYLES),
            availability=sorted(availability),
            email=email,
        ))

    return students


if __name__ == "__main__":
    students = generate_sample_students(10)
    for s in students:
        print(f"{s.name:25s} | avg={s.average_score:.1f} | strengths={s.strengths}")
