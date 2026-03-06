# Kubernetes Troubleshooting Reference

Use this file for targeted diagnostics after baseline checks.

## CrashLoopBackOff

```bash
/usr/local/bin/kubectl --kubeconfig <cfg> get pods -n <ns>
/usr/local/bin/kubectl --kubeconfig <cfg> describe pod <pod> -n <ns>
/usr/local/bin/kubectl --kubeconfig <cfg> logs <pod> -n <ns> --previous --tail=200
/usr/local/bin/kubectl --kubeconfig <cfg> logs <pod> -n <ns> --tail=200
```

Focus on restart count, last termination reason, probe failures, and app boot errors.

## ImagePullBackOff or ErrImagePull

```bash
/usr/local/bin/kubectl --kubeconfig <cfg> describe pod <pod> -n <ns>
/usr/local/bin/kubectl --kubeconfig <cfg> get secret -n <ns>
```

Check image tag, imagePullSecrets, registry auth, and network reachability.

## Pending Pod

```bash
/usr/local/bin/kubectl --kubeconfig <cfg> describe pod <pod> -n <ns>
/usr/local/bin/kubectl --kubeconfig <cfg> get nodes -o wide
/usr/local/bin/kubectl --kubeconfig <cfg> top nodes
```

Check insufficient CPU/memory, taints and tolerations, node selectors, and PVC binding.

## Service Not Reachable

```bash
/usr/local/bin/kubectl --kubeconfig <cfg> get svc -n <ns>
/usr/local/bin/kubectl --kubeconfig <cfg> get endpoints -n <ns>
/usr/local/bin/kubectl --kubeconfig <cfg> get pods -n <ns> -o wide
```

Check selector mismatch, empty endpoints, targetPort mismatch, and pod readiness.

## Ingress Issues

```bash
/usr/local/bin/kubectl --kubeconfig <cfg> get ingress -n <ns>
/usr/local/bin/kubectl --kubeconfig <cfg> describe ingress <name> -n <ns>
/usr/local/bin/kubectl --kubeconfig <cfg> get svc -n <ingress-controller-ns>
```

Check ingress class, host/path rules, controller status, and backend service mapping.

## Rollout Stuck

```bash
/usr/local/bin/kubectl --kubeconfig <cfg> rollout status deployment/<name> -n <ns>
/usr/local/bin/kubectl --kubeconfig <cfg> describe deployment <name> -n <ns>
/usr/local/bin/kubectl --kubeconfig <cfg> get rs -n <ns>
```

Check unavailable replicas, failing probes, and blocked image pulls.
