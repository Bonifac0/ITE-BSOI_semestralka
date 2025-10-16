function fill_components() {
    document.getElementById("button_show_image").innerHTML = shown ? "Hide image" : "Show image";
    document.getElementById("img_lena").style.visibility = shown ? "visible" : "hidden"
    document.getElementById("div_info").innerHTML = "Lena shown "+count+" times.";
}

function on_loaded() {
    fill_components()
}

function show_hide_image() {
    shown = !shown
    if (shown) {
        count++;
    }
    fill_components()
}