# nginx reverse proxy for einki

Runs as a Docker Compose service. Terminates TLS on port 443 and proxies
to the einki container on port 5000. HTTP requests on port 80 are
redirected to HTTPS.

## How it works

```
Internet
   │
   ├── :80  ──▶  nginx  ──▶  HTTP 301 → https://...
   └── :443 ──▶  nginx  ──▶  proxy_pass http://einki:5000
                  ▲
                  │ reads certs from shared Docker volume
                  │
          letsencrypt volume ◀── certbot / certbot-renew
```

### DuckDNS + Let's Encrypt + DNS-01

- **DuckDNS** provides a free `*.duckdns.org` subdomain that points to
  the server's IP. The `duckdns` container updates this every 5 minutes.
- **Let's Encrypt** issues free SSL certificates. The `certbot` container
  obtains the initial cert; the `certbot-renew` container keeps it fresh.
- **DNS-01 challenge**: certbot proves domain ownership by setting a TXT
  record via the DuckDNS HTTP API. This is done by two small shell scripts
  in `docker/certbot/hooks/` — just a `curl` call each. See
  [docker/certbot/README.md](../certbot/README.md) for details.
  Because DNS-01 doesn't need port 80, nginx doesn't need to be running
  during certificate issuance — avoiding the chicken-and-egg bootstrap
  problem.

### Certificate renewal

Renewal is fully automatic and Docker-managed:

1. The `certbot-renew` container runs a loop, attempting renewal every
   12 hours. Certbot only actually renews when the cert is within 30
   days of expiry (~every 60 days).
2. The `nginx` container reloads its config every 6 hours (via a
   background loop in its `command`), picking up any renewed certs.
   This is a zero-downtime operation.

No cron or systemd is needed.

## Configuration

`default.conf` is mounted read-only into the nginx container.
Edit it and restart the service to apply changes:

```bash
docker compose restart nginx
```

### Config walkthrough

The config has two `server` blocks:

1. **Port 80 (HTTP)** — returns `301 https://$host$request_uri` for all
   requests, sending browsers to the HTTPS version.

2. **Port 443 (HTTPS)** — terminates TLS and proxies to einki:
   - `ssl_certificate` / `ssl_certificate_key` — paths inside the
     `letsencrypt` volume managed by certbot
   - `ssl_protocols TLSv1.2 TLSv1.3` — only modern TLS versions
   - `ssl_prefer_server_ciphers on` — server chooses the cipher
   - `Strict-Transport-Security` header — tells browsers to always
     use HTTPS (HSTS, 1 year)
   - `proxy_pass http://einki:5000` — Docker DNS resolves the
     service name
   - `proxy_set_header` directives — pass original client info to Flask

## Troubleshooting

### nginx won't start: "cannot load certificate"

The SSL certificate hasn't been obtained yet. Run the bootstrap script:
```bash
./scripts/setup_https.sh
```

### Certificate renewal failures

Check the certbot-renew logs:
```bash
docker compose logs certbot-renew
```

Common causes:
- DuckDNS token expired or invalid
- Network issues preventing DNS API calls
- Let's Encrypt rate limits (5 duplicate certs/week)

To force a manual renewal:
```bash
docker compose --profile setup run --rm certbot renew
docker compose exec nginx nginx -s reload
```

### Testing with staging certificates

Let's Encrypt has rate limits. For testing, use staging certificates
by temporarily adding `--staging` to the certbot command in
`docker-compose.yml` (both `certbot` and `certbot-renew` services).

## Firewall

- Open: 80 (HTTP → HTTPS redirect), 443 (HTTPS)
- Close: 5000, 8765, 5900 (internal to Docker network)
