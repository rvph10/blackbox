from datetime import datetime, timezone
from typing import List, Dict, Generator
from PIL import Image, ImageDraw, ImageFont, ImageChops
import logging

logger = logging.getLogger("Dashboard.Renderer")

class Theme:
    BG = (18, 18, 18)
    CARD_BG = (30, 30, 30)
    TEXT_MAIN = (224, 224, 224)
    TEXT_SEC = (160, 160, 160)
    ACCENT = (52, 152, 219)
    SUCCESS = (46, 204, 113)
    WARNING = (241, 196, 15)
    ERROR = (231, 76, 60)

class Renderer:
    """Handles drawing the dashboard to a PIL Image."""

    def __init__(self, config, monitor):
        self.config = config
        self.monitor = monitor
        self.fonts = self._load_fonts()
        self.current_page = 0
        self.total_pages = 3
        self._last_image = None
        self._transitioning = False

    def _load_fonts(self) -> Dict[str, ImageFont.FreeTypeFont]:
        try:
            return {
                'huge': ImageFont.truetype(self.config.FONT_PATH_BOLD, 56),
                'xl': ImageFont.truetype(self.config.FONT_PATH_BOLD, 32),
                'lg': ImageFont.truetype(self.config.FONT_PATH_BOLD, 20),
                'md': ImageFont.truetype(self.config.FONT_PATH_BOLD, 16),
                'sm': ImageFont.truetype(self.config.FONT_PATH_REGULAR, 14),
                'xs': ImageFont.truetype(self.config.FONT_PATH_REGULAR, 11),
            }
        except IOError:
            logger.warning("Custom fonts not found. Using defaults.")
            d = ImageFont.load_default()
            return {k: d for k in ['huge', 'xl', 'lg', 'md', 'sm', 'xs']}

    def next_page(self) -> Generator[Image.Image, None, None]:
        """Advances to next page with optional animation. Yields transition frames."""
        if not self.config.ANIMATION_ENABLED or self.config.ANIMATION_TYPE == "none":
            # No animation - just change page instantly
            self.current_page = (self.current_page + 1) % self.total_pages
            return

        # Capture current state
        old_page = self.current_page
        old_image = self.render()

        # Move to next page
        self.current_page = (self.current_page + 1) % self.total_pages
        new_image = self.render()

        # Generate animation frames
        self._transitioning = True
        try:
            yield from self._animate_transition(old_image, new_image, old_page, self.current_page)
        finally:
            self._transitioning = False

    def render(self) -> Image.Image:
        image = Image.new("RGB", (self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT), Theme.BG)
        draw = ImageDraw.Draw(image)

        if self.current_page == 0:
            self._draw_home(draw)
        elif self.current_page == 1:
            self._draw_network(draw)
        elif self.current_page == 2:
            self._draw_storage(draw)

        self._draw_indicators(draw)
        return image

    def render_alert(self, failed_services: List[str]) -> Image.Image:
        image = Image.new("RGB", (self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT), Theme.BG)
        draw = ImageDraw.Draw(image)
        
        # Flashing red border effect
        draw.rectangle((0, 0, self.config.SCREEN_WIDTH-1, self.config.SCREEN_HEIGHT-1), 
                      outline=Theme.ERROR, width=5)
        
        self._draw_centered_text(draw, "SYSTEM ALERT", 60, Theme.ERROR, 'xl')
        
        y = 120
        for svc in failed_services[:4]:
            self._draw_centered_text(draw, f"DOWN: {svc}", y, Theme.TEXT_MAIN, 'lg')
            y += 35
            
        return image

    # ... Helper drawing methods ...
    def _draw_card(self, draw, x, y, w, h, title=None):
        draw.rounded_rectangle((x, y, x+w, y+h), 8, fill=Theme.CARD_BG)
        if title:
            draw.text((x+10, y+8), title, fill=Theme.TEXT_SEC, font=self.fonts['xs'])

    def _draw_centered_text(self, draw, text, y, color, font_key):
        font = self.fonts[font_key]
        w = draw.textlength(text, font=font)
        draw.text(((self.config.SCREEN_WIDTH - w)/2, y), text, fill=color, font=font)

    def _draw_progress_bar(self, draw, x, y, w, h, percent, color):
        draw.rectangle((x, y, x+w, y+h), fill=(40,40,40))
        fill_w = int(w * (max(0, min(100, percent)) / 100))
        draw.rectangle((x, y, x+fill_w, y+h), fill=color)

    def _draw_home(self, draw):
        # Time & Date
        now = datetime.now()
        self._draw_centered_text(draw, now.strftime("%H:%M"), 10, Theme.TEXT_MAIN, 'huge')
        self._draw_centered_text(draw, now.strftime("%A, %d %B"), 75, Theme.ACCENT, 'lg')

        # Weather Card
        wx, wy = 10, 110
        self._draw_card(draw, wx, wy, 225, 130, "BRUSSELS")
        
        weather = self.monitor.get_state('weather')
        if weather:
            code = weather.get('weathercode', 0)
            desc = self._get_weather_desc(code)
            draw.text((wx+15, wy+35), f"{weather.get('temperature')}°C", fill=Theme.TEXT_MAIN, font=self.fonts['xl'])
            draw.text((wx+15, wy+80), desc, fill=Theme.TEXT_SEC, font=self.fonts['md'])
            draw.text((wx+15, wy+100), f"Wind: {weather.get('windspeed')} km/h", fill=Theme.TEXT_SEC, font=self.fonts['sm'])
        else:
            draw.text((wx+15, wy+50), "Fetching...", fill=Theme.TEXT_SEC, font=self.fonts['sm'])

        # System Card
        sx, sy = 245, 110
        self._draw_card(draw, sx, sy, 225, 130, "SYSTEM HEALTH")
        sys_stats = self.monitor.get_state('system')
        
        self._draw_system_metric(draw, sx+15, sy+35, "CPU", sys_stats['cpu'])
        self._draw_system_metric(draw, sx+15, sy+65, "RAM", sys_stats['ram'])
        
        # Temp
        t_col = Theme.SUCCESS if sys_stats['temp'] < 60 else Theme.WARNING
        draw.text((sx+15, sy+95), f"Temp: {sys_stats['temp']:.1f}°C", fill=t_col, font=self.fonts['md'])

        # Global Status
        failed = [k for k,v in self.monitor.get_state('services').items() if not v]
        self._draw_status_pill(draw, failed)

    def _draw_system_metric(self, draw, x, y, label, val):
        draw.text((x, y), label, fill=Theme.TEXT_MAIN, font=self.fonts['sm'])
        self._draw_progress_bar(draw, x+40, y+3, 140, 10, val, Theme.ACCENT)
        draw.text((x+190, y), f"{int(val)}%", fill=Theme.TEXT_SEC, font=self.fonts['xs'])

    def _draw_status_pill(self, draw, failed_services):
        if failed_services:
            text = f"ALERT: {', '.join(failed_services[:2])}"
            color = Theme.ERROR
        else:
            text = "ALL SYSTEMS OPERATIONAL"
            color = Theme.SUCCESS
            
        font = self.fonts['md']
        w = draw.textlength(text, font=font)
        # Centered pill at bottom
        rect = ((self.config.SCREEN_WIDTH-w)/2 - 10, 260, (self.config.SCREEN_WIDTH+w)/2 + 10, 290)
        draw.rounded_rectangle(rect, 15, fill=Theme.CARD_BG)
        draw.text(((self.config.SCREEN_WIDTH-w)/2, 265), text, fill=color, font=font)

    def _draw_network(self, draw):
        self._draw_page_header(draw, "NETWORK STATUS")
        
        # WAN Card
        wx, wy = 10, 50
        self._draw_card(draw, wx, wy, 460, 100, "WAN INTERFACE")
        
        net = self.monitor.get_state('network')
        
        # DL/UL Layout
        draw.text((wx+30, wy+35), "DOWNLOAD", fill=Theme.TEXT_SEC, font=self.fonts['xs'])
        draw.text((wx+30, wy+50), f"{net['dl']:.1f}", fill=Theme.SUCCESS, font=self.fonts['xl'])
        draw.text((wx+140, wy+62), "MB/s", fill=Theme.TEXT_SEC, font=self.fonts['sm'])
        
        draw.text((wx+250, wy+35), "UPLOAD", fill=Theme.TEXT_SEC, font=self.fonts['xs'])
        draw.text((wx+250, wy+50), f"{net['ul']:.1f}", fill=Theme.ACCENT, font=self.fonts['xl'])
        draw.text((wx+360, wy+62), "MB/s", fill=Theme.TEXT_SEC, font=self.fonts['sm'])
        
        # Services Grid
        gy = 165
        self._draw_card(draw, 10, gy, 460, 140, "SERVICES & LATENCY")
        
        # Latency
        lat = net.get('latency')
        lat_txt = f"{lat:.0f} ms" if lat else "N/A"
        lat_col = Theme.SUCCESS if lat and lat < 50 else Theme.WARNING
        draw.text((30, gy+35), "LATENCY:", fill=Theme.TEXT_MAIN, font=self.fonts['sm'])
        draw.text((110, gy+35), lat_txt, fill=lat_col, font=self.fonts['md'])
        
        # Service Grid
        services = self.monitor.get_state('services')
        sx, sy = 30, gy+65
        for i, (name, status) in enumerate(services.items()):
            col = i % 2
            row = i // 2
            px = sx + (col * 200)
            py = sy + (row * 25)
            
            color = Theme.SUCCESS if status else Theme.ERROR
            draw.ellipse((px, py+2, px+10, py+12), fill=color)
            draw.text((px+20, py), name, fill=Theme.TEXT_MAIN, font=self.fonts['sm'])

    def _draw_storage(self, draw):
        self._draw_page_header(draw, "STORAGE & BACKUPS")
        
        # Storage
        usage = self._get_disk_usage("/mnt/appdata")
        self._draw_card(draw, 10, 50, 460, 80, "NAS STORAGE (/mnt/appdata)")
        
        if usage:
            percent, total, used, free = usage
            self._draw_progress_bar(draw, 30, 85, 420, 15, percent, Theme.ACCENT)
            info = f"Used: {used:.1f} GB  /  Total: {total:.1f} GB  ({percent:.1f}%)"
            draw.text((30, 105), info, fill=Theme.TEXT_SEC, font=self.fonts['sm'])
        
        # Backups
        self._draw_card(draw, 10, 140, 460, 160, "BACKUP STATUS")
        backups = self.monitor.get_state('backups') or {}
        
        by = 175
        if not backups:
            draw.text((30, by), "No backup data available", fill=Theme.WARNING, font=self.fonts['md'])
        else:
            for k, v in list(backups.items())[:4]:
                status = v.get('status') == 'ok'
                ago = self._format_time_ago(v.get('last_run'))
                
                col = Theme.SUCCESS if status else Theme.ERROR
                draw.text((30, by), "•", fill=col, font=self.fonts['lg'])
                draw.text((50, by+2), v.get('label', k), fill=Theme.TEXT_MAIN, font=self.fonts['md'])
                draw.text((300, by+2), ago, fill=Theme.TEXT_SEC, font=self.fonts['sm'])
                by += 30

    def _draw_page_header(self, draw, title):
        draw.text((10, 10), title, fill=Theme.TEXT_MAIN, font=self.fonts['lg'])
        draw.line((10, 40, 50, 40), fill=Theme.ACCENT, width=2)

    def _draw_indicators(self, draw):
        for i in range(self.total_pages):
            color = Theme.ACCENT if i == self.current_page else Theme.CARD_BG
            x = 220 + (i * 15)
            draw.ellipse((x, 305, x+10, 315), fill=color)

    def _animate_transition(self, old_img: Image.Image, new_img: Image.Image,
                           old_page: int, new_page: int) -> Generator[Image.Image, None, None]:
        """Generate transition frames between two pages."""
        total_frames = int(self.config.ANIMATION_DURATION * self.config.ANIMATION_FPS)

        if self.config.ANIMATION_TYPE == "slide":
            # Determine slide direction (right for forward, left for backward)
            direction = 1 if new_page > old_page or (old_page == self.total_pages - 1 and new_page == 0) else -1

            for frame in range(total_frames):
                progress = (frame + 1) / total_frames
                # Ease-out cubic for smooth deceleration
                eased = 1 - pow(1 - progress, 3)

                offset = int(self.config.SCREEN_WIDTH * eased * direction)

                # Create composite frame
                composite = Image.new("RGB", (self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT), Theme.BG)

                # Position old and new images
                composite.paste(old_img, (offset, 0))
                composite.paste(new_img, (offset - direction * self.config.SCREEN_WIDTH, 0))

                yield composite

        elif self.config.ANIMATION_TYPE == "fade":
            for frame in range(total_frames):
                progress = (frame + 1) / total_frames
                # Ease-in-out for smooth fade
                eased = progress * progress * (3 - 2 * progress)

                # Blend images
                composite = Image.blend(old_img, new_img, eased)
                yield composite

        elif self.config.ANIMATION_TYPE == "minimal":
            # Simple "Cover" animation - New page slides over the old one
            # Direction: 1 = Next (from Right), -1 = Prev (from Left)
            direction = 1 if new_page > old_page or (old_page == self.total_pages - 1 and new_page == 0) else -1
            
            for frame in range(total_frames):
                progress = (frame + 1) / total_frames
                # Linear movement for snappiness (minimalist feel)
                # progress goes 0 -> 1
                
                composite = old_img.copy()
                
                if direction == 1:
                    # Next: Slide in from Right
                    x = int(self.config.SCREEN_WIDTH * (1 - progress))
                    composite.paste(new_img, (x, 0))
                else:
                    # Prev: Slide in from Left
                    x = int(self.config.SCREEN_WIDTH * (progress - 1))
                    composite.paste(new_img, (x, 0))
                    
                yield composite

    @staticmethod
    def _get_disk_usage(path):
        try:
            import shutil
            t, u, f = shutil.disk_usage(path)
            gb = 1024**3
            return (u/t)*100, t/gb, u/gb, f/gb
        except OSError:
            return None

    @staticmethod
    def _format_time_ago(date_str):
        if not date_str: return "-"
        try:
            # Handle timestamps (rudimentary ISO parsing)
            if date_str.endswith('Z'):
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            
            delta = datetime.now(timezone.utc) - dt
            secs = int(delta.total_seconds())
            
            if secs < 3600: return f"{secs//60}m ago"
            if secs < 86400: return f"{secs//3600}h ago"
            return f"{secs//86400}d ago"
        except ValueError:
            return "?"

    @staticmethod
    def _get_weather_desc(code):
        # Simplified WMO codes
        if code == 0: return "Clear"
        if code in (1, 2, 3): return "Cloudy"
        if code in (45, 48): return "Fog"
        if code in (51, 53, 55, 61, 63, 65): return "Rain"
        if code in (71, 73, 75): return "Snow"
        return "Unknown"

