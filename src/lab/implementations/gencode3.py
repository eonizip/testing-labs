# gencode3 — реализация от нейросети: Claude
import string

from lab.interfaces import IEmailValidator

_ALNUM = set(string.ascii_letters + string.digits)
_LOCAL_OK = _ALNUM | set("._%+-")
_LABEL_OK = _ALNUM | {"-"}
_LETTERS = set(string.ascii_letters)


# Реализация от Claude (GenCode3)
class EmailValidator(IEmailValidator):
    def is_valid(self, email: str | None) -> bool:
        if not isinstance(email, str) or not email or len(email) > 254:
            return False
        if email.count("@") != 1:
            return False
        local, domain = email.split("@")
        return self._valid_local(local) and self._valid_domain(domain)

    def extract_domain(self, email: str | None) -> str:
        if not self.is_valid(email):
            raise ValueError("Некорректный email")
        return email.split("@")[1].lower()

    @staticmethod
    def _valid_local(s: str) -> bool:
        if not 1 <= len(s) <= 64:
            return False
        if s[0] == "." or s[-1] == "." or ".." in s:
            return False
        return all(c in _LOCAL_OK for c in s)

    @staticmethod
    def _valid_domain(s: str) -> bool:
        labels = s.split(".")
        if len(labels) < 2:
            return False
        for label in labels:
            if not 1 <= len(label) <= 63:
                return False
            if label[0] == "-" or label[-1] == "-":
                return False
            if not all(c in _LABEL_OK for c in label):
                return False
        tld = labels[-1]
        return len(tld) >= 2 and all(c in _LETTERS for c in tld)
