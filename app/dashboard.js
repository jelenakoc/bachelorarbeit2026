const MONTH_OPTIONS = [
    { value: "01", label: "Januar" },
    { value: "02", label: "Februar" },
    { value: "03", label: "M\u00e4rz" },
    { value: "04", label: "April" },
    { value: "05", label: "Mai" },
    { value: "06", label: "Juni" },
    { value: "07", label: "Juli" },
    { value: "08", label: "August" },
    { value: "09", label: "September" },
    { value: "10", label: "Oktober" },
    { value: "11", label: "November" },
    { value: "12", label: "Dezember" }
];

const DETAIL_PAGE_SIZE = 5;

let projectChart = null;
let detailActivities = [];
let detailPage = 1;
let selectedDetailProjectId = null;
let selectedDetailProjectName = "";
let editingDetailActivityId = null;
let editingProjectId = null;

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function getWeekRange(dateString) {
    const date = new Date(dateString);
    const day = date.getDay();
    const diffToMonday = day === 0 ? -6 : 1 - day;

    const monday = new Date(date);
    monday.setDate(date.getDate() + diffToMonday);

    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    return { monday, sunday };
}

function populateSelect(selectId, options) {
    const select = document.getElementById(selectId);
    select.innerHTML = "";

    options.forEach(optionData => {
        const option = document.createElement("option");
        option.value = optionData.value;
        option.textContent = optionData.label;
        select.appendChild(option);
    });
}

function populatePeriodSelectors() {
    const currentYear = new Date().getFullYear();
    const years = [];

    for (let year = currentYear - 5; year <= currentYear + 5; year++) {
        years.push({ value: String(year), label: String(year) });
    }

    populateSelect("selectedMonthNumber", MONTH_OPTIONS);
    populateSelect("selectedMonthYear", years);
    populateSelect("selectedQuarterYear", years);
    populateSelect("selectedYear", years);
}

function updatePeriodInfo() {
    const period = document.getElementById("periodSelect").value;
    const selectedDate = document.getElementById("selectedDate").value;
    const selectedMonthNumber = document.getElementById("selectedMonthNumber").value;
    const selectedMonthYear = document.getElementById("selectedMonthYear").value;
    const selectedQuarter = document.getElementById("selectedQuarter").value;
    const selectedQuarterYear = document.getElementById("selectedQuarterYear").value;
    const selectedYear = document.getElementById("selectedYear").value;
    const info = document.getElementById("periodInfo");

    if (period === "month" && selectedMonthNumber && selectedMonthYear) {
        const monthLabel = MONTH_OPTIONS.find(option => option.value === selectedMonthNumber)?.label || selectedMonthNumber;
        info.textContent = `Gew\u00e4hlter Monat: ${monthLabel} ${selectedMonthYear}`;
    } else if (period === "day" && selectedDate) {
        info.textContent = `Gew\u00e4hlter Tag: ${formatDate(selectedDate)}`;
    } else if (period === "week" && selectedDate) {
        const range = getWeekRange(selectedDate);
        info.textContent = `Gew\u00e4hlte Woche: ${range.monday.toLocaleDateString("de-AT")} bis ${range.sunday.toLocaleDateString("de-AT")}`;
    } else if (period === "quarter" && selectedQuarter && selectedQuarterYear) {
        info.textContent = `Gew\u00e4hltes Quartal: ${selectedQuarterYear} ${selectedQuarter}`;
    } else if (period === "year" && selectedYear) {
        info.textContent = `Gew\u00e4hltes Jahr: ${selectedYear}`;
    } else {
        info.textContent = "Zeitraum";
    }
}

function formatDate(dateString) {
    const d = new Date(dateString);
    return d.toLocaleDateString("de-AT");
}

function formatTime(dateString) {
    const d = new Date(dateString);
    return d.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" });
}

function toDateTimeLocalValue(dateString) {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function formatHoursAndMinutes(decimalHours) {
    const numericHours = Number(decimalHours);

    if (!Number.isFinite(numericHours)) {
        return "0 Min";
    }

    const totalMinutes = Math.round(numericHours * 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours > 0 && minutes > 0) {
        return `${hours} Std ${minutes} Min`;
    }

    if (hours > 0) {
        return `${hours} Std`;
    }

    return `${minutes} Min`;
}

function handlePeriodChange() {
    const period = document.getElementById("periodSelect").value;

    document.getElementById("dayWeekPicker").style.display = "none";
    document.getElementById("monthPicker").style.display = "none";
    document.getElementById("quarterPicker").style.display = "none";
    document.getElementById("yearPicker").style.display = "none";

    if (period === "day" || period === "week") {
        document.getElementById("dayWeekPicker").style.display = "block";
    } else if (period === "month") {
        document.getElementById("monthPicker").style.display = "block";
    } else if (period === "quarter") {
        document.getElementById("quarterPicker").style.display = "block";
    } else if (period === "year") {
        document.getElementById("yearPicker").style.display = "block";
    }
}

function getQueryParams() {
    const period = document.getElementById("periodSelect").value;
    const selectedDate = document.getElementById("selectedDate").value;
    const selectedMonthNumber = document.getElementById("selectedMonthNumber").value;
    const selectedMonthYear = document.getElementById("selectedMonthYear").value;
    const selectedQuarter = document.getElementById("selectedQuarter").value;
    const selectedQuarterYear = document.getElementById("selectedQuarterYear").value;
    const selectedYear = document.getElementById("selectedYear").value;

    const params = new URLSearchParams();
    params.append("period", period);

    if ((period === "day" || period === "week") && selectedDate) {
        params.append("selected_date", selectedDate);
    }

    if (period === "month" && selectedMonthYear && selectedMonthNumber) {
        params.append("selected_month", `${selectedMonthYear}-${selectedMonthNumber}`);
    }

    if (period === "quarter" && selectedQuarterYear && selectedQuarter) {
        params.append("selected_quarter", `${selectedQuarterYear}-${selectedQuarter}`);
    }

    if (period === "year" && selectedYear) {
        params.append("selected_year", selectedYear);
    }

    return params.toString();
}

function resetProjectDetails() {
    detailActivities = [];
    detailPage = 1;
    selectedDetailProjectId = null;
    selectedDetailProjectName = "";
    editingDetailActivityId = null;
    document.getElementById("selectedProjectInfo").textContent = "Klicke im Balkendiagramm auf ein Projekt, um Details zu sehen.";
    document.getElementById("detailPageInfo").textContent = "";
    document.getElementById("detailTable").innerHTML = "";
    document.getElementById("taskSummaryTable").innerHTML = "";
    document.getElementById("detailPagination").style.display = "none";
}

async function loadData() {
    updatePeriodInfo();
    resetProjectDetails();

    try {
        await loadTrackingStatus();
    } catch (e) {
        console.error("Fehler bei loadTrackingStatus()", e);
    }

    try {
        await loadChart();
    } catch (e) {
        console.error("Fehler bei loadChart()", e);
    }

    try {
        await loadBillingTable();
    } catch (e) {
        console.error("Fehler bei loadBillingTable()", e);
    }

    try {
        await loadTaskStats();
    } catch (e) {
        console.error("Fehler bei loadTaskStats()", e);
    }

    try {
        await loadUnassigned();
    } catch (e) {
        console.error("Fehler bei loadUnassigned()", e);
    }

    try {
        await loadRevenue();
    } catch (e) {
        console.error("Fehler bei loadRevenue()", e);
    }

    try {
        await loadReviewTable();
    } catch (e) {
        console.error("Fehler bei loadReviewTable()", e);
    }

    try {
        await loadProjects();
    } catch (e) {
        console.error("Fehler bei loadProjects()", e);
    }
}

async function loadTrackingStatus() {
    const status = document.getElementById("trackingStatus");
    const button = document.getElementById("trackingToggleButton");

    if (!status || !button) {
        return;
    }

    const res = await fetch("/tracking/status");
    const data = await res.json();
    const enabled = Boolean(data.enabled);
    const processRunning = Boolean(data.process_running);

    status.textContent = enabled && processRunning
        ? "Tracking aktiv"
        : enabled
            ? "Tracking startet..."
            : "Tracking pausiert";
    button.textContent = enabled ? "Tracking ausschalten" : "Tracking einschalten";
    button.classList.toggle("on", enabled);
    button.classList.toggle("off", !enabled);
    button.setAttribute("aria-pressed", enabled ? "true" : "false");
}

async function toggleTracking() {
    const button = document.getElementById("trackingToggleButton");
    const status = document.getElementById("trackingStatus");

    if (button) {
        button.disabled = true;
    }

    try {
        const currentlyEnabled = button?.getAttribute("aria-pressed") === "true";
        const targetEnabled = !currentlyEnabled;

        const res = await fetch("/tracking/set", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ enabled: targetEnabled })
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        await loadTrackingStatus();
    } catch (error) {
        if (status) {
            status.textContent = "Tracking-API nicht erreichbar";
        }
        console.error("Fehler beim Umschalten des Trackings", error);
    } finally {
        if (button) {
            button.disabled = false;
        }
    }
}

async function loadChart() {
    const query = getQueryParams();
    const res = await fetch(`/stats/projects?${query}`);
    const stats = await res.json();
    const mode = document.getElementById("chartMode").value;
    const labels = stats.map(p => p.project_name);
    const data = mode === "revenue" ? stats.map(p => p.revenue) : stats.map(p => p.total_hours_billable);
    const datasetLabel = mode === "revenue" ? "Umsatz" : "Zeit";
    const yAxisLabel = mode === "revenue" ? "Umsatz (\u20ac)" : "Stunden (h)";
    const colors = stats.map(p => p.color || "#999999");
    const ctx = document.getElementById("projectChart").getContext("2d");

    if (projectChart) {
        projectChart.destroy();
    }

    projectChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: datasetLabel,
                    data,
                    backgroundColor: colors,
                    barPercentage: 0.5,
                    categoryPercentage: 0.6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            devicePixelRatio: window.devicePixelRatio || 1,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const p = stats[context.dataIndex];

                            if (mode === "revenue") {
                                return [
                                    `Umsatz: ${p.revenue} \u20ac`,
                                    `Abrechenbar: ${p.total_hours_billable} h`,
                                    `Gemessen: ${p.total_hours_raw} h`
                                ];
                            }

                            return [
                                `Abrechenbar: ${p.total_hours_billable} h`,
                                `Gemessen: ${p.total_hours_raw} h`,
                                `Umsatz: ${p.revenue} \u20ac`
                            ];
                        }
                    }
                }
            },
            onClick: async (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const project = stats[index];
                    await loadProjectDetails(project.project_id, project.project_name);
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: yAxisLabel,
                        color: "#241b4b",
                        font: {
                            size: 14,
                            weight: "bold"
                        }
                    }
                }
            }
        }
    });
}

async function loadBillingTable() {
    const query = getQueryParams();
    const res = await fetch(`/stats/projects?${query}`);
    const stats = await res.json();
    const table = document.getElementById("billingTable");
    table.innerHTML = "";

    stats.forEach(p => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${p.project_name}</td>
            <td>${formatHoursAndMinutes(p.total_hours_raw)}</td>
            <td>${formatHoursAndMinutes(p.total_hours_billable)}</td>
            <td>${p.hourly_rate ?? 0}</td>
            <td>${p.revenue}</td>
        `;
        table.appendChild(row);
    });

    if (stats.length === 0) {
        const row = document.createElement("tr");
        row.innerHTML = `<td colspan="5">Keine Daten vorhanden.</td>`;
        table.appendChild(row);
    }
}

async function loadTaskStats() {
    const query = getQueryParams();
    const res = await fetch(`/stats/tasks?${query}`);
    const tasks = await res.json();
    const table = document.getElementById("taskStatsTable");
    table.innerHTML = "";

    let currentProjectName = null;

    tasks.forEach(t => {
        if (t.project_name !== currentProjectName) {
            currentProjectName = t.project_name;
            const projectRow = document.createElement("tr");
            projectRow.className = "task-project-row";
            projectRow.innerHTML = `<td colspan="6">${t.project_name}</td>`;
            table.appendChild(projectRow);
        }

        const row = document.createElement("tr");
        row.innerHTML = `
            <td></td>
            <td>${t.task_name}</td>
            <td>${formatHoursAndMinutes(t.total_hours_raw)}</td>
            <td>${formatHoursAndMinutes(t.total_hours_billable)}</td>
            <td>${t.hourly_rate}</td>
            <td>${t.revenue}</td>
        `;
        table.appendChild(row);
    });

    if (tasks.length === 0) {
        const row = document.createElement("tr");
        row.innerHTML = `<td colspan="6">Keine Aufgaben-Daten vorhanden.</td>`;
        table.appendChild(row);
    }
}

function downloadTaskStats() {
    const query = getQueryParams();
    window.location.href = `/exports/tasks?${query}`;
}

async function loadUnassigned() {
    const query = getQueryParams();
    const res = await fetch(`/stats/unassigned?${query}`);
    const data = await res.json();
    document.getElementById("unassigned").textContent = formatHoursAndMinutes(data.unassigned_hours);
}

async function loadRevenue() {
    const query = getQueryParams();
    const res = await fetch(`/stats/revenue?${query}`);
    const data = await res.json();
    document.getElementById("revenueInfo").textContent = `${data.total_revenue} \u20ac`;
}

async function loadProjects() {
    const res = await fetch("/projects");
    const projects = await res.json();
    const taskEntries = await Promise.all(
        projects.map(async project => {
            const taskRes = await fetch(`/projects/${project.id}/tasks`);
            const tasks = await taskRes.json();
            return [project.id, tasks];
        })
    );
    const tasksByProject = Object.fromEntries(taskEntries);
    const table = document.getElementById("projectTable");
    table.innerHTML = "";

    projects.forEach(p => {
        const tasks = tasksByProject[p.id] ?? [];
        const taskHtml = tasks.length
            ? `
                <div>
                    <div class="mini-label">Aufgaben</div>
                    <div class="task-chip-list">
                        ${tasks.map(task => `
                            <span class="task-chip">
                                <span>${escapeHtml(task.name)}</span>
                                <button
                                    type="button"
                                    class="secondary icon-button"
                                    onclick='deleteProjectTask(${p.id}, ${task.id}, ${JSON.stringify(encodeURIComponent(task.name))})'
                                >\u2715</button>
                            </span>
                        `).join("")}
                    </div>
                </div>
            `
            : `
                <div>
                    <div class="mini-label">Aufgaben</div>
                    <small>Noch keine Aufgaben gespeichert.</small>
                </div>
            `;

        const row = document.createElement("tr");
        if (editingProjectId === p.id) {
            row.className = "project-edit-row";
            row.innerHTML = `
                <td><input type="text" id="edit-project-name-${p.id}" value="${p.name}"></td>
                <td><input type="number" id="edit-project-rate-${p.id}" step="0.01" value="${p.hourly_rate ?? ""}" placeholder="0"></td>
                <td><input type="date" id="edit-project-active-from-${p.id}" value="${p.active_from ?? ""}"></td>
                <td><input type="date" id="edit-project-active-to-${p.id}" value="${p.active_to ?? ""}"></td>
                <td>
                    <select id="edit-project-active-${p.id}">
                        <option value="true" ${p.is_active ? "selected" : ""}>Ja</option>
                        <option value="false" ${!p.is_active ? "selected" : ""}>Nein</option>
                    </select>
                </td>
                <td><input type="text" id="edit-project-keywords-${p.id}" value="${p.keywords.join(", ")}"></td>
                <td><input type="color" id="edit-project-color-${p.id}" value="${p.color ?? "#cccccc"}"></td>
                <td>
                    <div class="action-buttons">
                        <button class="secondary icon-button" type="button" onclick="saveProjectEdit(${p.id})">\u2713</button>
                        <button class="secondary icon-button" type="button" onclick="cancelProjectEdit()">\u2715</button>
                    </div>
                    <div id="project-edit-error-${p.id}" class="error"></div>
                </td>
            `;
        } else {
            row.innerHTML = `
                <td>${p.name}</td>
                <td>${p.hourly_rate ?? "\u2014"} \u20ac</td>
                <td>${p.active_from ?? "\u2014"}</td>
                <td>${p.active_to ?? "\u2014"}</td>
                <td>${p.is_active ? "Ja" : "Nein"}</td>
                <td>
                    <div class="project-meta">
                        <div>
                            <div class="mini-label">Keywords</div>
                            <div>${p.keywords.length ? escapeHtml(p.keywords.join(", ")) : "\u2014"}</div>
                        </div>
                        ${taskHtml}
                    </div>
                </td>
                <td>
                    <span style="display:inline-block; width:18px; height:18px; background:${p.color ?? "#cccccc"}; border-radius:4px;"></span>
                </td>
                <td>
                    <div class="action-buttons">
                        <button type="button" onclick="startProjectEdit(${p.id})">Bearbeiten</button>
                        ${p.is_active ? `<button type="button" onclick="deactivateProject(${p.id})">Beenden</button>` : ""}
                    </div>
                </td>
            `;
        }
        table.appendChild(row);
    });
}

async function deleteProjectTask(projectId, taskId, encodedTaskName) {
    const taskName = decodeURIComponent(encodedTaskName);
    const confirmed = confirm(`Aufgabe "${taskName}" aus der Auswahl entfernen?`);
    if (!confirmed) return;

    const res = await fetch(`/projects/${projectId}/tasks/${taskId}`, {
        method: "DELETE"
    });

    if (res.ok) {
        await loadProjects();
    } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Fehler beim Löschen der Aufgabe.");
    }
}

function startProjectEdit(projectId) {
    editingProjectId = projectId;
    loadProjects();
}

function cancelProjectEdit() {
    editingProjectId = null;
    loadProjects();
}

async function saveProjectEdit(projectId) {
    const name = document.getElementById(`edit-project-name-${projectId}`).value.trim();
    const hourlyRateValue = document.getElementById(`edit-project-rate-${projectId}`).value.trim();
    const activeFrom = document.getElementById(`edit-project-active-from-${projectId}`).value || null;
    const activeTo = document.getElementById(`edit-project-active-to-${projectId}`).value || null;
    const isActive = document.getElementById(`edit-project-active-${projectId}`).value === "true";
    const keywordsValue = document.getElementById(`edit-project-keywords-${projectId}`).value.trim();
    const color = document.getElementById(`edit-project-color-${projectId}`).value || null;
    const errorDiv = document.getElementById(`project-edit-error-${projectId}`);

    errorDiv.textContent = "";

    if (!name) {
        errorDiv.textContent = "Bitte einen Projektnamen eingeben.";
        return;
    }

    const payload = {
        name,
        color,
        hourly_rate: hourlyRateValue ? Number(hourlyRateValue) : null,
        active_from: activeFrom,
        active_to: activeTo,
        is_active: isActive,
        keywords: keywordsValue
            ? keywordsValue.split(",").map(keyword => keyword.trim()).filter(keyword => keyword.length > 0)
            : []
    };

    const res = await fetch(`/projects/${projectId}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (res.ok) {
        editingProjectId = null;
        await loadData();
    } else {
        errorDiv.textContent = data.detail || "Fehler beim Speichern.";
    }
}

async function deactivateProject(projectId) {
    const confirmed = confirm("Willst du dieses Projekt wirklich beenden?");
    if (!confirmed) return;

    const res = await fetch(`/projects/${projectId}/deactivate`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        }
    });

    const data = await res.json();

    if (res.ok) {
        await loadData();
    } else {
        alert(data.detail || "Fehler beim Beenden des Projekts.");
    }
}

function renderProjectDetails() {
    const table = document.getElementById("detailTable");
    const pagination = document.getElementById("detailPagination");
    const pageInfo = document.getElementById("detailPageInfo");
    const paginationText = document.getElementById("detailPaginationText");
    const prevButton = document.getElementById("detailPrevButton");
    const nextButton = document.getElementById("detailNextButton");

    table.innerHTML = "";

    if (detailActivities.length === 0) {
        pageInfo.textContent = "";
        pagination.style.display = "none";
        const row = document.createElement("tr");
        row.innerHTML = `<td colspan="9">Keine Eintr\u00e4ge f\u00fcr dieses Projekt im gew\u00e4hlten Zeitraum.</td>`;
        table.appendChild(row);
        return;
    }

    const totalPages = Math.ceil(detailActivities.length / DETAIL_PAGE_SIZE);
    const startIndex = (detailPage - 1) * DETAIL_PAGE_SIZE;
    const pageItems = detailActivities.slice(startIndex, startIndex + DETAIL_PAGE_SIZE);

    pageInfo.textContent = `${detailActivities.length} Eintr\u00e4ge f\u00fcr ${selectedDetailProjectName}`;
    paginationText.textContent = `Seite ${detailPage} von ${totalPages}`;
    prevButton.disabled = detailPage === 1;
    nextButton.disabled = detailPage === totalPages;
    pagination.style.display = totalPages > 1 ? "flex" : "none";

    pageItems.forEach(a => {
        const row = document.createElement("tr");
        if (editingDetailActivityId === a.id) {
            row.innerHTML = `
                <td>${formatDate(a.start_time)}</td>
                <td><input type="datetime-local" id="detail-start-${a.id}" value="${toDateTimeLocalValue(a.start_time)}"></td>
                <td><input type="datetime-local" id="detail-end-${a.id}" value="${toDateTimeLocalValue(a.end_time)}"></td>
                <td>${(a.duration_seconds / 60).toFixed(1)}</td>
                <td>${escapeHtml(a.app_name ?? "\u2014")}</td>
                <td>${escapeHtml(a.window_title ?? "\u2014")}</td>
                <td><input type="text" id="detail-task-${a.id}" value="${escapeHtml(a.task_text ?? "")}" placeholder="Aufgabe"></td>
                <td><input type="text" id="detail-comment-${a.id}" value="${escapeHtml(a.comment_text ?? "")}" placeholder="Kommentar"></td>
                <td>
                    <div class="action-buttons">
                        <button type="button" class="secondary icon-button" onclick="saveDetailActivityEdit(${a.id})">\u2713</button>
                        <button type="button" class="secondary icon-button" onclick="cancelDetailActivityEdit()">\u2715</button>
                    </div>
                </td>
            `;
        } else {
            row.innerHTML = `
                <td>${formatDate(a.start_time)}</td>
                <td>${formatTime(a.start_time)}</td>
                <td>${formatTime(a.end_time)}</td>
                <td>${(a.duration_seconds / 60).toFixed(1)}</td>
                <td>${escapeHtml(a.app_name ?? "\u2014")}</td>
                <td>${escapeHtml(a.window_title ?? "\u2014")}</td>
                <td>${escapeHtml(a.task_text ?? "\u2014")}</td>
                <td>${escapeHtml(a.comment_text ?? "\u2014")}</td>
                <td>
                    <div class="action-buttons">
                        <button type="button" class="secondary" onclick="startDetailActivityEdit(${a.id})">Bearbeiten</button>
                        <button
                            type="button"
                            class="secondary"
                            id="detail-delete-btn-${a.id}"
                            onclick="showDetailDeleteConfirm(${a.id})"
                        >L\u00f6schen</button>
                        <span id="detail-delete-confirm-${a.id}" style="display:none;">
                            <button type="button" class="secondary icon-button" onclick="confirmDetailDeleteActivity(${a.id})">\u2713</button>
                            <button type="button" class="secondary icon-button" onclick="hideDetailDeleteConfirm(${a.id})">\u2715</button>
                        </span>
                    </div>
                </td>
            `;
        }
        table.appendChild(row);
    });
}

function renderTaskSummary() {
    const summaryTable = document.getElementById("taskSummaryTable");
    summaryTable.innerHTML = "";

    if (detailActivities.length === 0) {
        const row = document.createElement("tr");
        row.innerHTML = `<td colspan="4">Keine Aufgaben-Zusammenfassung verf\u00fcgbar.</td>`;
        summaryTable.appendChild(row);
        return;
    }

    const activitiesAsc = [...detailActivities].sort(
        (a, b) => new Date(a.start_time) - new Date(b.start_time)
    );

    const summaryRows = [];
    let currentBlock = null;

    activitiesAsc.forEach(activity => {
        const taskName = (activity.task_text || "").trim() || "(ohne Aufgabe)";
        const start = new Date(activity.start_time);
        const end = new Date(activity.end_time);

        if (!currentBlock) {
            currentBlock = {
                taskName,
                start,
                end,
                totalSeconds: activity.duration_seconds
            };
            return;
        }

        const sameTask = currentBlock.taskName === taskName;
        const sameDay = currentBlock.end.toDateString() === start.toDateString();
        const continuesDirectly = start.getTime() <= currentBlock.end.getTime() + 60000;

        if (sameTask && sameDay && continuesDirectly) {
            if (end > currentBlock.end) {
                currentBlock.end = end;
            }
            currentBlock.totalSeconds += activity.duration_seconds;
            return;
        }

        summaryRows.push(currentBlock);
        currentBlock = {
            taskName,
            start,
            end,
            totalSeconds: activity.duration_seconds
        };
    });

    if (currentBlock) {
        summaryRows.push(currentBlock);
    }

    summaryRows.forEach(item => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${item.taskName}</td>
            <td>${item.start.toLocaleDateString("de-AT")} ${item.start.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" })}</td>
            <td>${item.end.toLocaleDateString("de-AT")} ${item.end.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" })}</td>
            <td>${formatHoursAndMinutes(item.totalSeconds / 3600)}</td>
        `;
        summaryTable.appendChild(row);
    });
}

async function loadProjectDetails(projectId, projectName) {
    const query = getQueryParams();
    const res = await fetch(`/activities/by-project/${projectId}?${query}`);
    detailActivities = await res.json();
    detailPage = 1;
    selectedDetailProjectId = projectId;
    selectedDetailProjectName = projectName;
    document.getElementById("selectedProjectInfo").textContent = `Details f\u00fcr: ${projectName}`;
    renderProjectDetails();
    renderTaskSummary();
}

function changeDetailPage(direction) {
    const totalPages = Math.ceil(detailActivities.length / DETAIL_PAGE_SIZE);
    detailPage = Math.min(Math.max(1, detailPage + direction), totalPages);
    editingDetailActivityId = null;
    renderProjectDetails();
}

function startDetailActivityEdit(activityId) {
    editingDetailActivityId = activityId;
    renderProjectDetails();
}

function cancelDetailActivityEdit() {
    editingDetailActivityId = null;
    renderProjectDetails();
}

async function saveDetailActivityEdit(activityId) {
    const activity = detailActivities.find(item => item.id === activityId);
    const startValue = document.getElementById(`detail-start-${activityId}`)?.value;
    const endValue = document.getElementById(`detail-end-${activityId}`)?.value;
    const taskValue = document.getElementById(`detail-task-${activityId}`)?.value.trim() ?? "";
    const commentValue = document.getElementById(`detail-comment-${activityId}`)?.value.trim() ?? "";

    if (!activity || !startValue || !endValue) {
        alert("Bitte Start und Ende angeben.");
        return;
    }

    if (new Date(endValue) <= new Date(startValue)) {
        alert("Endzeit muss nach der Startzeit liegen.");
        return;
    }

    const payload = {
        project_id: activity.project_id,
        task_text: taskValue,
        comment_text: commentValue,
        needs_review: false,
        start_time: startValue,
        end_time: endValue
    };

    const res = await fetch(`/activities/${activityId}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
        alert(data.detail || "Fehler beim Speichern.");
        return;
    }

    editingDetailActivityId = null;
    await loadChart();
    await loadBillingTable();
    await loadTaskStats();
    await loadUnassigned();
    await loadRevenue();
    await loadReviewTable();

    if (selectedDetailProjectId !== null) {
        await loadProjectDetails(selectedDetailProjectId, selectedDetailProjectName);
    }
}

function showDetailDeleteConfirm(activityId) {
    document.getElementById(`detail-delete-btn-${activityId}`).style.display = "none";
    document.getElementById(`detail-delete-confirm-${activityId}`).style.display = "inline";
}

function hideDetailDeleteConfirm(activityId) {
    document.getElementById(`detail-delete-btn-${activityId}`).style.display = "inline";
    document.getElementById(`detail-delete-confirm-${activityId}`).style.display = "none";
}

async function confirmDetailDeleteActivity(activityId) {
    const res = await fetch(`/activities/${activityId}`, {
        method: "DELETE"
    });

    if (!res.ok) {
        alert("Fehler beim L\u00f6schen.");
        return;
    }

    await loadChart();
    await loadBillingTable();
    await loadTaskStats();
    await loadUnassigned();
    await loadRevenue();
    await loadReviewTable();

    if (selectedDetailProjectId !== null) {
        await loadProjectDetails(selectedDetailProjectId, selectedDetailProjectName);
    } else {
        resetProjectDetails();
    }
}

async function loadReviewTable() {
    const activitiesRes = await fetch("/activities");
    const activities = await activitiesRes.json();

    const projectsRes = await fetch("/projects");
    const projects = await projectsRes.json();

    const table = document.getElementById("reviewTable");
    table.innerHTML = "";

    const reviewActivities = activities.filter(a => a.needs_review);

    for (const a of reviewActivities) {
        const row = document.createElement("tr");

        const projectOptions = projects.map(p => {
            const selected = a.project_id === p.id ? "selected" : "";
            return `<option value="${p.id}" ${selected}>${p.name}</option>`;
        }).join("");

        row.innerHTML = `
            <td>${formatDate(a.start_time)}</td>
            <td>${a.app_name ?? "\u2014"}</td>
            <td>${a.window_title ?? "\u2014"}</td>
            <td>${(a.duration_seconds / 60).toFixed(1)}</td>
            <td>
                <select id="project-${a.id}" onchange="resetReviewTaskInputs(${a.id}); loadTasksForReviewRow(${a.id}); clearReviewError(${a.id})">
                    <option value="">Bitte w\u00e4hlen</option>
                    ${projectOptions}
                </select>
            </td>
            <td>
                <select id="task-select-${a.id}" onchange="syncReviewTaskInputs(${a.id}, 'select'); clearReviewError(${a.id})">
                    <option value="">Bitte w\u00e4hlen</option>
                </select>
            </td>
            <td>
                <input type="text" id="task-new-${a.id}" value="${a.task_text ?? ""}" placeholder="Neue Aufgabe / Ticket" oninput="syncReviewTaskInputs(${a.id}, 'input'); clearReviewError(${a.id})">
            </td>
            <td>
                <input type="text" id="comment-${a.id}" value="${a.comment_text ?? ""}" placeholder="Kommentar / Details" oninput="clearReviewError(${a.id})">
            </td>
            <td>
                <button onclick="saveReviewActivity(${a.id})">Speichern</button>
                <button id="delete-btn-${a.id}" onclick="showDeleteConfirm(${a.id})">L\u00f6schen</button>
                <span id="delete-confirm-${a.id}" style="display:none;">
                    <button onclick="confirmDeleteActivity(${a.id})">\u2713</button>
                    <button onclick="hideDeleteConfirm(${a.id})">\u2715</button>
                </span>
                <div id="error-${a.id}" style="color:red; font-size:12px; margin-top:6px;"></div>
            </td>
        `;

        table.appendChild(row);
        syncReviewTaskInputs(a.id);

        if (a.project_id) {
            await loadTasksForReviewRow(a.id, a.task_text ?? "");
        }
    }

    if (reviewActivities.length === 0) {
        const row = document.createElement("tr");
        row.innerHTML = `<td colspan="9">Keine offenen Zeitbl\u00f6cke.</td>`;
        table.appendChild(row);
    }
}

async function loadTasksForReviewRow(activityId, selectedTask = "") {
    const projectValue = document.getElementById(`project-${activityId}`).value;
    const taskSelect = document.getElementById(`task-select-${activityId}`);

    taskSelect.innerHTML = `<option value="">Bitte w\u00e4hlen</option>`;

    if (!projectValue) {
        syncReviewTaskInputs(activityId);
        return;
    }

    const res = await fetch(`/projects/${projectValue}/tasks`);
    const tasks = await res.json();

    tasks.forEach(task => {
        const option = document.createElement("option");
        option.value = task.name;
        option.textContent = task.name;

        if (task.name === selectedTask) {
            option.selected = true;
        }

        taskSelect.appendChild(option);
    });

    syncReviewTaskInputs(activityId);
}

function resetReviewTaskInputs(activityId) {
    const taskSelect = document.getElementById(`task-select-${activityId}`);
    const newTaskInput = document.getElementById(`task-new-${activityId}`);

    if (!taskSelect || !newTaskInput) {
        return;
    }

    taskSelect.value = "";
    taskSelect.disabled = false;
    newTaskInput.value = "";
    newTaskInput.disabled = false;
    newTaskInput.placeholder = "Neue Aufgabe / Ticket";
}

function syncReviewTaskInputs(activityId, source = "") {
    const taskSelect = document.getElementById(`task-select-${activityId}`);
    const newTaskInput = document.getElementById(`task-new-${activityId}`);

    if (!taskSelect || !newTaskInput) {
        return;
    }

    const hasSelectedTask = Boolean(taskSelect.value);
    const hasNewTask = Boolean(newTaskInput.value.trim());

    if (source === "select" && hasSelectedTask) {
        newTaskInput.value = "";
    }

    if (source === "input" && hasNewTask) {
        taskSelect.value = "";
    }

    const shouldLockInput = Boolean(taskSelect.value);
    const shouldLockSelect = Boolean(newTaskInput.value.trim());

    newTaskInput.disabled = shouldLockInput;
    taskSelect.disabled = shouldLockSelect;
    newTaskInput.placeholder = shouldLockInput ? "Vorhandene Aufgabe gew\u00e4hlt" : "Neue Aufgabe / Ticket";
}

async function saveReviewActivity(activityId) {
    const projectValue = document.getElementById(`project-${activityId}`).value;
    const selectedTaskValue = document.getElementById(`task-select-${activityId}`).value;
    const newTaskValue = document.getElementById(`task-new-${activityId}`).value.trim();
    const commentValue = document.getElementById(`comment-${activityId}`).value.trim();
    const errorDiv = document.getElementById(`error-${activityId}`);

    errorDiv.textContent = "";

    if (!projectValue) {
        errorDiv.textContent = "Bitte zuerst ein Projekt ausw\u00e4hlen.";
        return;
    }

    if (selectedTaskValue && newTaskValue) {
        errorDiv.textContent = "Bitte entweder eine vorhandene Aufgabe w\u00e4hlen oder eine neue eingeben.";
        return;
    }

    const finalTask = newTaskValue || selectedTaskValue || "";

    if (!finalTask && !commentValue) {
        errorDiv.textContent = "Bitte Aufgabe oder Kommentar angeben.";
        return;
    }

    const payload = {
        project_id: Number(projectValue),
        task_text: finalTask,
        comment_text: commentValue,
        needs_review: false
    };

    const res = await fetch(`/activities/${activityId}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (res.ok) {
        await loadData();
    } else {
        errorDiv.textContent = data.detail || "Fehler beim Speichern.";
    }
}

function clearReviewError(activityId) {
    const errorDiv = document.getElementById(`error-${activityId}`);
    if (errorDiv) {
        errorDiv.textContent = "";
    }
}

function showDeleteConfirm(activityId) {
    document.getElementById(`delete-btn-${activityId}`).style.display = "none";
    document.getElementById(`delete-confirm-${activityId}`).style.display = "inline";
}

function hideDeleteConfirm(activityId) {
    document.getElementById(`delete-btn-${activityId}`).style.display = "inline";
    document.getElementById(`delete-confirm-${activityId}`).style.display = "none";
}

async function confirmDeleteActivity(activityId) {
    const res = await fetch(`/activities/${activityId}`, {
        method: "DELETE"
    });

    if (res.ok) {
        await loadData();
    } else {
        alert("Fehler beim L\u00f6schen.");
    }
}

async function createProject() {
    const name = document.getElementById("projectName").value.trim();
    const activeFrom = document.getElementById("activeFrom").value || null;
    const activeTo = document.getElementById("activeTo").value || null;
    const keywordText = document.getElementById("projectKeywords").value.trim();
    const color = document.getElementById("projectColor").value || null;
    const hourlyRateValue = document.getElementById("projectRate").value;
    const hourlyRate = hourlyRateValue ? Number(hourlyRateValue) : null;

    const keywords = keywordText
        ? keywordText.split(",").map(k => k.trim()).filter(k => k.length > 0)
        : [];

    const message = document.getElementById("projectMessage");
    message.className = "";
    message.textContent = "";

    if (!name) {
        message.className = "error";
        message.textContent = "Bitte einen Projektnamen eingeben.";
        return;
    }

    const payload = {
        name,
        color,
        hourly_rate: hourlyRate,
        active_from: activeFrom,
        active_to: activeTo,
        keywords
    };

    const res = await fetch("/projects", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (res.ok) {
        message.className = "success";
        message.textContent = "Projekt erfolgreich gespeichert.";

        document.getElementById("projectName").value = "";
        document.getElementById("activeFrom").value = "";
        document.getElementById("activeTo").value = "";
        document.getElementById("projectKeywords").value = "";
        document.getElementById("projectRate").value = "";

        await loadData();
    } else {
        message.className = "error";
        message.textContent = data.detail || "Fehler beim Speichern.";
    }
}

function setDefaultDates() {
    const today = new Date();
    const yyyy = String(today.getFullYear());
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    const quarter = `Q${Math.floor(today.getMonth() / 3) + 1}`;

    document.getElementById("selectedDate").value = `${yyyy}-${mm}-${dd}`;
    document.getElementById("selectedMonthNumber").value = mm;
    document.getElementById("selectedMonthYear").value = yyyy;
    document.getElementById("selectedQuarter").value = quarter;
    document.getElementById("selectedQuarterYear").value = yyyy;
    document.getElementById("selectedYear").value = yyyy;
}

function toggleAdvanced() {
    const div = document.getElementById("advancedOptions");
    div.style.display = div.style.display === "none" ? "block" : "none";
}

populatePeriodSelectors();
setDefaultDates();
handlePeriodChange();
loadData();
