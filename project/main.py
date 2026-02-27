"""
CLI entry point for the Peer-to-Peer Study Group Agent.

Usage:
    python main.py
"""
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.sample_students import generate_sample_students
from clustering.study_group_agent import StudyGroupAgent


def banner():
    print("""
╔══════════════════════════════════════════════════════╗
║        📚  Peer-to-Peer Study Group Agent  📚        ║
║    Optimising Collaborative Learning with AI         ║
╚══════════════════════════════════════════════════════╝
""")


def prompt_int(prompt: str, default: int, min_val: int, max_val: int) -> int:
    while True:
        try:
            raw = input(f"{prompt} [{default}]: ").strip()
            if raw == "":
                return default
            val = int(raw)
            if min_val <= val <= max_val:
                return val
            print(f"  ⚠  Please enter a number between {min_val} and {max_val}.")
        except ValueError:
            print("  ⚠  Invalid input. Please enter an integer.")


def prompt_choice(prompt: str, choices: list, default: str) -> str:
    choices_str = "/".join(choices)
    while True:
        raw = input(f"{prompt} [{choices_str}] (default={default}): ").strip().lower()
        if raw == "":
            return default
        if raw in choices:
            return raw
        print(f"  ⚠  Choose one of: {choices_str}")


def main():
    banner()

    # --- Load students ---
    print("Step 1 — Load students")
    n = prompt_int("  How many sample students to generate?", default=20, min_val=4, max_val=100)
    students = generate_sample_students(n)
    print(f"\n  ✔  Loaded {len(students)} students.\n")

    agent = StudyGroupAgent()
    agent.load_students(students)

    # --- Choose clustering method ---
    print("Step 2 — Choose clustering algorithm")
    method = prompt_choice(
        "  Algorithm", ["balanced", "gmm"], default="balanced"
    )

    # --- Choose number of groups ---
    print("\nStep 3 — Number of study groups")
    auto = prompt_choice(
        "  Auto-detect optimal group count?", ["y", "n"], default="y"
    )
    if auto == "y":
        n_groups = None
        print("  ✔  Will auto-detect optimal group count.\n")
    else:
        n_groups = prompt_int(
            "  How many groups?", default=max(2, n // 4), min_val=2, max_val=n // 2
        )

    # --- Form groups ---
    print(f"\n  ⏳ Running {method} clustering…")
    groups = agent.form_groups(method=method, n_groups=n_groups)

    # --- Print results ---
    agent.print_groups(groups)

    # --- Visualise ---
    print("Step 4 — Save cluster visualisation")
    viz_path = "cluster_plot.png"
    saved = agent.visualize_groups(groups, save_path=viz_path)
    if saved:
        print(f"  ✔  Plot saved → {os.path.abspath(saved)}\n")
    else:
        print("  ⚠  Visualisation could not be saved.\n")

    print("  Done!  Launch the web dashboard with:  python app.py\n")


if __name__ == "__main__":
    main()
