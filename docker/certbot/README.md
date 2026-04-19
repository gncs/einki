# certbot with DuckDNS hooks

Thin wrapper around the [official certbot image](https://hub.docker.com/r/certbot/certbot)
that adds two shell scripts for DuckDNS DNS-01 challenges.

## How it works

Let's Encrypt needs to verify you own the domain before issuing a
certificate. The DNS-01 challenge does this by asking you to create a
specific TXT record on your domain.

DuckDNS exposes a simple HTTP API for setting TXT records:
```
https://www.duckdns.org/update?domains=SUBDOMAIN&token=TOKEN&txt=VALUE
```

Certbot's `--manual` mode calls external scripts at two points:

1. **`hooks/auth-hook.sh`** — called *before* verification. Sets the TXT
   record on DuckDNS with the ACME challenge token, then waits 60 seconds
   for DNS propagation.

2. **`hooks/cleanup-hook.sh`** — called *after* verification. Clears the
   TXT record (good hygiene).

## Files

```
docker/certbot/
├── Dockerfile        # FROM certbot/certbot, copies hooks into image
├── README.md         # this file
└── hooks/
    ├── auth-hook.sh      # sets DuckDNS TXT record (3 lines of curl)
    └── cleanup-hook.sh   # clears DuckDNS TXT record (1 line of curl)
```

## Usage

This image is used by two services in `docker-compose.yml`:

- **`certbot`** (profile: setup) — obtains the initial certificate
- **`certbot-renew`** — always running, renews certificates every 12 hours
