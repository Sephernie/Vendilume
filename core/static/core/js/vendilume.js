(function () {
    "use strict";

    const body = document.body;
    const openButton = document.querySelector("[data-sidebar-open]");
    const closeButtons = document.querySelectorAll("[data-sidebar-close]");

    function setSidebar(open) {
        body.classList.toggle("sidebar-open", open);
        if (openButton) {
            openButton.setAttribute("aria-expanded", String(open));
        }
    }

    if (openButton) {
        openButton.addEventListener("click", function () {
            setSidebar(true);
        });
    }

    closeButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            setSidebar(false);
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            setSidebar(false);
        }
    });
}());
