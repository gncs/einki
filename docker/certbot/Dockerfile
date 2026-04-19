FROM certbot/certbot:latest

# The official certbot image is Alpine-based and doesn't include curl.
# Our DuckDNS hook scripts need it to call the DuckDNS API.
RUN apk add --no-cache curl

# Copy the DuckDNS hook scripts into the image.
# These are called by certbot's --manual mode during DNS-01 challenges:
#   auth-hook.sh    — sets the TXT record on DuckDNS before verification
#   cleanup-hook.sh — clears the TXT record after verification
COPY hooks/ /opt/duckdns-hooks/
