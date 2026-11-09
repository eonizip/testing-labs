# gencode1 — реализация от нейросети: ChatGPT
from lab.interfaces import IEmailValidator


class EmailValidator(IEmailValidator):
    _LOCAL_ALLOWED = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "._%+-"
    )

    _DOMAIN_ALLOWED = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "-."
    )

    def is_valid(self, email: str | None) -> bool:
        try:
            if not isinstance(email, str):
                return False

            if len(email) > 254:
                return False

            if any(ord(ch) > 127 or ord(ch) < 33 for ch in email):
                return False

            if email.count("@") != 1:
                return False

            local, domain = email.split("@")

            if not (1 <= len(local) <= 64):
                return False

            if local.startswith(".") or local.endswith("."):
                return False

            if ".." in local:
                return False

            if any(ch not in self._LOCAL_ALLOWED for ch in local):
                return False

            if not domain:
                return False

            if any(ch not in self._DOMAIN_ALLOWED for ch in domain):
                return False

            labels = domain.split(".")

            if len(labels) < 2:
                return False

            for label in labels:
                if not (1 <= len(label) <= 63):
                    return False

                if label.startswith("-") or label.endswith("-"):
                    return False

                if not all(
                    ("A" <= ch <= "Z")
                    or ("a" <= ch <= "z")
                    or ("0" <= ch <= "9")
                    or ch == "-"
                    for ch in label
                ):
                    return False

            tld = labels[-1]

            if len(tld) < 2:
                return False

            if not all(("A" <= ch <= "Z") or ("a" <= ch <= "z") for ch in tld):
                return False

            return True
        except Exception:
            return False

    def extract_domain(self, email: str | None) -> str:
        if not self.is_valid(email):
            raise ValueError("Invalid email")

        return email.split("@", 1)[1].lower()
