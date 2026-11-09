"""Read-only Windows counters and HWiNFO shared sensors; never a Core dependency."""
import ctypes as C
from ctypes import wintypes as W
import json
import math
import struct
import time

K = C.WinDLL('kernel32', use_last_error=True)


def bind(dll, name, args, result=W.BOOL):
    fn = getattr(dll, name)
    fn.argtypes, fn.restype = args, result
    return fn


get_topology = bind(K, 'GetLogicalProcessorInformationEx', [W.DWORD, C.c_void_p, C.POINTER(W.DWORD)])
close = bind(K, 'CloseHandle', [W.HANDLE])
current_process = bind(K, 'GetCurrentProcess', [], W.HANDLE)
affinity = bind(K, 'SetProcessAffinityMask', [W.HANDLE, C.c_size_t])


def topology():
    length = W.DWORD()
    get_topology(0, None, C.byref(length))
    buffer = C.create_string_buffer(length.value)
    if not get_topology(0, buffer, C.byref(length)):
        raise C.WinError(C.get_last_error())
    result, offset = [], 0
    while offset < length.value:
        relation, size = struct.unpack_from('<II', buffer, offset)
        assert relation == 0 and size >= 48
        flags, efficiency = struct.unpack_from('<BB', buffer, offset+8)
        groups = struct.unpack_from('<H', buffer, offset+30)[0]
        assert groups == 1
        mask, group = struct.unpack_from('<QH', buffer, offset+32)
        assert group == 0, 'multi-group host requires an explicit reviewed affinity policy'
        result.append(dict(core=len(result), efficiency_class=efficiency, smt=bool(flags & 1),
                           group=group, mask=mask, logical=[i for i in range(64) if mask >> i & 1]))
        offset += size
    assert offset == length.value
    return result


class PowerStatus(C.Structure):
    _fields_ = [('ac', W.BYTE), ('battery_flags', W.BYTE), ('battery_percent', W.BYTE),
                ('saver', W.BYTE), ('remaining_s', W.DWORD), ('full_s', W.DWORD)]


get_power = bind(K, 'GetSystemPowerStatus', [C.POINTER(PowerStatus)])
get_times = bind(K, 'GetSystemTimes', [C.POINTER(W.FILETIME)]*3)
get_process_times = bind(K, 'GetProcessTimes', [W.HANDLE]+[C.POINTER(W.FILETIME)]*4)
open_process = bind(K, 'OpenProcess', [W.DWORD, W.BOOL, W.DWORD], W.HANDLE)


def filetime(value):
    return (value.dwHighDateTime << 32) | value.dwLowDateTime


def system_ticks():
    values = [W.FILETIME() for _ in range(3)]
    if not get_times(*(C.byref(v) for v in values)):
        raise C.WinError(C.get_last_error())
    return tuple(filetime(v) for v in values)


class FmtUnion(C.Union):
    _fields_ = [('double', C.c_double), ('large', C.c_longlong)]


class FmtValue(C.Structure):
    _fields_ = [('status', W.DWORD), ('value', FmtUnion)]


class Counters:
    def __init__(self, logical):
        pdh = C.WinDLL('pdh')
        self.open = bind(pdh, 'PdhOpenQueryW', [W.LPCWSTR, C.c_size_t, C.POINTER(W.HANDLE)], W.LONG)
        self.add = bind(pdh, 'PdhAddEnglishCounterW', [W.HANDLE, W.LPCWSTR, C.c_size_t, C.POINTER(W.HANDLE)], W.LONG)
        self.collect = bind(pdh, 'PdhCollectQueryData', [W.HANDLE], W.LONG)
        self.format = bind(pdh, 'PdhGetFormattedCounterValue', [W.HANDLE, W.DWORD, C.POINTER(W.DWORD), C.POINTER(FmtValue)], W.LONG)
        self.close = bind(pdh, 'PdhCloseQuery', [W.HANDLE], W.LONG)
        self.query = W.HANDLE()
        assert self.open(None, 0, C.byref(self.query)) == 0
        self.items, self.errors = {}, {}
        names = {'frequency_mhz': 'Processor Frequency', 'performance_pct': '% Processor Performance',
                 'utility_pct': '% Processor Utility', 'processor_busy_pct': '% Processor Time',
                 'performance_limit_pct': '% Performance Limit'}
        for name, counter in names.items():
            handle = W.HANDLE()
            error = self.add(self.query, f'\\Processor Information(0,{logical})\\{counter}', 0, C.byref(handle))
            if error:
                self.errors[name] = error & 0xffffffff
            else:
                self.items[name] = handle
        self.collect(self.query)

    def sample(self):
        result = {'pdh_collect_status': self.collect(self.query) & 0xffffffff}
        for name, handle in self.items.items():
            value = FmtValue()
            error = self.format(handle, 0x200 | 0x8000, None, C.byref(value))
            result[name+'_status'] = (error & 0xffffffff) or value.status
            result[name] = value.value.double if not error and value.status in (0, 1) and math.isfinite(value.value.double) else ''
        return result

    def finish(self):
        self.close(self.query)


class Hwinfo:
    """Read the published packed HWiNFO SM2 layout with its mutex held briefly.

    Layout reference: HWiNFO SDK hwisenssm2.h; section offsets/strides are
    validated at runtime. Original labels are used, not renamed user labels.
    No driver, bypass, shared-memory write or remote sensor access is used.
    """
    def __init__(self):
        self.open_map = bind(K, 'OpenFileMappingW', [W.DWORD, W.BOOL, W.LPCWSTR], W.HANDLE)
        self.map_view = bind(K, 'MapViewOfFile', [W.HANDLE, W.DWORD, W.DWORD, W.DWORD, C.c_size_t], C.c_void_p)
        self.unmap = bind(K, 'UnmapViewOfFile', [C.c_void_p])
        self.open_mutex = bind(K, 'OpenMutexW', [W.DWORD, W.BOOL, W.LPCWSTR], W.HANDLE)
        self.wait = bind(K, 'WaitForSingleObject', [W.HANDLE, W.DWORD], W.DWORD)
        self.release = bind(K, 'ReleaseMutex', [W.HANDLE])
        self.mapping = self.open_map(4, False, 'Global\\HWiNFO_SENS_SM2')
        self.error = 0 if self.mapping else C.get_last_error()
        self.pointer = self.map_view(self.mapping, 4, 0, 0, 0) if self.mapping else None
        if self.mapping and not self.pointer:
            self.error = C.get_last_error()
        self.mutex = self.open_mutex(0x100001, False, 'Global\\HWiNFO_SM2_MUTEX') if self.pointer else None
        if self.pointer and not self.mutex:
            self.error = C.get_last_error()
        self.last_poll = None

    def sample(self):
        if not self.pointer or not self.mutex:
            return dict(status='unavailable', winerror=self.error), []
        status = self.wait(self.mutex, 20)
        if status not in (0, 0x80):
            return dict(status='mutex_timeout', winerror=status), []
        try:
            header = C.string_at(self.pointer, 48)
            signature, version, revision, poll, so, ss, sn, ro, rs, rn = struct.unpack_from('<IIIqIIIIII', header)
            assert signature in (0x53695748, 0x48576953) and version in (1, 2), 'inactive or unsupported HWiNFO layout'
            assert ss >= 264 and rs >= 316 and sn < 10000 and rn < 100000
            end = max(so+ss*sn, ro+rs*rn)
            assert 44 <= so < end <= 64*1024*1024 and 44 <= ro < end
            data = C.string_at(self.pointer, end)
        finally:
            self.release(self.mutex)
        period = struct.unpack_from('<I', header, 44)[0] if revision >= 1 else None
        meta = dict(status='available', version=version, revision=revision, poll_time_s=poll, polling_period_ms=period)
        readings = []
        def label(blob):
            return blob.split(b'\0', 1)[0].decode('utf-8', errors='replace')
        for i in range(rn):
            row = data[ro+i*rs:ro+(i+1)*rs]
            kind, sensor, ident = struct.unpack_from('<III', row)
            assert sensor < sn
            sensor_row = data[so+sensor*ss:so+(sensor+1)*ss]
            name = label(sensor_row[8:136])
            if not name.startswith('CPU'):
                continue
            title, unit = label(row[12:140]), label(row[268:284])
            if kind not in (1, 5, 6, 7) and not any(t in title.lower() for t in ('throttl', 'limit', 'thermal')):
                continue
            value = struct.unpack_from('<d', row, 284)[0]
            if not math.isfinite(value):
                continue
            sid, instance = struct.unpack_from('<II', sensor_row)
            readings.append(dict(sensor_id=sid, instance=instance, reading_id=ident, kind=kind,
                                 sensor=name, label=title, unit=unit, value=value))
        return meta, readings

    def finish(self):
        if self.pointer:
            self.unmap(self.pointer)
        for handle in (self.mapping, self.mutex):
            if handle:
                close(handle)


if __name__ == '__main__':
    cores = topology()
    logical = min(i for c in cores if c['efficiency_class'] == max(x['efficiency_class'] for x in cores) for i in c['logical'])
    hw = Hwinfo()
    meta, readings = hw.sample()
    counters = Counters(logical)
    time.sleep(.2)
    print(json.dumps(dict(topology=cores, selected_logical=logical, pdh=counters.sample(),
                          hwinfo=meta, sensors=readings), indent=2))
    hw.finish()
    counters.finish()
