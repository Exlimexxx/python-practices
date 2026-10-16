// Небольшой помощник: автоподстановка даты выезда на день позже заезда.
document.addEventListener("DOMContentLoaded", function () {
    var checkIn = document.querySelector('input[name="check_in"]');
    var checkOut = document.querySelector('input[name="check_out"]');
    if (!checkIn || !checkOut) {
        return;
    }
    checkIn.addEventListener("change", function () {
        if (!checkIn.value) {
            return;
        }
        var next = new Date(checkIn.value);
        next.setDate(next.getDate() + 2);
        checkOut.min = checkIn.value;
        if (!checkOut.value || checkOut.value <= checkIn.value) {
            checkOut.value = next.toISOString().slice(0, 10);
        }
    });
});
