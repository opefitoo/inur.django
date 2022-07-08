$(document).on('click', '#id_medical_prescription', function () {
    let patient_name = $('#id_patient').find(":selected").text();

    const url = $("#id_medical_prescription").attr("data-medical-prescriptions-url");
    let selected_medical_prescription_id = $("#id_medical_prescription").find(":selected").val();
    console.error(selected_medical_prescription_id);

    $.ajax({                       // initialize an AJAX request
        url: url,                    // set the url of the request (= /persons/ajax/load-cities/ )
        data: {
            'patient_name': patient_name,
            'selected_medical_prescription_id': selected_medical_prescription_id
        },
        success: function (data) {   // `data` is the return of the `load_cities` view function
            $("#id_medical_prescription").html(data);  // replace the contents of the city input with the data that came from the server
            console.log(data);
        }
    });

});
