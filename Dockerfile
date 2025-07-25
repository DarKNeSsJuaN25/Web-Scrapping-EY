FROM amazon/aws-lambda-python:3.12

# Eliminar curl-minimal antes de instalar dependencias
RUN dnf install -y \
    atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel nss mesa-libgbm jq unzip

# Copiar e instalar Chrome + ChromeDriver
COPY chrome-installer.sh ./chrome-installer.sh
RUN chmod +x chrome-installer.sh && ./chrome-installer.sh && rm ./chrome-installer.sh

# Instalar dependencias Python
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copiar el código fuente
COPY app.py ./

# Ejecutar Lambda
CMD [ "app.lambda_handler" ]
