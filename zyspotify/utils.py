class FormatUtils:
    """Utility class for string formatting and sanitization."""

    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    RESET = "\033[0m"

    def sanitize_data(value: str) -> str:
        """Returns the string with problematic characters removed."""
        SANITIZE_CHARS = ["\\", "/", ":", "*", "?", "'", "<", ">", '"', "|"]

        for char in SANITIZE_CHARS:
            value = value.replace(char, "" if char != "|" else "-")
        return value
