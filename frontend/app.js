// Change this if your backend runs on a different address
const API = "http://127.0.0.1:8000/api";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, method = "GET", body) {
  const res = await fetch(API + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

let toastTimer;
function toast(msg, isError = false) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "show" + (isError ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.className = ""), 3000);
}

async function guard(fn) {
  try { await fn(); } catch (e) { toast(e.message, true); }
}

// ------------------------------------------------------------ navigation
document.querySelectorAll(".nav").forEach((btn) =>
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    btn.classList.add("active");
    $(btn.dataset.view).classList.add("active");
    loaders[btn.dataset.view]?.();
  })
);

let departments = [], facultyList = [];

async function loadLookups() {
  [departments, facultyList] = await Promise.all([api("/departments"), api("/faculty")]);
  $("f_dept").innerHTML = departments.map((d) => `<option value="${d.id}">${esc(d.name)}</option>`).join("");
  const opts = facultyList.map((f) => `<option value="${f.id}">${esc(f.name)}</option>`).join("");
  $("c_faculty").innerHTML = `<option value="">Unassigned</option>` + opts;
  $("l_faculty").innerHTML = opts;
}

// ------------------------------------------------------------ dashboard
async function loadDashboard() {
  const d = await api("/dashboard");
  $("stats").innerHTML = [
    [d.faculty, "Faculty members", ""],
    [d.departments, "Departments", ""],
    [d.courses, "Courses", ""],
    [d.unassigned_courses, "Courses without a teacher", d.unassigned_courses ? "alert" : ""],
    [d.pending_leaves, "Leave requests to review", d.pending_leaves ? "alert" : ""],
  ].map(([n, l, c]) => `<div class="stat ${c}"><b>${n}</b><span>${l}</span></div>`).join("");

  $("loadBars").innerHTML = d.workload.map((w) => {
    const pct = Math.min(w.utilization_pct, 100);
    const cls = w.utilization_pct > 100 ? "over" : w.utilization_pct > 85 ? "high" : "";
    return `<div class="bar-row"><span>${esc(w.faculty)}</span>
      <div class="bar"><i class="${cls}" style="width:${pct}%"></i></div>
      <span>${w.assigned_hours}/${w.max_hours} h (${w.utilization_pct}%)</span></div>`;
  }).join("");
}

// ------------------------------------------------------------ faculty
async function loadFaculty() {
  await loadLookups();
  const rows = facultyList.map((f) => `<tr>
    <td>${esc(f.name)}</td><td>${esc(f.designation)}</td><td>${esc(f.department)}</td>
    <td>${esc(f.email)}</td><td>${f.assigned_hours}/${f.max_hours_per_week} h</td>
    <td><button class="small" onclick="editFaculty(${f.id})">Edit</button>
        <button class="small danger" onclick="deleteFaculty(${f.id})">Delete</button></td></tr>`).join("");
  $("facultyTable").innerHTML = `<tr><th>Name</th><th>Designation</th><th>Department</th><th>Email</th><th>Load</th><th></th></tr>` +
    (rows || `<tr><td class="empty" colspan="6">No faculty yet. Use "Add faculty" to create one.</td></tr>`);
}

$("addFacultyBtn").onclick = () => { $("facultyForm").reset(); $("f_id").value = ""; $("facultyForm").classList.remove("hidden"); };
$("cancelFaculty").onclick = () => $("facultyForm").classList.add("hidden");

window.editFaculty = (id) => {
  const f = facultyList.find((x) => x.id === id);
  $("f_id").value = f.id; $("f_name").value = f.name; $("f_email").value = f.email; $("f_phone").value = f.phone || "";
  $("f_designation").value = f.designation; $("f_dept").value = f.department_id;
  $("f_join").value = f.joining_date || ""; $("f_max").value = f.max_hours_per_week;
  $("facultyForm").classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
};

window.deleteFaculty = (id) => guard(async () => {
  if (!confirm("Delete this faculty member? Their courses become unassigned.")) return;
  await api(`/faculty/${id}`, "DELETE");
  toast("Faculty deleted");
  await loadFaculty();
});

$("facultyForm").onsubmit = (e) => { e.preventDefault(); guard(async () => {
  const body = {
    name: $("f_name").value.trim(), email: $("f_email").value.trim(), phone: $("f_phone").value || null,
    designation: $("f_designation").value, department_id: +$("f_dept").value,
    joining_date: $("f_join").value || null, max_hours_per_week: +$("f_max").value || 16,
  };
  const id = $("f_id").value;
  await api(id ? `/faculty/${id}` : "/faculty", id ? "PUT" : "POST", body);
  toast("Faculty saved");
  $("facultyForm").classList.add("hidden");
  await loadFaculty();
}); };

// ------------------------------------------------------------ courses
async function loadCourses() {
  await loadLookups();
  const courses = await api("/courses");
  const rows = courses.map((c) => `<tr>
    <td>${esc(c.code)}</td><td>${esc(c.title)}</td><td>${c.credits}</td><td>${c.hours_per_week} h</td>
    <td><select onchange="assignCourse(${c.id}, this.value)">
      <option value="">Unassigned</option>
      ${facultyList.map((f) => `<option value="${f.id}" ${f.id === c.faculty_id ? "selected" : ""}>${esc(f.name)}</option>`).join("")}
    </select></td>
    <td><button class="small danger" onclick="deleteCourse(${c.id})">Delete</button></td></tr>`).join("");
  $("courseTable").innerHTML = `<tr><th>Code</th><th>Title</th><th>Credits</th><th>Hours</th><th>Taught by</th><th></th></tr>` +
    (rows || `<tr><td class="empty" colspan="6">No courses yet. Use "Add course" to create one.</td></tr>`);
}

$("addCourseBtn").onclick = () => { $("courseForm").reset(); $("courseForm").classList.remove("hidden"); };
$("cancelCourse").onclick = () => $("courseForm").classList.add("hidden");

window.assignCourse = (id, fid) => guard(async () => {
  await api(`/courses/${id}/assign`, "PATCH", { faculty_id: fid ? +fid : null });
  toast("Course assignment updated");
});

window.deleteCourse = (id) => guard(async () => {
  if (!confirm("Delete this course?")) return;
  await api(`/courses/${id}`, "DELETE");
  toast("Course deleted");
  await loadCourses();
});

$("courseForm").onsubmit = (e) => { e.preventDefault(); guard(async () => {
  await api("/courses", "POST", {
    code: $("c_code").value.trim(), title: $("c_title").value.trim(), credits: +$("c_credits").value || 3,
    hours_per_week: +$("c_hours").value || 3, faculty_id: $("c_faculty").value ? +$("c_faculty").value : null,
  });
  toast("Course saved");
  $("courseForm").classList.add("hidden");
  await loadCourses();
}); };

// ------------------------------------------------------------ leaves
async function loadLeaves() {
  await loadLookups();
  const leaves = await api("/leaves");
  const rows = leaves.map((l) => `<tr>
    <td>${esc(l.faculty)}</td><td>${l.start_date} to ${l.end_date}</td><td>${esc(l.reason)}</td>
    <td><span class="badge ${l.status}">${l.status}</span></td>
    <td>${l.status === "Pending"
      ? `<button class="small" onclick="setLeave(${l.id}, 'Approved')">Approve</button>
         <button class="small danger" onclick="setLeave(${l.id}, 'Rejected')">Reject</button>` : ""}</td></tr>`).join("");
  $("leaveTable").innerHTML = `<tr><th>Faculty</th><th>Dates</th><th>Reason</th><th>Status</th><th></th></tr>` +
    (rows || `<tr><td class="empty" colspan="5">No leave requests yet.</td></tr>`);
}

window.setLeave = (id, status) => guard(async () => {
  await api(`/leaves/${id}/status`, "PATCH", { status });
  toast(`Leave ${status.toLowerCase()}`);
  await loadLeaves();
});

$("leaveForm").onsubmit = (e) => { e.preventDefault(); guard(async () => {
  await api("/leaves", "POST", {
    faculty_id: +$("l_faculty").value, start_date: $("l_start").value, end_date: $("l_end").value, reason: $("l_reason").value,
  });
  toast("Leave request submitted");
  $("leaveForm").reset();
  await loadLeaves();
}); };

// ------------------------------------------------------------ AI
$("singleBtn").onclick = () => guard(async () => {
  const out = $("singleOut");
  out.innerHTML = `<span class="loading">The agent is checking the database...</span>`;
  try {
    const r = await api("/ai/single", "POST", { text: $("singleQ").value });
    out.innerHTML = (r.steps || []).map((s) => `<div class="step">${esc(s)}</div>`).join("") + `<div>${esc(r.answer)}</div>`;
  } catch (e) { out.textContent = ""; throw e; }
});

$("multiBtn").onclick = () => guard(async () => {
  const out = $("multiOut");
  out.innerHTML = `<span class="loading">Three agents are working. This takes 10 to 20 seconds...</span>`;
  try {
    const r = await api("/ai/multi", "POST", { text: $("multiQ").value });
    out.innerHTML = r.agents.map((a, i) =>
      `<div class="agent ${i === r.agents.length - 1 ? "final" : ""}"><b>${esc(a.name)}</b>${esc(a.output)}</div>`).join("");
  } catch (e) { out.textContent = ""; throw e; }
});

// ------------------------------------------------------------ start
const loaders = { dashboard: loadDashboard, faculty: loadFaculty, courses: loadCourses, leaves: loadLeaves, ai: () => {} };
guard(loadDashboard);
