let selectedDate = new Date();
let submitButton = document.getElementById("submit-btn")
function disableInput(elem) {
    if (elem.checked)
        elem.disabled = true;
}
submitButton.addEventListener("click", function() {
    fetch("/date-select/?user-id={{ user_id }}", {
        method: "POST",
        body: JSON.stringify({
            date: selectedDate.getTime() / 1000
        })
    });
});
$(function(){
    let minDate = new Date();
    minDate.setHours(0, 0, 0, 0);
    let maxDate = new Date();
    maxDate.setDate(maxDate.getDate() + 60);
    $('#datepicker').datepicker({
        minDate: minDate,
        maxDate: maxDate,
        onSelect: function(formattedDate, date, inst) {
            selectedDate = date;
            submitButton.style.opacity = 1;
            submitButton.style.boxShadow="0 0 5px #0ff";
            submitButton.removeAttribute("disabled");
        }
    })
})