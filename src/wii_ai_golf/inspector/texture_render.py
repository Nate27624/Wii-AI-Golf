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
from typing import Any, Callable

from .visual_model import PrivateVisualModel, VisualAssetError, _read_local, MAX_PNG_BYTES
from .scene_camera import VisualCamera, camera_axes
from .texture_sampling import (
    build_rgba_mips, bilinear_wrapped_rgba, screen_texture_lod,
)

MAX_VIEW_WIDTH = 1280
MAX_VIEW_HEIGHT = 800
# The source loader admits at most 100k triangles. Never stride-drop faces.
MAX_PREVIEW_FACES = 100_000


class PreviewCancelled(Exception):
    """A newer camera request superseded this CPU render (not an asset error)."""


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
                   max_faces: int = MAX_PREVIEW_FACES,
                   cancelled: Callable[[], bool] | None = None,
                   camera: VisualCamera | None = None,
                   filtered: bool = False,
                   mipmaps: dict[str, tuple] | None = None):
    """Depth-tested UV raster preview with source PNGs and optional filtering.

    Explicit limits prevent a single malformed triangle from allocating an
    unbounded raster. This is a first-pass source-UV preview, not GX rendering.
    """
    np, Image = _dependencies()
    if (type(width) is not int or type(height) is not int or
            not 16 <= width <= MAX_VIEW_WIDTH or not 16 <= height <= MAX_VIEW_HEIGHT or
            type(max_faces) is not int or not 1 <= max_faces <= MAX_PREVIEW_FACES or
            not all(math.isfinite(v) for v in (yaw,pitch,zoom,*pan)) or not 0.04 <= zoom <= 64):
        raise VisualAssetError('Invalid preview dimensions or camera')
    if type(filtered) is not bool:
        raise VisualAssetError("Texture filtering mode must be a bool")
    if len(model.faces) > max_faces:
        # A source mesh must never be presented as complete after
        # drawing a random/stride-thinned subset of its native faces.
        raise VisualAssetError('Original visual mesh exceeds full-face preview budget')
    if cancelled is not None and cancelled():
        raise PreviewCancelled()
    if textures is None:
        textures = prepare_textures(model)
    if filtered and mipmaps is None:
        # Standalone API derives preview-only levels from verified base
        # textures; the embedded viewer supplies a once-per-model cache.
        mipmaps = {name:build_rgba_mips(arr)
                   for name,arr in textures.items()}
    # Project the whole model in vectorized NumPy to reduce per-drag overhead.
    src = np.asarray(model.vertices, dtype=np.float64)
    if src.ndim != 2 or src.shape[1] != 3 or not len(src):
        raise VisualAssetError('No valid preview geometry')
    if camera is not None:
        # True scene-editor camera: changing yaw/pitch never translates the
        # camera or recenters the model on its changing projected bounds.
        # Depth > 0 points into the view from the fixed camera position.
        if not all(math.isfinite(c) for c in (*camera.position,
                *camera.focus, camera.yaw, camera.pitch, camera.scale)):
            raise VisualAssetError('Invalid scene-editor camera position')
        right, up, toward_viewer = camera_axes(camera.yaw, camera.pitch)
        displacement = src - np.asarray(camera.position, dtype=np.float64)
        depth = -displacement @ np.asarray(toward_viewer, dtype=np.float64)
        near = max(1e-6, camera.scale * 0.001)
        in_front = np.isfinite(depth) & (depth > near)
        # Avoid dividing behind-camera vertices by near-zero depths.
        good_depth = np.maximum(depth, near)
        focal = height / (2. * math.tan(math.radians(55.)*.5))
        screen = np.empty_like(src)
        screen[:,0] = width*.5 + focal * (
            displacement @ np.asarray(right, dtype=np.float64)) / good_depth
        screen[:,1] = height*.5 - focal * (
            displacement @ np.asarray(up, dtype=np.float64)) / good_depth
        screen[:,2] = 1. / good_depth   # near surfaces win in the z-buffer
        if not np.isfinite(screen).all():
            raise VisualAssetError('Scene-editor perspective projection invalid')
    else:
        # Original orthographic API preserved for OBJ previews and regression
        # tests, but never automatically recenters a fixed-position camera.
        cy, sy = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        forward = src[:, 2]*cy - src[:, 0]*sy
        xyz = np.column_stack((src[:, 0]*cy + src[:, 2]*sy,
                               src[:, 1]*cp + forward*sp,
                               forward*cp - src[:, 1]*sp))
        if not np.isfinite(xyz).all():
            raise VisualAssetError('Model projection not finite')
        x_min, y_min = xyz[:,:2].min(axis=0)
        x_max, y_max = xyz[:,:2].max(axis=0)
        fit = min((width-60)/max(1e-8,x_max-x_min), (height-60)/max(1e-8,y_max-y_min))
        midx, midy = (x_min+x_max)*.5, (y_min+y_max)*.5
        screen = np.empty_like(xyz)
        screen[:,0] = width/2 + pan[0] + (xyz[:,0]-midx)*fit*zoom
        screen[:,1] = height/2 + pan[1] - (xyz[:,1]-midy)*fit*zoom
        screen[:,2] = xyz[:,2]
    result = np.empty((height,width,3),dtype=np.uint8)
    result[:,:,:] = (19,32,46)
    zbuf = np.full((height,width), -np.inf, dtype=np.float32)
    drawn = 0
    for face_index, face in enumerate(model.faces):
        if cancelled is not None and face_index % 32 == 0 and cancelled():
            raise PreviewCancelled()
        if camera is not None and not all(in_front[v] for v in face.vertices):
            # Fail closed on unimplemented near-plane triangle clipping.
            # Front-facing triangles are rendered with depth-correct UVs.
            continue
        # Preserve source-exported MTL Kd as a solid face where original
        # Collada material has no texture slot; no fabricated texture image.
        is_textured = face.material in textures
        if not is_textured and face.material not in model.solid_colors:
            raise VisualAssetError('Visual face material has neither PNG nor source Kd')
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
        # Sparse pixel shading: bound the triangle with broadcasted grid
        # coordinates, then sample PNG only for actually visible pixels.
        # Avoid RGBA arrays over enormous thin-triangle bounding rectangles.
        xp=np.arange(left,right,dtype=np.float64)[None,:]+.5
        yp=np.arange(top,bottom,dtype=np.float64)[:,None]+.5
        b0=((y1-y2)*(xp-x2)+(x2-x1)*(yp-y2))/det
        b1=((y2-y0)*(xp-x2)+(x0-x2)*(yp-y2))/det
        b2=1-b0-b1
        inside=(b0>=-1e-6)&(b1>=-1e-6)&(b2>=-1e-6)
        if not inside.any():
            continue
        current=zbuf[top:bottom,left:right]
        depth=(b0*p0[2]+b1*p1[2]+b2*p2[2]).astype(np.float32)
        visible=inside&(depth>current)
        if not visible.any():
            continue
        iy,ix=np.nonzero(visible)
        if is_textured:
            uv=np.asarray([model.uvs[i] for i in face.uvs],dtype=np.float64)
            if camera is not None:
                # Screen barycentric weights need reciprocal-depth correction
                # for an actual perspective camera to avoid swimming textures.
                w0=b0[iy,ix]*p0[2]
                w1=b1[iy,ix]*p1[2]
                w2=b2[iy,ix]*p2[2]
                scale=1. / (w0+w1+w2)
                w0,w1,w2=w0*scale,w1*scale,w2*scale
            else:
                w0,w1,w2=b0[iy,ix],b1[iy,ix],b2[iy,ix]
            u=w0*uv[0,0]+w1*uv[1,0]+w2*uv[2,0]
            v=w0*uv[0,1]+w1*uv[1,1]+w2*uv[2,1]
            texture=textures[face.material]
            if filtered:
                levels=mipmaps[face.material]
                mip=screen_texture_lod(
                    pts[:,:2], uv, texture.shape[1], texture.shape[0],
                    len(levels))
                pixels=bilinear_wrapped_rgba(levels[mip],u,v)
            else:
                th,tw=texture.shape[:2]
                tx=np.floor(np.mod(u,1.)*tw).astype(np.intp)%tw
                ty=np.floor(np.mod(1.-v,1.)*th).astype(np.intp)%th
                pixels=texture[ty,tx]
            alpha_ok=pixels[:,3]>16
            if not alpha_ok.any():
                continue
            iy,ix=iy[alpha_ok],ix[alpha_ok]
            pixels=pixels[alpha_ok]
        else:
            pixels=np.empty((len(iy),4),dtype=np.uint8)
            pixels[:,:3]=model.solid_colors[face.material]
            pixels[:,3]=255
        dest=result[top:bottom,left:right]
        if np.all(pixels[:,3]==255):
            dest[iy,ix]=pixels[:,:3]
        else:
            alpha=pixels[:,3:4].astype(np.float32)/255.
            prior=dest[iy,ix].astype(np.float32)
            blended=pixels[:,:3].astype(np.float32)*alpha+prior*(1.-alpha)
            dest[iy,ix]=blended.astype(np.uint8)
        current[iy,ix]=depth[iy,ix]
        drawn+=1
    return Image.fromarray(result,mode='RGB'),drawn
