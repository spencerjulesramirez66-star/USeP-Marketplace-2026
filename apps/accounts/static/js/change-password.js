const password = document.getElementById("new-password");
const confirmPassword = document.getElementById("confirm-password");

const lengthCheck = document.getElementById("length-check");
const uppercaseCheck = document.getElementById("uppercase-check");
const lowercaseCheck = document.getElementById("lowercase-check");
const numberCheck = document.getElementById("number-check");
const specialCheck = document.getElementById("special-check");

const strengthText = document.getElementById("strength-text");
const passwordMatch = document.getElementById("password-match");


password.addEventListener("input", function () {

    const value = password.value;

    const hasLength = value.length >= 8;
    const hasUppercase = /[A-Z]/.test(value);
    const hasLowercase = /[a-z]/.test(value);
    const hasNumber = /[0-9]/.test(value);
    const hasSpecial = /[^A-Za-z0-9]/.test(value);

    updateCheck(lengthCheck, hasLength);
    updateCheck(uppercaseCheck, hasUppercase);
    updateCheck(lowercaseCheck, hasLowercase);
    updateCheck(numberCheck, hasNumber);
    updateCheck(specialCheck, hasSpecial);

    const score = [
        hasLength,
        hasUppercase,
        hasLowercase,
        hasNumber,
        hasSpecial
    ].filter(Boolean).length;

    if (value.length === 0) {
        strengthText.textContent = "None";
    } else if (score <= 2) {
        strengthText.textContent = "Weak";
    } else if (score <= 4) {
        strengthText.textContent = "Moderate";
    } else {
        strengthText.textContent = "Strong";
    }

    checkPasswordMatch();
});


confirmPassword.addEventListener(
    "input",
    checkPasswordMatch
);


function updateCheck(element, valid) {

    if (valid) {
        element.classList.add("valid");
        element.classList.remove("invalid");
    } else {
        element.classList.add("invalid");
        element.classList.remove("valid");
    }
}


function checkPasswordMatch() {

    if (confirmPassword.value.length === 0) {
        passwordMatch.textContent = "";
        passwordMatch.classList.remove("valid", "invalid");
        return;
    }

    if (password.value === confirmPassword.value) {
        passwordMatch.textContent = "Passwords match.";
        passwordMatch.classList.add("valid");
        passwordMatch.classList.remove("invalid");
    } else {
        passwordMatch.textContent = "Passwords do not match.";
        passwordMatch.classList.add("invalid");
        passwordMatch.classList.remove("valid");
    }
}