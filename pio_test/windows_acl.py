"""Read-only Windows DACL inspection through system DLLs, no shell or installs.

Require owner=current user, a non-null DACL, and only explicit/inherited allow
ACEs for current user or LocalSystem. IPC root must protect its DACL. Unsupported
ACE forms fail closed. Windows integration still requires local validation.
"""
import ctypes as c
from ctypes import wintypes as w

from .errors import require


def check_private_acl(path, directory):
    adv = c.WinDLL('advapi32', use_last_error=True)
    kernel = c.WinDLL('kernel32', use_last_error=True)
    pointer = c.c_void_p
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    adv.OpenProcessToken.restype = w.BOOL
    adv.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, pointer, w.DWORD, c.POINTER(w.DWORD)]
    adv.GetTokenInformation.restype = w.BOOL
    adv.ConvertSidToStringSidW.argtypes = [pointer, c.POINTER(pointer)]
    adv.ConvertSidToStringSidW.restype = w.BOOL
    adv.GetNamedSecurityInfoW.argtypes = [w.LPWSTR, c.c_int, w.DWORD,
                                         c.POINTER(pointer), pointer, c.POINTER(pointer), pointer, c.POINTER(pointer)]
    adv.GetNamedSecurityInfoW.restype = w.DWORD
    adv.GetSecurityDescriptorControl.argtypes = [pointer, c.POINTER(w.WORD), c.POINTER(w.DWORD)]
    adv.GetSecurityDescriptorControl.restype = w.BOOL
    adv.GetAce.argtypes = [pointer, w.DWORD, c.POINTER(pointer)]
    adv.GetAce.restype = w.BOOL
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer
    kernel.CloseHandle.argtypes = [w.HANDLE]

    def sid_text(sid):
        output = pointer()
        require(bool(adv.ConvertSidToStringSidW(sid, c.byref(output))), 'ACL_INSPECTION_FAILED')
        try:
            return c.wstring_at(output)
        finally:
            kernel.LocalFree(output)

    token = w.HANDLE()
    require(bool(adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, c.byref(token))), 'ACL_INSPECTION_FAILED')
    try:
        size = w.DWORD()
        adv.GetTokenInformation(token, 1, None, 0, c.byref(size))
        require(0 < size.value < 65536, 'ACL_INSPECTION_FAILED')
        data = c.create_string_buffer(size.value)
        require(bool(adv.GetTokenInformation(token, 1, data, size, c.byref(size))), 'ACL_INSPECTION_FAILED')
        current = sid_text(c.cast(data, c.POINTER(pointer))[0])
    finally:
        kernel.CloseHandle(token)

    class ACL(c.Structure):
        _fields_ = [('revision', w.BYTE), ('reserved', w.BYTE), ('size', w.WORD),
                    ('count', w.WORD), ('reserved2', w.WORD)]

    descriptor, owner, dacl = pointer(), pointer(), pointer()
    result = adv.GetNamedSecurityInfoW(str(path), 1, 5, c.byref(owner), None,
                                      c.byref(dacl), None, c.byref(descriptor))
    require(result == 0, 'ACL_INSPECTION_FAILED')
    try:
        require(owner.value and dacl.value and sid_text(owner) == current, 'PRIVATE_PERMISSIONS_REQUIRED')
        control, revision = w.WORD(), w.DWORD()
        require(bool(adv.GetSecurityDescriptorControl(descriptor, c.byref(control), c.byref(revision))), 'ACL_INSPECTION_FAILED')
        if directory:
            require(control.value & 0x1000, 'PRIVATE_PERMISSIONS_REQUIRED')
        acl = c.cast(dacl, c.POINTER(ACL)).contents
        require(0 < acl.count <= 32, 'PRIVATE_PERMISSIONS_REQUIRED')
        for index in range(acl.count):
            ace = pointer()
            require(bool(adv.GetAce(dacl, index, c.byref(ace))), 'ACL_INSPECTION_FAILED')
            # ACCESS_ALLOWED_ACE: 4-byte header, 4-byte mask, then SID.
            require(c.c_ubyte.from_address(ace.value).value == 0, 'PRIVATE_PERMISSIONS_REQUIRED')
            require(sid_text(ace.value + 8) in (current, 'S-1-5-18'), 'PRIVATE_PERMISSIONS_REQUIRED')
    finally:
        kernel.LocalFree(descriptor)
