"""Small ISO-BMFF probe so validation works even without a separate ffprobe binary."""
import struct
import zlib


def validate_png(path,resolution=None):
    data=path.read_bytes()
    if data[:8]!=b'\x89PNG\r\n\x1a\n':
        raise ValueError('Bad PNG header: '+str(path))
    offset=8
    size=None
    while offset+12<=len(data):
        length=struct.unpack_from('>I',data,offset)[0]
        kind=data[offset+4:offset+8]
        end=offset+12+length
        if end>len(data):
            raise ValueError('Truncated PNG: '+str(path))
        payload=data[offset+8:offset+8+length]
        crc=struct.unpack_from('>I',data,offset+8+length)[0]
        if zlib.crc32(kind+payload)&0xffffffff!=crc:
            raise ValueError('PNG checksum mismatch: '+str(path))
        if kind==b'IHDR':
            size=list(struct.unpack_from('>II',payload))
        if kind==b'IEND':
            if end!=len(data) or size is None or (resolution and list(resolution)!=size):
                raise ValueError('Unexpected PNG geometry or trailing data')
            return size
        offset=end
    raise ValueError('PNG has no final chunk: '+str(path))


def atoms(data,start=0,end=None):
    end=len(data) if end is None else end
    offset=start
    while offset+8<=end:
        size,kind=struct.unpack_from('>I4s',data,offset)
        header=8
        if size==1:
            size=struct.unpack_from('>Q',data,offset+8)[0]
            header=16
        elif size==0:
            size=end-offset
        if size<header or offset+size>end:
            raise ValueError('Invalid MP4 atom')
        yield kind,offset+header,offset+size
        offset+=size


def child(data,start,end,kind):
    return next((a,b) for k,a,b in atoms(data,start,end) if k==kind)


def probe(path):
    data=path.read_bytes()
    moov=child(data,0,len(data),b'moov')
    tracks=[]
    for kind,a,b in atoms(data,*moov):
        if kind!=b'trak':
            continue
        mdia=child(data,a,b,b'mdia')
        ha,hb=child(data,*mdia,b'hdlr')
        media_type=data[ha+8:ha+12].decode('ascii')
        ma,mb=child(data,*mdia,b'mdhd')
        if data[ma]==1:
            timescale=struct.unpack_from('>I',data,ma+20)[0]
            duration=struct.unpack_from('>Q',data,ma+24)[0]
        else:
            timescale,duration=struct.unpack_from('>II',data,ma+12)
        minf=child(data,*mdia,b'minf')
        stbl=child(data,*minf,b'stbl')
        za,zb=child(data,*stbl,b'stsz')
        samples=struct.unpack_from('>I',data,za+8)[0]
        track={'type':media_type,'duration':duration/timescale,'samples':samples}
        if media_type=='vide':
            ta,tb=child(data,a,b,b'tkhd')
            width,height=struct.unpack_from('>II',data,tb-8)
            track.update(width=width/65536,height=height/65536,fps=samples/(duration/timescale))
        tracks.append(track)
    return {'tracks':tracks,'bytes':len(data)}
