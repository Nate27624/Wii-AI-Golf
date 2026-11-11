"""Optional, bounded CPU preview of user-extracted visual-model UV textures.

This renders UV-mapped OBJ faces using local PNGs. It is NOT Wii GX TEV,
vertex-color/multitexture shader, lighting, sky, map camera, or KCL physics.
Pillow + NumPy are imported lazily so the ordinary inspector stays lightweight.
Rendering runs on preview input only, never in the 230 ms live sampling loop.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from .visual_model import PrivateVisualModel, VisualAssetError, _read_local, MAX_PNG_BYTES

MAX_VIEW_WIDTH = 1280
MAX_VIEW_HEIGHT = 800
MAX_PREVIEW_FACES = 4_000


def _dependencies():
    try:
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        raise VisualAssetError('Textured preview needs Pillow and NumPy; install: py -m pip install -e ".[visual]"') from exc
    return np, Image


def prepare_textures(model: PrivateVisualModel) -> dict[str, Any]:
    """Load only source-bound PNG bytes into immutable-ish in-memory arrays once."""
    np, Image = _dependencies()
    out = {}
    for name, tex in model.textures.items():
        # Fail if files were replaced between OBJ admission and renderer init.
        blob = _read_local(Path(tex.filename), MAX_PNG_BYTES)
        if hashlib.sha256(blob).hexdigest() != tex.sha256:
            raise VisualAssetError('Private PNG changed after model validation')
        import io
        try:
            with Image.open(io.BytesIO(blob)) as im:
                if im.format != 'PNG' or im.size != tex.size:
                    raise VisualAssetError('Source texture dimensions/format changed')
                im.load()
                out[name] = np.asarray(im.convert('RGBA'), dtype=np.uint8).copy()
        except (OSError, ValueError, SyntaxError) as exc:
            raise VisualAssetError('PNG could not be safely decoded') from exc
    return out


def _project_point(point: tuple[float, float, float], yaw: float, pitch: float):
    x, y, z = point
    forward = z*math.cos(yaw) - x*math.sin(yaw)
    return (x*math.cos(yaw) + z*math.sin(yaw),
            y*math.cos(pitch) + forward*math.sin(pitch),
            forward*math.cos(pitch) - y*math.sin(pitch))


def render_preview(model: PrivateVisualModel, width: int, height: int, *,
                   yaw: float = 0.65, pitch: float = 0.48, zoom: float = 1.0,
                   pan: tuple[float, float] = (0., 0.),
                   textures: dict[str, Any] | None = None,
                   max_faces: int = MAX_PREVIEW_FACES):
    """Depth-tested UV raster preview with repeated nearest-neighbor PNG texels.

    Explicit limits prevent a single malformed triangle from allocating an
    unbounded raster. This is a first-pass source-UV preview, not GX rendering.
    """
    np, Image = _dependencies()
    if (type(width) is not int or type(height) is not int or
            not 16 <= width <= MAX_VIEW_WIDTH or not 16 <= height <= MAX_VIEW_HEIGHT or
            type(max_faces) is not int or not 1 <= max_faces <= MAX_PREVIEW_FACES or
            not all(math.isfinite(v) for v in (yaw,pitch,zoom,*pan)) or not 0.04 <= zoom <= 64):
        raise VisualAssetError('Invalid preview dimensions or camera')
    if textures is None:
        textures = prepare_textures(model)
    xyz = np.asarray([_project_point(p, yaw, pitch) for p in model.vertices], dtype='float64')
    if not np.isfinite(xyz).all():
        raise VisualAssetError('Model projection not finite')
    x_min, y_min = xyz[:,:2].min(axis=0)
    x_max, y_max = xyz[:,:2].max(axis=0)
    fit = min((width-60)/max(1e-8,x_max-x_min), (height-60)/max(1e-8,y_max-y_min))
    midx, midy = (x_min+x_max)*.5, (y_min+y_max)*.5
    screen = np.empty_like(xyz)
    screen[:,0] = width/2 + pan[0] + (xyz[:,0]-midx)*fit*zoom
    screen[:,1] = height/2 + pan[1] - (xyz[:,1]-midy)*fit*zoom
    screen[:,2] = xyz[:,2]  # viewer-depth coordinate, more-positive nearer
    result = np.empty((height,width,3),dtype=np.uint8)
    result[:,:,:] = (19,32,46)
    zbuf = np.full((height,width), -np.inf, dtype=np.float32)
    step=max(1,(len(model.faces)+max_faces-1)//max_faces)
    drawn = 0
    for face in model.faces[::step][:max_faces]:
        if face.material not in textures:
            continue
        pts = screen[list(face.vertices)]
        p0, p1, p2 = pts
        x0,y0,x1,y1,x2,y2 = float(p0[0]),float(p0[1]),float(p1[0]),float(p1[1]),float(p2[0]),float(p2[1])
        det = (y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
        if abs(det)<1e-8:
            continue
        left=max(0,int(math.floor(min(x0,x1,x2))))
        top=max(0,int(math.floor(min(y0,y1,y2))))
        right=min(width,int(math.ceil(max(x0,x1,x2)))+1)
        bottom=min(height,int(math.ceil(max(y0,y1,y2)))+1)
        if left >= right or top >= bottom:
            continue
        yy,xx=np.mgrid[top:bottom,left:right]
        xp=xx+.5; yp=yy+.5
        b0=((y1-y2)*(xp-x2)+(x2-x1)*(yp-y2))/det
        b1=((y2-y0)*(xp-x2)+(x0-x2)*(yp-y2))/det
        b2=1-b0-b1
        on=(b0>=-1e-6)&(b1>=-1e-6)&(b2>=-1e-6)
        if not on.any():
            continue
        z=(b0*p0[2]+b1*p1[2]+b2*p2[2]).astype(np.float32)
        current=zbuf[top:bottom,left:right]
        visible=on&(z>current)
        if not visible.any():
            continue
        uv=np.asarray([model.uvs[i] for i in face.uvs],dtype=np.float64)
        u=b0*uv[0,0]+b1*uv[1,0]+b2*uv[2,0]
        v=b0*uv[0,1]+b1*uv[1,1]+b2*uv[2,1]
        texture=textures[face.material]
        th,tw=texture.shape[:2]
        # OBJ V=0 is bottom, PNG raster y=0 is top; repeat UVs safely.
        tx=(np.floor((u-np.floor(u))*tw).astype(np.int64))%tw
        ty=(np.floor((1-v-np.floor(1-v))*th).astype(np.int64))%th
        pixels=texture[ty,tx]
        visible &= pixels[:,:,3]>16
        if not visible.any():
            continue
        dest=result[top:bottom,left:right]
        alpha=(pixels[:,:,3:4].astype(np.float32)/255.)
        blended=(pixels[:,:,:3].astype(np.float32)*alpha+dest.astype(np.float32)*(1-alpha)).astype(np.uint8)
        dest[visible]=blended[visible]
        current[visible]=z[visible]
        drawn+=1
    return Image.fromarray(result,mode='RGB'),drawn
