const otpInputs = document.querySelectorAll('.otp');

otpInputs.forEach((input, index) => {

    input.addEventListener('input', () => {
        input.value = input.value.replace(/\D/g, '');

        if (input.value && index < otpInputs.length - 1) {
            otpInputs[index + 1].focus();
        }
    });

    input.addEventListener('keydown', (event) => {
        if (
            event.key === 'Backspace' &&
            !input.value &&
            index > 0
        ) {
            otpInputs[index - 1].focus();
        }
    });

    input.addEventListener('paste', (event) => {
        event.preventDefault();

        const pastedData = event.clipboardData
            .getData('text')
            .replace(/\D/g, '')
            .slice(0, otpInputs.length);

        pastedData.split('').forEach((digit, i) => {
            otpInputs[i].value = digit;
        });

        if (pastedData.length > 0) {
            const nextIndex = Math.min(
                pastedData.length,
                otpInputs.length - 1
            );

            otpInputs[nextIndex].focus();
        }
    });

});