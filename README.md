# Documentación - Diligencia de Proveedores - Api Web-Scraping
Este documento describe el servicio de web scraping que utiliza **AWS Lambda** con **Selenium** para recopilar información de diversas fuentes, así como su propio sistema de autenticación de usuarios. Este servicio es fundamental para los procesos de diligencia de proveedores.

# Visión General del Servicio

Este es un servicio de web scraping **serverless** diseñado para automatizar la extracción de datos de páginas web específicas. Además, incluye funcionalidades de autenticación y registro de usuarios gestionadas internamente.

## Tecnologías Usadas

- **AWS Lambda:** El servicio se ejecuta en funciones Lambda, lo que permite escalabilidad automática y pago por uso.
- **Python 3.10/3.12:** El lenguaje de programación utilizado para el desarrollo de las funciones Lambda.
- **Selenium WebDriver:** Herramienta utilizada para la automatización de navegadores web (simulando interacciones humanas para acceder y extraer datos de sitios dinámicos).
- **Chromium/ChromeDriver:** Una versión *headless* de Chrome que Selenium utiliza para navegar por las páginas web en el entorno Lambda.
- **AWS API Gateway:** Actúa como el punto de entrada HTTP para invocar las funciones Lambda desde el exterior.
- **AWS DynamoDB:** Base de datos NoSQL utilizada para almacenar las credenciales de los usuarios internos del servicio de scraping.
- **PyJWT:** Librería para la gestión de JSON Web Tokens (JWT) para la autenticación interna del servicio.
- **Bcrypt:** Para el hashing seguro de contraseñas de los usuarios internos.
- **BeautifulSoup4:** Para el parsing de HTML y la extracción de datos una vez que Selenium ha cargado la página.
- **Docker:** Utilizado para construir la imagen de la función Lambda, empaquetando Chrome, ChromeDriver y todas las dependencias de Python.
- **Serverless Framework:** Herramienta para el despliegue y gestión de la infraestructura serverless en AWS.

## Flujo de Operación

1. **Invocación Externa:** La **API del Backend** (tu API de Diligencia de Proveedores) o cualquier otro cliente envía una solicitud HTTP al **API Gateway**.
2. **Enrutamiento a Lambda:** **API Gateway** enruta la solicitud a la función **AWS Lambda** correspondiente (`scrape`, `login`, `register`, `validate`).
3. **Autenticación Interna (para `/scrape`):** Para el endpoint de scraping (`/scrape`), la función Lambda primero realiza una **validación de JWT** para asegurar que la solicitud proviene de un cliente autorizado (ej., tu backend).
4. **Lógica de Negocio:**
    1. **Para Scraping (`/scrape`):** La función inicializa **Selenium** con **Chromium**, navega a la URL objetivo (`https://projects.worldbank.org/en/projects-operations/procurement/debarred-firms`), interactúa con la página (espera elementos), extrae datos usando `BeautifulSoup4` y filtra por el `nombre` de la entidad.
    2. **Para Autenticación (`/login`, `/register`, `/validate`):** Las funciones interactúan con **DynamoDB** para almacenar o verificar credenciales de usuario y emiten/validan JWTs.
5. **Respuesta:** La función **Lambda** devuelve los resultados (datos scrapeados, token JWT, mensajes de éxito/error) al **API Gateway**.
6. **Retorno al Cliente:** **API Gateway** reenvía la respuesta HTTP de vuelta al cliente que realizó la solicitud.

# Configuración y Despliegue

El servicio se despliega en AWS utilizando el Serverless Framework y Docker para el empaquetado.

### Requisitos Previos

- **Cuenta AWS:** Con permisos para crear Lambda Functions, API Gateway, DynamoDB, ECR (Elastic Container Registry), IAM Roles.
- **AWS CLI:** Configurado y autenticado localmente.
- **Serverless Framework CLI:** Instalado globalmente (`npm install -g serverless`).
- **Docker:** Instalado y en ejecución localmente (necesario para construir la imagen de Lambda con Selenium/Chromium).
- **Python 3.10/3.12:** Entorno de desarrollo local.

### Configuración de Variables de Entorno (en AWS Lambda)

Las variables sensibles y configurables se gestionan como variables de entorno de Lambda, definidas en `serverless.yml`.

- `TABLE_NAME`: Nombre de la tabla de DynamoDB utilizada para almacenar usuarios (ej., `UsuariosTable`).
- `JWT_SECRET`: Clave secreta utilizada para firmar y verificar los JWTs internos del servicio. **¡Crucial para la seguridad! Debe ser una cadena larga y compleja.**

### Proceso de Despliegue

El despliegue se gestiona a través del Serverless Framework, que utiliza Docker para empaquetar la función Lambda como una imagen de contenedor.

1. **Construcción de la Imagen Docker:** El `Dockerfile` define el entorno de ejecución, instalando Chromium, ChromeDriver y todas las dependencias de Python desde `requirements.txt`.
2. **Empaquetado y Subida a ECR:** Serverless Framework utiliza Docker para construir la imagen localmente y luego la sube a Amazon Elastic Container Registry (ECR).
3. **Creación de Recursos AWS:** Serverless Framework lee el `serverless.yml` para provisionar:
    - Las funciones AWS Lambda (`scrape`, `register`, `login`, `validate`).
    - Los endpoints de API Gateway para cada función.
    - Las tablas DynamoDB (`UsuariosTable-dev`, `UsuariosTable-prod`, etc., según la etapa).
    - Los roles IAM necesarios para que Lambda acceda a otros servicios de AWS.
4. **Comando de Despliegue:** Desde la raíz del proyecto serverless, ejecuta:Bash
    
    ```bash
    sls deploy --stage dev
    # o para producción
    # sls deploy --stage prod
    ```
    
    - `--stage [nombre_de_la_etapa]`: Despliega la aplicación en la etapa especificada, cargando las variables de entorno correspondientes.

# Interacción con el Servicio (Endpoints)

El servicio expone varios endpoints a través de AWS API Gateway.

### Endpoint de Scraping

- **Propósito:** Realiza el web scraping en la URL predefinida ([https://projects.worldbank.org/en/projects-operations/procurement/debarred-firms](https://projects.worldbank.org/en/projects-operations/procurement/debarred-firms)) y busca una entidad específica. Requiere autenticación JWT.
- **Endpoint:**
    
    `GET /scrape`
    
- **Roles Requeridos (Internos):** El token JWT debe ser válido (emitido por el propio servicio de autenticación de este backend serverless).
- **Limitación de Tasa:** Este endpoint tiene una **limitación de 20 solicitudes por segundo (maxRequestsPerSecond)** y **5 solicitudes concurrentes (maxConcurrentRequests)**. Las solicitudes que excedan estos límites recibirán un error `429 Too Many Requests`.
- **Parámetros de Consulta (Query Parameters):**
    - `nombre` (string, **Requerido**): El nombre de la entidad/firma a buscar en la página web.
- **Ejemplo de Solicitud:**
    
    ```
    GET https://[id-api-gateway].execute-api.[region].amazonaws.com/dev/scrape?nombre=Example%20Firm
    ```
    
    - **Encabezado de Autorización:**
        
        `Authorization: Bearer <TOKEN_JWT_INTERNO>`
        
- **Ejemplo de Respuesta Exitosa**
    
    ```bash
    {
      "hits": 1,
      "resultados": [
        {
          "Firm Name": "Example Firm Ltd.",
          "Additional Info": "Subsidiary of XYZ Corp.",
          "Address": "123 Main St, City, Country",
          "Country": "United States",
          "From": "2023-01-01",
          "To": "2025-12-31",
          "Grounds": "Fraudulent practices"
        }
      ]
    }
    ```
    
- **Códigos de Error:**
    - `400 Bad Request`: Falta el parámetro `nombre`.
    - `401 Unauthorized`: Token JWT ausente, malformado o inválido/expirado.
    - `500 Internal Server Error`: Error durante el proceso de scraping (ej., timeout, error en la navegación, tabla no encontrada).

### Endpoint de Registro de Usuarios Internos

- **Propósito:** Registra un nuevo usuario para el servicio de scraping.
- **Endpoint:**
    
    `POST /register`
    
- **Body de Solicitud**
    
    ```json
    {
      "tenant_id": "ID_DE_TU_TENANT",
      "username": "nuevo_usuario_scraping",
      "password": "contraseña_segura"
    }
    ```
    
- **Ejemplo de Respuesta Exitosa:**
    
    ```json
    {
      "message": "Usuario creado exitosamente"
    }
    ```
    
- **Códigos de Error:**
    - `409 Conflict`: El usuario ya existe.
    - `500 Internal Server Error`: Error interno del servidor.

### Endpoint de Login de Usuarios Internos

- **Propósito:** Autentica un usuario interno y devuelve un token JWT para acceder a los endpoints protegidos del servicio (como `/scrape`).
- **Endpoint:**
    
    `POST /login`
    
- **Body de Solicitud:**
    
    ```json
    {
      "tenant_id": "ID_DE_TU_TENANT",
      "username": "usuario_existente",
      "password": "contraseña_del_usuario"
    }
    ```
    
- **Ejemplo de Respuesta Exitosa**
    
    ```json
    {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    
- **Códigos de Error:**
    - `401 Unauthorized`: Credenciales inválidas.
    - `500 Internal Server Error`: Error interno del servidor.

### Endpoint de Validación de Token Interno

- **Propósito:** Valida un token JWT emitido por este servicio.
- **Endpoint:**
    
    `GET /validate`
    
- **Encabezado de Autorización:**
    
    `Authorization: Bearer <TOKEN_JWT_INTERNO>`
    
- **Ejemplo de Solicitud:**
    
    ```
    GET https://[id-api-gateway].execute-api.[region].amazonaws.com/dev/validate
    ```
    
- **Ejemplo de Respuesta Exitosa:**
    
    ```json
    {
      "message": "Token válido",
      "payload": {
        "tenant_id": "ID_DE_TU_TENANT",
        "username": "usuario_validado",
        "exp": 1753634609
      }
    }
    ```
    
- **Códigos de Error:**
    - `401 Unauthorized`: Token requerido, expirado o inválido.

# Autenticación Interna del Servicio (JWT y DynamoDB)

Este servicio serverless implementa su propio sistema de autenticación para controlar el acceso a sus endpoints, especialmente al de scraping.

### Almacenamiento de Usuarios

- Las credenciales de usuario (tenant ID, username, password hasheado) se almacenan en una tabla de **AWS DynamoDB**. El nombre de la tabla incluye la etapa de despliegue (ej., `UsuariosTable-dev`, `UsuariosTable-prod`) para aislar los datos entre entornos.
- Las contraseñas se almacenan de forma segura utilizando **bcrypt**.

### Generación y Validación de JWT

- Al iniciar sesión (`/login`), el servicio genera un JWT firmado con `JWT_SECRET`. Esta clave se carga dinámicamente desde el archivo `env.{stage}.yml` correspondiente a la etapa de despliegue.
- Este token incluye el `tenant_id`, `username` y una fecha de expiración.
- Para acceder al endpoint `/scrape`, el token debe ser incluido en el encabezado `Authorization` y es validado por la función Lambda antes de proceder con el scraping.
- El endpoint `/validate` permite verificar la validez de un token JWT en cualquier momento.
