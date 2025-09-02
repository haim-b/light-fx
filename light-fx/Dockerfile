ARG BUILD_FROM
FROM $BUILD_FROM

# Install required packages
RUN apk add --no-cache \
    python3 \
    py3-pip

# Copy root filesystem
COPY rootfs /

# Set workdir
WORKDIR /app

# Install pip requirements
COPY requirements.txt /app/
RUN pip3 install -r requirements.txt

# Make run script executable
RUN chmod a+x /app/run.sh

# Set entrypoint
ENTRYPOINT ["/app/run.sh"]
