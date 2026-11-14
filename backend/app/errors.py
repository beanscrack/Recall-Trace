"""Precondition failures in replay/court. main.py maps these to 409; anything else stays a 500."""


class Conflict(Exception):
    pass
