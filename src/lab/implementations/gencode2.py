# gencode2 — реализация от нейросети: DeepSeek
from lab.interfaces import IEmailValidator


class EmailValidator(IEmailValidator):
    _LOCAL_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._%+-")
    _DOMAIN_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-")
    _LETTERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")

    def is_valid(self, email: str | None) -> bool:
        if not isinstance(email, str):
            return False

        if len(email) > 254:
            return False

        if email.count("@") != 1:
            return False

        local, domain = email.split("@", 1)

        if not self._is_valid_local(local):
            return False

        if not self._is_valid_domain(domain):
            return False

        return True

    def extract_domain(self, email: str | None) -> str:
        if not self.is_valid(email):
            raise ValueError("Invalid email")
        return email.split("@", 1)[1].lower()

    def _is_valid_local(self, local: str) -> bool:
        if not (1 <= len(local) <= 64):
            return False

        if local[0] == "." or local[-1] == ".":
            return False

        if ".." in local:
            return False

        for ch in local:
            if ch not in self._LOCAL_CHARS:
                return False

        return True

    def _is_valid_domain(self, domain: str) -> bool:
        if not domain:
            return False

        labels = domain.split(".")

        if len(labels) < 2:
            return False

        for label in labels:
            if not (1 <= len(label) <= 63):
                return False

            if label[0] == "-" or label[-1] == "-":
                return False

            for ch in label:
                if ch not in self._DOMAIN_CHARS:
                    return False

        tld = labels[-1]

        if len(tld) < 2:
            return False

        for ch in tld:
            if ch not in self._LETTERS:
                return False

        return True
