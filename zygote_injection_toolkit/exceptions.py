class ZygoteInjectionException(Exception):
    pass

class ZygoteInjectionNotVulnerableException(ZygoteInjectionException):
    pass

class ZygoteInjectionCommandFailedException(ZygoteInjectionException):
    pass

class ZygoteInjectionConnectException(ZygoteInjectionException):
    pass

class ZygoteInjectionNoDeviceException(ZygoteInjectionConnectException):
    pass

class ZygoteInjectionMultipleDevicesException(ZygoteInjectionConnectException):
    pass

class ZygoteInjectionDeviceNotFoundException(ZygoteInjectionConnectException):
    pass
__all__ = ['ZygoteInjectionException', 'ZygoteInjectionNotVulnerableException', 'ZygoteInjectionCommandFailedException', 'ZygoteInjectionConnectException', 'ZygoteInjectionNoDeviceException', 'ZygoteInjectionMultipleDevicesException', 'ZygoteInjectionDeviceNotFoundException']