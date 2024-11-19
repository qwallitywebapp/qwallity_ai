
$(".toggle-password").click(function() {

  $(this).toggleClass("fa-eye fa-eye-slash");
  var input = $($(this).attr("toggle"));
  if (input.attr("type") == "password") {
    input.attr("type", "text");
  } else {
    input.attr("type", "password");
  }
});

function getUserLocation() {

  function locationSuccess(position) {
    console.log("success");
    var coords = position.coords;
    generateURL(coords);
  }

  function locationError() {
    console.log("error");
  }
  navigator.geolocation.getCurrentPosition(locationSuccess, locationError);
}

function generateURL(coords) {
  var URL = 'https://api.openweathermap.org/data/2.5/weather?lat='+ coords.latitude + '&lon=' + coords.longitude + '&appid=3d22940be1eb70fcfe47f0fc0de9a7fa';
  var Http = new XMLHttpRequest();
  Http.open("GET", URL);
  Http.send();
  Http.onreadystatechange = (e) => {
    var resp1 = (Http.responseText);
    var obj = JSON.parse(resp1)
    descr = obj['weather'][0]['description'];
    tempr = obj['main']['temp']-273.15;
    tempr_round = Math.round(tempr);
    document.getElementById('weather').innerHTML = tempr_round+'°C';
  }
}

function js_remove_token() {
  // Remove the token from local storage
  localStorage.removeItem('token')
  localStorage.removeItem('username')
}
function validateform(){  
  var field1=document.myform.number1.value  
  var field2=document.myform.number2.value 
  var error1 = document.getElementById("errornumber1")
  var error2 = document.getElementById("errornumber2")

  if (isNaN(field1)){
    error1.textContent = "Please enter a valid number" 
    error1.style.color = "red"
    document.getElementById("Calculate").disabled = true}
  else if (isNaN(field2)){
    error2.textContent = "Please enter a valid number" 
    error2.style.color = "red"
    document.getElementById("Calculate").disabled = true
    return false;
  }else {  
    error1.textContent = ""
    error2.textContent = ""
    document.getElementById("Calculate").disabled = false

    return true;
  }  
}  

function js_add_payment(){  
  var amount=document.getElementById('amount').value
  var payment=document.getElementById('payment').value 
  var card_num=document.getElementById('card_num').value
  var exp_date=document.getElementById('exp_date').value
  var card_cvv = document.getElementById("card_cvv").value


var xhr = new XMLHttpRequest();
xhr.open("POST", "/add_account_balance/payment_api");
xhr.setRequestHeader("Accept", "application/json");
xhr.setRequestHeader("Content-Type", "application/json" );
xhr.setRequestHeader("Authorization", `Bearer ${token}`); 


var data = {
  "amount": amount,
  "payment": payment,
  "card_num": card_num,
  "exp_date": exp_date,
  "card_cvv":card_cvv
}

json_data = JSON.stringify(data)
xhr.send(json_data);
clearinputfield()


var success = document.getElementById("successmessage")
success.textContent = "Payment is added."
success.style.backgroundColor = "green"
location.reload(true)
  // var error1 = document.getElementById("errornumber1")
  // var error2 = document.getElementById("errornumber2" 
}  
function js_login(event) {
  event.preventDefault();  // Prevent default form submission
  console.log("Form submission prevented");

  var username = document.getElementById('username').value;
  var password = document.getElementById('password').value;
  // Show loading message
  var loadingMessage = document.getElementById("loadingMessage");
  loadingMessage.textContent = "Logging in, please wait...";
  loadingMessage.style.display = "block";

  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/login/api");
  xhr.setRequestHeader("Accept", "application/json");
  xhr.setRequestHeader("Content-Type", "application/json");

  var data = {
      "username": username,
      "password": password
  };

  var json_data = JSON.stringify(data);
  xhr.send(json_data);
  console.log("Login data sent:", json_data);

  xhr.onload = () => {
      console.log('XHR Status:', xhr.status);
      console.log('Response:', xhr.responseText);

      if (xhr.status === 200) {
          const res = JSON.parse(xhr.responseText);
          console.log('Response received:', res);
          localStorage.setItem("token", res['token']);
          console.log('Token stored:', res['token']);
     
          // Increase delay to see if it helps with redirection
          setTimeout(() => {
              console.log('Redirecting to:', window.location.origin + '/home');
              // Hide loading message
              loadingMessage.style.display = "none";
              location.replace('/home'); // Redirect after delay
          }, 2000); // 2 seconds delay
      } else {
          var error = document.getElementById("successmessage");
          error.textContent = "Invalid username or password";
          error.style.backgroundColor = "red";
          console.log("Error: Invalid credentials");
      }
  };

  xhr.onerror = () => {
      // Hide loading message
      loadingMessage.style.display = "none";
      
      var error = document.getElementById("successmessage");
      error.textContent = "Network error. Please try again.";
      error.style.backgroundColor = "orange";
      console.log("Network error occurred");
  };
}

// Attach the event listener to your form
document.getElementById('loginForm').addEventListener('submit', js_login);



function js_add_course(){  
  var title=document.getElementById('title').value
  var price=document.getElementById('price').value 
  var type=document.getElementById('coursetype').value
  var description=document.getElementById('description').value
  var success = document.getElementById("successmessage")
  var submit = document.getElementById("Submit")

  if (title === '' && title.hasAttribute('required')){

    submit.disabled = true}
  
    
  if (price === '' && price.hasAttribute('required')){

    submit.disabled = true}

var xhr = new XMLHttpRequest();
xhr.open("POST", "/add_course/api");
xhr.setRequestHeader("Accept", "application/json");
xhr.setRequestHeader("Content-Type", "application/json" );

xhr.onreadystatechange = function () {
   if (xhr.readyState == 4) {
      console.log(xhr.status);
      console.log(xhr.responseText);
   }};

var data = {
  "title": title,
  "price": price,
  "coursetype": type,
  "body": description
}
json_data = JSON.stringify(data)
xhr.send(json_data);
clearinputfield()
cleartextareafield()
success.textContent = "Course is added"
success.style.backgroundColor = "green"

location.replace('/home');
  // var error1 = document.getElementById("errornumber1")
  // var error2 = document.getElementById("errornumber2" 
}  
function upload(){
  var imgcanvas = document.getElementById("canv1");
  var fileinput = document.getElementById("finput");
  var image = new SimpleImage(fileinput);
  image.drawTo(imgcanvas, 150, 150);
}

function clearinputfield(){
  var elements = document.getElementsByTagName("input");
  for (var ii=0; ii < elements.length; ii++) {
  
      elements[ii].value = "";
  }

}
function cleartextareafield(){
  var elements = document.getElementsByTagName("textarea");
  for (var ii=0; ii < elements.length; ii++) {
  
      elements[ii].value = "";
  }

}
function getWeather(){
  var city_name = document.getElementById("city").value
  var URL = 'https://api.openweathermap.org/data/2.5/weather?q='+ city_name + '&appid=3d22940be1eb70fcfe47f0fc0de9a7fa';
  var Http = new XMLHttpRequest();
  Http.open("GET", URL);
  Http.send();
  Http.onreadystatechange = (e) => {
    var resp1 = (Http.responseText);
    var obj = JSON.parse(resp1)
    descr = obj['weather'][0]['description'];
    tempr = obj['main']['temp']-273.15;
    tempr_round = Math.round(tempr);
    document.getElementById('city_temp').innerHTML = tempr_round+'°C';
    document.getElementById('city_name').innerHTML = city_name;
    document.getElementById('descr').innerHTML =  descr.charAt(0).toUpperCase()
    + descr.slice(1)
  }
}
