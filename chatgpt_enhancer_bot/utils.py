import os


def get_secrets():
    # Load the secrets from a file
    secrets = {}
    secrets_path = os.path.join(os.path.dirname(__file__), 'secrets.txt')
    with open(secrets_path, "r") as f:
        for line in f:
            key, value = line.strip().split(":", 1)
            secrets[key] = value
    return secrets
