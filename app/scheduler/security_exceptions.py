"""安全验证模块异常类"""

class SecurityError(Exception):
    """安全验证错误"""

    def __init__(self, message: str, code: str = "SECURITY_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)