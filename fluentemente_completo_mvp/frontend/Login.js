const API_URL =
    "https://fluencesmente.onrender.com/";


const form =
    document.getElementById("loginForm");


const email =
    document.getElementById("email");


const password =
    document.getElementById("password");


const errorMessage =
    document.getElementById("errorMessage");


const loginButton =
    document.getElementById("loginButton");


const buttonText =
    document.getElementById("buttonText");


const loading =
    document.getElementById("loading");


const togglePassword =
    document.getElementById("togglePassword");


// =====================================================
// MOSTRAR / ESCONDER SENHA
// =====================================================

togglePassword.addEventListener(
    "click",
    () => {

        if (
            password.type === "password"
        ) {

            password.type = "text";

            togglePassword.textContent =
                "Esconder";

        } else {

            password.type = "password";

            togglePassword.textContent =
                "Mostrar";

        }

    }
);


// =====================================================
// DEVICE ID
// =====================================================

function getDeviceId() {

    let deviceId =
        localStorage.getItem(
            "fluentemente_device_id"
        );


    if (!deviceId) {

        deviceId =
            crypto.randomUUID();

        localStorage.setItem(
            "fluentemente_device_id",
            deviceId
        );

    }


    return deviceId;

}


// =====================================================
// MOSTRAR ERRO
// =====================================================

function showError(message) {

    errorMessage.textContent =
        message;

    errorMessage.style.display =
        "block";

}


// =====================================================
// LOGIN
// =====================================================

form.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();


        errorMessage.style.display =
            "none";


        loginButton.disabled =
            true;


        buttonText.style.display =
            "none";


        loading.style.display =
            "inline";


        try {

            const formData =
                new URLSearchParams();


            formData.append(
                "username",
                email.value.trim()
            );


            formData.append(
                "password",
                password.value
            );


            // -----------------------------------------
            // LOGIN
            // -----------------------------------------

            const loginResponse =
                await fetch(
                    `${API_URL}/api/login`,
                    {

                        method: "POST",

                        headers: {

                            "Content-Type":
                                "application/x-www-form-urlencoded"

                        },

                        body:
                            formData

                    }
                );


            const loginData =
                await loginResponse.json();


            if (!loginResponse.ok) {

                throw new Error(

                    loginData.detail ||
                    "E-mail ou senha incorretos."

                );

            }


            const token =
                loginData.access_token;


            // -----------------------------------------
            // REGISTRAR DISPOSITIVO
            // -----------------------------------------

            const deviceId =
                getDeviceId();


            const deviceResponse =
                await fetch(
                    `${API_URL}/api/device`,
                    {

                        method: "POST",

                        headers: {

                            "Content-Type":
                                "application/json",

                            "Authorization":
                                `Bearer ${token}`

                        },

                        body: JSON.stringify({

                            device_id:
                                deviceId

                        })

                    }
                );


            const deviceData =
                await deviceResponse.json();


            if (!deviceResponse.ok) {

                throw new Error(

                    deviceData.detail ||
                    "Este dispositivo não está autorizado."

                );

            }


            // -----------------------------------------
            // SALVAR SESSÃO
            // -----------------------------------------

            localStorage.setItem(
                "fluentemente_token",
                token
            );


            localStorage.setItem(
                "fluentemente_email",
                loginData.email
            );


            // -----------------------------------------
            // IR PARA O SITE
            // -----------------------------------------

            window.location.href =
                "/";

        }


        catch (error) {

            console.error(
                error
            );


            showError(
                error.message ||
                "Não foi possível entrar."
            );

        }


        finally {

            loginButton.disabled =
                false;


            buttonText.style.display =
                "inline";


            loading.style.display =
                "none";

        }

    }
);
