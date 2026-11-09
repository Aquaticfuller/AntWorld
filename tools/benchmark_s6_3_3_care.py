"""Windows diagnostic care smoke timing/memory; not the controlled <=6x qualification."""
import argparse,csv,ctypes as C,json,subprocess,time
from pathlib import Path
class Memory(C.Structure):
    _fields_=[('cb',C.c_ulong),('faults',C.c_ulong)]+[(name,C.c_size_t) for name in ['peak','resident','paged_peak','paged','nonpaged_peak','nonpaged','pagefile','pagefile_peak']]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    k=C.WinDLL('kernel32',use_last_error=True);ps=C.WinDLL('psapi');k.OpenProcess.argtypes=[C.c_ulong,C.c_bool,C.c_ulong];k.OpenProcess.restype=C.c_void_p;k.CloseHandle.argtypes=[C.c_void_p]
    ps.GetProcessMemoryInfo.argtypes=[C.c_void_p,C.POINTER(Memory),C.c_ulong];ps.GetProcessMemoryInfo.restype=C.c_bool
    data=[]
    for i in range(5):
        directory=a.out/f'smoke{i}';assert not directory.exists(),'Do not overwrite a measured run'
        start=time.perf_counter();process=subprocess.Popen([str(a.binary.resolve()),str(directory),'0','smoke'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        h=k.OpenProcess(0x0400|0x0010,False,process.pid);assert h
        peak=0;samples=0
        try:
            while process.poll() is None:
                m=Memory();m.cb=C.sizeof(m)
                if ps.GetProcessMemoryInfo(h,C.byref(m),C.sizeof(m)):peak=max(peak,m.peak);samples+=1
                time.sleep(.01)
            output=process.communicate()[0];assert process.returncode==0,output
        finally:k.CloseHandle(h)
        data.append(dict(repetition=i,warmup=int(i==0),wall_ms=(time.perf_counter()-start)*1000,peak_working_set_bytes=peak,memory_samples=samples,status='DIAGNOSTIC_NOT_QUIET_GATE'))
    with (a.out/'process.csv').open('w',newline='') as f:w=csv.DictWriter(f,list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
    print(json.dumps(data))
if __name__=='__main__':main()
