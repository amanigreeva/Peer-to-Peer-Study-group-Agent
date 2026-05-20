"""
Student data model for the Peer-to-Peer Study Group Agent.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


SUBJECTS = ["Mathematics", "Physics", "Chemistry", "Biology", "English", "Computer Science"]

LEARNING_STYLES = ["Visual", "Auditory", "Reading/Writing", "Kinesthetic"]

AVAILABILITY_OPTIONS = ["Morning", "Afternoon", "Evening", "Weekend"]


@dataclass
class Student:
    """Represents a student with academic profile."""
    id: int
    name: str
    subjects: Dict[str, float] = field(default_factory=dict)
    learning_style: str = "Visual"
    availability: List[str] = field(default_factory=list)
    email: Optional[str] = None

    def __post_init__(self):
        # Clamp subject scores to 0-100
        for subj, score in self.subjects.items():
            self.subjects[subj] = max(0.0, min(100.0, float(score)))

    @property
    def strengths(self) -> List[str]:
        """Subjects where score >= 70."""
        return [s for s, score in self.subjects.items() if score >= 70]

    @property
    def weaknesses(self) -> List[str]:
        """Subjects where score < 50."""
        return [s for s, score in self.subjects.items() if score < 50]

    @property
    def average_score(self) -> float:
        if not self.subjects:
            return 0.0
        return sum(self.subjects.values()) / len(self.subjects)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "subjects": self.subjects,
            "learning_style": self.learning_style,
            "availability": self.availability,
            "email": self.email,
            "average_score": round(self.average_score, 2),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Student":
        return cls(
            id=data["id"],
            name=data["name"],
            subjects=data.get("subjects", {}),
            learning_style=data.get("learning_style", "Visual"),
            availability=data.get("availability", []),
            email=data.get("email"),
        )

    def __repr__(self) -> str:
        return f"Student(id={self.id}, name='{self.name}', avg={self.average_score:.1f})"
