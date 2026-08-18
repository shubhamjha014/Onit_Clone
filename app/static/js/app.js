document.addEventListener("click", (event) => {
    const opener = event.target.closest("[data-modal-target]");
    if (opener) {
        document.getElementById(opener.dataset.modalTarget)?.classList.add("open");
        return;
    }

    if (event.target.closest("[data-modal-close]")) {
        event.target.closest(".modal")?.classList.remove("open");
        return;
    }

    if (event.target.classList.contains("modal")) {
        event.target.classList.remove("open");
        return;
    }

    if (event.target.closest("[data-toggle-sidebar]")) {
        document.getElementById("sidebar")?.classList.toggle("collapsed");
    }
});

// Show a loading state on forms that create records.
document.querySelectorAll("form[data-loading-text]").forEach((form) => {
    form.addEventListener("submit", () => {
        if (!form.checkValidity()) return;

        // Hide create modal if open
        const createModal = form.closest('.modal');
        if (createModal) {
            createModal.classList.remove('open');
        }

        // Show loading modal
        const loadingModal = document.getElementById('loadingModal');
        if (loadingModal) {
            loadingModal.classList.add('open');
            const h3 = loadingModal.querySelector('h3');
            if (h3) {
                h3.textContent = form.dataset.loadingText;
            }
        }

        const button = form.querySelector("button[type=submit]");
        if (button) {
            button.disabled = true;
            // Removed textContent update so button doesn't visually break
        }
    });
});


// Reusable Bulk Selection Logic
function updateBulkToolbar(table) {
    if (!table) return;
    const count = table.querySelectorAll(".bulk-select-row:checked").length;

    const actionBtn = table.querySelector(".bulk-action-btn");
    if (actionBtn) {
        if (count > 0) {
            actionBtn.disabled = false;
            actionBtn.textContent = `✓ ${count} record${count === 1 ? '' : 's'} selected ˅`;
        } else {
            actionBtn.disabled = true;
            actionBtn.textContent = 'Actions ˅';
            const textSpan = actionBtn.parentElement.parentElement.querySelector(".bulk-action-text");
            if (textSpan) {
                textSpan.style.display = "none";
            }

            // hide dropdown if open
            const menu = table.querySelector(".dropdown-menu");
            if (menu) menu.classList.add("hidden");
        }
    }
}

document.addEventListener("change", (event) => {
    if (event.target.classList.contains("bulk-select-all")) {
        const checked = event.target.checked;
        const table = event.target.closest('table');
        if (table) {
            table.querySelectorAll(".bulk-select-row").forEach((checkbox) => {
                checkbox.checked = checked;
            });
            updateBulkToolbar(table);
        }
    } else if (event.target.classList.contains("bulk-select-row")) {
        const table = event.target.closest('table');
        if (table) {
            const allSelect = table.querySelector(".bulk-select-all");
            if (allSelect) {
                const total = table.querySelectorAll(".bulk-select-row").length;
                const checked = table.querySelectorAll(".bulk-select-row:checked").length;
                allSelect.checked = (total > 0 && checked === total);
            }
            updateBulkToolbar(table);
        }
    }
});

document.addEventListener("click", (event) => {
    // ... existing modal logic ...

    // Dropdown toggle
    if (event.target.classList.contains("bulk-action-btn")) {
        const menu = event.target.nextElementSibling;
        if (menu && menu.classList.contains("dropdown-menu")) {
            menu.classList.toggle("hidden");
        }
    } else if (!event.target.closest(".bulk-action-dropdown")) {
        // Close all dropdowns if click outside
        document.querySelectorAll(".dropdown-menu").forEach(menu => {
            menu.classList.add("hidden");
        });
    }
});

document.addEventListener("click", (event) => {
    // Handle bulk action menu items
    if (event.target.classList.contains("dropdown-item")) {
        event.preventDefault();
        const action = event.target.dataset.action;
        const table = event.target.closest('table');
        if (table && action) {
            const selectedIds = Array.from(table.querySelectorAll(".bulk-select-row:checked")).map(cb => cb.value);
            if (selectedIds.length > 0) {
                // For now, since APIs aren't requested, we'll just show an alert.
                // Alternatively, this could be extended to make a real fetch request based on the action.
                alert(`Triggered action '${action}' for ${selectedIds.length} item(s)`);
                // Close menu
                const menu = event.target.closest(".dropdown-menu");
                if (menu) menu.classList.add("hidden");
            }
        }
    }
});
