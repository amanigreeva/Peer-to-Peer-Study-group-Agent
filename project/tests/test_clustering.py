"""
Unit tests for the Study Group Agent clustering engine.
Run with:  python -m pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models.student import Student, SUBJECTS
from clustering.study_group_agent import StudyGroupAgent
from data.sample_students import generate_sample_students


# ── Fixtures ──────────────────────────────────────────────────────────

def make_student(sid: int, scores: dict) -> Student:
    """Helper: create a Student with given subject scores."""
    base = {s: 50.0 for s in SUBJECTS}
    base.update(scores)
    return Student(id=sid, name=f"Student {sid}", subjects=base)


@pytest.fixture
def small_class():
    """6 students with distinct profiles."""
    return [
        make_student(1, {"Mathematics": 95, "Computer Science": 90, "English": 40}),
        make_student(2, {"Mathematics": 88, "Physics": 85, "Biology": 35}),
        make_student(3, {"English": 92, "Biology": 88, "Mathematics": 38}),
        make_student(4, {"English": 85, "Chemistry": 80, "Computer Science": 32}),
        make_student(5, {"Mathematics": 30, "Physics": 28, "English": 75}),
        make_student(6, {"Biology": 92, "Chemistry": 88, "Mathematics": 42}),
    ]


@pytest.fixture
def large_class():
    """30 auto-generated students."""
    return generate_sample_students(30)


@pytest.fixture
def agent():
    return StudyGroupAgent()


# ── Student model tests ───────────────────────────────────────────────

class TestStudentModel:
    def test_strengths(self):
        s = make_student(1, {"Mathematics": 85, "English": 45})
        assert "Mathematics" in s.strengths
        assert "English" not in s.strengths

    def test_weaknesses(self):
        s = make_student(1, {"Mathematics": 85, "English": 45})
        assert "English" in s.weaknesses
        assert "Mathematics" not in s.weaknesses

    def test_average_score(self):
        s = Student(id=1, name="T", subjects={"A": 80, "B": 60, "C": 40})
        assert abs(s.average_score - 60.0) < 1e-6

    def test_score_clamping(self):
        s = Student(id=1, name="T", subjects={"Math": 150, "Eng": -10})
        assert s.subjects["Math"] == 100.0
        assert s.subjects["Eng"] == 0.0

    def test_to_dict_roundtrip(self):
        s = make_student(5, {"English": 77})
        d = s.to_dict()
        s2 = Student.from_dict(d)
        assert s.name == s2.name
        assert s.subjects == s2.subjects


# ── Clustering engine tests ───────────────────────────────────────────

class TestStudyGroupAgent:

    def test_load_students(self, agent, small_class):
        agent.load_students(small_class)
        assert len(agent.get_students()) == 6

    def test_add_student(self, agent):
        s = make_student(99, {})
        agent.add_student(s)
        assert s in agent.get_students()

    def test_clear(self, agent, small_class):
        agent.load_students(small_class)
        agent.clear()
        assert agent.get_students() == []

    def test_gmm_correct_group_count_alternate(self, agent, small_class):
        agent.load_students(small_class)
        groups = agent.form_groups(method="hierarchical", n_groups=3)
        assert len(groups) == 3

    def test_hierarchical_correct_group_count(self, agent, small_class):
        agent.load_students(small_class)
        groups = agent.form_groups(method="hierarchical", n_groups=2)
        assert len(groups) == 2

    def test_groups_contain_all_students(self, agent, small_class):
        agent.load_students(small_class)
        groups = agent.form_groups(method="hierarchical", n_groups=3)
        all_ids = {s.id for members in groups.values() for s in members}
        expected_ids = {s.id for s in small_class}
        assert all_ids == expected_ids

    def test_hierarchical_auto_detect_n_groups(self, agent, large_class):
        agent.load_students(large_class)
        groups = agent.form_groups(method="hierarchical", n_groups=None)
        assert 2 <= len(groups) <= len(large_class) // 2

    def test_hierarchical_large_alt(self, agent, large_class):
        agent.load_students(large_class)
        groups = agent.form_groups(method="hierarchical", n_groups=6)
        total = sum(len(m) for m in groups.values())
        assert total == len(large_class)

    def test_hierarchical_large(self, agent, large_class):
        agent.load_students(large_class)
        groups = agent.form_groups(method="hierarchical", n_groups=5)
        total = sum(len(m) for m in groups.values())
        assert total == len(large_class)

    def test_invalid_method_raises(self, agent, small_class):
        agent.load_students(small_class)
        with pytest.raises(ValueError, match="Unknown method"):
            agent.form_groups(method="gmm")

    def test_no_students_raises(self, agent):
        with pytest.raises(ValueError, match="No students"):
            agent.form_groups()

    def test_single_student_returns_one_group(self, agent):
        agent.load_students([make_student(1, {})])
        groups = agent.form_groups()
        assert len(groups) == 1
        assert len(list(groups.values())[0]) == 1

    def test_balanced_correct_group_count(self, agent, small_class):
        agent.load_students(small_class)
        # 6 students in groups of 2
        groups = agent.form_groups(method="balanced", n_groups=3)
        assert len(groups) == 3

    def test_balanced_large(self, agent, large_class):
        agent.load_students(large_class)
        # 30 students / 5 groups = 6 students per group
        groups = agent.form_groups(method="balanced", n_groups=5)
        total = sum(len(m) for m in groups.values())
        assert total == len(large_class)
        for gid, members in groups.items():
            assert len(members) == 6

    # ── Evaluation ──

    def test_evaluation_keys(self, agent, small_class):
        agent.load_students(small_class)
        groups = agent.form_groups(method="hierarchical", n_groups=2)
        ev = agent.evaluate_groups(groups)
        assert "complementarity_score" in ev
        assert "diversity_index" in ev
        assert "group_stats" in ev
        assert "n_groups" in ev

    def test_evaluation_group_stats_structure(self, agent, small_class):
        agent.load_students(small_class)
        groups = agent.form_groups(method="hierarchical", n_groups=2)
        ev = agent.evaluate_groups(groups)
        for gid, stats in ev["group_stats"].items():
            assert "size" in stats
            assert "avg_score" in stats
            assert "members" in stats
            assert "subject_averages" in stats

    def test_complementarity_positive(self, agent, large_class):
        agent.load_students(large_class)
        groups = agent.form_groups(method="hierarchical", n_groups=5)
        ev = agent.evaluate_groups(groups)
        assert ev["complementarity_score"] >= 0

    # ── Visualisation ──

    def test_visualize_creates_file(self, agent, large_class, tmp_path):
        agent.load_students(large_class)
        groups = agent.form_groups(method="hierarchical", n_groups=5)
        path = str(tmp_path / "test_plot.png")
        saved = agent.visualize_groups(groups, save_path=path)
        assert saved == path
        assert os.path.exists(path)
        assert os.path.getsize(path) > 1000   # non-trivial PNG
