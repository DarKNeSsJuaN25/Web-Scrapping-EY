import json
import time
import os
from tempfile import mkdtemp

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

# Clave secreta compartida con los endpoints de login/register
SECRET_KEY = os.environ["JWT_SECRET"]

def verificar_token(headers):
    auth_header = headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise InvalidTokenError("Missing or malformed Authorization header")

    token = auth_header.split(" ")[1]
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded
    except ExpiredSignatureError:
        raise InvalidTokenError("Token has expired")
    except InvalidTokenError:
        raise InvalidTokenError("Invalid token")

def initialise_driver():
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument(f"--user-data-dir={mkdtemp()}")
    chrome_options.add_argument(f"--data-path={mkdtemp()}")
    chrome_options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    chrome_options.add_argument("--remote-debugging-pipe")
    chrome_options.binary_location = "/opt/chrome/chrome-linux64/chrome"

    service = Service(
        executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
        service_log_path="/tmp/chromedriver.log"
    )

    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(15)
    return driver

def lambda_handler(event, context):
    # Autenticación JWT
    try:
        headers = event.get("headers", {})
        user_info = verificar_token(headers)
        print("Usuario autenticado:", user_info["username"])
    except InvalidTokenError as e:
        return {
            "statusCode": 401,
            "body": json.dumps({"error": str(e)})
        }

    # Parámetros de entrada
    params = event.get('queryStringParameters') or {}
    nombre_entidad = params.get('nombre')

    if not nombre_entidad:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Falta el parámetro 'nombre'"})
        }

    driver = initialise_driver()

    try:
        url = "https://projects.worldbank.org/en/projects-operations/procurement/debarred-firms"
        print("Cargando página...")
        driver.get(url)

        print("Esperando el elemento...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#k-debarred-firms tbody tr td"))
        )

        print("Elemento encontrado, parseando HTML...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tabla = soup.find("div", {"id": "k-debarred-firms"})

        if not tabla:
            print("No se encontró la tabla.")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "hits": 0,
                    "resultados": [],
                    "warning": "No se encontró la tabla en la página"
                })
            }

        filas = tabla.find_all("tr")
        data = []

        print("Firmas encontradas:")
        for fila in filas:
            celdas = fila.find_all("td")
            if len(celdas) == 7:
                fila_datos = [c.text.strip() for c in celdas]
                print(f"- {fila_datos[0]}")
                if nombre_entidad.lower() in fila_datos[0].lower():
                    data.append({
                        "Firm Name": fila_datos[0],
                        "Additional Info": fila_datos[1],
                        "Address": fila_datos[2],
                        "Country": fila_datos[3],
                        "From": fila_datos[4],
                        "To": fila_datos[5],
                        "Grounds": fila_datos[6]
                    })

        print(f"Scraping completo. Resultados encontrados: {len(data)}")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "hits": len(data),
                "resultados": data
            })
        }

    except Exception as e:
        print(f"Error en scraping: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    finally:
        driver.quit()

