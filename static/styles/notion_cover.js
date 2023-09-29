let uploadButton = document.getElementById("upload-button");
let container = document.getElementById("container");
let error = document.getElementById("error");
let imageDisplay = document.getElementById("image-display");
let generateButton = document.getElementById("generate-button");


const fileHandler = (file, name, type) => {
  if (type.split("/")[0] !== "image") {
    //File Type Error
    error.innerText = "Please upload an image file";
    return false;
  }
  error.innerText = "";
  
  let reader = new FileReader();
  reader.readAsDataURL(file);
  reader.onloadend = () => {
    //image and file name
    let imageContainer = document.createElement("figure");
    let img = document.createElement("img");
    img.src = reader.result;
    imageContainer.appendChild(img);
    // imageContainer.innerHTML += `<figcaption>${name}</figcaption>`;
    imageDisplay.appendChild(imageContainer);

    generateButton.style.display = "block";
  };
};

//Upload Button
uploadButton.addEventListener("change", () => {
  imageDisplay.innerHTML = "";
  fileHandler(uploadButton.files[0], uploadButton.files[0].name, uploadButton.files[0].type);
});


container.addEventListener("dragenter", (e) => {
  e.preventDefault();
  // e.stopPropogation();
  container.classList.add("active");
},
false
);


container.addEventListener("dragleave", (e) => {
  e.preventDefault();
  // e.stopPropogation();
  container.classList.remove("active");
},
                           false
);


container.addEventListener("dragover", (e) => {
  e.preventDefault();
  // e.stopPropogation();
  container.classList.add("active");
},
                           false
);


container.addEventListener("drop", (e) => {
  e.preventDefault();
  // e.stopPropogation();
  container.classList.remove("active");
  let files = e.dataTransfer.files;
  document.getElementById('upload-button').files = files;
  imageDisplay.innerHTML = "";
  fileHandler(files[0], files[0].name, files[0].type);
},
                           false
                          );


window.onload = () => {
  error.innerText = "";
  uploadButton.value = "";

};

