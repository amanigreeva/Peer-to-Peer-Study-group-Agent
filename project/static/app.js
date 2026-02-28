/* ── Study Group Agent — Frontend Logic ── */

const GROUP_COLORS = [
    { bg: "linear-gradient(135deg,#7c3aed,#a855f7)", text: "#fff" },
    { bg: "linear-gradient(135deg,#ec4899,#f472b6)", text: "#fff" },
    { bg: "linear-gradient(135deg,#0891b2,#22d3ee)", text: "#fff" },
    { bg: "linear-gradient(135deg,#059669,#34d399)", text: "#fff" },
    { bg: "linear-gradient(135deg,#d97706,#fbbf24)", text: "#fff" },
    { bg: "linear-gradient(135deg,#dc2626,#f87171)", text: "#fff" },
    { bg: "linear-gradient(135deg,#7c3aed,#06b6d4)", text: "#fff" },
    { bg: "linear-gradient(135deg,#be185d,#7c3aed)", text: "#fff" },
];

const AVATAR_COLORS = [
    "#7c3aed", "#ec4899", "#0891b2", "#059669",
    "#d97706", "#dc2626", "#2563eb", "#9333ea",
];

// ── State ────────────────────────────────────────────────────────────
let studentsMap = {}; // ID -> Student Object

// ── Utility ──────────────────────────────────────────────────────────

let toastTimer = null;
function showToast(msg, type = "success") {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.className = `toast ${type}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.classList.add("hidden"); }, 3200);
}

function setLoader(show) {
    const l = document.getElementById("loader");
    show ? l.classList.remove("hidden") : l.classList.add("hidden");
}

function initials(name) {
    if (!name) return "??";
    return name.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
}

// ── Student Modal ───────────────────────────────────────────────────

function openStudentModal(sid) {
    const s = studentsMap[sid];
    if (!s) return;

    document.getElementById("modalName").textContent = s.name;
    document.getElementById("modalEmail").textContent = s.email || "No email provided";
    document.getElementById("modalStyle").textContent = s.learning_style;
    document.getElementById("modalAvail").textContent = (s.availability || []).join(", ") || "None";

    // Avatar
    const avatar = document.getElementById("modalAvatar");
    avatar.textContent = initials(s.name);

    // Subjects List
    const list = document.getElementById("modalSubjectsList");
    list.innerHTML = "";
    const subjects = ["Mathematics", "Physics", "Chemistry", "Biology", "English", "Computer Science"];

    subjects.forEach(subj => {
        const score = (s.subjects && s.subjects[subj] !== undefined) ? s.subjects[subj] : 0;
        const color = score >= 70 ? "#10b981" : (score >= 50 ? "#f59e0b" : "#ef4444");

        const row = document.createElement("div");
        row.className = "modal-subject-row";
        row.innerHTML = `
            <span class="modal-subject-name">${subj}</span>
            <div class="modal-subject-bar-wrap">
                <div class="modal-subject-fill" style="width: ${score}%; background: ${color}"></div>
            </div>
            <span class="modal-subject-score" style="color: ${color}">${Math.round(score)}</span>
        `;
        list.appendChild(row);
    });

    document.getElementById("studentModal").classList.remove("hidden");
}

function closeStudentModal() {
    document.getElementById("studentModal").classList.add("hidden");
}

document.getElementById("modalClose").addEventListener("click", closeStudentModal);
document.getElementById("studentModal").addEventListener("click", (e) => {
    if (e.target.id === "studentModal") closeStudentModal();
});

// ── Render students table ─────────────────────────────────────────────

function renderStudentRow(s) {
    const avgClass = s.average_score >= 70 ? "badge-high" : s.average_score >= 50 ? "badge-mid" : "badge-low";
    const strengthTags = (s.strengths || []).slice(0, 2)
        .map(t => `<span class="tag tag-strength">${t}</span>`).join("");
    const weaknessTags = (s.weaknesses || []).slice(0, 2)
        .map(t => `<span class="tag tag-weakness">${t}</span>`).join("");
    return `
    <tr class="student-row clickable" data-id="${s.id}">
      <td class="cell-id">${s.id}</td>
      <td class="cell-name">${s.name}</td>
      <td><span class="badge ${avgClass}">${s.average_score.toFixed(1)}</span></td>
      <td class="cell-tags">${strengthTags}</td>
      <td class="cell-tags">${weaknessTags}</td>
      <td>${s.learning_style}</td>
      <td><button class="btn-del" data-id="${s.id}" title="Remove">✕</button></td>
    </tr>`;
}

async function refreshStudents() {
    const res = await fetch("/api/students");
    const students = await res.json();

    // Update map
    studentsMap = {};
    students.forEach(s => studentsMap[s.id] = s);

    document.getElementById("totalStudents").textContent = students.length;
    const tbody = document.getElementById("studentsBody");
    tbody.innerHTML = students.map(renderStudentRow).join("");
    attachHandlers();
}

// ── Handlers ─────────────────────────────────────────────────────────

function attachHandlers() {
    // Delete handlers
    document.querySelectorAll(".btn-del").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation(); // Don't trigger row click
            const sid = btn.dataset.id;
            const res = await fetch(`/api/remove_student/${sid}`, { method: "DELETE" });
            const data = await res.json();
            if (data.success) {
                document.querySelector(`tr[data-id="${sid}"]`)?.remove();
                const cnt = parseInt(document.getElementById("totalStudents").textContent, 10);
                document.getElementById("totalStudents").textContent = cnt - 1;
                showToast("Student removed");
                delete studentsMap[sid];
            } else {
                showToast(data.error || "Failed to remove", "error");
            }
        });
    });

    // Row click handlers for profile
    document.querySelectorAll(".student-row").forEach(row => {
        row.addEventListener("click", () => {
            openStudentModal(row.dataset.id);
        });
    });
}

// ── Add student ───────────────────────────────────────────────────────

document.getElementById("addStudentForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const payload = {
        name: document.getElementById("fname").value.trim(),
        email: document.getElementById("femail").value.trim(),
        learning_style: document.getElementById("fstyle").value,
        availability: [...form.querySelectorAll("input[name='availability']:checked")].map(c => c.value),
    };
    form.querySelectorAll("input[type='range']").forEach(r => {
        payload[r.name] = parseFloat(r.value);
    });
    if (!payload.name) { showToast("Name is required", "error"); return; }

    const res = await fetch("/api/add_student", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.success) {
        showToast(`✔ Added ${data.student.name}`);
        studentsMap[data.student.id] = data.student;

        const tbody = document.getElementById("studentsBody");
        tbody.insertAdjacentHTML("afterbegin", renderStudentRow(data.student));
        attachHandlers();

        const cnt = parseInt(document.getElementById("totalStudents").textContent, 10);
        document.getElementById("totalStudents").textContent = cnt + 1;
        form.reset();
        form.querySelectorAll(".slider-val").forEach((s, i) => { s.textContent = 50; });
        form.querySelectorAll("input[type='range']").forEach(r => { r.value = 50; });
    } else {
        showToast(data.error || "Failed to add student", "error");
    }
});

// ── Seed ──────────────────────────────────────────────────────────────

document.getElementById("btnSeed").addEventListener("click", async () => {
    const n = parseInt(document.getElementById("seedCount").value, 10) || 20;
    const res = await fetch("/api/seed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n }),
    });
    const data = await res.json();
    if (data.success) {
        showToast(`✔ Loaded ${data.count} sample students`);
        refreshStudents();
        document.getElementById("groupsSection").classList.add("hidden");
    }
});

// ── Form groups ───────────────────────────────────────────────────────

document.getElementById("btnFormGroups").addEventListener("click", async () => {
    const method = document.getElementById("algorithm").value;
    const nRaw = document.getElementById("nGroups").value.trim();
    const payload = { method, n_groups: nRaw !== "" ? parseInt(nRaw, 10) : null };

    setLoader(true);
    document.getElementById("groupsSection").classList.add("hidden");

    const res = await fetch("/api/form_groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await res.json();
    setLoader(false);

    if (!data.success) {
        showToast(data.error || "Failed to form groups", "error");
        return;
    }

    renderGroups(data.groups, data.evaluation);
    const methodLabel = method === "balanced" ? "Subject-Balanced" : "Agglomerative Hierarchical";
    showToast(`✔ Formed ${Object.keys(data.groups).length} groups using ${methodLabel}`);
});

// ── Render groups ─────────────────────────────────────────────────────

function renderGroups(groups, evaluation) {
    // Update header stats
    document.getElementById("totalGroups").textContent = Object.keys(groups).length;
    const coverageVal = evaluation.subject_coverage_score;
    document.getElementById("compScore").textContent =
        coverageVal != null ? coverageVal.toFixed(1) : "—";

    const evalBar = document.getElementById("evalBar");
    evalBar.innerHTML = `
    <div class="eval-item">
      <span class="eval-label">Groups Formed</span>
      <span class="eval-value">${evaluation.n_groups}</span>
    </div>
    <div class="eval-item">
      <span class="eval-label">Total Students</span>
      <span class="eval-value">${evaluation.total_students}</span>
    </div>
    <div class="eval-item">
      <span class="eval-label">📊 Subject Coverage</span>
      <span class="eval-value" style="color:#10b981">${evaluation.subject_coverage_score?.toFixed(1) ?? "—"}</span>
    </div>
    <div class="eval-item">
      <span class="eval-label">Complementarity</span>
      <span class="eval-value">${evaluation.complementarity_score?.toFixed(2)}</span>
    </div>
    <div class="eval-item">
      <span class="eval-label">Diversity Index</span>
      <span class="eval-value">${evaluation.diversity_index?.toFixed(2)}</span>
    </div>
  `;

    const grid = document.getElementById("groupsGrid");
    grid.innerHTML = "";
    const sortedIds = Object.keys(groups).map(Number).sort((a, b) => a - b);

    sortedIds.forEach((gid, idx) => {
        const members = groups[gid];
        const col = GROUP_COLORS[idx % GROUP_COLORS.length];
        const card = document.createElement("div");
        card.className = "group-card";
        card.style.animationDelay = `${idx * 0.05}s`;

        const memberHTML = members.map((m, mi) => {
            const avColor = AVATAR_COLORS[(idx + mi) % AVATAR_COLORS.length];
            const stTags = (m.strengths || []).slice(0, 2)
                .map(t => `<span class="tag tag-strength">${t}</span>`).join("");
            const wkTags = (m.weaknesses || []).slice(0, 2)
                .map(t => `<span class="tag tag-weakness">${t}</span>`).join("");
            return `
        <div class="group-member clickable" data-id="${m.id}">
          <div class="member-avatar" style="background:${avColor}">${initials(m.name)}</div>
          <div class="member-info">
            <div class="member-name">${m.name}</div>
            <div class="member-tags">${stTags}${wkTags}</div>
          </div>
          <span class="badge ${m.average_score >= 70 ? 'badge-high' : m.average_score >= 50 ? 'badge-mid' : 'badge-low'}">
            ${m.average_score.toFixed(1)}
          </span>
        </div>`;
        }).join("");

        const gStats = evaluation.group_stats && evaluation.group_stats[gid];
        let subjectCoverageHTML = "";
        if (gStats && gStats.subject_coverage) {
            const bars = Object.entries(gStats.subject_coverage).map(([subj, score]) => {
                const pct = Math.round(score);
                const color = pct >= 70 ? "#10b981" : pct >= 50 ? "#f59e0b" : "#ef4444";
                const label = subj.replace("Computer Science", "Comp.Sci");
                return `
          <div class="subj-bar-row">
            <span class="subj-name">${label}</span>
            <div class="subj-bar-track">
              <div class="subj-bar-fill" style="width:${pct}%;background:${color}"></div>
            </div>
            <span class="subj-score" style="color:${color}">${pct}</span>
          </div>`;
            }).join("");
            subjectCoverageHTML = `
        <div class="subj-coverage">
          <div class="subj-coverage-title">📊 Best Expert per Subject</div>
          ${bars}
        </div>`;
        }

        card.innerHTML = `
      <div class="group-header" style="background:${col.bg};color:${col.text}">
        <span>Group ${gid}</span>
        <span class="group-size">${members.length} student${members.length !== 1 ? "s" : ""}</span>
      </div>
      <div class="group-body">${memberHTML}${subjectCoverageHTML}</div>`;
        grid.appendChild(card);
    });

    // Attach click handlers to members in cards
    document.querySelectorAll(".group-member.clickable").forEach(el => {
        el.addEventListener("click", () => {
            openStudentModal(el.dataset.id);
        });
    });

    const vizImg = document.getElementById("vizImg");
    vizImg.src = `/static/cluster_plot.png?t=${Date.now()}`;
    document.getElementById("groupsSection").classList.remove("hidden");
}

// ── Search ────────────────────────────────────────────────────────────

document.getElementById("searchBox").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll(".student-row").forEach(row => {
        const name = row.querySelector(".cell-name")?.textContent.toLowerCase() ?? "";
        row.style.display = name.includes(q) ? "" : "none";
    });
});

// ── Init ──────────────────────────────────────────────────────────────

refreshStudents();
