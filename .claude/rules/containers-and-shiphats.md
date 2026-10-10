---
paths:
  - "Dockerfile*"
  - ".dockerignore"
  - "**/*.shiphats"
  - "activate-shiphats.sh"
  - ".gitlab/**"
---

# Sandbox Containers & Inert SHIP-HATS Rules

- **Contextualise `initial-templates/` — never copy blind.** Bind the server to **`0.0.0.0:3000`** (`HOST=0.0.0.0`, `PORT=3000`, `EXPOSE 3000`), run as an unprivileged **numeric `USER`** (e.g. `65532:65532` for `runAsNonRoot`), pin base images by exact version + digest (never `latest`), include a `HEALTHCHECK` (subcommand in distroless Go/Rust images where no shell/curl exists), and keep `.env*`, `.git`, `node_modules`, and build artefacts out via `.dockerignore` while preserving `viper-agent/`.
- **Trust reverse proxies by CIDR (`127.0.0.0/8`, RFC1918, link-local), never by hop count** (Fastify 5.12 treats a bare hop count unexpectedly; trusting all hops lets clients spoof `X-Forwarded-For`).
- **Keep SHIP-HATS pipeline files inert (`*.shiphats`) from day one** (`.gitlab-ci.yml.shiphats`, `.gitlab/ci/*.shiphats`, `sonar-project.properties.shiphats`, `.gitlab/CODEOWNERS.shiphats`, MR template) using `@@SHIPHATS_<NAME>@@` placeholders — **never secrets**.
- **2026 SHIP-HATS platform constraints to preserve:**
  - Pin `ship-hats-templates` literal ref (`>= v1.1.12` post-Rekor decommissioning); keep canonical stage names (`.pre`, `build`, `test`, `static-test`, `sign`, `runtime-test`) and job names (`build-job`, `deploy-prod-manual-job` / `deploy-final-job`).
  - Build container images with **Kaniko** (not Docker-in-Docker) on `ship_docker` runners; respect Nexus Repository proxy URLs and **Nexus IQ's 7-day minimum component age gate** (pin dependencies >= 7 days old; Trivy `>= 0.69.3`; no EOL base images).
  - Keep `activate-shiphats.sh` Bash 3.2-compatible and in lockstep with local test/lint gates.
