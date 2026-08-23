// 1. General UI & Modal Logic
document.addEventListener("click", (event) => {
    // Open Modals
    const opener = event.target.closest("[data-modal-target]");
    if (opener) {
        document.getElementById(opener.dataset.modalTarget)?.classList.add("open");
        return;
    }
    // Close Modals
    if (event.target.closest("[data-modal-close]") || event.target.classList.contains("modal")) {
        const modalToClose = event.target.closest(".modal") || event.target;
        modalToClose.classList.remove("open");
        return;
    }
    // Actions Dropdown Toggle
    const actionBtn = event.target.closest(".bulk-action-btn");
    if (actionBtn) {
        const menu = actionBtn.nextElementSibling;
        if (menu && menu.classList.contains("dropdown-menu")) {
            menu.classList.toggle("hidden");
        }
        return;
    }
    // Close dropdowns if clicking outside
    if (!event.target.closest(".bulk-action-dropdown")) {
        document.querySelectorAll(".dropdown-menu").forEach(menu => menu.classList.add("hidden"));
    }
    // Segmented / Toggle Buttons Logic
    if (event.target.closest('.segmented-btn')) {
        const btn = event.target.closest('.segmented-btn');
        btn.closest('.segmented-control').querySelectorAll('.segmented-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }
    if (event.target.closest('.toggle-btn')) {
        const btn = event.target.closest('.toggle-btn');
        btn.closest('.toggle-group').querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }
});

// 2. Generic Checkbox & Button Enabling Logic (Works for ALL pages)
function updateBulkToolbar(table) {
    const total = table.querySelectorAll(".bulk-select-row").length;
    const selected = table.querySelectorAll(".bulk-select-row:checked").length;
    const selectAll = table.querySelector(".bulk-select-all");
    
    if (selectAll) {
        selectAll.checked = total > 0 && selected === total;
        selectAll.indeterminate = selected > 0 && selected < total;
    }

    // Find the toolbar (Users page uses data-bulk-toolbar, Matters uses the generic wrapper)
    const toolbarSelector = table.dataset.bulkToolbar;
    const toolbar = toolbarSelector ? document.querySelector(toolbarSelector) : table.closest('.panel')?.previousElementSibling;
    
    if (toolbar) {
        const actionButton = toolbar.querySelector(".bulk-action-btn");
        if (actionButton) {
            actionButton.disabled = selected === 0; // Enables the button when > 0
        }
        if (selected === 0) {
            toolbar.querySelector(".dropdown-menu")?.classList.add("hidden");
        }
    }
}

document.addEventListener("change", (event) => {
    if (!event.target.matches(".bulk-select-all, .bulk-select-row")) return;
    
    const table = event.target.closest("table");
    if (!table) return;
    
    // Check/Uncheck all rows
    if (event.target.classList.contains("bulk-select-all")) {
        table.querySelectorAll(".bulk-select-row").forEach(cb => {
            cb.checked = event.target.checked;
        });
    }
    
    // Update the button state
    updateBulkToolbar(table);
});


// 3. AJAX Refresh Logic with Spinning Animation (Matters Page)
document.addEventListener("click", (event) => {
    const refreshBtn = event.target.closest("#ajaxRefreshBtn");
    if (!refreshBtn) return;
    
    const icon = refreshBtn.querySelector(".refresh-icon");
    if (icon) icon.classList.add("spin-icon");
    
    const container = document.getElementById("table-container");
    if (container) container.style.opacity = "0.5";

    fetch(window.location.href)
        .then(res => res.text())
        .then(html => {
            const doc = new DOMParser().parseFromString(html, "text/html");
            const newTable = doc.getElementById("table-container");
            if (newTable && container) {
                container.innerHTML = newTable.innerHTML;
            }
        })
        .finally(() => {
            if (container) container.style.opacity = "1";
            if (icon) icon.classList.remove("spin-icon");
        });
});

// 4. AJAX Bulk Action Trigger (Matters Page)
let pendingBulkAction = null;

document.addEventListener("click", (event) => {
    const actionLink = event.target.closest("[data-bulk-action]");
    if (!actionLink) return;
    event.preventDefault();
    
    const action = actionLink.dataset.bulkAction;
    const container = document.getElementById("table-container");
    const selectedIds = Array.from(container.querySelectorAll(".bulk-select-row:checked")).map(cb => cb.value);
    
    if (selectedIds.length === 0) {
        alert("Please select at least one record to perform this action.");
        return;
    }
    
    pendingBulkAction = { action, selectedIds };
    document.getElementById("bulk-confirm-modal").classList.add("open");
    actionLink.closest(".dropdown-menu")?.classList.add("hidden"); 
});

// 5. AJAX Confirm Execution inside the Modal (Matters Page)
document.addEventListener("click", (event) => {
    if (event.target.id !== "confirm-bulk-btn") return;
    if (!pendingBulkAction || pendingBulkAction.action !== "delete") return;
    
    const csrfToken = document.getElementById("csrf-token")?.value;
    const deleteUrl = document.getElementById("table-container")?.dataset.deleteUrl;
    const confirmBtn = event.target;
    
    confirmBtn.disabled = true; 
    
    fetch(deleteUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ matter_ids: pendingBulkAction.selectedIds })
    })
    .then(async res => {
        if (!res.ok) {
            if (res.status === 400 || res.status === 401) {
                throw new Error("Security session expired. Please refresh the page and log back in.");
            }
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || "An unknown server error occurred.");
        }
        return res.json();
    })
    .then(data => {
        if (data.success) {
            document.getElementById("bulk-confirm-modal").classList.remove("open");
            document.getElementById("ajaxRefreshBtn")?.click(); 
        } else {
            alert("Error: " + data.error);
        }
    })
    .catch(err => alert(err.message))
    .finally(() => {
        confirmBtn.disabled = false;
        pendingBulkAction = null;
    });
});

// 6. LEGACY Form-based Bulk Delete (Users Page)
document.addEventListener("click", (event) => {
    // Looks specifically for the old data-bulk-delete-url attribute
    const deleteItem = event.target.closest("[data-bulk-delete-url]");
    if (!deleteItem) return;
    event.preventDefault();

    const toolbar = deleteItem.closest(".bulk-action-dropdown");
    const table = toolbar?.id 
        ? document.querySelector(`table[data-bulk-toolbar="#${toolbar.id}"]`) 
        : document.querySelector("table");
        
    const selectedIds = table ? Array.from(table.querySelectorAll(".bulk-select-row:checked")).map(cb => cb.value) : [];
    
    if (!selectedIds.length) return;

    if (!window.confirm(`Are you sure you want to delete ${selectedIds.length} selected record(s)? This action cannot be undone.`)) {
        return;
    }

    const csrfToken = document.getElementById("csrf-token")?.value;
    if (!csrfToken) {
        window.alert("Unable to verify this request. Please refresh the page and try again.");
        return;
    }

    // Build the invisible form and submit it to the old python route
    const form = document.createElement("form");
    form.method = "POST";
    form.action = deleteItem.dataset.bulkDeleteUrl;
    
    const addField = (name, value) => {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = name;
        input.value = value;
        form.append(input);
    };
    
    addField("csrf_token", csrfToken);
    selectedIds.forEach((id) => addField("user_ids", id));
    
    document.body.append(form);
    form.submit();
});

// 7. Tab Switching Logic (Details Page)
document.addEventListener("click", function(e) {
    const tab = e.target.closest('.nav-tabs a');
    if (!tab) return;
    
    e.preventDefault();
    const tabContainer = tab.closest('.tab-navigation').nextElementSibling; 
    
    tab.closest('.nav-tabs').querySelectorAll('a').forEach(t => t.classList.remove('active'));
    tabContainer.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');
    
    tab.classList.add('active');
    const targetId = tab.getAttribute('href');
    const targetPane = document.querySelector(targetId);
    if (targetPane) {
        targetPane.style.display = 'block';
    }
});

// 8. Edit Details Form Logic (Details Page)
window.enableEdit = function() {
    document.querySelectorAll('.view-mode').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.edit-mode').forEach(el => el.style.display = 'inline-block');
    document.getElementById('editBtn').style.display = 'none';
    document.getElementById('cancelBtn').style.display = 'inline-block';
    document.getElementById('updateBtn').style.display = 'inline-block';
};

window.cancelEdit = function() {
    document.querySelectorAll('.view-mode').forEach(el => el.style.display = '');
    document.querySelectorAll('.edit-mode').forEach(el => el.style.display = 'none');
    document.getElementById('editBtn').style.display = 'inline-block';
    document.getElementById('cancelBtn').style.display = 'none';
    document.getElementById('updateBtn').style.display = 'none';
};

// 9. More Actions Dropdown (Details Page)
document.addEventListener("click", function(e) {
    const toggle = e.target.closest("#more-actions-toggle");
    const menu = document.getElementById("more-actions-menu");
    
    if (toggle && menu) {
        e.stopPropagation();
        menu.classList.toggle("show");
        return;
    }
    
    if (menu && !e.target.closest("#more-actions-btn")) {
        menu.classList.remove("show");
    }
});

// --- 10. Generic Dynamic Column Filtering ---
document.addEventListener("DOMContentLoaded", () => {
    // 1. Create and inject the popup modal dynamically so it works anywhere
    const columnFilterPopup = document.createElement("div");
    columnFilterPopup.id = "column-filter-popup";
    columnFilterPopup.style.cssText = "display: none; position: absolute; background: white; border: 1px solid #ccc; box-shadow: 0 4px 16px rgba(0,0,0,0.2); padding: 14px; border-radius: 8px; z-index: 9999; width: 240px;";
    columnFilterPopup.innerHTML = `
        <div style="font-size: 13px; font-weight: 700; margin-bottom: 10px; color: #333;" id="filter-popup-title">Filter</div>
        <input type="text" id="filter-popup-input" placeholder="Type to filter..." style="width: 100%; margin-bottom: 12px; padding: 8px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; outline: none;">
        <div style="display: flex; justify-content: space-between;">
            <button type="button" class="btn btn-light" style="padding: 6px 12px; font-size: 12px;" onclick="clearColumnFilter()">Clear</button>
            <button type="button" class="btn btn-primary" style="padding: 6px 12px; font-size: 12px;" onclick="applyColumnFilter()">OK</button>
        </div>
    `;
    document.body.appendChild(columnFilterPopup);

    let activeTableFilters = {}; 
    let currentFilterColIndex = -1;
    let currentFilterTable = null;

    // Grab the new Master Clear button
    const clearAllBtn = document.getElementById("clear-all-filters-btn");
    
    // Listen for Master Clear button clicks
    if (clearAllBtn) {
        clearAllBtn.addEventListener("click", () => {
            activeTableFilters = {}; // Wipe out all stored filters
            renderTableFilters();    // Re-render the table visually
        });
    }

    // Submit filter smoothly when user presses 'Enter'
    document.getElementById("filter-popup-input").addEventListener("keypress", function(e) {
        if (e.key === "Enter") applyColumnFilter();
    });

    // 2. Listen for clicks on ANY filter line in any table
    document.addEventListener("click", (e) => {
        const filterLine = e.target.closest(".table-filter-line");
        if (filterLine) {
            e.preventDefault();
            e.stopPropagation();
            
            const th = filterLine.closest("th");
            currentFilterColIndex = Array.from(th.parentNode.children).indexOf(th);
            currentFilterTable = th.closest("table");
            
            // Dynamically grab the column name from the row directly above it
            const colName = currentFilterTable.rows[0].cells[currentFilterColIndex].textContent.trim();
            document.getElementById("filter-popup-title").textContent = colName ? `${colName} Filter` : "Column Filter";
            
            // Populate the input if a filter is already active for this column
            const input = document.getElementById("filter-popup-input");
            input.value = activeTableFilters[currentFilterColIndex] || "";
            
            // Position the popup exactly under the clicked filter line
            const rect = filterLine.getBoundingClientRect();
            columnFilterPopup.style.top = `${rect.bottom + window.scrollY + 8}px`;
            columnFilterPopup.style.left = `${rect.left + window.scrollX}px`;
            columnFilterPopup.style.display = "block";
            
            input.focus();
            return;
        }
        
        // Close popup if the user clicks anywhere outside of it
        if (!e.target.closest("#column-filter-popup")) {
            document.getElementById("column-filter-popup").style.display = "none";
        }
    });

    // 3. Apply the filter logic
    window.applyColumnFilter = function() {
        const val = document.getElementById("filter-popup-input").value.trim().toLowerCase();
        if (val) {
            activeTableFilters[currentFilterColIndex] = val;
        } else {
            delete activeTableFilters[currentFilterColIndex];
        }
        document.getElementById("column-filter-popup").style.display = "none";
        renderTableFilters();
    };

    // 4. Clear a single filter logic
    window.clearColumnFilter = function() {
        delete activeTableFilters[currentFilterColIndex];
        document.getElementById("column-filter-popup").style.display = "none";
        renderTableFilters();
    };

    // 5. Visually update the table, rows, and the Master Clear Button
    function renderTableFilters() {
        if (!currentFilterTable) return;
        
        // --- NEW: Toggle the Master Clear Button state ---
        if (clearAllBtn) {
            // Count how many keys (filters) exist in the dictionary
            const hasFilters = Object.keys(activeTableFilters).length > 0;
            
            // Disable if 0, Enable if > 0
            clearAllBtn.disabled = !hasFilters;
            clearAllBtn.style.opacity = hasFilters ? "1" : "0.5";
        }

        // Update the visual text sitting directly on the filter line
        const filterHeaders = currentFilterTable.rows[1].cells; 
        for (let i = 0; i < filterHeaders.length; i++) {
            const filterLine = filterHeaders[i].querySelector(".table-filter-line");
            if (filterLine) {
                // Create a text span to hold the typed value next to the icon
                let textSpan = filterLine.querySelector(".filter-text-display");
                if (!textSpan) {
                    textSpan = document.createElement("span");
                    textSpan.className = "filter-text-display";
                    textSpan.style.cssText = "margin-left: 6px; font-size: 12px; color: #1f51b5; font-weight: 600;";
                    filterLine.appendChild(textSpan);
                }
                
                // Inject the text and color the icon blue if active
                textSpan.textContent = activeTableFilters[i] || "";
                const icon = filterLine.querySelector(".filter-icon");
                if (icon) icon.style.color = activeTableFilters[i] ? "#1f51b5" : "#555";
            }
        }
        
        // Combine all active filters and hide/show matching rows
        const tbody = currentFilterTable.querySelector("tbody");
        if (!tbody) return;
        
        const rows = tbody.querySelectorAll("tr:not(.empty)");
        rows.forEach(row => {
            let showRow = true;
            
            for (const [colIndex, filterText] of Object.entries(activeTableFilters)) {
                if (row.cells[colIndex]) {
                    const cellText = row.cells[colIndex].textContent.trim().toLowerCase();
                    // If the row text doesn't include the typed filter, hide it
                    if (!cellText.includes(filterText)) {
                        showRow = false;
                        break; 
                    }
                }
            }
            row.style.display = showRow ? "" : "none";
        });
    }
});