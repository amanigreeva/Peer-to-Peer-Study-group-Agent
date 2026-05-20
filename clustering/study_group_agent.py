"""
Study Group Agent — core clustering engine.

Supports a hybrid grouping framework:
  - 'hierarchical': Agglomerative Hierarchical Clustering (Ward linkage).
                 Forms a hierarchy by iteratively merging pairs that
                 minimize within-cluster variance.
  - 'balanced'   : Subject-coverage balancing — guarantees each group
                 has expert representation across ALL subjects,
                 optimised further by a Hill Climbing local search.

Framework: KNN-based missing value imputation → Z-score normalization →
           Ward-based hierarchical clustering → greedy constraint balancing.
"""

import os
import math
import random
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")          # non-interactive backend for server use
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.impute import KNNImputer
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from models.student import Student, SUBJECTS


class StudyGroupAgent:
    """
    AI agent that automatically forms optimal peer-to-peer study groups
    by clustering students based on their academic profiles.
    """

    def __init__(self):
        self._students: List[Student] = []
        self._scaler = StandardScaler()
        self._imputer = KNNImputer(n_neighbors=5)
        self._last_groups: Optional[Dict[int, List[Student]]] = None

    # ------------------------------------------------------------------
    # Student management
    # ------------------------------------------------------------------

    def add_student(self, student: Student) -> None:
        self._students.append(student)

    def load_students(self, students: List[Student]) -> None:
        self._students = list(students)

    def get_students(self) -> List[Student]:
        return list(self._students)

    def clear(self) -> None:
        self._students = []
        self._last_groups = None

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    def _build_feature_matrix(self) -> Tuple[np.ndarray, List[str]]:
        """
        Build a feature matrix from student subject scores.
        Implements KNN-based missing value imputation and Z-score normalization.
        Returns (matrix, column_names).
        """
        subjects = SUBJECTS
        rows = []
        for student in self._students:
            # We use None for missing data to signal KNNImputer, but 0.0 is also treated as missing here
            row = [student.subjects.get(s, np.nan) for s in subjects]
            # If all are nan, use 0.0 to avoid crash
            if all(np.isnan(row)): row = [0.0] * len(subjects)
            rows.append(row)

        matrix = np.array(rows, dtype=float)

        # KNN Imputation for missing marks
        if np.isnan(matrix).any():
            matrix = self._imputer.fit_transform(matrix)

        # Z-score Normalization (StandardScaler)
        matrix = self._scaler.fit_transform(matrix)
        return matrix, subjects

    # ------------------------------------------------------------------
    # Auto-select optimal number of groups
    # ------------------------------------------------------------------

    def _optimal_n_groups(self, matrix: np.ndarray) -> int:
        """
        Use the silhouette method to find the best k in [2, sqrt(n)].
        AgglomerativeClustering is used to evaluate group quality at each k.
        Falls back to ceil(n / 4) if n is too small.
        """
        n = len(self._students)
        if n < 4:
            return 2
        max_k = max(2, int(math.sqrt(n)))
        if max_k < 3:
            return 2

        best_k, best_score = 2, -1.0
        for k in range(2, min(max_k + 1, n)):
            model = AgglomerativeClustering(n_clusters=k, linkage='ward')
            labels = model.fit_predict(matrix)
            if len(set(labels)) < 2:
                continue
            score = silhouette_score(matrix, labels)
            if score > best_score:
                best_score = score
                best_k = k
        return best_k

    # ------------------------------------------------------------------
    # Group formation
    # ------------------------------------------------------------------

    def _default_n_groups(self) -> int:
        """Sensible default: ~4-5 students per group."""
        n = len(self._students)
        return max(2, round(n / 4))

    def _balanced_grouping(self, n_groups: int) -> Dict[int, List[Student]]:
        """
        Subject-Balanced (Greedy) Grouping Algorithm
        ============================================
        Goal: every group should have a strong student in each subject.
        Iteratively assigns students to the group where they provide the most
        immediate benefit to subject coverage deficiencies.
        """
        students = list(self._students)
        n = len(students)
        groups: Dict[int, List[Student]] = {i + 1: [] for i in range(n_groups)}
        max_size = math.ceil(n / n_groups)

        # Sort students by their maximum subject score (experts first)
        sorted_students = sorted(
            students,
            key=lambda s: max(s.subjects.values()) if s.subjects else 0,
            reverse=True
        )

        for student in sorted_students:
            best_gid = -1
            max_reduction = -1.0
            
            # Find the group that has the largest deficit in this student's expertise
            # but still has room.
            potential_gids = [gid for gid, m in groups.items() if len(m) < max_size]
            if not potential_gids:
                potential_gids = [min(groups.keys(), key=lambda gid: len(groups[gid]))]

            for gid in potential_gids:
                members = groups[gid]
                deficit_reduction = 0.0
                
                # For each subject, how much does this student improve the group's best score?
                for subj in SUBJECTS:
                    current_max = max([m.subjects.get(subj, 0.0) for m in members]) if members else 0.0
                    student_score = student.subjects.get(subj, 0.0)
                    if student_score > current_max:
                        deficit_reduction += (student_score - current_max)
                
                if deficit_reduction > max_reduction:
                    max_reduction = deficit_reduction
                    best_gid = gid
                elif deficit_reduction == max_reduction:
                    # Tie-break: pick the smaller group
                    if best_gid == -1 or len(groups[gid]) < len(groups[best_gid]):
                        best_gid = gid
            
            groups[best_gid].append(student)
            
        groups = self._balance_hill_climb(groups)
            
        return groups

    def _balance_hill_climb(self, groups: Dict[int, List[Student]], iterations: int = 1000) -> Dict[int, List[Student]]:
        """
        Local Search (Hill Climbing) optimization for study groups.
        Attempts to swap students between groups to improve the overall
        subject coverage and complementarity.
        """
        def evaluate(g: Dict[int, List[Student]]) -> float:
            # We want to maximize the average of the max expert score per subject across groups
            coverage_totals = []
            comp_scores = []
            
            for gid, members in g.items():
                if not members:
                    continue
                
                # Subject coverage
                subject_max = {}
                for subj in SUBJECTS:
                    scores = [m.subjects.get(subj, 0.0) for m in members]
                    subject_max[subj] = max(scores) if scores else 0.0
                coverage_totals.append(np.mean(list(subject_max.values())))

                # Complementarity (std-dev of member averages - higher means more diverse mix)
                member_avgs = [m.average_score for m in members]
                if len(member_avgs) > 1:
                    comp_scores.append(np.std(member_avgs))
                else:
                    comp_scores.append(0.0)
            
            # Weighted score: mostly care about coverage, but complementarity breaks ties
            # We add them together because we want to maximize both
            return np.mean(coverage_totals) + (np.mean(comp_scores) * 0.5)

        current_score = evaluate(groups)
        group_ids = list(groups.keys())
        
        if len(group_ids) < 2:
            return groups

        for _ in range(iterations):
            g1_id, g2_id = random.sample(group_ids, 2)
            if not groups[g1_id] or not groups[g2_id]:
                continue
                
            idx1 = random.randrange(len(groups[g1_id]))
            idx2 = random.randrange(len(groups[g2_id]))
            
            # Swap
            student1 = groups[g1_id][idx1]
            student2 = groups[g2_id][idx2]
            
            groups[g1_id][idx1] = student2
            groups[g2_id][idx2] = student1
            
            new_score = evaluate(groups)
            
            if new_score > current_score + 1e-5: # Strict improvement needed to avoid infinite plateaus
                current_score = new_score
            else:
                # Revert
                groups[g1_id][idx1] = student1
                groups[g2_id][idx2] = student2
                
        return groups

    def form_groups(
        self,
        method: str = "balanced",
        n_groups: Optional[int] = None,
    ) -> Dict[int, List[Student]]:
        """
        Form study groups using the chosen algorithm.

        Args:
            method: 'balanced' (default) or 'hierarchical'
            n_groups: Number of groups. Auto-detected if None.

        Returns:
            dict mapping group_id (1-indexed) → list of Student objects.
        """
        if not self._students:
            raise ValueError("No students loaded. Call load_students() first.")
        if len(self._students) < 2:
            return {1: list(self._students)}

        if n_groups is None:
            if method == "balanced":
                n_groups = self._default_n_groups()
            else:
                matrix, _ = self._build_feature_matrix()
                n_groups = self._optimal_n_groups(matrix)
        n_groups = min(n_groups, len(self._students))

        if method == "balanced":
            groups = self._balanced_grouping(n_groups)
            self._last_groups = groups
            return groups

        matrix, _ = self._build_feature_matrix()

        if method == "hierarchical":
            model = AgglomerativeClustering(n_clusters=n_groups, linkage='ward')
            labels = model.fit_predict(matrix)
        else:
            raise ValueError(
                f"Unknown method '{method}'. Choose 'balanced' or 'hierarchical'."
            )

        groups_raw: Dict[int, List[Student]] = {i + 1: [] for i in range(n_groups)}
        for student, label in zip(self._students, labels):
            groups_raw[int(label) + 1].append(student)

        non_empty = {new_id + 1: members
                     for new_id, (_, members) in enumerate(groups_raw.items())
                     if members}
        self._last_groups = non_empty
        return non_empty

    # ------------------------------------------------------------------
    # Group evaluation
    # ------------------------------------------------------------------

    def evaluate_groups(
        self, groups: Optional[Dict[int, List[Student]]] = None
    ) -> Dict:
        """
        Evaluate the quality of the current group assignment.

        Returns a dict with:
          - complementarity_score : within-group std-dev of subject averages
          - diversity_index       : std-dev of group average scores
          - subject_coverage_score: avg of (max expert score per subject)
                                    across all groups — KEY metric for balanced mode
          - group_stats           : per-group details
        """
        groups = groups or self._last_groups
        if not groups:
            return {}

        group_stats = {}
        comp_scores = []
        avg_scores = []
        coverage_totals = []

        for gid, members in groups.items():
            if not members:
                continue

            # Subject averages and max-expert within group
            subject_avgs: Dict[str, float] = {}
            subject_max: Dict[str, float] = {}
            for subj in SUBJECTS:
                scores = [m.subjects.get(subj, 0.0) for m in members]
                subject_avgs[subj] = round(float(np.mean(scores)), 2)
                subject_max[subj] = round(float(max(scores)), 2)

            # Complementarity: std-dev of individual member averages (within group)
            member_avgs_within = [m.average_score for m in members]
            comp = float(np.std(member_avgs_within))
            comp_scores.append(comp)

            # Subject coverage: average of best-score-per-subject for this group
            coverage = float(np.mean(list(subject_max.values())))
            coverage_totals.append(coverage)

            group_avgs_val = float(np.mean(member_avgs_within))
            avg_scores.append(group_avgs_val)

            group_stats[gid] = {
                "size": len(members),
                "avg_score": round(group_avgs_val, 2),
                "subject_averages": subject_avgs,
                "subject_coverage": subject_max,   # best expert per subject
                "complementarity": round(comp, 2),
                "coverage_score": round(coverage, 2),
                "members": [m.name for m in members],
            }

        return {
            "n_groups": len(groups),
            "total_students": sum(len(m) for m in groups.values()),
            "complementarity_score": round(float(np.mean(comp_scores)), 2),
            "diversity_index": round(float(np.std(avg_scores)), 2),
            "subject_coverage_score": round(float(np.mean(coverage_totals)), 2),
            "group_stats": group_stats,
        }

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def visualize_groups(
        self,
        groups: Optional[Dict[int, List[Student]]] = None,
        save_path: Optional[str] = None,
    ) -> str:
        """
        Generate a 2-D PCA scatter plot of students coloured by group.
        Saves as PNG and returns the file path.
        """
        groups = groups or self._last_groups
        if not groups or not self._students:
            return ""

        matrix, feature_names = self._build_feature_matrix()

        # PCA to 2 dimensions
        pca = PCA(n_components=2, random_state=42)
        coords = pca.fit_transform(matrix)

        # Build label array
        student_to_group = {}
        for gid, members in groups.items():
            for m in members:
                student_to_group[m.id] = gid
        labels = np.array([student_to_group.get(s.id, 0) for s in self._students])

        n_groups = len(groups)
        colors = matplotlib.colormaps.get_cmap("tab20")

        fig, ax = plt.subplots(figsize=(10, 7))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#16213e")

        for gid in sorted(groups.keys()):
            mask = labels == gid
            ax.scatter(
                coords[mask, 0],
                coords[mask, 1],
                s=120,
                color=colors(gid),
                label=f"Group {gid}",
                edgecolors="white",
                linewidths=0.6,
                alpha=0.9,
                zorder=3,
            )
            # Annotate names
            for idx in np.where(mask)[0]:
                name_parts = self._students[idx].name.split()
                name = name_parts[0] if name_parts else "Student"
                ax.annotate(
                    name,
                    (coords[idx, 0], coords[idx, 1]),
                    fontsize=7,
                    color="white",
                    alpha=0.8,
                    xytext=(4, 4),
                    textcoords="offset points",
                )

        ax.set_title(
            "Peer Study Groups — PCA Projection",
            color="white",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )
        ax.set_xlabel(
            f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)",
            color="#aaaacc",
        )
        ax.set_ylabel(
            f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)",
            color="#aaaacc",
        )
        ax.tick_params(colors="gray")
        for spine in ax.spines.values():
            spine.set_edgecolor("#333355")

        legend = ax.legend(
            loc="upper right",
            facecolor="#1a1a2e",
            edgecolor="#555577",
            labelcolor="white",
            fontsize=9,
        )

        plt.tight_layout()
        if save_path:
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
            fig.savefig(save_path, dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            return save_path
        else:
            import io
            import base64
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)
            img_b64 = base64.b64encode(buf.read()).decode("utf-8")
            return f"data:image/png;base64,{img_b64}"

    # ------------------------------------------------------------------
    # Pretty-print
    # ------------------------------------------------------------------

    def print_groups(self, groups: Optional[Dict[int, List[Student]]] = None) -> None:
        groups = groups or self._last_groups
        if not groups:
            print("No groups formed yet.")
            return

        width = 60
        print("\n" + "=" * width)
        print(" 📚  PEER STUDY GROUPS ".center(width))
        print("=" * width)

        for gid, members in sorted(groups.items()):
            print(f"\n  Group {gid}  ({len(members)} student{'s' if len(members) != 1 else ''})")
            print("  " + "-" * (width - 2))
            for m in members:
                strengths_str = ", ".join(m.strengths) or "—"
                weaknesses_str = ", ".join(m.weaknesses) or "—"
                print(f"    ▸ {m.name:<22} avg={m.average_score:5.1f}")
                print(f"        💪 {strengths_str}")
                print(f"        🔧 {weaknesses_str}")

        eval_data = self.evaluate_groups(groups)
        print("\n" + "=" * width)
        print(f"  Complementarity score : {eval_data.get('complementarity_score', 0):.2f}")
        print(f"  Diversity index       : {eval_data.get('diversity_index', 0):.2f}")
        print("=" * width + "\n")
