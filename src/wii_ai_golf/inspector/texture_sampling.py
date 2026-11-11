"""Display-only UV texture minification for the private Wii Golf inspector.

Original PNG bytes/UVs are never modified; these extra mip levels are
generated in memory for anti-aliased VISUAL PREVIEW. They are not source
TEX0 mip banks and not Nintendo GX/TEV filter reconstruction.
"""
from __future__ import annotations

import math

MAX_MIP_LEVELS = 16


def build_rgba_mips(rgba):
    """Return level 0 plus bounded alpha-aware Pillow BOX downsample levels.

    Pillow performs source-aware RGBA resize, preserving cutout silhouettes
    substantially better than averaging independently straight-alpha RGB.
    """
    import numpy as np
    from PIL import Image

    a = np.asarray(rgba)
    if a.ndim != 3 or a.shape[2] != 4 or a.dtype != np.uint8:
        raise ValueError("Mip source must be RGBA uint8")
    h, w = a.shape[:2]
    if not 1 <= w <= 8192 or not 1 <= h <= 8192:
        raise ValueError("Mip source dimensions out of bounds")
    levels = [np.ascontiguousarray(a)]
    while (w > 1 or h > 1) and len(levels) < MAX_MIP_LEVELS:
        w, h = max(1, w // 2), max(1, h // 2)
        small = Image.fromarray(levels[-1], mode="RGBA").resize(
            (w, h), resample=Image.Resampling.BOX)
        levels.append(np.ascontiguousarray(np.asarray(small, dtype=np.uint8)))
    return tuple(levels)


def screen_texture_lod(points, uvs, texture_width: int,
                       texture_height: int, mip_count: int) -> int:
    """Conservative affine face LOD from source UV pixel derivatives.

    This is one per-triangle preview filter level, not Wii per-pixel mip
    hardware. Perspective-correct UV interpolation happens separately.
    """
    if mip_count < 1 or not 1 <= texture_width <= 8192 or not 1 <= texture_height <= 8192:
        raise ValueError("Invalid mip bounds")
    (x0,y0),(x1,y1),(x2,y2) = ((float(p[0]),float(p[1])) for p in points)
    (u0,v0),(u1,v1),(u2,v2) = ((float(uv[0]),float(uv[1])) for uv in uvs)
    det=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
    if not math.isfinite(det) or abs(det) < 1e-8:
        return 0
    du_dx=((u0-u2)*(y1-y2)+(u1-u2)*(y2-y0))/det
    du_dy=((u0-u2)*(x2-x1)+(u1-u2)*(x0-x2))/det
    dv_dx=((v0-v2)*(y1-y2)+(v1-v2)*(y2-y0))/det
    dv_dy=((v0-v2)*(x2-x1)+(v1-v2)*(x0-x2))/det
    rho=max(math.hypot(du_dx*texture_width,dv_dx*texture_height),
            math.hypot(du_dy*texture_width,dv_dy*texture_height))
    if not math.isfinite(rho):
        return mip_count-1
    if rho <= 1.:
        return 0
    return min(mip_count-1, max(0, int(math.floor(math.log2(rho)+.5))))


def bilinear_wrapped_rgba(texture, u, v):
    """Sample correctly wrapped bilinear RGBA, alpha-aware in NumPy.

    u/v arrays are perspective-corrected source Collada coordinates.
    """
    import numpy as np

    h,w=texture.shape[:2]
    px=np.mod(u,1.)*w-.5
    py=np.mod(1.-v,1.)*h-.5
    fx=np.floor(px)
    fy=np.floor(py)
    tx0=fx.astype(np.intp)%w
    ty0=fy.astype(np.intp)%h
    tx1=(tx0+1)%w
    ty1=(ty0+1)%h
    ax=(px-fx)[:,None]
    ay=(py-fy)[:,None]
    taps=((texture[ty0,tx0],(1.-ax)*(1.-ay)),
          (texture[ty0,tx1],ax*(1.-ay)),
          (texture[ty1,tx0],(1.-ax)*ay),
          (texture[ty1,tx1],ax*ay))
    alpha=np.zeros((len(u),1),dtype=np.float64)
    premul=np.zeros((len(u),3),dtype=np.float64)
    for pixel, weight in taps:
        a=pixel[:,3:4].astype(np.float64)
        alpha+=weight*a
        premul+=weight*a*pixel[:,:3].astype(np.float64)
    rgb=np.where(alpha>1e-8,premul/np.maximum(alpha,1e-8),0.)
    return np.concatenate((
        np.clip(rgb,0.,255.),
        np.clip(alpha,0.,255.)),axis=1).astype(np.uint8)
