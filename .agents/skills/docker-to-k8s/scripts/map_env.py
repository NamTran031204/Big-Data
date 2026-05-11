#!/usr/bin/env python3
"""
map_env.py — Parse a Docker .env file with flag-comment sections
and generate Kubernetes Secret/ConfigMap YAML files.

Flag format in .env:
    #component-name
    KEY=value
    SECRET_KEY=secret_value

    #another-component
    OTHER_KEY=other_value

Usage:
    python map_env.py --env-file ./init/.env --output-dir ./k8s/secrets/
"""

import argparse
import base64
import os
import re
import sys
from pathlib import Path

# Keywords that indicate a value should be a Secret rather than ConfigMap
SENSITIVE_KEYWORDS = [
    "password", "secret", "key", "token", "credential",
    "passwd", "pwd", "api_key", "apikey", "access_key",
    "secret_key", "private_key", "auth"
]


def is_sensitive(key: str) -> bool:
    """Check if a key name suggests it holds sensitive data."""
    key_lower = key.lower()
    return any(kw in key_lower for kw in SENSITIVE_KEYWORDS)


def parse_env_file(env_path: str) -> dict:
    """
    Parse .env file into sections based on flag comments.

    Returns:
        {
            "postgres": {"POSTGRES_USER": "postgres", "POSTGRES_PASSWORD": "xxx"},
            "minio": {"MINIO_ROOT_USER": "admin", ...},
            ...
        }
    """
    sections = {}
    current_section = "default"

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check for flag comment: #component-name
            flag_match = re.match(r"^#(\w[\w-]*)$", line)
            if flag_match:
                current_section = flag_match.group(1).lower()
                if current_section not in sections:
                    sections[current_section] = {}
                continue

            # Skip regular comments (those with spaces after #, or explanatory)
            if line.startswith("#"):
                continue

            # Parse KEY=VALUE
            kv_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
            if kv_match:
                key = kv_match.group(1)
                value = kv_match.group(2).strip().strip('"').strip("'")
                if current_section not in sections:
                    sections[current_section] = {}
                sections[current_section][key] = value

    return sections


def generate_secret_yaml(component: str, data: dict, namespace: str = "bigdata") -> str:
    """Generate a Kubernetes Secret YAML string."""
    encoded = {}
    for k, v in data.items():
        encoded[k] = base64.b64encode(v.encode("utf-8")).decode("utf-8")

    lines = [
        "apiVersion: v1",
        "kind: Secret",
        "metadata:",
        f"  name: {component}-secret",
        f"  namespace: {namespace}",
        "  labels:",
        f"    app: {component}",
        "    part-of: bigdata",
        "type: Opaque",
        "data:",
    ]
    for k, v in encoded.items():
        lines.append(f"  {k}: {v}")

    return "\n".join(lines) + "\n"


def generate_configmap_yaml(component: str, data: dict, namespace: str = "bigdata") -> str:
    """Generate a Kubernetes ConfigMap YAML string."""
    lines = [
        "apiVersion: v1",
        "kind: ConfigMap",
        "metadata:",
        f"  name: {component}-config",
        f"  namespace: {namespace}",
        "  labels:",
        f"    app: {component}",
        "    part-of: bigdata",
        "data:",
    ]
    for k, v in data.items():
        lines.append(f"  {k}: \"{v}\"")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Map Docker .env variables to Kubernetes Secrets and ConfigMaps"
    )
    parser.add_argument(
        "--env-file",
        required=True,
        help="Path to the .env file with flag comments"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for generated YAML files"
    )
    parser.add_argument(
        "--namespace",
        default="bigdata",
        help="Kubernetes namespace (default: bigdata)"
    )

    args = parser.parse_args()

    # Validate input
    if not os.path.isfile(args.env_file):
        print(f"ERROR: .env file not found: {args.env_file}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse .env file
    sections = parse_env_file(args.env_file)

    if not sections:
        print("WARNING: No sections found in .env file. "
              "Make sure to use flag comments like #postgres, #minio, etc.")
        sys.exit(0)

    generated_files = []

    for component, variables in sections.items():
        if not variables:
            continue

        # Split into sensitive (Secret) and non-sensitive (ConfigMap)
        secret_vars = {}
        config_vars = {}
        for k, v in variables.items():
            if is_sensitive(k):
                secret_vars[k] = v
            else:
                config_vars[k] = v

        # Generate Secret YAML if there are sensitive vars
        if secret_vars:
            secret_yaml = generate_secret_yaml(component, secret_vars, args.namespace)
            secret_path = output_dir / f"{component}-secret.yaml"
            with open(secret_path, "w", encoding="utf-8") as f:
                f.write(secret_yaml)
            generated_files.append(str(secret_path))
            print(f"[OK] Secret:    {secret_path} ({len(secret_vars)} keys)")

        # Generate ConfigMap YAML if there are non-sensitive vars
        if config_vars:
            configmap_yaml = generate_configmap_yaml(component, config_vars, args.namespace)
            configmap_path = output_dir / f"{component}-configmap.yaml"
            with open(configmap_path, "w", encoding="utf-8") as f:
                f.write(configmap_yaml)
            generated_files.append(str(configmap_path))
            print(f"[OK] ConfigMap: {configmap_path} ({len(config_vars)} keys)")

    print(f"\n{'='*50}")
    print(f"  Generated {len(generated_files)} file(s) for {len(sections)} component(s)")
    print(f"  Output directory: {output_dir}")
    print(f"{'='*50}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
