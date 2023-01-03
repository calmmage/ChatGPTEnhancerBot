import os
import random


def get_secrets():
    # Load the secrets from a file
    secrets = {}
    secrets_path = os.path.join(os.path.dirname(__file__), 'secrets.txt')
    with open(secrets_path, "r") as f:
        for line in f:
            key, value = line.strip().split(":", 1)
            secrets[key] = value
    return secrets


reasons_path = os.path.join(os.path.dirname(__file__), 'resources/reasons.txt')
reasons = open(reasons_path).read().splitlines()
consolations_path = os.path.join(os.path.dirname(__file__), 'resources/consolations.txt')
consolations = open(consolations_path).read().splitlines()


def generate_funny_reason():
    return random.choice(reasons)


def generate_funny_consolation():
    return random.choice(consolations)
