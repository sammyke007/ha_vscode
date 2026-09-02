"""Custom Exceptions for HAVSCode."""


class HAVSCodeException(Exception):
    """Super basic."""


class HAVSCodeAuthenticationException(HAVSCodeException):
    exception_message = (
        "The tunnel was not authenticated in the required time frame, "
        "please re-authorize the tunnel."
    )

    def __init__(self) -> None:
        super().__init__(self.exception_message)


class HAVSCodeDownloadException(HAVSCodeException):
    exception_message = (
        "Could not download or install the VS Code CLI. "
        "Check connectivity, architecture and directory permissions."
    )

    def __init__(self) -> None:
        super().__init__(self.exception_message)


class HAVSCodeZipException(HAVSCodeException):
    exception_message = "Unzip failed"

    def __init__(self) -> None:
        super().__init__(self.exception_message)


class HAVSCodeTarException(HAVSCodeException):
    exception_message = "Untar failed"

    def __init__(self) -> None:
        super().__init__(self.exception_message)
