"""Optional separate Tk scene preview for original user-extracted UV visual models.

A second window avoids running texture rasterization on each live Felk read.
It does NOT alter the native game, source-aligned KCL, or main inspector plot.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .navigation import pan_by, wheel_steps, zoom_at_cursor
from .texture_render import prepare_textures, render_preview
from .visual_model import PrivateVisualModel, VisualAssetError


class TexturedPreviewWindow:
    def __init__(self, parent: tk.Misc, model: PrivateVisualModel):
        # Decode/verify before creating a window so failures are handled by
        # the inspector's existing error dialog and do not leave blank UI.
        self.textures = prepare_textures(model)
        self.model = model
        self.top = tk.Toplevel(parent)
        self.top.title("Wii Golf · PRIVATE game visual model / UV texture preview")
        self.top.geometry("1040x720")
        self.top.minsize(480,360)
        self.zoom = 1.0
        self.pan = (0., 0.)
        self.yaw, self.pitch = 0.65, 0.48
        self.drag_origin: tuple[int,int] | None = None
        self.drag_button: int | None = None
        self.image_ref = None
        self._pending = None
        head = ttk.Frame(self.top,padding=8)
        head.pack(fill="x")
        ttk.Label(head,text=f"PRIVATE visual mesh: {model.source_name} · {len(model.faces):,} UV triangles · {len(model.textures)} PNG texture(s)",font=("Segoe UI",12,"bold")).pack(anchor="w")
        ttk.Label(head,text="Original-file preview only · NOT KCL collision/physics · Wii lighting/shaders & model-to-world transform UNVERIFIED",wraplength=990).pack(anchor="w")
        if model.skipped_source_faces:
            ttk.Label(
                head,
                text=f"Source DAE has {model.skipped_source_faces:,} face(s) with no recoverable original diffuse appearance: omitted, NOT recolored.",
                wraplength=990,
            ).pack(anchor="w")
        controls=ttk.Frame(self.top,padding=(8,2))
        controls.pack(fill="x")
        ttk.Button(controls,text="Frame visual model (F)",command=self.frame).pack(side="left")
        ttk.Label(controls,text="Scroll: cursor zoom · Middle drag: pan · Left/right drag: orbit · F: frame",padding=(10,0)).pack(side="left")
        self.canvas = tk.Canvas(self.top, background="#13202e",highlightthickness=0)
        self.canvas.pack(fill="both",expand=True,padx=8,pady=8)
        self.canvas.bind("<Configure>",lambda e:self.schedule())
        for button in (1,2,3):
            self.canvas.bind(f"<ButtonPress-{button}>",self.drag_start)
            self.canvas.bind(f"<B{button}-Motion>",self.drag_move)
            self.canvas.bind(f"<ButtonRelease-{button}>",self.drag_end)
        self.canvas.bind("<MouseWheel>",self.wheel)
        self.canvas.bind("<Button-4>",self.wheel)
        self.canvas.bind("<Button-5>",self.wheel)
        self.canvas.bind("<KeyPress-f>",self.frame)
        self.canvas.bind("<KeyPress-F>",self.frame)
        self.status = tk.StringVar(value="Preparing texture preview (no Dolphin/guest access)")
        ttk.Label(self.top,textvariable=self.status,padding=(8,0)).pack(fill="x")
        self.top.protocol("WM_DELETE_WINDOW",self.close)
        self.schedule()

    def schedule(self):
        if self._pending is not None:
            try:self.top.after_cancel(self._pending)
            except tk.TclError:pass
        self._pending = self.top.after(70,self.draw)

    def draw(self):
        self._pending = None
        width=min(1280,self.canvas.winfo_width())
        height=min(800,self.canvas.winfo_height())
        if width<16 or height<16:
            return
        try:
            from PIL import ImageTk
            image,drawn=render_preview(self.model,width,height,yaw=self.yaw,pitch=self.pitch,
                                       zoom=self.zoom,pan=self.pan,textures=self.textures)
            self.image_ref=ImageTk.PhotoImage(image,master=self.canvas)
            self.canvas.delete("all")
            self.canvas.create_image(0,0,image=self.image_ref,anchor="nw")
            self.status.set(f"{drawn:,} UV-textured faces shown (bounded 4,000 max) · {self.zoom:.2f}× zoom · visual/world alignment unverified")
        except (VisualAssetError, OSError, ValueError, ImportError) as exc:
            self.status.set(f"Textured visual preview unavailable: {exc}")

    def drag_start(self,event):
        self.drag_origin=(event.x,event.y)
        self.drag_button=getattr(event,"num",1)
        self.canvas.focus_set()

    def drag_move(self,event):
        if self.drag_origin is None:
            return
        dx,dy=event.x-self.drag_origin[0],event.y-self.drag_origin[1]
        if self.drag_button==2:
            self.pan=pan_by(self.pan,dx,dy)
        else:
            self.yaw += dx*0.01
            self.pitch=max(-1.4,min(1.4,self.pitch+dy*.01))
        self.drag_origin=(event.x,event.y)
        self.schedule()

    def drag_end(self,event):
        if self.drag_button==getattr(event,"num",None):
            self.drag_origin=None
            self.drag_button=None

    def wheel(self,event):
        n=wheel_steps(getattr(event,"delta",None),getattr(event,"num",None))
        if not n:
            return
        viewport=(max(16,self.canvas.winfo_width()),max(16,self.canvas.winfo_height()))
        self.zoom,self.pan=zoom_at_cursor(self.zoom,self.pan,(event.x,event.y),viewport,n)
        self.canvas.focus_set()
        self.schedule()

    def frame(self,event=None):
        self.zoom=1.
        self.pan=(0.,0.)
        self.schedule()

    def close(self):
        if self._pending is not None:
            try:self.top.after_cancel(self._pending)
            except tk.TclError:pass
        self.image_ref=None
        self.top.destroy()
