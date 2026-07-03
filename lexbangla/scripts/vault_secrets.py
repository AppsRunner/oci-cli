#!/usr/bin/env python3
"""
OCI Vault helper — fetches current secret versions and rotates them.

Usage:
    # Inject secrets into the environment at container startup:
    eval "$(python scripts/vault_secrets.py export)"

    # Rotate a specific secret (creates a new version in OCI Vault):
    python scripts/vault_secrets.py rotate --name lexbangla-django-secret-key

Environment variables required:
    OCI_CONFIG_FILE      path to ~/.oci/config  (default: ~/.oci/config)
    OCI_CONFIG_PROFILE   profile name            (default: DEFAULT)
    OCI_VAULT_VAULT_ID   OCID of the OCI Vault
    OCI_VAULT_COMPARTMENT_ID  compartment OCID
"""

import argparse
import base64
import json
import logging
import os
import secrets
import string
import sys

import oci

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _oci_config() -> dict:
    config_file = os.environ.get("OCI_CONFIG_FILE", os.path.expanduser("~/.oci/config"))
    profile = os.environ.get("OCI_CONFIG_PROFILE", "DEFAULT")
    return oci.config.from_file(config_file, profile)


def _secrets_client(config: dict) -> oci.secrets.SecretsClient:
    return oci.secrets.SecretsClient(config)


def _vaults_client(config: dict) -> oci.vault.VaultsClient:
    return oci.vault.VaultsClient(config)


def get_secret_value(client: oci.secrets.SecretsClient, secret_name: str, vault_id: str, compartment_id: str) -> str:
    """Return the current plaintext value of a named secret."""
    vaults = oci.vault.VaultsClient(_oci_config())
    secrets_list = vaults.list_secrets(
        compartment_id=compartment_id,
        vault_id=vault_id,
        name=secret_name,
    ).data

    if not secrets_list:
        raise ValueError(f"Secret '{secret_name}' not found in vault {vault_id}")

    secret_id = secrets_list[0].id
    bundle = client.get_secret_bundle(secret_id).data
    raw = bundle.secret_bundle_content.content
    return base64.b64decode(raw).decode("utf-8")


def export_secrets(vault_id: str, compartment_id: str) -> None:
    """Print export statements for each known secret."""
    config = _oci_config()
    client = _secrets_client(config)

    secret_map: dict[str, str] = json.loads(
        os.environ.get(
            "VAULT_SECRET_MAP",
            json.dumps(
                {
                    "DJANGO_SECRET_KEY": "lexbangla-django-secret-key",
                    "DB_PASSWORD": "lexbangla-db-password",
                }
            ),
        )
    )

    for env_var, secret_name in secret_map.items():
        try:
            value = get_secret_value(client, secret_name, vault_id, compartment_id)
            safe = value.replace("'", "'\\''")
            print(f"export {env_var}='{safe}'")
        except Exception as exc:
            logger.error("Failed to fetch secret %s: %s", secret_name, exc)
            sys.exit(1)


def rotate_secret(vault_id: str, compartment_id: str, secret_name: str) -> None:
    """Create a new secret version with a fresh random value."""
    config = _oci_config()
    vaults = _vaults_client(config)

    secrets_list = vaults.list_secrets(
        compartment_id=compartment_id,
        vault_id=vault_id,
        name=secret_name,
    ).data

    if not secrets_list:
        raise ValueError(f"Secret '{secret_name}' not found")

    secret_id = secrets_list[0].id

    # Generate a cryptographically random 64-char secret
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    new_value = "".join(secrets.choice(alphabet) for _ in range(64))
    encoded = base64.b64encode(new_value.encode()).decode()

    vaults.update_secret(
        secret_id=secret_id,
        update_secret_details=oci.vault.models.UpdateSecretDetails(
            secret_content=oci.vault.models.Base64SecretContentDetails(
                content_type=oci.vault.models.SecretContentDetails.CONTENT_TYPE_BASE64,
                content=encoded,
            )
        ),
    )
    logger.info("Rotated secret '%s' (new version created in OCI Vault)", secret_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="OCI Vault secret manager for LexBangla")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("export", help="Print export statements for all secrets")

    rot = sub.add_parser("rotate", help="Rotate a named secret")
    rot.add_argument("--name", required=True, help="Secret name in OCI Vault")

    args = parser.parse_args()

    vault_id = os.environ["OCI_VAULT_VAULT_ID"]
    compartment_id = os.environ["OCI_VAULT_COMPARTMENT_ID"]

    if args.command == "export":
        export_secrets(vault_id, compartment_id)
    elif args.command == "rotate":
        rotate_secret(vault_id, compartment_id, args.name)


if __name__ == "__main__":
    main()
