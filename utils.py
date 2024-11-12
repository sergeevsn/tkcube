import segyio
import numpy as np

class HeaderStartBytes:
    def __init__(self, x_start_byte, y_start_byte, inline_start_byte, xline_start_byte) -> None:        
        self.inline = inline_start_byte
        self.xline = xline_start_byte    
        self.x = x_start_byte
        self.y = y_start_byte


def scan_segy(filename, start_bytes=None, progress_callback=None):   
    cdp_x = []
    cdp_y = []

    inlines = []
    xlines = []
    smin = np.finfo(np.float32).max
    smax = np.finfo(np.float32).min

    if not start_bytes:
        start_bytes = HeaderStartBytes(189, 193, 181, 185)

    # Пример обновления прогресса
    with segyio.open(filename, strict=False) as f:
        n_samples = f.bin[segyio.BinField.Samples]
        dt = f.bin[segyio.BinField.Interval]//1000
        chunks = f.tracecount//100
        for i in range(f.tracecount):
            if i % chunks == 0:
                if progress_callback:
                    progress_callback(100*i/f.tracecount + 1)
            cdp_x.append(f.header[i][start_bytes.x])
            cdp_y.append(f.header[i][start_bytes.y])
          
            inlines.append(f.header[i][start_bytes.inline])
            xlines.append(f.header[i][start_bytes.xline]) 
            trace = f.trace[i]
            if trace.max() > smax:
                smax = trace.max()
            if trace.min() < smin:
                smin = trace.min()                  
    return np.array(cdp_x), np.array(cdp_y), np.array(inlines), np.array(xlines), dt, np.arange(n_samples), smin, smax

def scale_trace_uint8(trace, min_val, max_val):         
    if min_val == max_val:       
        return np.full_like(trace, 0 if min_val < 0 else 255, dtype=np.uint8)    
 
    scaled_arr = np.round(255 * (trace - min_val) / (max_val - min_val))    
    
    return scaled_arr.astype(np.uint8)

def get_cube(filename, start_bytes, unique_inlines, unique_crosslines, samples, smin, smax, progress_callback=None):       
    with segyio.open(filename, strict=False) as f:        
        n_inlines = len(unique_inlines)
        n_xlines= len(unique_crosslines)
        n_samples = len(samples)
        cube_8bit = np.ones((n_inlines, n_xlines, n_samples), dtype=np.uint8)
        chunks = f.tracecount//100
        for i in range(f.tracecount):
            if i % chunks == 0:
                if progress_callback:
                    progress_callback(100*i/f.tracecount + 1)                   
            inl_idx = np.where(unique_inlines == f.header[i][start_bytes.inline])[0]                          
            xln_idx = np.where(unique_crosslines == f.header[i][start_bytes.xline])[0]                     
            cube_8bit[inl_idx, xln_idx] =  scale_trace_uint8(f.trace[i], smin, smax)
   
    return cube_8bit
