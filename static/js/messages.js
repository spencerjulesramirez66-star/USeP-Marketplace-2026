document.addEventListener("DOMContentLoaded", () => {
    const alerts = document.querySelectorAll(".alert");

    alerts.forEach((alert) => {
        const dismissButton = alert.querySelector(".alert-dismiss");

        dismissButton.addEventListener("click", () => {
            alert.remove();
        });

        setTimeout(() => {
            alert.remove();
        }, 3000);
    });
});