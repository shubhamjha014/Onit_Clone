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
        const button = form.querySelector("button[type=submit]");
        if (button) {
            button.disabled = true;
            button.textContent = form.dataset.loadingText;
        }
    });
});
