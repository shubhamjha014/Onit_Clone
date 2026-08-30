// 1. General UI & Modal Logic
document.addEventListener("click", (event) => {
    const opener = event.target.closest("[data-modal-target]");
    if (opener) {
        const targetId = opener.dataset.modalTarget;
        // GENERIC FIX: Look inside current tab/container FIRST
        const parentContext = opener.closest('.tab-pane, .tab-embedded-grid, section');
        let targetModal = parentContext ? (parentContext.querySelector(`#${targetId}`) || parentContext.querySelector(`.${targetId}`)) : null;
        
        // Fallback to global search if it's a standard page
        if (!targetModal) targetModal = document.getElementById(targetId);
        
        if (targetModal) targetModal.classList.add("open");
        return;
    }

    // ADDED FIX: Modal Close Logic
    const closer = event.target.closest("[data-modal-close]");
    if (closer) {
        const modal = closer.closest(".modal");
        if (modal) modal.classList.remove("open");
        return;
    }
    
    // Actions Dropdown
    const actionBtn = event.target.closest(".bulk-action-btn");
    if (actionBtn) {
        const menu = actionBtn.nextElementSibling;
        if (menu && menu.classList.contains("dropdown-menu")) menu.classList.toggle("hidden");
        return;
    }
    
    // NEW: Export Dropdown
    const exportBtn = event.target.closest(".export-btn");
    if (exportBtn) {
        const menu = exportBtn.nextElementSibling;
        if (menu && menu.classList.contains("dropdown-menu")) menu.classList.toggle("hidden");
        return;
    }

    // Close dropdowns if clicking outside
    if (!event.target.closest(".bulk-action-dropdown") && !event.target.closest(".export-btn")) {
        document.querySelectorAll(".dropdown-menu").forEach(menu => menu.classList.add("hidden"));
    }
    
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

// 2. Generic Checkbox & Button Enabling Logic
function updateBulkToolbar(table) {
    const total = table.querySelectorAll(".bulk-select-row").length;
    const selected = table.querySelectorAll(".bulk-select-row:checked").length;
    const selectAll = table.querySelector(".bulk-select-all");
    
    if (selectAll) {
        selectAll.checked = total > 0 && selected === total;
        selectAll.indeterminate = selected > 0 && selected < total;
    }

    // 100% BULLETPROOF HYBRID APPROACH:
    // Step 1: If we are in a tab/embedded grid, lock the search to that specific container.
    // If we are on a main page, fallback to the entire document.
    const searchContext = table.closest('.tab-pane, .tab-embedded-grid') || document;
    
    // Step 2: Now safely search for the toolbar within that locked context.
    const toolbarSelector = table.dataset.bulkToolbar || ".list-toolbar";
    const toolbar = searchContext.querySelector(toolbarSelector);
    
    if (toolbar) {
        const actionButton = toolbar.querySelector(".bulk-action-btn");
        if (actionButton) {
            actionButton.disabled = selected === 0; 
        }
        
        if (selected === 0) {
            const dropMenu = toolbar.querySelector(".dropdown-menu");
            if (dropMenu) dropMenu.classList.add("hidden");
        }
    }
}

document.addEventListener("change", (event) => {
    if (!event.target.matches(".bulk-select-all, .bulk-select-row")) return;
    const table = event.target.closest("table");
    if (!table) return;
    if (event.target.classList.contains("bulk-select-all")) {
        table.querySelectorAll(".bulk-select-row").forEach(cb => { cb.checked = event.target.checked; });
    }
    updateBulkToolbar(table);
});

// 3. AJAX Refresh Logic (Context-Aware & Legacy-Safe)
document.addEventListener("click", (event) => {
    // Looks for EITHER the old ID or the new Class
    const refreshBtn = event.target.closest("#ajaxRefreshBtn, .ajaxRefreshBtn");
    if (!refreshBtn) return;
    
    const icon = refreshBtn.querySelector(".refresh-icon");
    if (icon) icon.classList.add("spin-icon");
    
    const parentContext = refreshBtn.closest('.tab-pane, .tab-embedded-grid') || document.body;
    
    // Looks for EITHER the old ID or the new Class
    const container = parentContext.querySelector("#table-container, .table-container");
    
    if (container) container.style.opacity = "0.5";

    fetch(window.location.href)
        .then(res => res.text())
        .then(html => {
            const doc = new DOMParser().parseFromString(html, "text/html");
            let newTable = null;
            
            const tabPane = refreshBtn.closest('.tab-pane');
            if (tabPane && tabPane.id) {
                const fetchedTabPane = doc.getElementById(tabPane.id);
                if (fetchedTabPane) newTable = fetchedTabPane.querySelector("#table-container, .table-container");
            } else {
                newTable = doc.querySelector("#table-container, .table-container");
            }

            if (newTable && container) {
                container.innerHTML = newTable.innerHTML;
                if (window.currentGridLayout && typeof applyGridLayout === 'function') {
                    applyGridLayout(window.currentGridLayout, container.querySelector('.table'));
                }
                if (typeof renderTableFilters === 'function') renderTableFilters();
            }
        })
        .finally(() => {
            if (container) container.style.opacity = "1";
            if (icon) icon.classList.remove("spin-icon");
        });
});

// 4. AJAX Bulk Action Trigger (Context-Aware & Legacy-Safe)
let pendingBulkAction = null;
document.addEventListener("click", (event) => {
    const actionLink = event.target.closest("[data-bulk-action]");
    if (!actionLink) return;
    event.preventDefault();
    
    const action = actionLink.dataset.bulkAction;
    const parentContext = actionLink.closest('.tab-pane, .tab-embedded-grid') || document.body;
    
    // Looks for EITHER the old ID or the new Class
    const container = parentContext.querySelector("#table-container, .table-container");
    
    if (!container) return;
    
    const selectedIds = Array.from(container.querySelectorAll(".bulk-select-row:checked")).map(cb => cb.value);
    
    if (selectedIds.length === 0) return alert("Please select at least one record to perform this action.");
    
    pendingBulkAction = { action, selectedIds, container };
    
    const confirmModal = parentContext.querySelector("#bulk-confirm-modal, .bulk-confirm-modal");
    if (confirmModal) confirmModal.classList.add("open");
    actionLink.closest(".dropdown-menu")?.classList.add("hidden"); 
});

// 5. AJAX Confirm Execution inside the Modal (Context-Aware & Legacy-Safe)
document.addEventListener("click", (event) => {
    const confirmBtn = event.target.closest("#confirm-bulk-btn, .confirm-bulk-btn");
    if (!confirmBtn) return;
    if (!pendingBulkAction || pendingBulkAction.action !== "delete") return;
    
    const csrfToken = document.getElementById("csrf-token")?.value;
    const deleteUrl = pendingBulkAction.container.dataset.deleteUrl;
    
    confirmBtn.disabled = true; 
    
    fetch(deleteUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify({ ids: pendingBulkAction.selectedIds })
    })
    .then(async res => {
        if (!res.ok) {
            if (res.status === 400 || res.status === 401) throw new Error("Security session expired. Please refresh the page and log back in.");
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || "An unknown server error occurred.");
        }
        return res.json();
    })
    .then(data => {
        if (data.success) {
            event.target.closest(".modal").classList.remove("open");
            const refreshBtn = pendingBulkAction.container.closest('.tab-pane, .tab-embedded-grid, body').querySelector("#ajaxRefreshBtn, .ajaxRefreshBtn");
            if (refreshBtn) refreshBtn.click();
        } else alert("Error: " + data.error);
    })
    .catch(err => alert(err.message))
    .finally(() => {
        confirmBtn.disabled = false;
        pendingBulkAction = null;
    });
});
// 6. LEGACY Form-based Bulk Delete (Users Page)
document.addEventListener("click", (event) => {
    const deleteItem = event.target.closest("[data-bulk-delete-url]");
    if (!deleteItem) return;
    event.preventDefault();

    const toolbar = deleteItem.closest(".bulk-action-dropdown");
    const table = toolbar?.id ? document.querySelector(`table[data-bulk-toolbar="#${toolbar.id}"]`) : document.querySelector("table");
    const selectedIds = table ? Array.from(table.querySelectorAll(".bulk-select-row:checked")).map(cb => cb.value) : [];
    
    if (!selectedIds.length) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedIds.length} selected record(s)? This action cannot be undone.`)) return;

    const csrfToken = document.getElementById("csrf-token")?.value;
    if (!csrfToken) return window.alert("Unable to verify this request. Please refresh the page and try again.");

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
    selectedIds.forEach(id => addField("user_ids", id));
    
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
    if (targetPane) targetPane.style.display = 'block';
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
    if (menu && !e.target.closest("#more-actions-btn")) menu.classList.remove("show");
});

// --- 10. Generic Dynamic Column Filtering ---
let activeTableFilters = {}; 
window.renderTableFilters = function() {} 
document.addEventListener("DOMContentLoaded", () => {
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

    let currentFilterColName = null;
    let currentFilterTable = null;

    const clearAllBtn = document.getElementById("clear-all-filters-btn");
    if (clearAllBtn) {
        clearAllBtn.addEventListener("click", () => {
            activeTableFilters = {}; 
            renderTableFilters();    
        });
    }

    document.getElementById("filter-popup-input").addEventListener("keypress", function(e) {
        if (e.key === "Enter") applyColumnFilter();
    });

    document.addEventListener("click", (e) => {
        const filterLine = e.target.closest(".table-filter-line");
        if (filterLine) {
            e.preventDefault();
            e.stopPropagation();
            
            const th = filterLine.closest("th");
            const index = Array.from(th.parentNode.children).indexOf(th);
            currentFilterTable = th.closest("table");
            
            const headerTh = currentFilterTable.rows[0].cells[index];
            currentFilterColName = headerTh.dataset.col;
            document.getElementById("filter-popup-title").textContent = currentFilterColName ? `${currentFilterColName} Filter` : "Column Filter";
            
            const input = document.getElementById("filter-popup-input");
            input.value = activeTableFilters[currentFilterColName] || "";
            
            const rect = filterLine.getBoundingClientRect();
            columnFilterPopup.style.top = `${rect.bottom + window.scrollY + 8}px`;
            columnFilterPopup.style.left = `${rect.left + window.scrollX}px`;
            columnFilterPopup.style.display = "block";
            
            input.focus();
            return;
        }
        if (!e.target.closest("#column-filter-popup")) document.getElementById("column-filter-popup").style.display = "none";
    });

    window.applyColumnFilter = function() {
        const val = document.getElementById("filter-popup-input").value.trim().toLowerCase();
        if (val) activeTableFilters[currentFilterColName] = val;
        else delete activeTableFilters[currentFilterColName];
        
        document.getElementById("column-filter-popup").style.display = "none";
        renderTableFilters();
    };

    window.clearColumnFilter = function() {
        delete activeTableFilters[currentFilterColName];
        document.getElementById("column-filter-popup").style.display = "none";
        renderTableFilters();
    };

    window.renderTableFilters = function() {
        if (!currentFilterTable) currentFilterTable = document.querySelector(".table");
        if (!currentFilterTable) return;
        
        if (clearAllBtn) {
            const hasFilters = Object.keys(activeTableFilters).length > 0;
            clearAllBtn.disabled = !hasFilters;
            clearAllBtn.style.opacity = hasFilters ? "1" : "0.5";
        }

        const headers = currentFilterTable.rows[0].cells;
        const filterHeaders = currentFilterTable.rows[1].cells; 
        
        for (let i = 1; i < filterHeaders.length; i++) {
            const colName = headers[i].dataset.col;
            const filterLine = filterHeaders[i].querySelector(".table-filter-line");
            if (filterLine) {
                let textSpan = filterLine.querySelector(".filter-text-display");
                if (!textSpan) {
                    textSpan = document.createElement("span");
                    textSpan.className = "filter-text-display";
                    textSpan.style.cssText = "margin-left: 6px; font-size: 12px; color: #1f51b5; font-weight: 600;";
                    filterLine.appendChild(textSpan);
                }
                textSpan.textContent = activeTableFilters[colName] || "";
                const icon = filterLine.querySelector(".filter-icon");
                if (icon) icon.style.color = activeTableFilters[colName] ? "#1f51b5" : "#555";
            }
        }
        
        const tbody = currentFilterTable.querySelector("tbody");
        if (!tbody) return;
        
        const rows = tbody.querySelectorAll("tr:not(.empty)");
        rows.forEach(row => {
            let showRow = true;
            for (const [colName, filterText] of Object.entries(activeTableFilters)) {
                let colIndex = -1;
                for (let i = 1; i < headers.length; i++) {
                    if (headers[i].dataset.col === colName) { colIndex = i; break; }
                }
                if (colIndex !== -1 && row.cells[colIndex]) {
                    const cellText = row.cells[colIndex].textContent.trim().toLowerCase();
                    if (!cellText.includes(filterText)) { showRow = false; break; }
                }
            }
            row.style.display = showRow ? "" : "none";
        });
    }
});

// --- 11. Generic Dynamic "Select Fields" Modal & Grid Reordering ---
window.currentGridLayout = null; 

// Accepts a specific table element so it doesn't accidentally affect the wrong grid
window.applyGridLayout = function(selectedFields, targetTableElement) {
    const table = targetTableElement || document.querySelector(".table");
    if (!table) return;

    const headers = Array.from(table.rows[0].cells);
    const colMap = {};
    headers.forEach((th, index) => {
        if (index === 0) return; 
        colMap[th.dataset.col] = index; 
    });

    Array.from(table.rows).forEach((row) => {
        if (row.classList.contains("empty")) {
            if(row.cells[0]) row.cells[0].colSpan = selectedFields.length + 1;
            return;
        }
        
        const cells = Array.from(row.cells);
        const checkboxCell = cells[0];
        
        cells.forEach((cell, i) => { if (i !== 0) cell.style.display = "none"; });
        
        row.appendChild(checkboxCell); 
        selectedFields.forEach(field => {
            const origIndex = colMap[field];
            if (origIndex !== undefined && cells[origIndex]) {
                cells[origIndex].style.display = ""; 
                row.appendChild(cells[origIndex]); 
            }
        });
    });
};

document.addEventListener("DOMContentLoaded", () => {
    // GENERIC FIX: Loop through ALL select-fields modals on the page
    document.querySelectorAll(".select-cols-modal-inner").forEach(modalInner => {
        const modal = modalInner.closest('.modal');
        if (!modal) return;

        // Contextual lookups within this specific modal
        const allFieldsList = modalInner.querySelector("#all-fields-list, .all-fields-list");
        const showOnGridList = modalInner.querySelector("#show-on-grid-list, .show-on-grid-list");
        const selectAllCheckbox = modalInner.querySelector("#select-all-fields-cb, .select-all-fields-cb");

        modalInner.querySelectorAll(".field-search-input").forEach(searchInput => {
            searchInput.addEventListener("input", (e) => {
                const term = e.target.value.toLowerCase();
                const container = e.target.closest(".select-cols-left, .select-cols-right");
                container.querySelectorAll(".field-item, .selected-field-item").forEach(item => {
                    item.style.display = item.textContent.toLowerCase().includes(term) ? "" : "none";
                });
            });
        });

        if (allFieldsList) {
            allFieldsList.addEventListener("change", (e) => {
                if (e.target.type === "checkbox") {
                    const fieldName = e.target.closest(".field-item").dataset.field;
                    if (e.target.checked) addToRightList(fieldName);
                    else removeFromRightList(fieldName);
                    updateSelectAllState();
                }
            });
        }

        if (showOnGridList) {
            showOnGridList.addEventListener("click", (e) => {
                if (e.target.classList.contains("remove-btn")) {
                    const fieldName = e.target.closest(".selected-field-item").dataset.field;
                    removeFromRightList(fieldName);
                    const leftCb = allFieldsList.querySelector(`.field-item[data-field="${fieldName}"] input`);
                    if (leftCb) leftCb.checked = false;
                    updateSelectAllState();
                }
            });
        }

        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener("change", (e) => {
                const isChecked = e.target.checked;
                allFieldsList.querySelectorAll(".field-item input[type='checkbox']").forEach(cb => {
                    if (cb.checked !== isChecked) {
                        cb.checked = isChecked;
                        const fieldName = cb.closest(".field-item").dataset.field;
                        if (isChecked) addToRightList(fieldName);
                        else removeFromRightList(fieldName);
                    }
                });
            });
        }

        function addToRightList(fieldName) {
            if (showOnGridList.querySelector(`.selected-field-item[data-field="${fieldName}"]`)) return;
            const div = document.createElement("div");
            div.className = "selected-field-item";
            div.dataset.field = fieldName;
            div.draggable = true;
            div.innerHTML = `<div class="selected-field-item-left"><span class="drag-handle">⋮⋮</span> ${fieldName}</div><span class="remove-btn">&times;</span>`;
            showOnGridList.appendChild(div);
            setupDragAndDrop(div);
        }

        function removeFromRightList(fieldName) {
            const item = showOnGridList.querySelector(`.selected-field-item[data-field="${fieldName}"]`);
            if (item) item.remove();
        }

        function updateSelectAllState() {
            const total = allFieldsList.querySelectorAll(".field-item input[type='checkbox']").length;
            const checked = allFieldsList.querySelectorAll(".field-item input[type='checkbox']:checked").length;
            if (selectAllCheckbox) selectAllCheckbox.checked = (total > 0 && total === checked);
        }

        let draggedItem = null;
        function setupDragAndDrop(el) {
            el.addEventListener("dragstart", function(e) {
                draggedItem = this;
                e.dataTransfer.effectAllowed = "move";
                e.dataTransfer.setData("text/plain", this.dataset.field);
                setTimeout(() => this.style.opacity = "0.5", 0);
            });
            el.addEventListener("dragend", function() {
                setTimeout(() => { this.style.opacity = "1"; draggedItem = null; }, 0);
            });
            el.addEventListener("dragover", function(e) {
                e.preventDefault();
                this.style.borderTop = "2px solid #2f6feb";
            });
            el.addEventListener("dragleave", function() { this.style.borderTop = ""; });
            el.addEventListener("drop", function(e) {
                e.preventDefault();
                this.style.borderTop = "";
                if (draggedItem !== this && draggedItem.classList.contains("selected-field-item")) {
                    this.parentNode.insertBefore(draggedItem, this);
                }
            });
        }
        
        if (showOnGridList) {
            showOnGridList.querySelectorAll(".selected-field-item").forEach(setupDragAndDrop);
            showOnGridList.addEventListener("dragover", e => e.preventDefault());
            showOnGridList.addEventListener("drop", function(e) {
                e.preventDefault();
                const fieldName = e.dataTransfer.getData("text/plain");
                if (fieldName) {
                    const leftCb = allFieldsList.querySelector(`.field-item[data-field="${fieldName}"] input`);
                    if (leftCb && !leftCb.checked) {
                        leftCb.checked = true;
                        addToRightList(fieldName);
                        updateSelectAllState();
                    }
                }
            });
        }

        if (allFieldsList) {
            allFieldsList.querySelectorAll(".field-item").forEach(item => {
                item.draggable = true;
                item.addEventListener("dragstart", function(e) {
                    e.dataTransfer.effectAllowed = "copy";
                    e.dataTransfer.setData("text/plain", this.dataset.field);
                });
            });
        }

        const applyBtn = modalInner.querySelector(".btn-apply");
        if (applyBtn) {
            applyBtn.addEventListener("click", () => {
                const selectedFields = Array.from(showOnGridList.querySelectorAll(".selected-field-item")).map(i => i.dataset.field);
                window.currentGridLayout = selectedFields;
                
                // GENERIC FIX: Find the specific table associated with THIS modal
                const contextWrapper = modal.closest('.tab-pane, .tab-embedded-grid, section, body');
                const activeTable = contextWrapper.querySelector('.table');
                
                applyGridLayout(selectedFields, activeTable);
                modal.classList.remove("open");
            });
        }
    });
});

// --- 12. WYSIWYG Table Exporter (Matches selected columns, order, and active filters) ---
window.exportTableToCSV = function(filename, excelFriendly = false) {
    const table = document.querySelector(".table");
    if (!table) return;

    let csv = [];
    const rows = table.querySelectorAll("tr");
    
    for (let i = 0; i < rows.length; i++) {
        // Skip the visual filter row ≚ line
        if (rows[i].classList.contains("table-filter-row")) continue;
        
        // Exclude rows that the user currently has hidden via filters
        if (rows[i].style.display === "none") continue;

        let rowData = [];
        const cols = rows[i].querySelectorAll("td, th");
        
        for (let j = 0; j < cols.length; j++) {
            // Only capture the columns the user currently has visible!
            // Skip the checkbox column (index 0)
            if (cols[j].style.display !== "none" && j !== 0) {
                // Strip out quotes to prevent CSV breaks
                let text = cols[j].innerText.replace(/"/g, '""').trim();
                rowData.push('"' + text + '"');
            }
        }
        if (rowData.length > 0) csv.push(rowData.join(","));
    }

    let csvString = csv.join("\n");
    
    // Add UTF-8 BOM if user selected Excel so formatting stays perfect
    if (excelFriendly) {
        csvString = '\uFEFF' + csvString;
    }

    const blob = new Blob([csvString], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

/**
 * lists_filter.js
 * 
 * Provides client-side (browser) filtering for data tables.
 * Used on the Lists dashboard and List Details pages to instantly 
 * search and filter rows based on user input without reloading the page.
 */

/**
 * Filters a table's rows based on the text entered into a specific input field.
 * 
 * @param {string} inputId - The HTML ID of the search/filter input field.
 * @param {string} tableId - The HTML ID of the table to be filtered.
 */
function filterTable(inputId, tableId) {
    // 1. Grab the input element and the search text (converted to lowercase for case-insensitive matching)
    const input = document.getElementById(inputId);
    if (!input) return; // Exit safely if the input doesn't exist on the page
    const filterText = input.value.toLowerCase();

    // 2. Grab the table element and all of its rows (<tr>)
    const table = document.getElementById(tableId);
    if (!table) return; // Exit safely if the table doesn't exist
    const rows = table.getElementsByTagName("tr");

    // 3. Loop through all table rows (starting at index 1 to skip the header row `<th>`)
    for (let i = 1; i < rows.length; i++) {
        // Extract all text content from the current row
        let rowText = rows[i].textContent || rows[i].innerText;
        
        // 4. Check if the row's text contains the search filter string
        if (rowText.toLowerCase().indexOf(filterText) > -1) {
            // Match found: reset the display property so the row is visible
            rows[i].style.display = "";
        } else {
            // No match: hide the row
            rows[i].style.display = "none";
        }
    }
}

/**
 * Clears the search input and resets the table to show all rows.
 * 
 * @param {string} inputId - The HTML ID of the search/filter input field.
 * @param {string} tableId - The HTML ID of the table to be reset.
 */
function clearFilter(inputId, tableId) {
    // 1. Grab the input element
    const input = document.getElementById(inputId);
    if (!input) return;

    // 2. Clear the text inside the input field
    input.value = '';

    // 3. Re-run the filter function with the now-empty string to unhide all rows
    filterTable(inputId, tableId);
}
// Pagination Script
function changePage(page, perPage) {
    // 1. Ensure page is at least 1
    page = Math.max(1, page);
    
    // 2. Update URL search parameters safely
    const url = new URL(window.location.href);
    url.searchParams.set('page', page);
    url.searchParams.set('per_page', perPage);
    
    // 3. Reload page with new data
    window.location.href = url.toString();
}