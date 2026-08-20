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

document.querySelectorAll("form[data-loading-text]").forEach((form) => {
    form.addEventListener("submit", () => {
        if (!form.checkValidity()) return;
        form.closest(".modal")?.classList.remove("open");
        const loadingModal = document.getElementById("loadingModal");
        if (loadingModal) {
            loadingModal.classList.add("open");
            const heading = loadingModal.querySelector("h3");
            if (heading) heading.textContent = form.dataset.loadingText;
        }
        const button = form.querySelector("button[type=submit]");
        if (button) button.disabled = true;
    });
});

// Shared selection behaviour for any table that uses the bulk-select classes.
function getBulkToolbar(table) {
    return table.dataset.bulkToolbar
        ? document.querySelector(table.dataset.bulkToolbar)
        : table;
}

function updateBulkToolbar(table) {
    const total = table.querySelectorAll(".bulk-select-row").length;
    const selected = table.querySelectorAll(".bulk-select-row:checked").length;
    const selectAll = table.querySelector(".bulk-select-all");
    if (selectAll) {
        selectAll.checked = total > 0 && selected === total;
        selectAll.indeterminate = selected > 0 && selected < total;
    }

    const toolbar = getBulkToolbar(table);
    const actionButton = toolbar?.querySelector(".bulk-action-btn");
    if (!actionButton) return;
    const label = toolbar.dataset.bulkActionLabel || "Actions";
    actionButton.disabled = selected === 0;
    //actionButton.textContent = selected ? `${label} (${selected}) ˅` : `${label} ˅`;
    if (!selected) toolbar.querySelector(".dropdown-menu")?.classList.add("hidden");
}

document.addEventListener("change", (event) => {
    if (!event.target.matches(".bulk-select-all, .bulk-select-row")) return;
    const table = event.target.closest("table");
    if (!table) return;
    if (event.target.classList.contains("bulk-select-all")) {
        table.querySelectorAll(".bulk-select-row").forEach((checkbox) => {
            checkbox.checked = event.target.checked;
        });
    }
    updateBulkToolbar(table);
});

document.addEventListener("click", (event) => {
    const actionButton = event.target.closest(".bulk-action-btn");
    if (actionButton) {
        actionButton.nextElementSibling?.classList.toggle("hidden");
        return;
    }
    if (!event.target.closest(".bulk-action-dropdown")) {
        document.querySelectorAll(".dropdown-menu").forEach((menu) => menu.classList.add("hidden"));
    }
});

document.addEventListener("click", (event) => {
    const deleteItem = event.target.closest("[data-bulk-delete-url]");
    if (!deleteItem) return;
    event.preventDefault();

    const toolbar = deleteItem.closest(".bulk-action-dropdown");
    const table = toolbar?.id
        ? document.querySelector(`table[data-bulk-toolbar="#${toolbar.id}"]`)
        : null;
    const selectedIds = table
        ? Array.from(table.querySelectorAll(".bulk-select-row:checked"), (checkbox) => checkbox.value)
        : [];
    if (!selectedIds.length) return;

    const suffix = selectedIds.length === 1 ? "user" : "users";
    if (!window.confirm(`Delete selected users? Are you sure you want to delete ${selectedIds.length} selected ${suffix}? This action cannot be undone.`)) {
        return;
    }

    const csrfToken = document.getElementById("csrf-token")?.value;
    if (!csrfToken) {
        window.alert("Unable to verify this request. Please refresh the page and try again.");
        return;
    }

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

// Existing list pages can keep adding non-destructive actions while their APIs are built.
document.addEventListener("click", (event) => {
    const actionItem = event.target.closest("[data-action]");
    if (!actionItem) return;
    event.preventDefault();
    const table = actionItem.closest("table");
    const selected = table?.querySelectorAll(".bulk-select-row:checked").length || 0;
    if (selected) window.alert(`Triggered action '${actionItem.dataset.action}' for ${selected} item(s)`);
    actionItem.closest(".dropdown-menu")?.classList.add("hidden");
});
