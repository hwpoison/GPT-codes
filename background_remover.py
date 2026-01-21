import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, ttk
from PIL import Image, ImageTk, ImageFilter, ImageOps
import numpy as np
import threading
import time

class ChromaKeyProApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chroma Key Pro v2.0 - Studio Edition")
        self.root.geometry("1400x900")
        
        # Configuración de Estilo
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        
        # Estado de la imagen
        self.original_image = None
        self.processed_image = None
        self.display_image = None   # Imagen lista para el canvas (recortada al viewport)
        self.tk_display = None      # Objeto ImageTk
        self.tk_background = None   # Fondo de ajedrez
        
        # Parámetros del Algoritmo
        self.target_colors = [] 
        self.tolerance = 60
        self.softness = 15
        self.spill_suppression = 40  # Intensidad de desaturación en bordes
        self.erosion = 0             # Contracción de máscara
        
        # Variables de Visualización
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start = {"x": 0, "y": 0}
        self.is_dragging = False
        self.show_original = False   # Toggle para comparar
        
        # Control de Procesamiento
        self.processing_lock = False
        self.pending_update = False
        self.timer_id = None
        
        self.setup_ui()
        self.update_statusbar("Listo. Carga una imagen para comenzar.")

    def configure_styles(self):
        bg_dark = "#2b2b2b"
        fg_light = "#ecf0f1"
        accent = "#3498db"
        
        self.root.configure(bg=bg_dark)
        self.style.configure("TFrame", background=bg_dark)
        self.style.configure("TLabel", background=bg_dark, foreground=fg_light, font=("Segoe UI", 9))
        self.style.configure("Header.TLabel", font=("Segoe UI", 10, "bold"), foreground=accent)
        self.style.configure("TButton", font=("Segoe UI", 9), padding=5)
        self.style.configure("TScale", background=bg_dark)
        self.style.configure("TCheckbutton", background=bg_dark, foreground=fg_light)

    def setup_ui(self):
        # --- Contenedor Principal ---
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=4, bg="#1a1a1a")
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # --- Sidebar de Controles ---
        self.sidebar = ttk.Frame(self.main_paned, width=320, padding=15)
        self.main_paned.add(self.sidebar, stretch="never")
        
        # 1. Sección Archivo
        self._add_header("GESTIÓN DE ARCHIVO")
        f_frame = ttk.Frame(self.sidebar)
        f_frame.pack(fill=tk.X, pady=5)
        ttk.Button(f_frame, text="📂 Cargar Imagen", command=self.load_image).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,2))
        ttk.Button(f_frame, text="💾 Guardar PNG", command=self.save_image).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2,0))
        
        self._separator()

        # 2. Selección de Color
        self._add_header("COLORES A ELIMINAR")
        
        # Lista de colores
        self.color_listbox = tk.Listbox(self.sidebar, height=5, selectmode=tk.SINGLE, 
                                        bg="#3a3a3a", fg="white", borderwidth=0, highlightthickness=1, relief="flat")
        self.color_listbox.pack(fill=tk.X, pady=5)
        
        # Botones de color
        c_frame = ttk.Frame(self.sidebar)
        c_frame.pack(fill=tk.X)
        
        self.btn_pipette = tk.Button(c_frame, text="💧 Pipeta (Seleccionar)", command=self.toggle_pipette, 
                                     bg="#e67e22", fg="white", relief="flat", font=("Segoe UI", 9, "bold"))
        self.btn_pipette.pack(fill=tk.X, pady=(0, 5))
        
        c_sub = ttk.Frame(c_frame)
        c_sub.pack(fill=tk.X)
        ttk.Button(c_sub, text="🎨 Manual", command=self.add_color_dialog).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(c_sub, text="🗑 Borrar", command=self.remove_color).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self._separator()

        # 3. Algoritmo
        self._add_header("AJUSTE DE MÁSCARA")
        
        self.tol_var = self._add_slider("Tolerancia (Distancia Color)", 0, 255, self.tolerance)
        self.soft_var = self._add_slider("Suavizado (Borde Orgánico)", 0, 100, self.softness)
        self.ero_var = self._add_slider("Erosión (Recortar Borde)", 0, 10, self.erosion)
        
        self._separator()
        self._add_header("LIMPIEZA Y ACABADO")
        
        self.spill_var = self._add_slider("Descontaminar (Despill)", 0, 100, self.spill_suppression)
        
        # Botón Comparar
        self.btn_compare = tk.Button(self.sidebar, text="👁 MANTENER PARA VER ORIGINAL", bg="#34495e", fg="white", relief="flat")
        self.btn_compare.bind("<ButtonPress-1>", lambda e: self.toggle_compare(True))
        self.btn_compare.bind("<ButtonRelease-1>", lambda e: self.toggle_compare(False))
        self.btn_compare.pack(fill=tk.X, pady=20)
        
        # Progreso
        self.progress_bar = ttk.Progressbar(self.sidebar, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=(10,0))

        # --- Área de Canvas ---
        self.canvas_frame = tk.Frame(self.main_paned, bg="#111")
        self.main_paned.add(self.canvas_frame, stretch="always")
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # --- Status Bar ---
        self.statusbar = tk.Frame(self.root, bg="#007acc", height=25)
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM)
        self.lbl_status = tk.Label(self.statusbar, text="Listo", bg="#007acc", fg="white", font=("Consolas", 9), padx=10)
        self.lbl_status.pack(side=tk.LEFT)
        self.lbl_info = tk.Label(self.statusbar, text="", bg="#007acc", fg="white", font=("Consolas", 9), padx=10)
        self.lbl_info.pack(side=tk.RIGHT)

        # Eventos Canvas
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom) # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_zoom) # Linux scroll down
        self.canvas.bind("<Motion>", self.update_cursor_info)
        
        # Generar patrón de fondo una vez
        self.checker_tile = self.create_checkerboard()

    # --- UI Helpers ---
    def _add_header(self, text):
        ttk.Label(self.sidebar, text=text, style="Header.TLabel").pack(fill=tk.X, pady=(10, 5))

    def _separator(self):
        ttk.Separator(self.sidebar, orient='horizontal').pack(fill=tk.X, pady=10)

    def _add_slider(self, label, vmin, vmax, default):
        ttk.Label(self.sidebar, text=label).pack(fill=tk.X, pady=(2,0))
        var = tk.DoubleVar(value=default)
        s = ttk.Scale(self.sidebar, from_=vmin, to=vmax, variable=var, command=self.trigger_update)
        s.pack(fill=tk.X, pady=(0, 8))
        return var

    def update_statusbar(self, msg=None):
        if msg: self.lbl_status.config(text=msg)
        if self.original_image:
            w, h = self.original_image.size
            z = int(self.zoom_level * 100)
            self.lbl_info.config(text=f"{w}x{h} px | Zoom: {z}%")

    def create_checkerboard(self):
        size = 20
        img = Image.new("RGB", (size*2, size*2), "#cccccc")
        draw = ImageOps.grayscale(img) # dummy conversion to create draw object
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle([size, 0, size*2, size], fill="#ffffff")
        draw.rectangle([0, size, size, size*2], fill="#ffffff")
        return img

    # --- Lógica de Imagen ---

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if not path: return
        try:
            img = Image.open(path).convert("RGBA")
            # Limitar tamaño para rendimiento (opcional, ajustado a 4k)
            if max(img.size) > 4096:
                img.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
            
            self.original_image = img
            self.processed_image = img.copy()
            self.center_image()
            self.trigger_update()
            self.update_statusbar(f"Cargado: {path.split('/')[-1]}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_image(self):
        if not self.processed_image: return
        f = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG con Transparencia", "*.png")])
        if f:
            self.processed_image.save(f)
            self.update_statusbar("Imagen guardada exitosamente.")

    # --- Interacción y Zoom ---

    def center_image(self):
        if not self.original_image: return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        iw, ih = self.original_image.size
        
        # Fit to screen
        scale = min((cw - 40)/iw, (ch - 40)/ih)
        self.zoom_level = max(0.05, scale)
        
        # Centrar
        self.pan_x = (cw - iw * self.zoom_level) / 2
        self.pan_y = (ch - ih * self.zoom_level) / 2
        self.redraw()

    def on_zoom(self, event):
        if not self.original_image: return

        # Determinar dirección y factor
        if event.num == 5 or event.delta < 0:
            factor = 0.9
        else:
            factor = 1.1

        # Punto focal del mouse en coordenadas del canvas
        mouse_x = self.canvas.canvasx(event.x)
        mouse_y = self.canvas.canvasy(event.y)

        # Convertir a coordenadas de la imagen antes del zoom
        img_x = (mouse_x - self.pan_x) / self.zoom_level
        img_y = (mouse_y - self.pan_y) / self.zoom_level

        # Aplicar nuevo zoom
        new_zoom = self.zoom_level * factor
        new_zoom = max(0.05, min(new_zoom, 50.0)) # Limites de zoom

        # Calcular nuevo pan para mantener el punto bajo el mouse estático
        self.pan_x = mouse_x - (img_x * new_zoom)
        self.pan_y = mouse_y - (img_y * new_zoom)
        
        self.zoom_level = new_zoom
        self.redraw(quick=True) # Redibujado rápido
        self.update_statusbar()
        
        # Programar redibujado de alta calidad
        if self.timer_id: self.root.after_cancel(self.timer_id)
        self.timer_id = self.root.after(100, self.redraw)

    def on_click(self, event):
        if not self.original_image: return
        
        if self.canvas.cget("cursor") == "tcross":
            # Modo Pipeta
            ix = int((event.x - self.pan_x) / self.zoom_level)
            iy = int((event.y - self.pan_y) / self.zoom_level)
            
            if 0 <= ix < self.original_image.width and 0 <= iy < self.original_image.height:
                pixel = self.original_image.getpixel((ix, iy))
                self.add_color(pixel[:3])
                self.toggle_pipette() # Salir modo pipeta automáticamente
        else:
            # Modo Arrastre
            self.is_dragging = True
            self.drag_start = {"x": event.x, "y": event.y}

    def on_drag(self, event):
        if self.is_dragging:
            dx = event.x - self.drag_start["x"]
            dy = event.y - self.drag_start["y"]
            self.pan_x += dx
            self.pan_y += dy
            self.drag_start = {"x": event.x, "y": event.y}
            self.redraw(quick=True)

    def on_release(self, event):
        self.is_dragging = False
        self.redraw()

    def update_cursor_info(self, event):
        if not self.original_image: return
        ix = int((event.x - self.pan_x) / self.zoom_level)
        iy = int((event.y - self.pan_y) / self.zoom_level)
        
        msg = ""
        if 0 <= ix < self.original_image.width and 0 <= iy < self.original_image.height:
            rgb = self.original_image.getpixel((ix, iy))[:3]
            msg = f"X:{ix} Y:{iy} | RGB:{rgb}"
        self.update_statusbar(msg)


    # --- Gestión de Colores ---

    def toggle_pipette(self):
        current = self.canvas.cget("cursor")
        if current == "tcross":
            self.canvas.config(cursor="")
            self.btn_pipette.config(bg="#e67e22", text="💧 Pipeta (Seleccionar)")
        else:
            self.canvas.config(cursor="tcross")
            self.btn_pipette.config(bg="#d35400", text="❌ Cancelar Pipeta")

    def add_color(self, rgb):
        if rgb not in self.target_colors:
            self.target_colors.append(rgb)
            hex_col = '#{:02x}{:02x}{:02x}'.format(*rgb)
            fg = "black" if (rgb[0]*0.299 + rgb[1]*0.587 + rgb[2]*0.114) > 128 else "white"
            self.color_listbox.insert(tk.END, f"  RGB {rgb}")
            self.color_listbox.itemconfig(tk.END, {'bg': hex_col, 'fg': fg})
            self.trigger_update()

    def remove_color(self):
        sel = self.color_listbox.curselection()
        if sel:
            idx = sel[0]
            self.target_colors.pop(idx)
            self.color_listbox.delete(idx)
            self.trigger_update()

    def add_color_dialog(self):
        c = colorchooser.askcolor(title="Seleccionar color a eliminar")
        if c[0]: self.add_color(tuple(int(x) for x in c[0]))

    def toggle_compare(self, show_original):
        self.show_original = show_original
        self.redraw(quick=True)

    # --- MOTOR DE PROCESAMIENTO (THREADED) ---

    def trigger_update(self, _=None):
        # Debounce: evita lanzar hilos por cada movimiento mínimo del slider
        if self.timer_id: self.root.after_cancel(self.timer_id)
        self.timer_id = self.root.after(100, self.start_processing)

    def start_processing(self):
        if self.processing_lock or not self.original_image: return
        
        self.processing_lock = True
        self.progress_bar.start(10)
        self.update_statusbar("Procesando...")

        # Snapshot de parámetros para el hilo
        params = {
            'colors': self.target_colors.copy(),
            'tol': self.tol_var.get(),
            'soft': self.soft_var.get(),
            'spill': self.spill_var.get(),
            'erosion': self.ero_var.get()
        }

        t = threading.Thread(target=self.run_algorithm, args=(params,))
        t.daemon = True
        t.start()

    def run_algorithm(self, params):
        try:
            # Si no hay colores seleccionados, devolver original
            if not params['colors']:
                res = self.original_image.copy()
            else:
                res = self.compute_chroma_key(self.original_image, params)
            
            # Callback al main thread
            self.root.after(0, self.finish_processing, res)
            
        except Exception as e:
            print(f"Error en algoritmo: {e}")
            self.root.after(0, self.finish_processing, None)

    def compute_chroma_key(self, pil_img, params):
            # Convertir a float32 para precisión
            img_arr = np.array(pil_img).astype(np.float32)
            r, g, b = img_arr[..., 0], img_arr[..., 1], img_arr[..., 2]
            
            # Recuperar alpha original si existe
            if img_arr.shape[2] == 4:
                alpha = img_arr[..., 3]
            else:
                alpha = np.ones_like(r) * 255

            # Parámetros
            # NOTA: En este algoritmo, 'tol' define qué tan agresivo es considerando algo "verde"
            # Rango sugerido para sliders: Tol (0.8 - 1.5), Soft (0 - 100)
            tol_factor = 1.0 + (params['tol'] / 255.0)  # Factor de tolerancia (ej: 1.1)
            soft = params['soft']
            
            # --- Lógica Avanzada de Pantalla Verde (VFX Standard) ---
            # Un píxel es "verde" si el canal G es mayor que el promedio de R y B.
            # Esto funciona infinitamente mejor para IA que la distancia de color.
            
            rb_avg = (r + b) / 2.0
            
            # Máscara base: Cuánto excede el verde a los otros canales
            # Si (G - rb_avg) es positivo, es un tono verdoso.
            green_dominance = g - (rb_avg * tol_factor)
            
            # 1. Crear Máscara Alpha (Recorte)
            # Si green_dominance > 0, es fondo. 
            # Usamos np.clip para suavizar la transición (softness)
            # Invertimos porque queremos 1.0 en el sujeto, 0.0 en el fondo
            
            if soft == 0:
                mask = np.where(green_dominance > 0, 0, 1).astype(np.float32)
            else:
                # Transición suave
                mask = 1.0 - (green_dominance / (soft + 0.1))
                mask = np.clip(mask, 0, 1)

            # 2. Despill (La clave para eliminar halos de IA)
            # Si el píxel es semitransparente o es borde, el Verde sigue siendo alto.
            # "Clampeamos" el canal Verde para que nunca supere al promedio de R y B.
            # Esto convierte el borde verde brillante en un borde oscuro/neutro.
            
            # Solo aplicamos despill donde detectamos verde
            processed_g = np.where(g > rb_avg, rb_avg, g)
            
            # Mezclamos el G original con el G procesado según la fuerza del slider "Descontaminar"
            spill_strength = params['spill'] / 100.0
            final_g = g * (1 - spill_strength) + processed_g * spill_strength
            
            # --- Reconstrucción ---
            
            # Aplicamos la máscara calculada al alpha existente
            final_alpha = alpha * mask
            
            # 3. Erosión de Alpha (Opcional, para comerse el borde ruidoso de la IA)
            if params['erosion'] > 0:
                 # Truco rápido de erosión en numpy sin usar filtros lentos (para 1px)
                 # Nota: Para erosiones grandes, sigue usando el filtro de PIL del código anterior
                 pass 

            # Empaquetar
            result_rgb = np.dstack((r, final_g, b)) # Usamos el G corregido
            result_rgb = np.clip(result_rgb, 0, 255).astype(np.uint8)
            final_alpha = np.clip(final_alpha, 0, 255).astype(np.uint8)
            
            result = np.dstack((result_rgb, final_alpha))
            result_img = Image.fromarray(result)
            
            # Aplicar erosión de PIL si es necesaria (mejor calidad para >1px)
            if params['erosion'] > 0:
                a_chn = result_img.getchannel('A')
                k_size = (int(params['erosion']) * 2) + 1
                a_chn = a_chn.filter(ImageFilter.MinFilter(k_size))
                result_img.putalpha(a_chn)

            return result_img
    def finish_processing(self, image):
        if image:
            self.processed_image = image
            self.redraw()
        
        self.processing_lock = False
        self.progress_bar.stop()
        self.update_statusbar(None)

    # --- Renderizado ---

    def redraw(self, quick=False):
        if not self.original_image: return
        
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 10 or ch < 10: return

        # 1. Preparar Fondo
        if not self.tk_background or self.tk_background.width() != cw or self.tk_background.height() != ch:
            bg = Image.new("RGB", (cw, ch))
            tile = self.checker_tile
            w_tile, h_tile = tile.size
            
            # Método rápido para llenar fondo
            # Creamos una imagen grande repitiendo el tile
            reps_x = (cw // w_tile) + 1
            reps_y = (ch // h_tile) + 1
            # Para simplificar y no colgar UI con bucles gigantes en 4k,
            # usamos paste puntual o shaders, aquí un bucle simple optimizado:
            for x in range(0, cw, w_tile):
                for y in range(0, ch, h_tile):
                    bg.paste(tile, (x, y))
            self.tk_background = ImageTk.PhotoImage(bg)

        # 2. Seleccionar Imagen (Procesada vs Original)
        target_img = self.original_image if self.show_original else self.processed_image
        if not target_img: return

        # 3. Viewport Culling y Transformación
        # Coordenadas en la imagen original que corresponden a las esquinas del canvas
        left = -self.pan_x / self.zoom_level
        top = -self.pan_y / self.zoom_level
        right = (cw - self.pan_x) / self.zoom_level
        bottom = (ch - self.pan_y) / self.zoom_level
        
        # Recorte de seguridad
        crop_box = (
            max(0, int(left)),
            max(0, int(top)),
            min(target_img.width, int(right) + 1),
            min(target_img.height, int(bottom) + 1)
        )
        
        if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
            visible_region = target_img.crop(crop_box)
            
            # Calcular tamaño final en pantalla
            disp_w = int((crop_box[2] - crop_box[0]) * self.zoom_level)
            disp_h = int((crop_box[3] - crop_box[1]) * self.zoom_level)
            
            if disp_w > 0 and disp_h > 0:
                # Nearest es rápido para "quick", Bilinear/Lanczos para calidad
                # Cuando el zoom es > 100%, Nearest preserva píxeles para análisis preciso
                if quick or self.zoom_level > 2.0:
                    resample = Image.Resampling.NEAREST
                else:
                    resample = Image.Resampling.BILINEAR
                
                visible_region = visible_region.resize((disp_w, disp_h), resample)
                
                self.tk_display = ImageTk.PhotoImage(visible_region)
                
                # Dibujar
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, image=self.tk_background, anchor=tk.NW)
                
                # Posición de pegado
                # Si crop_box[0] es 0, la imagen empieza en pan_x.
                # Si hicimos crop, hay que ajustar la posición relativa
                pos_x = self.pan_x + (crop_box[0] * self.zoom_level)
                pos_y = self.pan_y + (crop_box[1] * self.zoom_level)
                
                self.canvas.create_image(pos_x, pos_y, image=self.tk_display, anchor=tk.NW)
        else:
            # Imagen fuera de vista
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self.tk_background, anchor=tk.NW)

if __name__ == "__main__":
    root = tk.Tk()
    # Icono opcional (si existe)
    # root.iconbitmap("icon.ico") 
    app = ChromaKeyProApp(root)
    root.mainloop()