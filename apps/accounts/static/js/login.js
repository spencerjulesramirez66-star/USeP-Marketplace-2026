const cover = document.getElementById("cover-container");

function handleScroll() {
    if (window.innerWidth > 768) {
        cover.style.transform = "";
        return;
    }

    const scrollY = window.scrollY;
    const coverHeight = window.innerHeight;

    const progress = Math.min(
        scrollY / coverHeight,
        1
    );

    cover.style.transform =
        `translateY(${-progress * 100}%)`;
}

window.addEventListener("scroll", handleScroll, {
    passive: true
});

window.addEventListener("resize", handleScroll);

handleScroll();


// SHOW PASSWORD

const show_password = document.getElementById("show-password");
const password = document.getElementById("password");

show_password.addEventListener("click", function () {
    if (password.type === "password") {
        password.type = "text";
        show_password.classList.remove("bi-eye-slash");
        show_password.classList.add("bi-eye");
    } else {
        password.type = "password";
        show_password.classList.remove("bi-eye");
        show_password.classList.add("bi-eye-slash");
    }
});