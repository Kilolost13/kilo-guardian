## K3s Deploy Checklist

Use this PR template when adding or modifying `k3s/` manifests or automation.

- [ ] I have updated `k3s/README.md` with any host-specific instructions.
- [ ] I validated YAML with `kubectl apply --recursive --dry-run=client -f k3s/`.
- [ ] If persistent tokens are required, I documented how to create and store the token.

### Creating `KUBECONFIG_BASE64` (recommended for GitHub Actions)

1. On your K3s host, generate a kubeconfig with host IP accessible from GitHub Actions:

```bash
# replace <node-ip> where appropriate
cat /etc/rancher/k3s/k3s.yaml | sed "s/127.0.0.1/<node-ip>/" | base64 -w0 > k3s/kubeconfig_base64.txt
```

2. Add the contents of `k3s/kubeconfig_base64.txt` to the repository secret `KUBECONFIG_BASE64`.

3. If you are air-gapped and cannot add the secret, run `./k3s/deploy.sh` directly on the host instead.

### SKIP_PROMETHEUS (useful for air-gapped clusters)
- To skip Helm-based Prometheus install, set `SKIP_PROMETHEUS=true` on the host or in CI environment.

---

Please include any special notes about the changes and a short verification plan below:

- Verification steps:
  1. ...
  2. ...
