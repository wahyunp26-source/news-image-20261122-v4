#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - Sunday 22 November 2026.
One-page newspaper front page summing up the world news of 22 November 2026.
Pure Python standard library, no network, deterministic.
"""
import base64
import json
import math
import random
import struct
import sys
import zlib

W, H = 1024, 1024

# ---- palette ----
PAPER = (250, 244, 228)
PAPER2 = (243, 235, 212)
INK = (28, 28, 28)
GREY = (90, 86, 76)
RED = (176, 32, 32)
DRED = (140, 22, 22)
NAVY = (16, 36, 64)
BLUE = (28, 76, 140)
GREEN = (0, 104, 68)
GOLD = (198, 128, 0)
PURPLE = (92, 58, 140)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

REG_EU = (28, 76, 150)
REG_ME = (176, 32, 32)
REG_AM = (0, 104, 68)
REG_AP = (198, 128, 0)
REG_WO = (92, 58, 140)


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def mix(c1, c2, t):
    return (round(c1[0] + (c2[0] - c1[0]) * t),
            round(c1[1] + (c2[1] - c1[1]) * t),
            round(c1[2] + (c2[2] - c1[2]) * t))


# ---- canvas ----
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        for i in range(0, len(self.buf), 3):
            self.buf[i] = bg[0]
            self.buf[i + 1] = bg[1]
            self.buf[i + 2] = bg[2]
        self.cx0, self.cy0, self.cx1, self.cy1 = 0, 0, w, h
        self._clip_stack = []

    def clip(self, x, y, w, h):
        self._clip_stack.append((self.cx0, self.cy0, self.cx1, self.cy1))
        self.cx0 = max(self.cx0, x)
        self.cy0 = max(self.cy0, y)
        self.cx1 = min(self.cx1, x + w)
        self.cy1 = min(self.cy1, y + h)

    def unclip(self):
        self.cx0, self.cy0, self.cx1, self.cy1 = self._clip_stack.pop()

    def set(self, x, y, c):
        if self.cx0 <= x < self.cx1 and self.cy0 <= y < self.cy1:
            i = (y * self.w + x) * 3
            self.buf[i] = c[0]
            self.buf[i + 1] = c[1]
            self.buf[i + 2] = c[2]

    def blend(self, x, y, c, a):
        """a: 0..255 opacity of c over current pixel."""
        if a <= 0:
            return
        if self.cx0 <= x < self.cx1 and self.cy0 <= y < self.cy1:
            i = (y * self.w + x) * 3
            if a >= 255:
                self.buf[i] = c[0]
                self.buf[i + 1] = c[1]
                self.buf[i + 2] = c[2]
            else:
                b = self.buf
                b[i] = (c[0] * a + b[i] * (255 - a)) // 255
                b[i + 1] = (c[1] * a + b[i + 1] * (255 - a)) // 255
                b[i + 2] = (c[2] * a + b[i + 2] * (255 - a)) // 255

    def rect(self, x, y, w, h, c):
        x0 = max(x, self.cx0)
        y0 = max(y, self.cy0)
        x1 = min(x + w, self.cx1)
        y1 = min(y + h, self.cy1)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                self.buf[i] = c[0]
                self.buf[i + 1] = c[1]
                self.buf[i + 2] = c[2]
                i += 3

    def rect_blend(self, x, y, w, h, c, a):
        x0 = max(x, self.cx0)
        y0 = max(y, self.cy0)
        x1 = min(x + w, self.cx1)
        y1 = min(y + h, self.cy1)
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                self.blend(xx, yy, c, a)

    def hline(self, x, y, w, c, t=1):
        for k in range(t):
            self.rect(x, y + k, w, 1, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, w=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        r = max(1, w // 2)
        while True:
            self.disc(x0, y0, r, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        if r <= 0:
            return
        for yy in range(cy - r, cy + r + 1):
            dx = int(math.sqrt(max(0, r * r - (yy - cy) ** 2)))
            self.rect(cx - dx, yy, 2 * dx + 1, 1, c)

    def disc_a(self, cx, cy, r, c, a):
        if r <= 0:
            return
        for yy in range(cy - r, cy + r + 1):
            dx = int(math.sqrt(max(0, r * r - (yy - cy) ** 2)))
            for xx in range(cx - dx, cx + dx + 1):
                self.blend(xx, yy, c, a)

    def ellipse(self, cx, cy, rx, ry, c):
        if rx <= 0 or ry <= 0:
            return
        for yy in range(cy - ry, cy + ry + 1):
            t = (yy - cy) / ry
            dx = int(rx * math.sqrt(max(0.0, 1 - t * t)))
            self.rect(cx - dx, yy, 2 * dx + 1, 1, c)

    def ellipse_a(self, cx, cy, rx, ry, c, a):
        if rx <= 0 or ry <= 0:
            return
        for yy in range(cy - ry, cy + ry + 1):
            t = (yy - cy) / ry
            dx = int(rx * math.sqrt(max(0.0, 1 - t * t)))
            for xx in range(cx - dx, cx + dx + 1):
                self.blend(xx, yy, c, a)

    def poly(self, pts, c):
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y_lo = max(int(min(ys)), self.cy0)
        y_hi = min(int(max(ys)), self.cy1 - 1)
        for yy in range(y_lo, y_hi + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    if y1 != y0:
                        xs.append(x0 + (yy - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.rect(int(math.ceil(xs[k])), yy,
                          int(math.floor(xs[k + 1])) - int(math.ceil(xs[k])) + 1, 1, c)

    def vgrad(self, x, y, w, h, stops):
        """stops: list of (pos 0..1, color)."""
        for yy in range(h):
            t = yy / max(1, h - 1)
            c = stops[0][1]
            for i in range(len(stops) - 1):
                p0, c0 = stops[i]
                p1, c1 = stops[i + 1]
                if p0 <= t <= p1:
                    c = mix(c0, c1, 0.0 if p1 == p0 else (t - p0) / (p1 - p0))
                    break
            else:
                c = stops[-1][1]
            self.rect(x, y + yy, w, 1, c)

    def hgrad(self, x, y, w, h, stops):
        for xx in range(w):
            t = xx / max(1, w - 1)
            c = stops[-1][1]
            for i in range(len(stops) - 1):
                p0, c0 = stops[i]
                p1, c1 = stops[i + 1]
                if p0 <= t <= p1:
                    c = mix(c0, c1, 0.0 if p1 == p0 else (t - p0) / (p1 - p0))
                    break
            self.rect(x + xx, y, 1, h, c)

    def glow(self, cx, cy, r, c, peak=200):
        """Radial glow: brightest at centre, fading out."""
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = math.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
                if d < 1:
                    a = int(peak * (1 - d) * (1 - d))
                    self.blend(xx, yy, c, a)

    def grain(self, x, y, w, h, seed, n, dark=(120, 110, 88), light=(255, 252, 240)):
        rnd = random.Random(seed)
        for _ in range(n):
            xx = rnd.randrange(x, x + w)
            yy = rnd.randrange(y, y + h)
            self.blend(xx, yy, dark if rnd.random() < 0.5 else light, rnd.randrange(10, 42))


# ---- PNG writer (stdlib only) ----
def write_png(path, cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ---- fonts ----
_FONT_CACHE = {}


def _font(name):
    if name not in _FONT_CACHE:
        data = json.loads(FONTS[name])
        glyphs = {}
        for ch, g in data["glyphs"].items():
            bw, bh, xo, yo, b85 = g
            bits = base64.b85decode(b85.encode("ascii")) if b85 else b""
            glyphs[ch] = (bw, bh, xo, yo, bits)
        _FONT_CACHE[name] = (data["ascent"], data["height"], glyphs, data["adv"])
    return _FONT_CACHE[name]


def text_w(s, font):
    _, _, _, adv = _font(font)
    return sum(adv.get(ch, adv.get(" ", 12)) for ch in s)


def draw_text(cv, x, y, s, font, color, align="l"):
    """Draw text; y is the TOP of the ascender line (PIL 'la' anchor)."""
    ascent, _, glyphs, adv = _font(font)
    w = text_w(s, font)
    if align == "c":
        x -= w // 2
    elif align == "r":
        x -= w
    px = x
    for ch in s:
        g = glyphs.get(ch)
        if g is None:
            px += adv.get(" ", 12)
            continue
        bw, bh, xo, yo, bits = g
        if bits and bw > 0 and bh > 0:
            gx, gy = px + xo, y + yo
            bi = 0
            for yy in range(bh):
                for xx in range(bw):
                    byte = bits[bi // 8]
                    if byte & (0x80 >> (bi % 8)):
                        cv.set(gx + xx, gy + yy, color)
                    bi += 1
        px += adv.get(ch, adv.get(" ", 12))
    return px


def wrap(s, font, maxw):
    words = s.split(" ")
    lines = []
    cur = ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if text_w(trial, font) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, s, font, color, maxw, lh):
    for ln in wrap(s, font, maxw):
        draw_text(cv, x, y, ln, font, color)
        y += lh
    return y
# Font data: 1-bit packed bitmaps rendered at build time from Liberation Serif.
# Each font is ONE line: (size, ascent, {char: (width, base85-bits)}).
FONTS = {}
FONTS['SB64'] = '{"ascent":58,"height":72,"glyphs":{"A":[48,45,-1,14,"0000000000ANT+O001BO00000AN&9S002My00000Kl}gy002M!00000fBpaf004jg00000^Zx(<008s<00000^Z$SV00H6ufB*mi;s1aD00F@NzyJUP!2iGi00Y4P-~a#zfPdfs00)47-~a#zfPe4+01p5^@Bjc006*{m01f~@_y7PN03Y}O03HAz`~Uzv01x~C06+i#`~Uzy|Ns5~0Du4g{r~`f|Ns5~0C)fg{{R5+00aL30Pp|<|9}DT00aMk0pI`u|9}DD00IBN1K<Dw|G)#l0095M1Hb?P|KJC}0095s2Y>(ofABx}00;m4Kl}g>|NcMx01yBE00000000"],"B":[45,45,-1,15,"0000000IC1|KI=*|NsBs06+i#|G)qr|Ns900RO-r`~V030DtfRKkxznfC2x25B>lT`~ZLO0Ds^E|9}Jk03ZASANT<O-~j)?2mSyD{s2Gl06*{n{{R91fFJk(5BvfDfB=8sANT+R|Ns9003ZMV-~a&s|Nrm+2mk;7-~d1H0sp`O|9}Vo01x~CAN&A+-~fN%1OEU6{{SEO03ZAS|G)tM;0OKy1OEU&@Blyf0snvj|G*FY01y5Ef8YRr-~;~v1OEUY_y9ln0RO-N|9}Vn03Y}OKllg#fFJ+=|M&s_|Ns905C8xFzyJUM0000000000000"],"C":[48,46,-1,14,"00000000005C6ab00960{r~_2|NsBM01yAc|G)qr`~V-o06*{m2fzS--~a=_0RO-M1Hb_PzyJfl0snvi1Hc3S0005N1OEU30l)+Q000002mSy6000O6000002mSy6000O6000005B>lE000mE000005B>lE000mE000005B>lE000mE000005B>lE000mE000005B>lE000mE000005B>lE000O6000002mSy6000O7000001OEU30l)+Q0005N1OI>k0l)$OfB*r&0RO-M0l)zNzyJZj0Ds^B1Hb@3_y7mM03ZASAHV<y|H1#j00aO3|G)qMfB*gf000mFfB*mh00000"],"D":[48,45,-1,15,"00000002M#|M&m^KmY&#fB+x=|Nr0s0ssI1_y7U_fIs{I0snvx{s000fCv8o0snvl|9}DifC2x20snvj|G)wNfB^r%0snvi|KI`tfB=8s0snvif8YWCfB=8+0snvifA9hSfB=8+0snvifA9hSfB--60snviKkxznfB--60snviKkxznfB--60snviKkxznfB--60snvifA9hSfB=8+0snvifA9hSfB=8s0snvif8YWCfB=8s0snvif4~9%fB^r%0snvi|9}DifC2x20snvj{{R91fCK&j0snvx`~U&};D7i4AOHXV@Blym|NnphKmY&y000000000000000000"],"E":[45,44,-1,15,"0000000IC1|Nr0*|NsC006+i#|M&nO|NsBM0RO-M9smda008g+KkxttfC2x206YK>`~U#p0Ds^B2LJ>A001}uANT+O0095M00007{r~^~06*{m-~a*tfCm5o5BvZ)004jB0l)wQ{{S8U03ZMV@Bje+|Nnph2mk;4002M#|KI=t|9}qw01x~CH~;{D-~qq@1OEUH001BO00000|G)qM00;g60000#@Bjc{0snvi2LKQJ001}uf8YQCzytpP01f~j_y7R#0RO-M2Y?6u002AyKmY&#;2;10|NjC1|NsB^5C8xF|G)qM00000"],"F":[41,44,-1,15,"0000003ZMV|NIaC|Ns62|NsC003ZMV|9}tt00Y1W{r~~s1OEU3@B#mT05|~uzyKTof8YQP06*{m2LK=V0000F`~Uy|2mSy600aL300061fB*mh|G)<T0Ds^EfB--60l)ws_yFJl5Bvad00;m7_y7a{|NH;}|Ns5~0RR90004jB1AqWO@BzR8ANT;^01x~CZ~zDX05|{x{{R300snvi0095M0001g-~a#sKkxtm03Y}O000mC00007{r~^~1OEU303ZMU001BV|9}7w|Np=M00000000"],"G":[52,46,-1,14,"00000000000Dt}f0001g|Nj6003ZMV{r~_6|HJ?A0095M0sjC1Kkxtp@Bjz?0018V0Dr&$0Pp}0`~UzC00IAi008g+AMgMG4*&!I0001R06*{m00007{r~^~004jB000002mSy60001g-~a#s01y5E00000|KI=s000mE000000RP|s0000F{r~^~0095s000005B>lE00030-~d1W_z(U71ONYk|KI>0|L_O?001BO0Ds^B0snvp{r~_U_yB+400IAi1OEU3ANT-2@Bjh-fC2x203Y}OANT+P|9}AhzyKfk00;a40snvif8YQg_y7a{fC2x201x~CANT+OfBYZ+fB*si|Nrm+00;m7@Bjb+2minT000000000"],"H":[52,44,-1,15,"00000000C3|KNZB{6GKx2mk-U|Np>0|M&s_fB--603Y}O1OEU4|9}8L@Bkn900aL30snviKkxt__y7a{00IAi06*{mANT+R{{R91fB--603Y}O1OEU4|9}8L@Bkn900aL30snviKkxt__y7a{00IAi06*{mANT+R{{R91|NsB+03ZMV|Nj61|NsC0@BknG|Ns900snviKkxt__y7a{00IAi06*{mANT+R{{R91fB--603Y}O1OEU4|9}8L@Bkn900aL30snviKkxt__y7a{00IAi06*{mANT+R{{R91fB--603Y}O1OEU4|9}8L@Bkn900aL3AOHLV|Nn#k|KNZB{6GKx2mk-T00000000"],"I":[27,44,-1,15,"00003|Nr2B|NIC4{{RpC00IAi06*{m2mSy6|G)qr_y7a{004jB01x~C0snviKkxtt{r~{~zyKfk00aL30Ds^B5BvZD|9}8L@Bjz?0095M03Y}O1OEU3f8YQQ`~U&}fB--600;g60RO-MANT+R{{R4g-~bQ&00IAi06*{m2mSyL|NaC2|KNZB`~Uy|00"],"J":[34,45,-1,15,"0000000;m7fC2yi-~d1W@BjdR-~a$0_y7P0{r~_0|9}7hf8YQBANT+O2mSy60snvi0Ds^B03Y}O00;g600IAi004jB001BO000O600061fB*o0-~a$0_y7P0{r~_0|9}7hf8YQBANT+O2mSy60snvi0Ds^B03Y}O00;g600I91004i$0{|cJ0N@Aw05}2v01g2EfCGR(-~jLs@Blmq_y7;b{s062{r~{~{{R3V{r~^~00000"],"K":[52,44,-1,15,"00000000C3|KJb*;6MNV0RR30|Np=T|G)wNfB+AG03Y}O0q_6;|9}8K001BO00+PT0snvj_y7PO_y9iu00IAi2jBnzANT<H00061fFA$=03Y}R-~a#t|A2e|001BO4}bsw0sn*W0000V_<w)^00IAx`~Uy|ANl{l00061zy1IK03ZMV@Bjb-|NsAh001BVfBXOd0srIwzyJUr{2%@R00IAi|L_0+ANU9VfB*sifPee|03Y}R|G)qN|9~I<001BO0RQj+0snvx|9}7=_yB+S00IAi1OLDPANT+t{s000fC2yT03Y}O5C4Dx|9}90_y8aH00aNPAOHLSAOFMu|KI`t{6GKx01yAb00000000"],"L":[45,44,-1,15,"0000000IC1_y7P8|Np=M06+iy0000V_y7O^0RO-M000O600000Kkxtm00IAi0000F`~Uy|0Ds^B000C300000ANT+O0095M00007{r~^~06*{m00061fB*mh5BvZC004jB00003{{R3003Y}O00030zyJUM2mSy6002Mm00001|9}7h01x~C0001g-~a#s1OEU3001BO00000|G)qM00;g601f~@@BjdC0snvi2Y?U!002Ayf8YQC-~;~v01p5k_y7R#0RO-M2Y?6u002AyKllJY;2;10|NjC1|NsB^5C8xF|G)qM00000"],"M":[62,44,-1,15,"0000000000|Nnph0RR8P|NZ~~1ONXA|NH;|5C8Z9|L_0+fBXOk|KI=t|L_1G|9}7w|G)r${r~_!{{R91`~U&}`~U~P@Bjz@@Bkiv-~c}VzyNvwfB^gd00HO!00Ynb00)o!03Sc_03JW^0C@kv0C<1k1LOYy0pb6E4-fnR2ZR3rd_V929uNEh@c+O7cpvx=gZ}^l;D6vg5BvZJf&akpKkxt^1OErW|G)rv5Bwej{{R8tANcqW`~U}lf8)SE@BkhF|K9-rzyNpy|9k`g00H0+|KJb&00)2{|A0U603HB;`~d&J0C)iZ@B{w<0pJ7wfDilt2Y?6u06*{m9snQk0RO-McmO}Z1OEU4-~j&s5BvZJfCKmdKkxt^00-az|G)rv03QGY{{SEV06YNy|KR`r0N@Az|HJ?I0e~O>{{R300000000"],"N":[48,44,-1,15,"00000002M#fC2yfKmWi1|NI~S-~fO40sr6t2Y>+o@BjyZ0RQ*^2Y>+o`~U}l0RQ{|2Y>+o{s0Gn0RR602Y>+g|9}U80Q3KV2Y>+a|G)=;0P+9e2Y>+Z|L_NZ0PuhC2Y>+ZKllfL0Pr9D2Y>+ZAN~h`0Pqk02Y>+Z2mc3v0Pq9<hkyX^1OLZ>0Pq3-=YRn40RQKJ0Pp~R_kaNK0Du300Pp}m|9}AS03ZK=0Pp}0|9}AS01y9w0Pp|@|9}AS00aMk0Pp|-|9}AS0094h0Pp|+|9}AS004i00Pp|+KY#)70019=AO8RVAAmpqfB+AGKmULL2Y>(o00000"],"O":[52,46,-1,14,"00000000000RQj+00030|L_0+06+i#zyJUb{s;d600I91ANT+Of8YRrzyJsQ00aI20RMmhAMgMl_y7U_fC2vi03Y}OKkxtm|G)$P000mC0Ds^B0RO-T{r~_6{s4dA004jB2mSy62mS#6-~a%B;1B))00;g6|KI=sfAA0f000O70RP|s0Dtfg{r~_6{{a8s004jR5B>lE2mb*7-~a%B@DKg~00;j7|KI=sf8Y=P000O60Ds^B0Ds^I{r~_6{s4dA004jB2mSy65BvZ>@Bje+zytpP01x~CAMgMH|9}DifB+xx01x;81OEU3f4~4g-~a>u00;a403YxH|9}7h|KNY{000C3|NH;|01yBF000005B~rF000000000"],"P":[41,44,-1,15,"0000003ZMV@Bk10|Nnpk|NsB+03ZMV{s0gB1OI>r{s8~L1OEU&@B#mTANT<Ozz6;Sf8YcE06*{n|9~I(0RO-b`~ZL82mSy*@B{w<ANT?PfDilt|G)?S0Ds^E{{TPm1OEUY_yPZb5BvfDfCv5o|G)$P|Np=N|NsAh0RR90fB=90`~Uzy@Bjb+ANT+O01x~C000O600003{{R300snvi0095M0001g-~a#sKkxtm03Y}O000mC00007{r~^~1OEU303ZMU001BV|9}7w|Np=M00000000"],"Q":[52,56,-1,14,"00000000000RQj+00030|L_0+06+i#zyJUb{s;d600I91ANT+Of8YRrzyJsQ00aI20RMmhAMgMl_y7U_fC2vi03Y}OKkxtm|G)$P000mC0Ds^B0RO-T{r~_6{s4dA004jB2mSy62mS#6-~a%B;1B))00;g6|KI=sfAA0f000O70RP|s0Dtfg{r~_6{{a8s004jR5B>lE2mb*7-~a%B@DKg~00;j7|KI=sf8YoH000O60Ds^B0Ds^I{r~_6{s4dA004jB2mSy65BvZ>@Bje+zytpP01x;8AMgMH|9}DifB+xx01x;81OEU3f4~4g-~a>u00;a403YxH|9}7h|KNY{000C3|NH;|01yBF000005C8Z800003|G)qM001BU000000sr6t0000F{{R30004jd000001OMOv0000V|L_0+00960000001OM;<0000F_y7O^00000"],"R":[49,44,-1,15,"00000001BV|NH;|5C8xF-~a>v|Nr~|03ZMV|9}7w`~d&p00;g6ANT+R{{RR400IAi1OEU3|G)wNfB=8s0Dr&$KkxuQ-~b=^03Y}O5BvZR`~V0300;a41OEU6{s000fCK*k0RO-N|9}90-~j)C06*{m|G)qr_yGUF01x~D|G)qT|NsBM00aO3|G)qN|NsAh00960|G)qMf8c-c002MmANT+OANUXc000mC1OI>k2mS#6zyJgP0DtfR0snv>`~U#|zz6>T0Ds^E|9}8L@Bshd03Y}OKllI-`~V;R00;g62mb&A{{R91z#sqo0RR3U|Nj6#|BwIwfDiw`00000000"],"S":[38,46,-1,14,"00000000mFfB*si|KI>0|Nnph|AYPj2k-&-06%~M-~jvp2Y?6g03HAzzyLS^e*ggB0sH_1fCumZ001B00001gzyJUN|G)qM2minT03ZM0002M#@Bje+|L_0-|Nrm+1ONZv00;m7-~b2z|9}7w|Nj602mk&600;m0000C3-~a#t|G)qM1OEU300;a5fB+Bh4gdfjz&ro|e*o|R0sI5N00-a?0019=JOBXx0Qdj{@B{DwAHWar0R8|!_#f~9|NsAh0RR8^001BV000000000"],"T":[45,44,-1,15,"0000000IC1|Ns9F|NsC0_<#TZ|Nq1M2mc5D9sob^0Pyeu|9}UF01x~CJU9S<-~r*l1OEUI4geqc061^}|G)vmfCv5n4gdf@@Bjb+0snvi000mC00000f8YQB00aL30000V_y7O^0RO-M000O600000Kkxtm00IAi0000F`~Uy|0Ds^B000C300000ANT+O0095M00007{r~^~06*{m00061fB*mh5BvZC004jB00003{{R3003Y}O00030zyJUM2mSy6002Mm00001|9}7h01x~C000mF|9}7h|Ns5~00;m7@Bjb+00000"],"U":[48,45,-1,15,"00000001BV{sI5|AOHRV|NI~S`~d&>0snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80snvi2Y><pfB*-80RO-M2Y>+ozyJ>b0RO-M4*&pv-~b;00DtfR9smG8_y9ft06+Wy`~UzS|L^z!01yBF@Bjb<|Nr0s00960fB*mhAN&9S00000000"],"V":[48,45,-1,15,"00000002M#@BlylKmYImKmI@e-~b=|2mb&71Hc3S000BP1OI>k2fzXUfB*-80sp`N2Y><pzyJ>b0RO-M4*&rF-~b;00Ds^B9smG;@BkhF06*{mJOBVc_y9Zr06+Kud;kC+_yBkS03ZAScmMzo`~dI(01y5E@Bjb@{sHg+00;j8-~a#z{{i3t00aL6zyJUP|AW8)00IApzyJUN|Hps;00IBUfB*mh|IYvb0095*00000fBpaf004jf00000KmGs!002My00000Kl}gy001BO00000ANT+O000m8000005AXm0000N@000002jBnz000Nz000001K<Dv00000000"],"W":[66,45,-1,15,"00000000005C8rE000mF!~g$)000C3@PGfn0001g_yhj{00000@Bsh701towd;mZA00ZCv9{>mb00H~}2Y><pfB=601K<FE@Bkmc0Qdk8`~VO506YK#|9}Jj03QGV|KI`tzz4tpANT-&@B!ce2mb&c`~Y|W0sp`c|A0OK06*{p|KJaR01y5F|NH~M00IAifBymS004jB9{<36001BS55M>x000C31IPXkfB*ph!SVmY-~a$W_<TR`@Bjb@{vHqfJOBUz|IdT}p8x;=fAhe9=YRkJ5B=~T{onuq1ONO3|M&m^0RR2~|NH;|03ZK=KmPy#00;lT2minT00IB-0srs-002My06+Ku000mE01y5E000C3fC2x20001gzyN>10000V@Bkn100007`~U;|00000{r~{}00000KY#!qfB*mh55NEi-~a#s0q_6;@Bjb+0DJ%dJOBUy0000000000"],"X":[48,44,-1,15,"00000001BV{{#Q<AOHUY|L_n0{sI5s0RP|sJ^%oJ@Blmj06*{md;kDH_yG6-03ZAT@Bjc0`~lzq01y5HzyJUT{s+JS00aLIfB*mk|DON=00IA=00000|NH;|0095|00000fA|0Z002Mm00000KllIu001BO00000AN&9S000mE000005B>lE001BV00000KmULL004defB*mh`TxKG008j+zyJUN@PFU{00ZEE@Bjb@z(4Q+00)2{_y7P803ZAS03QGk`~Uzx01y5E0DJ%k{{R4Z00aL30Pp|<|9}DT00IBNAO8R!|NKAyfIt8KKmUL~|NZ~~00000"],"Y":[48,44,-1,15,"00000002M#{{a8|KmY##|NI~S{s4dY0sp`N2Y>+o-~bPR0RP|s4*&pv@BkkG0Dt%ZJ^%ne_y9ft06+Wyd;kC+`~Z9a01y5E_y7P8{s8y@00;j8@Bjb@{{i3t00aMn-~a#v|AW8)00IBUzyJUN|Hps;0095*fB*mhfBygg004jg00000KmGs!002M!00000AN&9S001BS000005BvZC000mC000005BvZC000mC000005BvZC000mC000005BvZC000mC000005BvZC000mC000005BvZC000mC00000AN&9S00aO3-~a#z|Nrm+00;m7@Bjb+00000"],"Z":[45,44,-1,15,"00000001BV|Nr0s|NsC000;m7|M&nuzybfj0pI{1{s0dE0RP|sZ~zbf00V#k|L_1D00;j70N?<B@Bjw@2mgQo002Mu00003|9}7h06+Wy00061zyJUMAN&9S00IBt0000F{r~^~0RP|s000mF00000fA9bR00;j70000#_y7O^1OI>k002Mu00001|G)qM03ZAS00061-~a#s5B>lE0095s0000F{{R5s0DtfR2LK2E001}ufA|0azytq)03HB8_y7R#1OLDP2Y?^^002Az|KI@s;1B=*|Nj7g|NsB^1ONa3|G)qM00000"],"a":[34,33,-1,27,"0000000;ko03ZMS00;m7fC2bF@BnxR`~VyP|9}PnKi~m?5BLCJ1O5O20RMmh06*XW01x;800aI20ssGi2mk-z1ONZ{0sn*k0RMphfIr|r;2-c0_y_z0{sI30|A2qMKj0tm5BLZC1O5U3fd7C$@PFVB|Ns60|NsBMKm3321N;C00000000"],"b":[38,47,-1,13,"000000RQj+00aNP000O700007`~Uy|AMgMG0Dr&$00I91000O40000V@Bjb+f4~3$0sjC100;a4001BG0001gzyJUN{}1p02mSx}03ZMV@Bn}R|KI`t0RO-T`~m*}AMgkM0Dr&__yPX_Ki~)a0RO-r@B#k-f4~R)0sjCW@CW<=f50E`0sjDhzz6&R{{SEG2mAnkz#s4d{{Vl$2mAs506*Xd`~d%eAMgYI0Dr&_@B#k-f4~R)0sa6V@DK0+fAIf+0ssH}00IC1-~a$0`~Uy|00000"],"c":[30,33,-1,27,"0000003ZAS0ssC0AOH9O|Ht45{0D$P;0^)*05}Ky0N_910f7I21_S;803Y}O0Dr&$0sjC12mAm4AMgMGf4~3%{{R37{r~_U_y7Pu-~a&sfB*yj000O4001BG002MW0095s3<3ZD@B#n-zybgM0095M00000"],"d":[38,47,-1,13,"000000000V{r~^~fA|0Z0RP|s0094h000C20000F_y7O^Ki~iW0RMmh00aI2000m80000#-~a#s|9}7h1O5O201x;80slYX06+i#fC2yi{s15NKllKDz(3#v{s8}gAMgYI0Dr&__yPX_Kj07e0RMnL-~;{u|9}tp1O5O%;1Bo!|A0T>1O5R2fDiZs{s2GV5BLE8fIr{^{s8}g5BLNA06*Xl_yGTaKkx(o0Dr&__yPX_Ki~uY0RMmw{0II3AOHXS06+i#`~W}x|L_1mzyJUM00000"],"e":[30,33,-1,27,"0000006*XW2mjyzKmWi1{(pcE@c#gRf&Kyh2lx;8AK*XWe}Mmi{{#F7{2%Zi@PGgR!T<mN2mk;4ANT+Of4~3%{{R37`~UzS_y7Pu-~a&sfB*yj000mC001BG004jB0095s7y<wP-~<2vfCK;d00I9100000"],"f":[24,47,-1,12,"000001O5OX{s2Gz0Dt}f{|*8F4gvlK0saO9{s06100aI21O5O5{s06100aI21O5OX|M-9Z_<#TS1O5O5{s06100aI21O5O5{s06100aI21O5O5{s06100aI21O5O5{s06100aI21O5O5{s06100aI21O5O5{s06101y9wAOG+l|L_0+00"],"g":[34,49,-1,24,"000000000000000-~a#s_y8aL`~V;S{s15U|9}tp|G)?QAMgYI1O5R2fd7C$;2+=*@CW<{`~m*~{{Vl$KfoXG5BLZ81O5a40RMphfFJOGzytn2-~fOB@Bk10_y7a{@Bjet0001Z0000!0000VzyJUb_y7O{|Nrm+|NsAhKmY&m2mk;60ssI1z(4>0@B{z<`~mO-{{ip-AHe(o2k?FX0sJ3;0DlMI03U(;01x1QfDiBw{y+Eu|Nr~|AOHLS0RQj+0000000"],"h":[38,46,-1,13,"000000Dt%Z00IBt000C3fB*mk{r~^~5BLB806*XW0094h000C20000F_y7O^Ki~iW0RMmh00aI2000m80000#-~a#s|AG7f1O7k!01x~B_y9lu|L_3+^Z&pD{saF25BLZE06*X#_yGTaf8YcD0RMmw_yhg`Kj07e0RMnL-~;{u|9}tp1O5O%;1Bo!|A0T>1O5R2fDiZs{s2GV5BLE8fIr{^{s8}g5BLNA06*Xl_yGTaKi~uY0RMmw_yhg`|L{Nj2mj&!{2%{^|L_0+0000"],"i":[20,46,-1,13,"0000600H;_KfnY20Ds^I{s4dA1N;CVzyR<7000000000000000AN~RV;1B))Ki~uY06*XZ{s2GV1O5O%-~;{uKi~uY06*XZ{s2GV1O5O%-~;{uKi~uY06*XZ{s2GV1O5O%;1B-;|NKAyzyJU"],"j":[24,60,-2,13,"000002LJ#czyLqM06*XWKi~jA-~d1106*XWAHV<)fB*mh0000000000000002mjy)|KI`t-~d1106*XWKi~jA-~d1106*XWKi~jA-~d1106*XWKi~jA-~d1106*XWKi~jA-~d1106*XWKi~jA-~d1106*XWKi~jA-~d1106*XWKi~jA-~d1106*XWKi~jA;2=N1aDTvXf53SEfPeo0fBpb}`~W}T00000"],"k":[38,46,-1,13,"000000Dt%Z00IBt000C3fB*mk{r~^~5BLB806*XW0094h000C20000F_y7O^Ki~iW0RMmh00aI2000m80000#-~a#s|9}7h1O5U3zz_Hb{{TPW2k-#@fFA$@{s8y@5BLYb06*X!0094h@Bjn;2Y>(%_&fjrKjH8I0RNBR00aJifB+Bs{{R3#|NZ~~|Nr;^1ONZ<01y0s-~d11|9}AhgZ}^n{s;U35BMMW06*YA@BsgS|G)$O0snvx_yhj{|L`CF2mkQ@{vZFt|M&m^0000"],"l":[20,46,-1,13,"000C3;6MHV|KJDy0Ds^I{s4dA2mSzm;0OKyf8YoH0Ds^I{s4dA2mSzm;0OKyf8YoH0Ds^I{s4dA2mSzm;0OKyf8YoH0Ds^I{s4dA2mSzm;0OKyf8YoH0Ds^I{s4dA2mSzm;1B-;|NKAyzyJU"],"m":[55,32,-1,27,"000000000001w~;_yB+K|L{Nj0RQLz@&Eh)|NsC0|M&oZ`TzcZ_yGTa|KLCH0sjF1fIr{^{sI30f4~R)1OEX3fDiZw{sI30AMg+S1O5O%;2-!0`~ZKzKkyIu0RMo0;2-b-{{a8MKi~uY0snx1zz6&T{{a7h5BLZE0sjCW@DKb0{s2GVANU9S0Dr(g@DKO^|A2qsAMgSH0RO;0-~;{v|A2qM2mAy70RMmw_y_(0{{SEG5BvlE0RQkm{15*F|M36(KmP~+;s5x5{r~^~00000"],"n":[38,32,-1,27,"000000000Vzybfm|G)?TKmULa|Ns905C1>>06*YA@BsgSf8YcD0snvx_y_&~Kj07e0RMnL-~;{u|9}tp1O5O%;1Bo!|A0T>1O5R2fDiZs{s2GV5BLE8fIr{^{s8}g5BLNA06*Xl_yGTaKi~uY0RMmw_yhg`Kj07e0RMnL;1B-;|G<C#AOFGs_<#QZ00000"],"o":[34,33,-1,27,"0000000I9100aN<00aO300I9$-~j&v`~W||{{SE0AK(Z02lxa20sjF1fPcV0;2-c0_y_z0{sI31|A2qsf8ZbZANU9U2mS&7f&YMi;6LCW@DKP0`~&_0{{a7hf51QBAMgkG2lxU00sa6#!2bXb@ISx-|3BaWKmYIm1OM;<06*XW0000000"],"p":[38,46,-1,27,"000000003000aNu{{RpF|Nj6V|Ns5~ANUXa0Dr(A@B#k-f8YoF0RMm=@B{t;f4~p?0sjC$@CW<=f50E`0sjDhzz6&R{{SEG2mAnkz#s4d{{Vl$2mAs503YxN`~ZKzAMgYI0Dr&__yPX_Ki~)a0RMm=@CW<=f50E`0sjF1fCvAN`~V;S|KI?B|Na00|9{{B2mAm403YxG004i$0006100007`~Uy|AMgMG0Dr&$00I91000O40000V@Bjb-|L_0+5C8B006+i0000000000"],"q":[38,47,-1,26,"00000000009smG;`S<`2|Nr0sfB*l01OE^H03YxV_yGTaKi~)a0RMm=@B{t;f4~p;1O5O%;1Bo!|A0T>1O5R2fDiZs{s2GV5BLE8fIr{^{s8}g5BLNA06*Xl_yGTaKi~uY0RMmw_yhg`Kj07i0RMm=@B{t;f4~p;0RMnL-~;~w|9}Vo|Na0E|Nr;^5C6a501xp0fB*mk{r~^~5BLB806*XW0094h000C20000F_y7O^Ki~iW0RMmh00aI2000m800030@BjcG|L_0+fB(P$00000"],"r":[30,32,-1,27,"00000000BQ|KL9d|AYJo{vYrU`2WB^=l=lz|NI00_;3&Z0l+`-0|5WP3<LiF01x~C06*{m0RO-M1OEU35BvZCKkxtm|G)qP{{R3F`~Uzy@Bje+zyJgP000mC002Mm0095M00;lT0Du3$0ssF100000"],"s":[27,33,-1,27,"000005B>lL|L_6-{s4Xtz#o8k1K<Y$`~YAdfD8lp0Dymh01x~C0srs-AOFAu|Na0!|KJDz{s2G!zytsM03ZK=0DtfR0saO6AHcu?_#6N~1AqtMZ~*)dfIk8J55PbF@CX0=01x~C00000"],"t":[24,39,-1,21,"00000J^%oI004df0R8{~{r~~~00I605C8Z-|M)-u_yhg`1O5O5{s06100aI21O5O5{s06100aI21O5O5{s06100aI21O5O5{s06100aI21O5O5{s06100aI21OEU6{{R91`~d&_0Dt@dAK(B000"],"u":[38,32,-1,28,"000000RQkm`~&~M|L_O@0RO-T`~m*}AMgkK0Dr(A@B#k-f4~R)0sjCW@CW<=f50E`0sjDhzz6&R{{SEG2mAnkz#s4d{{Vl$2mAs503YxN`~ZKzAMgSH0Dr&-`~m*}AMgkK0Dr(A@B#k-f4~R+0sjCW_y_y|fB66K0RR90-~s>r|KJ1vhyQ>F_y7O^00000"],"v":[34,32,-1,28,"00000AOFCA=l}2@`2X+${2%xLJ_G&$4*>tb1Hd2f0pJJz0C)iZfII*{@DBhF`~$!N{{i3tf8clk5BNL)1OE>I0Dr@P03Z3_00aJb0095|001BV000O7fB*si-~a$W@Bjc0`~Uy}{{R30e}Di058wa*1MmO<0DJ%d03HAU00000"],"w":[48,32,-1,28,"00000004jg000O6fBygg2mU|&0005}5BLCh0Pqj^0C)iK5BLE10PqL=0Q>>q2mAs20pJJx0saBt1O5U21Hc3R1O5ZR0sjO41Hb|Q2mc3v0sja8hkyY8hku6v0RNAFj{pFFj(^Vp0Ds;;&Hw;^+&}&R06+X6{r~_!{2%-P06+L2`~UzS_z(O503YxV_y7P8@CWz+01w~?@Bjc0;0N#k00-a$@Bjb@zysg_00Y1Q-~a#s00000"],"x":[34,31,-1,28,"000005C8H1ga7=0;D7uF@CW_?@Bsh7cmN;pJOBs&9{>RV&wv0w_rL%L|KI=s|L_0+KllIu2mSy60RMmh06*{m00;g600aMk0095+004jf002DyfB+sp@Bj~o{s0HS|9}JFKkxwX2mSzf0RMn~0Dt&@;D7(0_#gk^00000"],"y":[34,45,-1,28,"000005C7nQ!~ggn@PGIN_z(C1JOlp#9{_*A2Y?^=0pJ7v0Pq0+z&rpS@DBh7{s({o|AF8DKj82H5Bxj;0sjsF0DtFz01x@#00aN<0095|001BU000O7fB*ph-~a$W@Bjb@`~Uy}{r~^~e}Di058wa*1MmO<0DJ%d03HAU00)2o00F=N008g+002Ay0015U05}JL01gAd00V&V008iK002My000mF000C30001gfB*mh00000"],"z":[30,31,-1,28,"00000fB*jh|Ns04|NrnG0snw_2mS%zKkx?t|G*pv{s1r^_y7R^zyJsT001BO0095M00aL303Y}O0Ds^B1OEU35BvZCf8Y!O|A250`~ko}@CO0^fE*9}0PsKX1Hu1*J_rB*_&@*u;Q#;sfB*mh00"],"0":[34,46,-1,14,"0000000I6000IBt00IC00093#zyLpo@Bkmc{s0f~KfnY05AXs01O5PifPa7=;2+=*_y_z0{sI30|A2qMKj0tm5BLZC1O5U30RMo0z<=N$_#gNO{s;a6|AGI2f8c-MANU{m2mS~C0sn#jfPdgW;2-c0_y_z0{sI30|A2qMKj0tm5BLZC1O5U30DpjgfFIx=;0O2*_yGR{`~W||{{RQ@KY#%KAHV=V&+q^T|M&m^fA|0Z2lxO000000"],"1":[34,44,-1,15,"000000018V001Ar000m0000mC000O7000O7zyJsT@Bjn<`~U#?{{R3mf4~3$AMgMG2mAm40sjC10Dr&$03YxG00;a400I91004i$001BG000O4000610001gzyJUr@Bjb@`~Uy}{{R30f4~3$AMgMG2mAm40sjC10Dr&$03YxG00;a400I91004i$001BG000O4000610001gzyJUr_y7a{|NH>||Nj6#|Np=M0000"],"2":[34,45,-1,14,"0000003ZAS0Du4R03ZMU00;2@zya_N_yBkT{{S8Uf8Ymz5BLGV1O5PT0RMm-06*XW01x;800aI20094h002MW000m8000C2000610001gzyJUr-~a#*_y7O{`~Uy}{r~^~{{R30e}Di0AHV<r58wa*2k-y@1MmO<0r&s_0Q>*|0Db@f06zc#03Uz=01tow00+PT00aO3{{a90|G+>0|L_n0|NI00|Nj90|Np>0|Nrm+00000"],"3":[34,46,-1,14,"0000006+Wy0Du4R03ZMU00;5^zya_d_yBkV{{S8Uf4~O-ANT>l2mSzX0RMm-06*XW01x;800aI200IAi004i$001BG000m8000O6000O7001BV000O700061@BjdR{{R30f8YQB2mAm40RMmh03YxG00;a400I91004jB000m8000C200061f#3jt;CKKZ_#OZU{0D#m{{Zj+|G+!|f8Y-QKkx(iKllLu|NH<y|NH;||M&m^00000"],"4":[34,44,-1,15,"00000000C0000300001gzyJV0@Bjc0`~Uz4{{R33|G)qM|L_0+fBXOdKmPy#4}ZV_2jB1j0q6Vx0P+6-0DOPI03ILk01pTJ00+VU00H2CzyR<c@Bn-V`~V&S{{RmFf4~R8AMgR-2mAo=0sjDe0Dr(A03YxV|NsBP|NsB+|NsB|KmY&#5C8xF!~g&P@BjdRzyJUr@Bjb@`~Uy}{{R30f4~3$AMgMG2mAm40sjC10000"],"5":[34,45,-1,15,"000000RR8|06+i#01yBFzytsP@Bsh+`~W}y{{RpF|G)!)0002s0000u0000E00003fB*mh-~a#sH~;_u4gdfE1AqVk0N?-s06G7F01yBC00aO3zySC^_y7O{{{R30Ki~iW5BvZC0sjC10Dr&$03YxG00;g600IAi004jB001BO000O61Aqbl0N?<Bz&HRO@D2b6`~$!P{s8a+|A0OK|G*FM|KJ1v|KI@s|L_0<|KI=s00000"],"6":[34,46,-1,14,"00000004jB004jgfB=90-~d0v_y8Z^J^&B!2Y?6o0pJ1t0C)iZ03HB;zyp9E@BrWk_y7O{{r~^~|9}7hKi~iW5BLB81O5O20so)i0Du4g03ZMV;0OQz`~m-g|A2qMKky&$2mA;80sjI2fPdhB;1Bp8_yhg}{s8}g|A0T>Kj07e5BLNA1O5R2fPa8L;2+=*_y_z0`~d#}{{TP0f4~R$AK(D~5AXmV=llQz|NH;|fBpaf1N;C000000"],"7":[34,44,-1,15,"000000ssI1z<>Y$@E`yG_y_<0{sI60|A2r0|G*#r|L_NZ0C)kw03HBv01tp100+Pa00Hm-008&^002G!0019=000NT000B<0002^0001f0000V0000FzyJUP@Bjb-_y7O^egFUfKL7v#55NEb2k-y@0r&s_0R8{~06zc#03W~r00-~@00Z~{008~~004gg001Ar000l*000B{000600001g0000#zyJUb-~a#s0000"],"8":[34,46,-1,14,"0000000aL300aN<00aO300I9$-~j&v`~ZKz|9~IhKi~)W2lxa20sjF1fPcV0;2-c0_y_z0{sI30|A2qMAK)M02lxm00sjO306)P000;PgfB^shzyJ^bzyJsT_y7m||9}Jh5AXs00sa7gfPa8L;2-c0@B{n@`~d%f{{TPWf4~p;AMgYI2mAp4f&TzM;D5jm_#f~C{sa60{{a7hf50E$AK(Z45BLE8kNf~1|Na00|NZ~~5BvZC00000"],"9":[34,46,-1,14,"0000000aI200;lz00aO200aI%zySXT_yB)^{s2GVKfn+85BLZC1O5U30Dpjgz#s4*@CW<{`~m*~{{Vl$f50E`AMgkK2mAs5f&T!1;D5j$_z(C8{saC2|A2qMf8ZbZANT|R|Na1f|Nnpo|Nr0sf1mIG00;a400I91004i$001BG000O4000600N?=sfH(j@;12)~@B_dH`~dI){s24x{{Rnwe}Du0KfnP0|KI>W|KI=s|KI=s00000"]," ":[16.0,0,-1,57,""],".":[18,12,-1,48,"0001Z0Dpi#@DKb0{{a8MKkyIy0sa6U0000"],",":[18,21,-1,47,"0002^0RMnL@E`mK{{a8sKllgy0RI3Fzyt6A_yB$Y9{?YKAHWa51Hb^l00000"],";":[23,41,-1,27,"00000_y7a=01x;8Kkxv5@Bshd0snvj{{R8}00Hm-0000000000000000000000000000000000003Uz=e}Do1fCK-42mb&M{s15R03Y}O5AXmF-~bPR06zc#d;kIP00+PTKL7#z00ZCv1^@s6000"],":":[23,33,-1,27,"00000_y7a=01x;8Kkxv5@Bshd0snvj{{R8}00Hm-00000000000000000000000000000000000000009{>P<00I912mSyL{s15R06*{mKi~jAfB-%K0000"],"!":[23,45,-1,15,"00003{s0I301x;8AMgM_-~fNX0Dpi0{{R9000Z~{2k-z7-~b=M06%~Le*ggf008^|0r&s|@BjzE01tow9{>P8004Xd0Qdj_@Bjng00Y1P2Y>(o00000000000005-00-~@AMgM_@Bshd0sp`O|9}Jj00Z~{1K<Dv000"],"?":[34,46,-1,14,"0000003ZAS0Du4R03ZMU00;2@zyaV7_yBkT{{S8Uf4~O-5BLGV1O5PT0RMm(06*XW01x;800aI20094h002MW000m8000O40006100030fB*phzyJaN-~a*t@Bjcm@Bjc0-~a#v-~a#s_y7O^J^%m!4}bsw0pI`t0C)fZ02}}S0000000000000000015U001B0000m8000C300030zyJV0@Bjc0`~Uz0{r~^~e}Di04}bsw00000"],"\'":[20,44,-1,15,"0000#zytgMKfnX{03Uz>_y8Y(0r&tPfC2CT9{>RG01p5F@Bj}00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"],"-":[23,20,-1,39,"0000#|KNZB!2kb&|NjI3{saH`000000000000000000000000000000000000000000000000"],"(":[23,60,-1,13,"0000003ZMWzyJq;03QGV`~U;+01v<bKY#%K00H~}2k-zN-~c~>0RI31{s05~01xm0AK(B#zyN=M0sjC4{s0I301x;8AMgM_zyN=M0RI31{s05~00;O05AXmV-~d110Dr&$|9}Di00aI21N;C7_y7;^03YB0AK(B#zyN=M0Dk}g{{R5~008~~0sH^~`~U&?00H;_0r&s__y7R#003YB06+i$00"],")":[23,60,-1,13,"0000W003|R0Pp|-_y7U;00H;_0r&s`_y7a=00Z~{2k-y~@Bk0s03YB0AHV=VzyN=M0RI31{{RF200aC02lxOF@Bkm+06)M0e}Dl000I911O5O9`~VO503YB0KfnNgfB^ph0sa63`~U~|03YxGKfnNgfB^ph0sa63_y7;^03W~rKY#%K00H~}2k-z7zyLo00Q>+0@Bk0M03HAUH~;`Z0000000"],"\\"":[38,44,-1,15,"0000000aCV-~bQsKY#!~!2SRLe*^dc0r(H#00-bdfB+wW`~U!c0q_6;_y@oM1K=M301tqC002Az@Bjet2fzRWz#aeq4*)m-00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"],"/":[22,46,-2,14,"000001Hb?u004Xd0pI`+fB-%K0Pp|@zyKcr0C)fc-~bPR06YKz@BjzE03HAU_y7ao01p5Fd;kIP00)2oJ^%pt00Y1P9{>P+00H0t4}btZ008g+2fzRy004LZ1K<D;fB-xI0q_6^zyKZq0Qdj{-~bN*0DJ%d0000"],"&":[55,46,-1,14,"00000000000Dr&$00007|KI=s001BV@Bjb+0Dq7000001{14y&000O0AK(B001xmVzyJUMAHYAr0000#fPa7h00930{{R300RI9000001{s;H~000C05AXm000;aZ-~a#s5BPt80000F`ThU^001BV_y7O^03ZM000000AO8UV{r~_!_yPa?00IB_0RP|s2mkm0{{R3#|M&s^0093#_yhO=1N=Yu2k-z7_&@j$-~b=sKlneu0Dr(g_<sNZ|A0UE{s00006+cs00aC0KmYIm2lxOV|G)qb@BknGfB+xh03ZGU06*XWAN&9Sf4~4A`~U#|fB+x-0094h0Dt@d0snvj|Na00|9}tw{s000<Nx3P00960{vZE<0Du4R5B~rFAN~LU000000000000"],"%":[66,46,-1,14,"000000000000930008g+0095+004Xd0095~002G!002K9zyJ>b0019@@BjzE000Nz{s05u000B{AAkYy0002~2k-!V0000#0sH_y0000Fz<&TA00003@E^bjzyJUM{0Hy@-~a#sKLPv!@Bjb+55Ru_d;kCd1MnZfJ^%m!0R9K?9{>OV06&5F2fzRT00-dy1K<Dv00H<v0q_6-002K9z<dAz000mF;64BV00030@E-twfB*mw@CU$u_y7O^00ZDZ{{R3000HnHkKh0R004Xs!TbOK002G%@IL?m0018W{13nY000NTe*^dc000BvAHe<q0005-2k<|D0001Z0r(H#0000!0Dc4b0000V03U$<00007fCunDfB*mk-~s#(-~a#t@Bn`U_y7O^cmN;3`~Uy|J^%yoKL7v#9{>RSAHV<r2Y>({kKh0R1K<Dy|L_0+0q_6-fA|0Z0C)fZ2lxO00000000000"],"$":[34,54,-1,10,"00000004LZ0015U000Mo0005t00061zyJgP{{RF3|G)wN@9+TrczghV9uEK?hk?Kk;oxus_;?%u{vHPaKZk$-58>bd1Ne9V0RJ8U06+JD01yA*00IB_004jgfB+Bw_y7a{|9}90|M&n8|Nj60|Nr0sAOH9O0RR6003ZLr00;m000HOz004M@fB+sJ-~b1M_y7Um{s#bfKY`#L58!wQgZLf+;Qj}Ics~K)9v{Gb2Z!Jv!Q=1;{(JZV|Nr~|AOHLS06+Wy004LZ0015U000Mo0005t00000000"],"#":[34,44,-1,15,"0000000ZD3008g@fB-xJ-~b;0_y7mMJ^%sm4}bu81Hb?t0Pp|@fP4T0;2!`0_y@oMJ^|nl|NsBP|NsB+|NsB|KmY&#03QJO00)3P00H0+008(0zyLl0@Bj~hd;kOB9{>RG2Y>)P1K<Py|Nrp+|Ns0y|Ns9F|NsBM9s%$G4}g3C1K=M30Qd*M06YQU01p6o00+Q600Hn1fB<|0-~b;0@BjyZJOBaU4*&r82fzRT0000"],"@":[62,57,-1,14,"00000000000000V{r~^~000O7|9}7h00960|G)qM01y5H|9}7h0Dpi0|9}7h2k-y@{{R30KY#!L{r~_0_y7O_`~UzSzyJUP@Bje*00007-~a>g0000VzyKeB0000#008^|0002|00-az0005_03Uz=Kl}&a0Q>+4|L`Ax1MmQU|A2k~AAkq{{sH&^egHoQ_y^zv@B#22;2(ewzz=}`0Db^J0Dc4f0r&y<1Mm;<2jB<bAHYArAAlc#e*ymhegJ+0_y_m_@B#P_;2+=*zz4uTfPa8L06zi#0sa8^0Q?8=5AXxv1MnZfKfoUV55Ru_{{VOZKLPv$`~%<s{0HzK@DBh3@E^c`fOr50z<+`M1Hb?uf&L%(9smG-2mk-`@Bjh$AOHXV000NzKl%Uo000lbf5ZQP002J#{0HCw004df0000000H;_0000000Zy<0000001w~*0000003W~r0096106%~L01f~E0Dk}g0Qdj^0RI304}bsw0sjC2`~Uy|0sp}NzyJUM1ONa0000000ssHN000000RQj+0000000000000"],"*":[34,44,-1,15,"0000000I60002J#000lb00RT?FaY5E8~}VC4}c$shu{zS=llczd;b9c|Np=P|Nj60AN~LU2mgQo5C8lCKmY&m5B=}_1O9pc0Dc}HfFB2g-~)s3Z~(yk3;+N>0000FzyJUT_y7O^000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"],"+":[38,38,-1,21,"000000005-00007zyJUM9{>OV0DJ%d00Hm-000NT0000V00000d;kCd0q_6-00+PT0018V0001d00001@Bje+|Ns00|NsB+5C8xFz(4>0{{Vmg|NH;|9{>OV0DJ%d00Hm-000NT0000V00000d;kCd0q_6-00+PT0018V0001d00001@Bjb+2fzRT000000000000000000000000000000000000000000"],"=":[38,32,-1,27,"0000006+i#{{a90|NI00|Nrn0|NsBMAOHXV00000000000000000000000000000000000000000000000030|Ns00|NsB+5C8xFz(4>0{{Vmg|NH;|000000000000000000000000000000000000000000000000000000000000000000000000000"],"<":[38,40,-1,19,"00000000000RR9102}}S00Hm-001Ar000610000V@Bjb-{{R30AMgMG0sjC103YxG00I91001BG000610000V@Bjb-{{R305AXm006%~L009300006100001{{R300sjC100I910006100001{{R300sjC100I910006100001{{R300sjC100H~}0005-00001zyJUM0RR91000000000000000000000000000000000"],">":[38,40,-1,19,"0000003ZMW007_s000Bv0000F-~a#sKi~iW06*XW002MW0000#-~a#sKi~iW06*XW002MW0000#-~a#sKi~iW06*XW002MW0000#zyJUMKL7v#1N;C006*XW00aI2002MW000C20000#-~a#v{r~^~Ki~iW1O5O206*XW00aI2002MW0002~00003-~a#s4gdfE03ZMW00000000000000000000000000000000000000"],"[":[23,55,-1,13,"00007|KJb*z#seoKfnNgfB^ph0sa63`~U~|01xm0AK(B#zyN=M0RI31{s05~00;O05AXmV-~d0s0Dpi0{{R9000aC02lxOF@Bkm+06)M0e}Dl000I601N;C7_y7;^03YB0KfnNgfB^ph0sa63`~U~|01xm0AK(B#zyN=M0RI31{s05~00;O05AXmV`~W}y0Dt}f0000"],"]":[23,55,-1,13,"0000#|A2r003ZGU1N;C7_y7;^03YB0KfnNgfB^ph0sa63`~U~|01xm0AK(B#zyN=M0RI31{s05~00;O05AXmV-~d0s0Dpi0{{R9000aC02lxOF@Bkm+06)M0e}Dl000I601N;C7_y7;^03YB0KfnNgfB^ph0sa63`~U~|01xm0AK(B#zyN=M0RI3F{sI5|1ONB{0000"],"\\u2014":[68,19,-2,40,"00000000002mk;7|NsC0{(t}f|NsC0|L6bz|NsC0|Nejf|NsC0|NrCv|NsC0|Nr~|000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"],"\\u2013":[36,19,-2,40,"000002mk;7{(t}f|L6bz|Nejf|NrCv|Nr~|0000000000000000000000000000000000000000000000000000000000000000000000000"],"\\u00b7":[23,28,-1,31,"00000_y7a=01x;8ANT-&@Bshd0RO-N{{R8}00Hm-00000000000000000000000000000000000000000000000000000000000000"],"\\u2019":[23,45,-1,14,"00000_y7a^01x~CANT-2_yB+K0RP|s|G)r$fB=2~0Q>*}@Bjng01towegFgb01v<b9smF^000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"],"\\u2018":[23,45,-1,14,"000000KfnbfB=600r&t1zyKcr0DJ%e_y7a&00-azAK(B#@Bn}C0RP|t|G)$PfCK*k1N;C3@Bjb+0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"],"\\u201c":[34,45,-1,14,"00000003YCfB^Ub-~fIB_yB$Z_y9ft_y8XOd;kxCJ^%;c4}byq2jBpH0r&tv!2bXb{6Fvm|BwCv|KtCFKluOP2mT-U0sn{o06)P000ZC;fB*mh0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"],"\\u201d":[34,45,-1,14,"000000Db}Z06)P003Y~&;0OO7`~m;R{{VmS|G*FYKkx(p2mAm(!2bXT@E^bc_ygboegXIZ9{_v+4}d-Z2f!bI2jCxo2k;-j0q_UF0AK-t000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"],"\\u2026":[66,12,-1,48,"000000000003QGVcmM<701w~*e}Dn}00;a4AMgPGfCK-45BvZ>@Bshd1OEUY`~W}r0RO-T{{RpE06*{m|G)wN00;a4Ki~jAfC2sh2k-y~zyKZq0Qdj^000000000"],"\\u00e9":[30,48,-1,12,"0000000I9101x~C06*XW0sa602k-y@KY#!L`~Uz4zyJU~0002+000000000000000000000000001x;80sr^_5C8B0f1lt3{6D}S;D3OBf&K&j2lx;8AK*XWf586%{|EdB{2%}S@PGgR!T<mN2mSy6AMgMGf4~3%{{R37{r~_E_y7Pu-~a&sfB*yk000O4001BO002Mu1^|Em_yGU^-~j*r004i$00000"],"\\u00fc":[38,46,-1,14,"00000000mM0005-egFUu;rIXmKacPL0RBI~00a2{000lc_y7P71Hb?P0000000000000000000000000000000000F{{#QPKl~5>0Dtfg`~ZKzAMgSH0Dr&-`~m*}AMgkK0Dr(A@B#k-f4~R)0sjCW@CW<=f50E`0sjDhzz6&R{{SEG2mAnkz#s4d{{Vl$2mAs503YxN`~ZKzAMgSH0Dr&-`~m*}AMgkK0Ds^g@B#mTf4~R-kN*G<|Ns5~AOGL}06+MD_yB)^000000000"],"\\u00f1":[38,47,-1,12,"000000018V000611Hb?e{to~EKm0rZ0ssHt00;m7fB+sp{r~`QKkxtnz<+=M004Xd000000000000000000000000000000000N@0DtiR@B#nN|KJ1v|Np=P|Ihyb5BLxK06*X#_yGTaf8YcD0snvx_yhg`Kj07e0RMnL-~;{u|9}tp1O5O%;1Bo!|A0T>1O5R2fDiZs{s2GV5BLE8fIr{^{s8}g5BLNA06*Xl_yGTaKi~uY0RMmw_yhg`Kj07e1OLGP@E`w&|L}kQAOFAr00000"]},"adv":{"A":46,"B":43,"C":46,"D":46,"E":43,"F":39,"G":50,"H":50,"I":25,"J":32,"K":50,"L":43,"M":60,"N":46,"O":50,"P":39,"Q":50,"R":46,"S":36,"T":43,"U":46,"V":46,"W":64,"X":46,"Y":46,"Z":43,"a":32,"b":36,"c":28,"d":36,"e":28,"f":21,"g":32,"h":36,"i":18,"j":21,"k":36,"l":18,"m":53,"n":36,"o":32,"p":36,"q":36,"r":28,"s":25,"t":21,"u":36,"v":32,"w":46,"x":32,"y":32,"z":28,"0":32,"1":32,"2":32,"3":32,"4":32,"5":32,"6":32,"7":32,"8":32,"9":32," ":16,".":16,",":16,";":21,":":21,"!":21,"?":32,"\'":18,"-":21,"(":21,")":21,"\\"":36,"/":18,"&":53,"%":64,"$":32,"#":32,"@":60,"*":32,"+":36,"=":36,"<":36,">":36,"[":21,"]":21,"\\u2014":64,"\\u2013":32,"\\u00b7":21,"\\u2019":21,"\\u2018":21,"\\u201c":32,"\\u201d":32,"\\u2026":64,"\\u00e9":28,"\\u00fc":36,"\\u00f1":36}}'
FONTS['SB30'] = '{"ascent":27,"height":34,"glyphs":{"A":[24,22,-1,6,"00000d;kD`004df0R8{~-v9vL00EDH0gr$K4}b#)zyk-s1_!_g|KJDz;0y!s3<2;Q0q__A_&5Rhegpmh000"],"B":[22,23,-1,6,"00061`~d&>1L5!wgWx_7fcQQG;P4NJz&<_z|L_C<@DGFFJ_o?~9|Pcg4}tJL2f+9~1OM=U{{R3000000"],"C":[24,22,-1,6,"00000f4~F(@CU#!4}dTa01zJl5FY>l9{>Oz002G!06qW!9smFz0018V03QGl4}cI4fDi}3FaiJY0Dr&$000"],"D":[24,23,-1,6,"0001g{s0gEfDeb@4}tIxf$$H2_z!^i4}ka&fcOu9_z!^i4}ka&fcOu9_z!^i4}kCwf$$H5;1B=6fBygg0000000"],"E":[22,22,-1,6,"00061{{a8|1K=<ZfIvP00Qdj{-~bPU06q)=|L_C<zz>4}J`4c(00ZC%4}c&(0D$-g1ONDc|KI=s00"],"F":[20,22,-1,6,"000O7{15-Y_zVw#!1xRgfB^Ua4}t*rAP<HB|KJb)0Qevef&lmc4}bvp01tow_y9lf0000"],"G":[25,22,-1,6,"00000Ki~j={s8y~0C)j_cmTkB03bd903QGV4*&oUfB*-;00ZDZ@c0AZd;#!20Qe7pd<Vcj0q`FHKmULS{r~^~00"],"H":[25,22,-1,6,"0000#@&AM1KLPL$0Qd)hd;`Ef0pK41@DG4^2f#c7|Na60{{Z+0fP4eMJ^|n#0Pqihcn82d1K=J3@E?c%Kkxtm00"],"I":[14,22,-1,6,"0095M`~%<*fIa~D1K<yUJ^=Uw;17U40Qdvo4}d-Z_yh1i@Bjb"],"J":[17,22,-1,6,"0006106qX801to%zysg`@BsJ#d;mTG9{>-42fzd10q`*R7<ddk2mAr}0000"],"K":[26,22,-1,6,"0000V_&<R72LL_;fDeJd1K{8Q_;3I|H~<fv00ZxU0RP|sKl}g>pMV47@BsLH06rgp4}<Un;C=x355PVH_<!(!00000"],"L":[22,22,-1,6,"00061zySCF1K<D;fB-%K0Qdj{-~bPR06qW!_y7ao01towJ^%pt00ZC*4}dT}0KoVL1ONDc|KI=s00"],"M":[30,22,-1,6,"00001{{TPW`~ds|@CWb@;2*$0fPVnr1AGH~4e$)`XTUSzp8&^>d;=db@C<#&z%c$F0K@ov0|&wI3?B!;Fgzasz~FoX1A*{=gdg|-0000"],"N":[24,22,-1,6,"0000#f&34Ea1X#R58yBl@GuSVFbw!G416#QelQF^Fbp3s3=gmj5AX~J@C*a+3<2;A0q_g}@C*QOKY%a*000"],"O":[25,22,-1,6,"00000f4~6$_yG7G0Qd)hcmv>k0q{Nmd>;Tl9{?W@fDebj2f^S2;P?UXd;su10Qe68d<Vch0q{HkfBXOk_y7O^00"],"P":[20,22,-1,6,"000O7;1B<R_<RqC!1z25gW&i)4}-w?d=H1f|M(C70Qdk8fB^Ua4}bvp01tow_y9lf0000"],"Q":[25,27,-1,6,"00000f4~6$_yG7G0Qd)hcmv>k0q{Nmd>;Tl9{?W@fDebj2f^S2;P?UXd;s`90Qe68d<Vch0q{HkfBXOk`~Uzx000kw00-az0sa60KL7v#00"],"R":[24,22,-1,6,"0001g{s0gEzz>7q4}sthf#45;@DG9D4}sthgWwN`zz_d`5B~rUkAM%4fDebj4};(jgWwN=@DG6aKj8iV000"],"S":[19,22,-1,6,"0001gz(4p80|CHbI0Od(0QdkO-~s;tKllOv01xm0J^%y2fH)8b0|4M~I1m2-|9}7h00"],"T":[22,22,-1,6,"00061|L6bzm>vdTco~7<U<ZHz9smG%00H0t2Y>(`004LZ0pI`!fB+r<0C)fa-~b1J06zc+{{R3000"],"U":[24,22,-1,6,"0000#;rtJPa1Vem4}dTafG`h$Fb{w*4}dTafG`h$Fb{w*4}dTafG`h$Fb{w*4}f3?z+eaAzytq)0RI30000"],"V":[24,22,-1,6,"0001g!2BNoI3EBo4}dTafM5r}U<bg!2jIX1;J^dnfC2G<0rLO=`v3s@008~~0Db@fd;kDE002Ay02lxO000"],"W":[32,22,-1,6,"00000f4~6#9{>P29{}Ju4}jn>4}kD64}tJ-2f_GY2gCSa1LOGM1LJ(a1Ll0d0roz?0scRL0sKFJ0Q?_-0QesO0Qe680C*1o0B{cg0B{BX00000"],"X":[24,22,-1,6,"0000#^Y{<I;0M6K1L1%J<A4G4008~~0Q>*|d;kD^002G!0Dk}g{{R5bfB}cV0|&qc1K<t;@Eif~e+T>k000"],"Y":[24,22,-1,6,"0001g@%$gaa1X$62f$zl;J^dmzytAs0r7wU`v3s{004df0Db@fJOBVZ002Ay06YKyJOBVZ004df0sp`N000"],"Z":[22,22,-1,6,"0001g|AGJh1_AIG4}f5P00Hm-4}buE00Hm-4}buE00Hm-55NF^00Hm_55OQk0D<rZ5C8Z-|KI=s00"],"a":[17,16,-1,12,"000O01HJ(VfP=sR-~jL+_#ZqU9uE%(hlAt5|KL9S000"],"b":[19,23,-1,5,"000lb0C)fo00H0tJOBrP0Pp}F`~&~Mczh2Bf#C2w9tVTq@OT~%1Hs^UJP!{6|G*FM0000"],"c":[15,16,-1,12,"000N@Kj8R5;D^Bv03HB50C)iS0Pq3u0snyh000"],"d":[19,23,-1,5,"00007-~fC82Y>+Z03HAXzyNpy{{jEtd^`^agW&Ld9uI@T@OVBC2f^TYJP(h6|L_mr0000"],"e":[15,16,-1,12,"000lbKfv?B=ZB9EA0Pfd_;>*D0Pq3u0sjH~000"],"f":[13,23,-1,5,"0018W_#Qy;4}g3F;D5pX2f#i7@DG4|1K=M3_y@o~0q`H-000"],"g":[17,24,-1,10,"0000000Dsif&akq;PCKxcsx809tZvb{s6!L-~j*dKl~s62mg)(#{t8D;s4-2zyJU"],"h":[19,23,-1,5,"000NT0C)fo00H0tJOBrP0Pp}Fd;|Z$e0&cNf#C2w9tVTK@OT~%1Hs^UJP!wf@$i3t0000"],"i":[10,24,-1,4,"009Bud>#XU0000Ff#7%^2Z7*t9tVNocpeAC_y7"],"j":[13,30,-2,4,"00000@CSfA0l)wN0002~0q_TaJOSVj0C)qy9suwMfII=<4*+-r!9EG#e*@qE00"],"k":[19,23,-1,5,"000NT0C)fo00H0tJOBrP0Pp}FAA`ZbcrXtP0pkEX;0OKy|G*!71INI4cn=SO@bG^>fB*m"],"l":[10,23,-1,5,"01tuScpe9V;CLPff#7%^2Z7*t9tVNocpneo00"],"m":[27,16,-1,12,"00007&xe42`}_}&kAdOv@H{>q2ZzJJ@c4Kh9}fe=;ox|DJP!|tf#LA*K0Y1~@8|FU000"],"n":[19,16,-1,12,"000NifPeT8kAdOvJRS#w!0>n;4+FvAcsvgWf#C2yJ`eBU000"],"o":[17,16,-1,12,"000B{1O5ZYf#bpP@c8(Ad_F!O9}ka%$ARO(f50EW000"],"p":[19,22,-1,12,"000l)fPeT84}swDJRS#w!0>z?4+FvAcsvgWf#Kjk{0II3@BkhF1Hb@y01p5M_y7O^00"],"q":[19,23,-1,11,"0000001x~J|AFxEJRT2&!SHxK4+p{E_&gs6f#C2y9s~ctKX?ES00H0tJOBrP0q_8S0000"],"r":[15,16,-1,12,"004eCeDHtZ{K4RZzz2X203HB50C)iK1K<zv000"],"s":[14,16,-1,12,"002LM-VPWzAn*hD2lx-*55f-!958VAf&2gf"],"t":[12,19,-1,9,"003|g0PsJ<{2u}E9|7<m0q`FI@E-y258!+N00"],"u":[19,16,-1,12,"000li;COrw4}szEJU$19!0`AU9|ObSczh2Jf${J^{sZUW000"],"v":[17,16,-1,12,"002LakAa84!QjC7U_4+SFb9wW_yGI>d;lH*4gd!L000"],"w":[24,16,-1,12,"0001g06snp96k&f9v&DU9xx9dFb_X453gVc=imqD-~+?J1H-@rgMa~nfB*mh"],"x":[17,16,-1,12,"002MV2gd{B0Q&$x03Uz{zyaU^_yN8Fj{(QP!SVC_000"],"y":[17,22,-1,12,"002LakAs83f$+e1Ks;a{FbA*$_yG6-d;mTG4gd!L0RRDj5Won)2fzcs0000"],"z":[15,16,-1,12,"004jR=i!fn9sqm*@B`onfFA%nF!*EO$Hx!;000"],"0":[17,22,-1,6,"0005-0sH~S0pq~&;CS$Sd_F!O9}ka*$HU{{@$mTgJa`^F4;}-K0R8|z0000"],"1":[17,22,-1,6,"0001R0Qdp?0iFO400)2rzyaU@@BnxKJOCa54*&;%1Hb{`0Pp~K0RI91-~a#"],"2":[17,22,-1,6,"000m02mS*OfrG$--~jLdcmO;AJ^&s79smvi4gd}S4gd}S4ge4ThyTO>-~a#"],"3":[17,22,-1,6,"000m02mS*Ofd{~W-~jLdcmR9=d;s_We*g!-0q_9$06Z{07#|ED2mb;70000"],"4":[17,22,-1,6,"0000U03QGkfDgbA;0Evpcm{j}J_8>EkAa85gW>=D|Nejf06qX801to%zyJU"],"5":[17,22,-1,6,"000mE2mb^Afq($O0AK(x02lxd_y_&~2Y>_M0q_8L0DLe$7#<7{2mb;70000"],"6":[17,22,-1,6,"0002~0sjHvfZ)LJV0Zw006qX8_z(XFhl9i6;PCi(d^{c=4-W&+0RI3#0000"],"7":[17,22,-1,6,"000mF2mgcr!GOSkU_fvHFaS6J7yujq4gd}S2LJ~E1Aqg-0l)#^0N?=d0000"],"8":[17,22,-1,6,"000B{1O5ZYf#bpP@c8&Vcpf|lJOTUx{{iE{;PCKxcsx8F9uEhP1OI@30000"],"9":[17,22,-1,6,"000B<1O5ZY1H-}L;PCi(d^|oL4+n>X|G<CX0q_9$0C+Gw7#<ED2mS&40000"]," ":[7.5,0,-1,26,""],".":[10,7,-1,21,"00#r$_&x^!00"],",":[10,11,-1,21,"00#r$_#Oj*;BYt?000"],";":[12,20,-1,12,"007_*0q_q1-~a#s0000E0q`Gy_y+)R1_8hj000"],":":[12,16,-1,12,"007_*0q_q1-~a#s0000E0Pr6G@D2a~"],"!":[12,22,-1,6,"008h00Pqh0@DBj+4gg>V0AL0HU;qFB1_1C60PqF?00"],"?":[17,22,-1,6,"000m02mS*OfrG$--~jLdcmR9=`~ds_cmOy67ytwS000Ak1K<Jh0Qdkn0000"],"\'":[10,22,-1,6,"00)8KI1U2<z%T#+00000000000000000000"],"-":[12,10,-1,18,"00aC#!~6gM000000000"],"(":[12,29,-1,5,"000C5z&Hm0a1H_B9s%GU1He23z&r!MJOjWU0pK11;0^$A2LLz#zytsQ"],")":[12,29,-1,5,"00ICo0l*Fb;0FMB2Y`47fII`hJOjWy1He27fOrRhcn1LB4gtV00ssI2"],"\\"":[19,22,-1,6,"0005wfIM&mjsS7M3^)OY05CuR000000000000000000000000000000000000000000"],"/":[12,22,-2,6,"000gEzzhMv7y*DV0{}1v0AL0HzzhJu7y*Dd0{}1p00"],"&":[27,22,-1,6,"00000AAkT4_y7UNfB<;#01qAj0OP;_9(Vu){r~_!58w~r@CW`L0Q2L(JU(y-gZ=>UKY$(s@B_d<06Y)y2mk*7Kg0L{0000"],"%":[32,22,-1,6,"000001K<My2lxg62RIG@4mb<|4m=nD4m>yj4m@xG4me-{2ROh02l>aq1L2S000SIw00$g!00taz01O;(02~}}02mx_05BYI0ALT`0N@9}00000"],"$":[17,26,-1,4,"0000$03ZPW0RO<`VDd0|7(9R<KnL&x{s8}gKi~)W0sH`-5JwCnh7rSw!T-QNzySaNfB*mh"],"#":[17,22,-1,6,"0004o0K))bfH1%~;22>4{(t`i3<HJ%#{k0v|M~y?IA9!b3@`>50}KI%0000"],"@":[30,28,-1,6,"0000003YB01OMOv90A|~-~+%800#gt01g4b05}c<_~1A{;eo-&h6fHjI2<_e;Bmvlfrk$a20S=081dnNW5<jE&pu!WAO8RxIPd^C0002+0005t0RRKQ8~_9VzyJgM0000000"],"*":[17,22,-1,6,"0002s0B{32f$PBk;17U5_#V6r<^XU2H~;_u000000000000000000000000"],"+":[19,19,-1,9,"0000S00V#kZ~zVf0l)w_0RQ|S|9~6-1AqW<01f~FzyLS^0000000000000"],"=":[19,16,-1,12,"000O7@c;e*00000000000ss6z|9}7h000000000000000000"],"<":[19,19,-1,9,"00000AOIc!4}b^21K<Jh0Pp}j00Y1P9smIN00+PTJ^%sW00;m800000000"],">":[19,19,-1,9,"000620Pp}0fB<{|1K<E3004LZ2Y><K0q_9$0DJ&G01p5FfB*mh00000000"],"[":[12,27,-1,5,"00I0Tf#4ni;2r_s9s%GU0pK11;2r_s9s%GU0pK11;2r_sAA$S;00"],"]":[12,27,-1,5,"00a0RfOrRhcn5%Z2Y`47fOrRhcn5%Z2Y`47fOrRhcn5%ZAA|S+00"],"\\u2014":[34,10,-2,18,"000005C8xF!~g&P@Bjb+0000000000000000000000000000000000"],"\\u2013":[19,10,-2,18,"000O7@c;e*00000000000000000000"],"\\u00b7":[12,14,-1,14,"003YQ0Pqh0U;qFB000000000000"],"\\u2019":[12,22,-1,6,"008h0fcOu9I0FE1907m;0000000000000000000000"],"\\u2018":[12,22,-1,6,"000OBfM5;);2#0_4}fq00000000000000000000000"],"\\u201c":[17,22,-1,6,"0001k0mFfZ0mA^}fcfx#_#b=+9smFU00000000000000000000000000000"],"\\u201d":[17,22,-1,6,"000LZ2j2tl!1LfZ;23ZmFg$P=AOHXW00000000000000000000000000000"],"\\u2026":[32,7,-1,21,"000004gr904+FsP9|OSn4+FsP4gtV$00000"],"\\u00e9":[15,23,-1,5,"0005-1Aq<yFaQ7m00007;2+?5;Pb=BhmVi{AN)K3cmQ|+_yGTa{r~^~"],"\\u00fc":[19,23,-1,5,"00002036^0-T*Ox000000001fKLf+yczh2Jf#L8xJ_m=u@c14d1H<5Wd=HO-|L`9_0000"],"\\u00f1":[19,23,-1,5,"0001Zz#s4f{s2dS000000000!d;|Z$e0&cNf#C2w9tVTK@OT~%1Hs^UJP!wf@$i3t0000"]},"adv":{"A":22,"B":20,"C":22,"D":22,"E":20,"F":18,"G":23,"H":23,"I":12,"J":15,"K":23,"L":20,"M":28,"N":22,"O":23,"P":18,"Q":23,"R":22,"S":17,"T":20,"U":22,"V":22,"W":30,"X":22,"Y":22,"Z":20,"a":15,"b":17,"c":13,"d":17,"e":13,"f":10,"g":15,"h":17,"i":8,"j":10,"k":17,"l":8,"m":25,"n":17,"o":15,"p":17,"q":17,"r":13,"s":12,"t":10,"u":17,"v":15,"w":22,"x":15,"y":15,"z":13,"0":15,"1":15,"2":15,"3":15,"4":15,"5":15,"6":15,"7":15,"8":15,"9":15," ":8,".":8,",":8,";":10,":":10,"!":10,"?":15,"\'":8,"-":10,"(":10,")":10,"\\"":17,"/":8,"&":25,"%":30,"$":15,"#":15,"@":28,"*":15,"+":17,"=":17,"<":17,">":17,"[":10,"]":10,"\\u2014":30,"\\u2013":15,"\\u00b7":10,"\\u2019":10,"\\u2018":10,"\\u201c":15,"\\u201d":15,"\\u2026":30,"\\u00e9":13,"\\u00fc":17,"\\u00f1":17}}'
FONTS['SB28'] = '{"ascent":25,"height":32,"glyphs":{"A":[23,20,-1,6,"00000@Bjnw00-az58wbdzyN1}0FQtJ9{>g)02n?1Fnj=i`~m;?0|4+00q__D;BW)s_#fZ^000"],"B":[21,21,-1,6,"000C3@B{zA9v=Ykcn5>vJRSky@DC3FfA9nU;2sZv@ID8D@H`KJ;Cv4Qz<&H6|G)qM00000"],"C":[22,20,-1,6,"00003{s2Gz0pJ)90APFpf#3iKfB-%K0Qdj{-~bPR03HAUcmRR$0t3Jp2Y_G?|9}tp0000"],"D":[22,21,-1,6,"00061@Bsh#1HteQ1K>Olfbbpzz<dt@@H_{=@E-%fd=CNeJO_aA9s|Jm4+FqI{s;fy00000000"],"E":[21,20,-1,6,"000C3`~&~s9s>aI2nT>bJOBaUzz+rhfA9nUfF2A0@BjyZ06YN!;0O-@z<>T9|L_0+00"],"F":[19,20,-1,6,"000mF@IU?sfWYt=9s>iw0C)fo1OecHKkx_s0PsK_2m`<XcmNLo0pI}tfB*mh"],"G":[24,20,-1,6,"00000|9}Jk@CSf!4*)P905Bc^03HAUJ^%nd002G!06qu&9su|r0Pr6G@DBj+2Y~Pc|L_3+zyJUM"],"H":[24,20,-1,6,"0001g=ll-=@DBj+4*>8F0Pqh0@DBj+4*>8F|L_n0@DBj+4*>8F0Pqh0@DBj+4*>8F0q}q4`~Uy|"],"I":[13,20,-1,6,"00I94;2!|^2f#i7@DG4|1K=M3_y@o~0q_rid=K~l00"],"J":[16,20,-1,6,"000O40Pq0t0Pq0t0Pq0t0Pq0t0Pq0t0Pq0tAn-8oG2lPIKY#!L"],"K":[24,20,-1,6,"0001g;rI^#;12=74+8)X1^^EX01p@d4}1U*`~VOB01qDk4<CRJ55Nxxzz+l94*~EG0r-F5{r~^~"],"L":[21,20,-1,6,"000C300Y1P9smIF00)2oJOBaU01p5FcmM;y03HAU@BjyZ06YN!;0O-@z<>T9|L_0+00"],"M":[28,20,-1,6,"00007_yPV8fFFST1Mm;PKLGv)@D1Q^0N)Jo4DinY&zSHG`Huj{xbO^r4*<jP@C-f=0Kwq!3>*&tz`*!_2!G%J000"],"N":[22,20,-1,6,"0005}58(I?1MnCR;9x(2fZqlKJ{SyqU@`fC!{!4A*bEQgFdu-xeggpb3<2OU1BdVq0000"],"O":[24,20,-1,6,"00000{{RE$zz>1o4*>8V0QepNcpd<FJ^*+=0C+wCcs>Al9sqbA0QesO_zwW^2Z7)N=fD8}00000"],"P":[19,20,-1,6,"000mFfIs{PhrsZ79uEV-;CMU_2Z7=6Kl}&&0Pp}F00Y1PcmNLo0pI}tfB*mh"],"Q":[24,24,-1,6,"00000{{RE$zz>1o4*>8V0QepNcpd<FJ^*+=0C+wCcs>Al9sqbA0QesO_zwW^2Z7)N=fD8}fB+AG00-az1NZ;|_y7O^"],"R":[23,20,-1,6,"00030`~W}x0C+wC@H_$Fcmu%j2Z7)Z2f!X506+WyfA9eD@B!iA1H<44gWwMX;2sCy|A+7Z000"],"S":[18,20,-1,6,"000300RO;nFdPI20Ri9uegGfv1OEU&-~;#o9t;D60N}tlI1Ufr0RI3000"],"T":[21,20,-1,6,"000C3{~!PO!SF^8f-rm#1K<E3008&^2fzS600Hm-4}buC00ZCv9{>RO00+PU|9}7h00"],"U":[22,20,-1,6,"00030kKynR1Hc#$0AM@;fba$bz!(nzU_1eU@CF0G7!LqoJOKdk3<KaW2f=_3`~VN&0000"],"V":[22,20,-1,6,"000602jTDr2f!E)0Kh&20C)%i@L&hQfDeoSJ}>}%fC2UZ1MmP3zyKcr0C)fZ-~a;v0000"],"W":[30,20,-1,6,"00001{{RQ!@Bjt}z;GB30l>gM4}$>sJ`4fy_+SUe@qiB>#sEI=umJl$zybV!00-gt03U<k06Y(X0Pq|D1AuS<1^~bS0000"],"X":[22,20,-1,6,"00030pTPJW0q|f0!vGJM03YB0KL7yu00Hm-2fzS7fB@bA27CZ8_yK|73<tn)4~OvofB*m"],"Y":[22,20,-1,6,"00061kKy<Z1K=<R!N4B|06sVX_`m`700Z~{55NE)004Xd0q_6^zyKcr0DJ%e@BlyX0000"],"Z":[21,20,-1,6,"00030{0INwFdqSd@CY9O0Qdk8fB^Ua2fzS)00+PTJ^%yY06qZ$@CY9O!TA0U|L_0+00"],"a":[16,15,-1,11,"000l*9QYV`0C)g+5BMH<Ja{~KJa{~KKll$m000"],"b":[18,21,-1,5,"0019=0pI|503HAbfC1nDf8Zbd2Zw>-;COf*9tVek;ox|99v%mW0sp{1zyJUM"],"c":[14,15,-1,11,"000lb|A&S=81MtY4*)y>@B`onfDiZ|zyJU"],"d":[18,21,-1,5,"0000FfC1nDcmN&%2Y><KANUXc2Zw>-;P7}n9uEhD!Qk+CJ{|{$fdAkhd;kCd"],"e":[14,15,-1,11,"0018W{|6jAc=6-^kNi9U@B_dHfDiB=fB*m"],"f":[12,21,-1,5,"002G@;N~6y;2sD39|7PV0pK11;2r_s9s%GU1NZ;{"],"g":[16,23,-1,9,"0000001OBGANV|YJUBc&JUBdfAMg+03;-MeKlmT~5B?Y)I1V@*Kll&e000"],"h":[18,21,-1,5,"000kw0pI|503HAbfC1nDdEg)X2akc_;COf*9tVek;ox|99v%mWf#Kl%`~Uy|"],"i":[10,22,-1,4,"0005tcpd`)002G*f#7%^2Z7*t9tVNocs~FD"],"j":[12,28,-2,4,"00003fP4plH~;_uAHaMEz<dY5d<VdM2f%y>z<dY5d<TGdCxh@l000"],"k":[18,21,-1,5,"000kw0pI|503HAbfC1nDczhlV2ZjOT0C|8O@CW<>|A2Ym9y|w+f#Kl%{r~^~"],"l":[10,21,-1,5,"01tuScpe9V;CLPff#7%^2Z7*t9tVNp`~Uy"],"m":[25,15,-1,11,"0000VJUj>g{{zRzf#Kue@bK_>cz8TKJRTk%4-XFqhlhj1!@=R>;raXc0000"],"n":[18,15,-1,11,"000l30sp{w_#Peyhk@bXcz7Nj2Zw>-;COf*9uLpJ000"],"o":[16,15,-1,11,"000Nz5AYs%JUl!+JUl!+JUl!+JUkwF5AX-z000"],"p":[18,21,-1,11,"001Ap0sp{wcpe@Hhk@bXcz7Nj2Zw>-;COf+{0IC2-~f049smb`0pJ1t00000"],"q":[18,22,-1,10,"000000Ds^=_#Peyhl9c3@OV5P4+n$6;COf*9s~b?ec%9i03HAbfC1nDcmRI@000"],"r":[14,15,-1,11,"008*m=ZF3un0O)J2Y?;`cmd!CfFA(<0000"],"s":[13,15,-1,11,"004dmaBzc!9{~OX_z&O@2slB*oFBjd00"],"t":[12,18,-1,8,"003YP0N_8t@E!r+9s%GU0pK11;2r?{2fzR"],"u":[18,15,-1,11,"001AKf#cwKcpe@Hhk@bXcz7Nj2Zw>-;CT2S{sZU0000"],"v":[16,15,-1,11,"004g;JPbYz9vB}O4=@j~2cQSw1K<O|0l)!(000"],"w":[23,15,-1,11,"0002|0Pyf&!QkP6;lcyQj04Y@2frW>Z@>?q03RLz96SIxZ~$;%00000"],"x":[16,15,-1,11,"004hH9vB}m4`2tt2fzcs1K<bn4Dc9u7<_#G000"],"y":[16,21,-1,11,"004hJJ`5fh9vB}O4=@j~2cQSw1K<O|1Hb`*0e}Gj0{|lcJ^(xb000"],"z":[14,15,-1,11,"0095P9|(9O;12+N0pJgSJR#wahCVp|-~a#"],"0":[16,20,-1,6,"000BP5AYs%9C#c!JUl!+JUl!+JUl!+JUl!+95^0$9(WJ%2fzRT"],"1":[16,20,-1,6,"0005N1Hcc!8^8m=1Hc2o1Hc2o1Hc2o1Hc2o1Hc2o1Hc2|AN&9S"],"2":[16,20,-1,6,"001B09q<@<5O@%H0C)g+0C)iK0N??@1Aqqr4geScKm0%ZKl}gy"],"3":[16,20,-1,6,"001B09q<r%5O@%H0C)g+0PqLk2k-!R06YLZAUrTUFnB%qAK(B0"],"4":[16,20,-1,6,"0001Z0C)iS0r&&>19%2_40sH97<e#vKm33GfBpb?0C)g+0C)fZ"],"5":[16,20,-1,6,"001BOANU{m7yuXm7yuXmAK)GM0C)gA06YLZFg!3kFnB%iAK(B0"],"6":[16,20,-1,6,"000B{2lx&c9ta)?JODfZKkz^JJbXMnJUl!+96TO89ykwp1K<Dv"],"7":[16,20,-1,6,"001BSAN(Ku5Eu{`05||J0B`_c0N?<?0l)#k1Aqg72LJ~E4gdfE"],"8":[16,20,-1,6,"000Nz5AYs%JUl!+JUkqD9(V`f5AYl~JUl!+JUl!+JUk!x2jBnz"],"9":[16,20,-1,6,"000NzAMiYQJa{}jJUl!+JUl);AN&ve06YLZ5O^?nFmOHKAHV<r"]," ":[7.0,0,-1,24,""],".":[9,7,-1,19,"01gj_!{Fcm"],",":[9,10,-1,19,"01gj_!QgN(a9{uc"],";":[11,18,-1,11,"00F>!4}tI;000000l<6@fbb3hfZ#9y00"],":":[11,15,-1,11,"00F>!4}tI;000000l<6@f$$sv00"],"!":[11,20,-1,6,"00H1U2LRw41AuT20Kgan00003fOsDP;5YyP"],"?":[16,20,-1,6,"001B09q<r%5O@%H0C)g+0r&&(1Hc0S0{{R30{{nr2Y?5F0{{R3"],"\'":[10,20,-1,6,"00)7<a0~+gz%T#+00000000000000000"],"-":[11,10,-1,16,"00;2?0000000000000"],"(":[11,27,-1,5,"000mM0l;t^1Ay=x1Ay=z1HgC>0pL6XfN&20;2Z(K907n3000"],")":[11,27,-1,5,"00aQQ4glaB1Hd>3fbbpzz<3V<;5-L_@E!wz@EijG;4lOL000"],"\\"":[18,20,-1,6,"000Bd0ONo-;08DWh5%uJ7+?SZ00000000000000000000000000000000"],"/":[12,20,-2,6,"000aCz!(95I0FDM1^{3N0Kg0Yz!(957y|$>000"],"&":[25,20,-1,6,"00000`~U#|fB^Bp0C?a4Ja7OWcmN0Z00Z#+0r)%v{u~3(jsfBK0N{TBcprc~2f!W!@CX0=0RJC=0000"],"%":[30,20,-1,6,"000004}dTLcL2ZxoCW|6I4}S>;lKdnh5!SOFaQp5fB+rNJODm3xBvl;Z~zQBzyLAF00D;_01OUr0B||L0f6oR3<2-}0000"],"$":[16,24,-1,4,"0004i0e}biANU=ZIhZ+sJ%B%eAK(x02lxT}0lWd6F`O}+F_=I2AK(Fi0e}Di"],"#":[16,20,-1,6,"0009R0~iJv1{ekyfBrxG3@{8Z3@{8ZfBrxG7+@G+7+@H{7{CAk"],"@":[28,25,-1,6,"000000RI30etZB90N?|F2LLbtI0gU#fZ%@^3=iSK!;TyrapA#-9vB$$;e(DGI5^|O1CBgk828Kp&;NiNdEfxx000L72mp8kfC2yD00;O000000"],"*":[16,20,-1,6,"000BP5r7$(J-i?I2jCz0J-iv15r6~000000000000000000000"],"+":[18,18,-1,8,"0000m01N;F006)MFaQhy|NKAy05AXy00RI3zyL4+3;+NC0000000"],"=":[18,15,-1,11,"000mFga6<F0000000000|M)-t000000000000000000"],"<":[18,19,-1,7,"00000fB@hCcmQ|+cmQ|+cmOy62Y>*000)2ocmM~00N?-!000000000"],">":[18,19,-1,7,"000O81AqW{00)2ocmM~00C)fo00)2vfCqpFfCqpBfB=91000000000"],"[":[11,25,-1,5,"00Z!N4*}pj2Y~P%1HgC>0pL6bfbbpzz<3V<;5-L_`~Uy"],"]":[11,25,-1,5,"00-b41AuT20l+v10N@-0fN%~0z&Hm0;2Z;ha1H^%_y7O"],"\\u2014":[32,10,-2,16,"00000KmY&yKmY&y00000000000000000000000000000000000"],"\\u2013":[18,10,-2,16,"000mF!~gIA0000000000000000000"],"\\u00b7":[11,14,-1,12,"00F=}4}kC-000000000000000"],"\\u2019":[11,20,-1,6,"00F>!2Y~Pn0f68T00000000000000000000"],"\\u2018":[11,20,-1,6,"001x?2LQl42f+9a00000000000000000000"],"\\u201c":[16,20,-1,6,"0009F4jddX7+^ebKKLGZ9ykC10000000000000000000000000"],"\\u201d":[16,20,-1,6,"0016%9(*5s4?G4K4mcceFu(u+0000000000000000000000000"],"\\u2026":[30,7,-1,19,"00000I1C2?@OVB4!Ql8G2ZP`^3<m%J0000"],"\\u00e9":[14,21,-1,5,"000BP9suA2000000q`I2al^-t9zXd1!@v&!JOFqA{{i>_00"],"\\u00fc":[18,21,-1,5,"000000CNBx;0G`O00001`S>0_2Zw>-;COf*9tVek;ox|99v%mef&bt>d;kCd"],"\\u00f1":[18,21,-1,5,"0002v0DpiV;0$m800000`QRV?2akc_;COf*9tVek;ox|99v%mWf#Kl%`~Uy|"]},"adv":{"A":20,"B":19,"C":20,"D":20,"E":19,"F":17,"G":22,"H":22,"I":11,"J":14,"K":22,"L":19,"M":26,"N":20,"O":22,"P":17,"Q":22,"R":20,"S":16,"T":19,"U":20,"V":20,"W":28,"X":20,"Y":20,"Z":19,"a":14,"b":16,"c":12,"d":16,"e":12,"f":9,"g":14,"h":16,"i":8,"j":9,"k":16,"l":8,"m":23,"n":16,"o":14,"p":16,"q":16,"r":12,"s":11,"t":9,"u":16,"v":14,"w":20,"x":14,"y":14,"z":12,"0":14,"1":14,"2":14,"3":14,"4":14,"5":14,"6":14,"7":14,"8":14,"9":14," ":7,".":7,",":7,";":9,":":9,"!":9,"?":14,"\'":8,"-":9,"(":9,")":9,"\\"":16,"/":8,"&":23,"%":28,"$":14,"#":14,"@":26,"*":14,"+":16,"=":16,"<":16,">":16,"[":9,"]":9,"\\u2014":28,"\\u2013":14,"\\u00b7":9,"\\u2019":9,"\\u2018":9,"\\u201c":14,"\\u201d":14,"\\u2026":28,"\\u00e9":12,"\\u00fc":16,"\\u00f1":16}}'
FONTS['SB19'] = '{"ascent":17,"height":22,"glyphs":{"A":[16,15,-1,3,"000Ak1Hc2o1>gkW4B!ax2yh?p5O@$cFgSR8000"],"B":[15,16,-1,3,"0095MbHL+)#{-TBI1lg~a5!*q;Nii?5BvZC000"],"C":[16,15,-1,3,"000O04j3E=JP0@dH~=^RH~=^RJO~^J4j2dc000"],"D":[16,16,-1,3,"004jB9B>>s95@_292^`R92^`R95@^}9B_Z&00000"],"E":[15,15,-1,3,"0095sa6sUJzyp8>5D(xSKsW$!0N_EvkN*Gw00"],"F":[14,15,-1,3,"00IBO!v_Q$0C54t2k;y~aRI;w02~1P0000"],"G":[17,15,-1,3,"0005}1BU~EgTMj60N?;{060Dz4i5(dgMi_{AHV<r"],"H":[17,15,-1,3,"002Kf2L}U#fx*Dw;Bat1_#7M#4hIJVgMq=r^Y8!w"],"I":[9,15,-1,3,"03U|~fxzH!I2;ZK1A)Q#00"],"J":[12,15,-1,3,"008_0fH(tyI0Jw<1AsUKf-olo-~a#"],"K":[17,15,-1,3,"002K92L=O#0mK000CxaCfF0ltcn2N>hXKRG`1k+-"],"L":[15,15,-1,3,"008~~Z~))|zyp8>01f~g05||}AmBm4kN*Gw00"],"M":[20,15,-1,3,"000NTd>#jZ;P@8{fpNGOlYu!n6SILHI1%H43^)+OhsgW@000"],"N":[16,15,-1,3,"004YE9ta)?7YGxG6UY(B5a<y25O@$c5Ey(I000"],"O":[17,15,-1,3,"000B{1C9fOgMq=oaNsy_95@af2Mz}VgMj0JKL7v#"],"P":[14,15,-1,3,"00I92&IcSEaB;!M2RI+VZ~?#v02~1P0000"],"Q":[17,18,-1,3,"000B{1C9fOgMq=oaNsy_95@af2Mz}VgMj0JKY#(i0Pp}F0000"],"R":[16,15,-1,3,"004jB9B>>s95@^}9B?1t9N-+_9B>?X95_B6000"],"S":[13,15,-1,3,"004dlFkpiK9sqs;_ygbv2pB-a3?IM%00"],"T":[15,15,-1,3,"0095-4k8>tH~??}-~qq`fCm5$02}}~0sH^}00"],"U":[16,15,-1,3,"002Hb90(i;90(i;90(i;90(i;92guJ4=@Md000"],"V":[16,15,-1,3,"004d*JO~^Z91so=4loBG2Ve)l1Hc2o0e}I3000"],"W":[21,15,-1,3,"000B<2ag08IB<c(j0YZIIr0I^kO$9zJa_@)zy}ThFkk_J00000"],"X":[16,15,-1,3,"002Kc9uN*72Ve)l1Aqg-1HcC01n>xO7&v@<000"],"Y":[16,15,-1,3,"004hH92gD|4loBG2jBz11Hc2o1Hc2o1HcF1000"],"Z":[15,15,-1,3,"004jB!@&mt9soE1-~+%102}~#AmBs6hyMTo00"],"a":[12,11,-1,7,"00Hn5fEWRR_&I|ZJA>Q+00"],"b":[13,15,-1,3,"00Y1d0B{3<AHe4a95~^}4mfdxoDaYN00"],"c":[10,11,-1,7,"00ZHO;xG&Y0N^|W-~a"],"d":[13,15,-1,3,"000gEFadxJ2jJre7&yVk4lr?poDc8-00"],"e":[10,11,-1,7,"00+ac?lX_$0N^+WzyJ"],"f":[9,15,-1,3,"00)Oh1B3A3a5x+e2LplN00"],"g":[12,16,-1,6,"000CZgSaun7(0RR5Cix>!wew993KDx"],"h":[13,15,-1,3,"00F=b0B{3<9pLu|7&yVk4lr?pj2`d+00"],"i":[7,16,-1,2,"05IUd01g~DaN)y;4*&"],"j":[9,20,-2,2,"00RSnzyJVv91aHqfxzH!I2;ZZ4gdf"],"k":[13,15,-1,3,"00F=b0B{3<9B|?XAUgs458!iyoF4E100"],"l":[7,15,-1,3,"0C3^MhYlP#aN)y;fB*"],"m":[18,11,-1,7,"000j6gWmAt95}}gF~f{-;~Y504|~7>00"],"n":[13,11,-1,7,"00G_)aB+i-9AM)I7&yW2000"],"o":[12,11,-1,7,"00HnjgPb|ToH@gsIf3v100"],"p":[13,15,-1,7,"00aCEaB;(q9B|`@967=K4ghcifIa{K00"],"q":[13,16,-1,6,"00003_%Xwd9B|`@95~^}2lxTN4ghcmfB*"],"r":[11,11,-1,7,"00%IB4ncr01^~bq2fzRT"],"s":[9,11,-1,7,"01pg?1Hte-1|uH;00"],"t":[9,13,-1,5,"01O5X!-2rya5x+X1Hb?"],"u":[13,11,-1,7,"00YhraC3v49N^~%I6c7s000"],"v":[12,11,-1,7,"00)dX!-yP#&<_Cc1^{3H00"],"w":[16,11,-1,7,"004LnID|OJ8OR;z9`Fuu4sZk@000"],"x":[12,11,-1,7,"00-PTf$$Ch;12<~Glx6?00"],"y":[12,15,-1,7,"00+!CgNPl0&<_Cc4gg>T06<6w0000"],"z":[11,11,-1,7,"00;1#2Y}!>2LZ%5kMIBh"],"0":[12,15,-1,3,"008hCgP1wPoH@gsIm4Ve!<ZX@@Bjb"],"1":[12,15,-1,3,"003YP0pJDzU<LqS1^{3N0AL0I_y7O"],"2":[12,15,-1,3,"00Zzdf*1jS7z2PX1^~bq0{}n6`~Uy"],"3":[12,15,-1,3,"00Zzdf;a<!I0Jz21ArU>!W<)m@Bjb"],"4":[12,15,-1,3,"001}xfOrppxEp~uBZvHdz&HbdH~;_"],"5":[12,15,-1,3,"00a0xg8(1`06zdY0l*vq!W<)m@Bjb"],"6":[12,15,-1,3,"008(LgNQf-fIkDcF~giW!<-p_@Bjb"],"7":[12,15,-1,3,"00aC#!U!RN7y$q<0svqJ0Kg0ZfB*m"],"8":[12,15,-1,3,"008higPb|Tm>YrcIfEQA!yGw*@Bjb"],"9":[12,15,-1,3,"00HnjgBWqc95KV3AHW;|f;b}s-~a#"]," ":[4.75,0,-1,16,""],".":[7,5,-1,13,"0C3^J00"],",":[7,8,-1,13,"0AS$3h8O?"],";":[8,14,-1,7,"02mw?0000OJRArZAOH"],":":[8,11,-1,7,"02mw?0000O92fu"],"!":[8,15,-1,3,"02~+?7#J8B7#IK;92fu"],"?":[12,15,-1,3,"00Zzdf*1jSI0t~>3;@6Y0Kg6azyJU"],"\'":[7,15,-1,3,"0B~S|0000000000000"],"-":[8,7,-1,11,"06shb0000"],"(":[8,19,-1,3,"00Img7&tgMFfcGUI5-#_3<3Z"],")":[8,19,-1,3,"03a|J91IK$4h{|s3=A9?FdzT"],"\\"":[13,15,-1,3,"007JeU^4)S0000000000000000000000"],"/":[9,15,-2,3,"0097iz(61{5C{we0s{d600"],"&":[18,15,-1,3,"0005t0L%b0fDGURumE}BJ}?=~4nG5jfZ*U9d;{~q000"],"%":[21,15,-1,3,"0001Z5C&m@GYA2gfDFt4W<UYt@Bn7O0%iasFasHYFl+$>zyJUM"],"$":[12,17,-1,2,"002M_gGe-kKs*ERAAo!Xz)U2=SU&(j000"],"#":[12,15,-1,3,"0077cfQSi){276e5eNJ;128iKAOHX"],"@":[20,19,-1,3,"0000Fzyk*WU>FPmfrrc(n8O*2GZ@1&h%-5ZGY~WW13Q2i00F=t4h#T400000"],"*":[12,15,-1,3,"003Y%gZvKz{5F7K00000000000000"],"+":[13,13,-1,5,"000mGfCK;_AMh9eKmq^|00000000"],"=":[13,11,-1,7,"00I9100000AMgMG00000000"],"<":[13,13,-1,5,"00031a1H^$7yxhp-~qq^00000000"],">":[13,13,-1,5,"0096F01f~g0B{EY;5Y#Q00000000"],"[":[8,18,-1,3,"06sW4I5;>sI5;>sI5;>sJ^%"],"]":[8,18,-1,3,"06ZKV92^`R92^`R92^`RJOB"],"\\u2014":[23,7,-2,11,"0001g|L_0+00000000000000000"],"\\u2013":[13,7,-2,11,"00IAi0000000000"],"\\u00b7":[8,10,-1,8,"02mw?00000000"],"\\u2019":[8,15,-1,3,"02mw`3>Yu~000000000"],"\\u2018":[8,15,-1,3,"00ama7#th`000000000"],"\\u201c":[12,15,-1,3,"007JxgD^9LxH*6T00000000000000"],"\\u201d":[12,15,-1,3,"00Wpi!JHU@7$N`w00000000000000"],"\\u2026":[21,5,-1,13,"0002Ph6fyQFyVjz000"],"\\u00e9":[10,16,-1,2,"00F>YFaQ7n@a#K`<M_Zh4gv50"],"\\u00fc":[13,16,-1,2,"00003U>g7c00HL*I61-24sdgWoF3qRfB*"],"\\u00f1":[13,16,-1,2,"004Fe;3oh8008d?xH!Sa4lr?pj2vM1fB*"]},"adv":{"A":14,"B":13,"C":14,"D":14,"E":13,"F":12,"G":15,"H":15,"I":7,"J":10,"K":15,"L":13,"M":18,"N":14,"O":15,"P":12,"Q":15,"R":14,"S":11,"T":13,"U":14,"V":14,"W":19,"X":14,"Y":14,"Z":13,"a":10,"b":11,"c":8,"d":11,"e":8,"f":6,"g":10,"h":11,"i":5,"j":6,"k":11,"l":5,"m":16,"n":11,"o":10,"p":11,"q":11,"r":8,"s":7,"t":6,"u":11,"v":10,"w":14,"x":10,"y":10,"z":8,"0":10,"1":10,"2":10,"3":10,"4":10,"5":10,"6":10,"7":10,"8":10,"9":10," ":5,".":5,",":5,";":6,":":6,"!":6,"?":10,"\'":5,"-":6,"(":6,")":6,"\\"":11,"/":5,"&":16,"%":19,"$":10,"#":10,"@":18,"*":10,"+":11,"=":11,"<":11,">":11,"[":6,"]":6,"\\u2014":19,"\\u2013":10,"\\u00b7":6,"\\u2019":6,"\\u2018":6,"\\u201c":10,"\\u201d":10,"\\u2026":19,"\\u00e9":8,"\\u00fc":11,"\\u00f1":11}}'
FONTS['SB13'] = '{"ascent":12,"height":15,"glyphs":{"A":[12,11,-1,2,"003YP0Pqt5Fdu>#A%+|P00"],"B":[11,12,-1,2,"00-dC8N)Ds3}K8hhu{DJ00"],"C":[11,11,-1,2,"00Hpg7y|%c3;}=`0q_6-"],"D":[11,12,-1,2,"00-d47~>3Kj4_Tehu{DJ00"],"E":[11,11,-1,2,"00;2G7y|%&3;}>JhwuOZ"],"F":[10,11,-1,2,"01v|ez%mbm0KhN~000"],"G":[12,11,-1,2,"008(HLjW)X05QW17{L4h00"],"H":[12,11,-1,2,"00W*d!wfLP{4m1|FvFez00"],"I":[7,11,-1,2,"0C3^MhYlP#Z~y"],"J":[9,11,-1,2,"01pEJfWTld7z`W$00"],"K":[13,11,-1,2,"00G7fKx6}89{|h-a52Hh000"],"L":[11,11,-1,2,"00#iT7y|%c3;}>JhwuOZ"],"M":[14,11,-1,2,"0080RhYvg~u(HB)3Ctoe$>0D0"],"N":[12,11,-1,2,"00WFTg2*m{Xd{9cA%h4200"],"O":[12,11,-1,2,"008(f!wfLP4lu(EFu?c#00"],"P":[10,11,-1,2,"01v}3&NC0g0KhN~000"],"Q":[12,13,-1,2,"008(f!wfLP4lu(EFu?c&fE)k-"],"R":[12,11,-1,2,"00ZzbgBUS`@G}EAF@u}{00"],"S":[9,11,-1,2,"01pU+0|4+G1|lB-00"],"T":[11,11,-1,2,"01x>w1^~bq0{~zQ1Hb?P"],"U":[12,11,-1,2,"00WFLg9tE#2rz>P7=Z8q00"],"V":[12,11,-1,2,"00)dPfruFa&<z0K1^_?+00"],"W":[15,11,-1,2,"008hf!XeB-oda42yazB0U>Lvv00"],"X":[12,11,-1,2,"00WpA0N@S)U=IPX5raGc00"],"Y":[12,11,-1,2,"00WE|fshRV;06F-1_1B?00"],"Z":[11,11,-1,2,"00;1l1At%{2LQk@hwuOZ"],"a":[9,8,-1,5,"03HE{#$zz}00"],"b":[9,11,-1,2,"05}W=1L2s=W-=cD00"],"c":[8,8,-1,5,"030x2U@#m2"],"d":[10,11,-1,2,"00F=-3?B@_FpM(~zyJ"],"e":[8,8,-1,5,"06ZjoU@$xY"],"f":[7,11,-1,2,"05HLah71@mU;q"],"g":[9,12,-1,4,"000k!!eQWmd_FM`000"],"h":[10,11,-1,2,"01N{Fz&;IwFw8RzzyJ"],"i":[6,11,-1,2,"0K)(<!wfLM00"],"j":[7,14,-2,2,"01zMn!Gi`27$C!d00"],"k":[10,11,-1,2,"01N{Fz%mU3!1y)|zyJ"],"l":[6,11,-1,2,"0K*J0!wfLM00"],"m":[13,8,-1,5,"00H+6m~6vl8!+8~00"],"n":[10,8,-1,5,"01ty;%rgwbZ~y"],"o":[9,8,-1,5,"03HpD#$mAV00"],"p":[9,11,-1,5,"06z@IV=<8UU@$lU00"],"q":[10,12,-1,4,"0005-%rgkXF#H1mz;FN"],"r":[8,8,-1,5,"05(1_Ffcd("],"s":[7,8,-1,5,"0C9oA$({f"],"t":[7,9,-1,4,"0AS&R1`Hek"],"u":[9,8,-1,5,"06Pta!(p)e00"],"v":[9,8,-1,5,"067eXfxy5Z00"],"w":[12,8,-1,5,"00#szLuem?uo(aV"],"x":[9,8,-1,5,"06Px@0l{Io00"],"y":[9,11,-1,5,"067eXfxy5Z5D+i`00"],"z":[8,8,-1,5,"0DK%6I52zw"],"0":[9,11,-1,2,"01gd=#$z#<Og0Vx00"],"1":[9,11,-1,2,"00a&L0f4|@Fc=>I00"],"2":[9,11,-1,2,"03Hc|z+hk?AUr<+00"],"3":[9,11,-1,2,"03Hc|z`)=b3`QOR00"],"4":[9,11,-1,2,"00IL8fk7d-`~(6300"],"5":[9,11,-1,2,"03HYg1HdpC3`QOR00"],"6":[9,11,-1,2,"01pg=2g5O#Y&H%600"],"7":[9,11,-1,2,"03Qi}fIwg%Fc=5`00"],"8":[9,11,-1,2,"03Hp7!(rf<%qAWH00"],"9":[9,11,-1,2,"03Hd9#$mAd3<Mki00"]," ":[3.25,0,-1,11,""],".":[5,4,-1,9,"0gM0"],",":[5,6,-1,9,"0SrU{"],";":[6,10,-1,5,"0K)(P!vr7z"],":":[6,8,-1,5,"0K)(P!vF"],"!":[6,11,-1,2,"0K*J0K>#qo00"],"?":[9,11,-1,2,"03Hc|z`)=@02mAa00"],"\'":[6,11,-1,2,"0Ky0W0000000"],"-":[6,6,-1,7,"0pI`t00"],"(":[6,14,-1,2,"03i%8f(RhP1PA~"],")":[6,14,-1,2,"0RjvdVTKrE2tWV"],"\\"":[9,11,-1,2,"02>8@fB*mh0000000"],"/":[7,11,-2,2,"00<yJf&>U4KmY"],"&":[13,11,-1,2,"003|Xz%~Kk4shEBa52F5000"],"%":[15,11,-1,2,"001~Z(E+prNCU0_mH{jTSP<X<00"],"$":[9,13,-1,1,"00a*OLV>_|910~50RR9"],"#":[9,11,-1,2,"00{+;!$BeVNGucp00"],"@":[14,13,-1,2,"0018Vg9HRK(2_#g3urIEfB^&p-~a#"],"*":[9,11,-1,2,"00a+%gWx~_0000000"],"+":[9,9,-1,4,"00aUD;DA5?0000"],"=":[9,8,-1,5,"03Uz=1MmO<00"],"<":[9,10,-1,3,"004o50sz1m0ssI2"],">":[9,10,-1,3,"01yTNfG}WSKmY&$"],"[":[6,13,-1,2,"0OJfW!wfLP4gd"],"]":[6,13,-1,2,"0Ko(hK?D#%3;+"],"\\u2014":[17,5,-2,8,"001BV000000000"],"\\u2013":[10,5,-2,8,"01w~*0000"],"\\u00b7":[6,7,-1,6,"0K)(P000"],"\\u2019":[6,11,-1,2,"0K)_z0000000"],"\\u2018":[6,11,-1,2,"07DEg0000000"],"\\u201c":[9,11,-1,2,"00{{PgJ1vv0000000"],"\\u201d":[9,11,-1,2,"02>X0!ax830000000"],"\\u2026":[15,4,-1,9,"003ez#9#mb"],"\\u00e9":[8,11,-1,2,"01OxaJS2QzFgyS"],"\\u00fc":[9,11,-1,2,"000F52Vt<-Y&IW&00"],"\\u00f1":[10,11,-1,2,"00w}-06q<aFw8RzzyJ"]},"adv":{"A":9,"B":9,"C":9,"D":9,"E":9,"F":8,"G":10,"H":10,"I":5,"J":6,"K":10,"L":9,"M":12,"N":9,"O":10,"P":8,"Q":10,"R":9,"S":7,"T":9,"U":9,"V":9,"W":13,"X":9,"Y":9,"Z":9,"a":6,"b":7,"c":6,"d":7,"e":6,"f":4,"g":6,"h":7,"i":4,"j":4,"k":7,"l":4,"m":11,"n":7,"o":6,"p":7,"q":7,"r":6,"s":5,"t":4,"u":7,"v":6,"w":9,"x":6,"y":6,"z":6,"0":6,"1":6,"2":6,"3":6,"4":6,"5":6,"6":6,"7":6,"8":6,"9":6," ":3,".":3,",":3,";":4,":":4,"!":4,"?":6,"\'":4,"-":4,"(":4,")":4,"\\"":7,"/":4,"&":11,"%":13,"$":6,"#":6,"@":12,"*":6,"+":7,"=":7,"<":7,">":7,"[":4,"]":4,"\\u2014":13,"\\u2013":6,"\\u00b7":4,"\\u2019":4,"\\u2018":4,"\\u201c":6,"\\u201d":6,"\\u2026":13,"\\u00e9":6,"\\u00fc":7,"\\u00f1":7}}'
FONTS['SB11'] = '{"ascent":10,"height":13,"glyphs":{"A":[10,10,-1,1,"00RKPSQY_;@Qh=C00"],"B":[10,11,-1,1,"01ty8*gg!yFw8yx000"],"C":[10,10,-1,1,"00+Ymz#td{0K^{v00"],"D":[10,11,-1,1,"01tyO%rOi@Fw8yx000"],"E":[9,10,-1,1,"03Qqn1Hpj6Vm|-?"],"F":[9,10,-1,1,"03Qqn1Hpj6U^oB("],"G":[11,10,-1,1,"00ZE_7y<xC3}K8P000"],"H":[11,10,-1,1,"00wZz7{mBu3}K8jfB*"],"I":[6,10,-1,1,"0K*J0!wfJ0"],"J":[8,10,-1,1,"02~Mi2nYxWcmM"],"K":[11,10,-1,1,"00tn)8Uw(54S|?3fB*"],"L":[9,10,-1,1,"02mAg0|9`*Vm|-?"],"M":[13,10,-1,1,"00D;%Fmr;O7ht;tm?Yo;00"],"N":[10,10,-1,1,"01QKr<ShxpaEu`U00"],"O":[11,10,-1,1,"00Y3p7{VAs3}J{K000"],"P":[9,10,-1,1,"03Hp7Lt*g1U^oB("],"Q":[11,12,-1,1,"00Y3p7{VAs3}J{L0N@S)00"],"R":[11,10,-1,1,"00+R#8G|r<4S|?5fB*"],"S":[8,10,-1,1,"06ZWdJRAlFJOB"],"T":[10,10,-1,1,"03XD_Fbo3#z%U#D00"],"U":[10,10,-1,1,"01QJA#4!v*5X2q;00"],"V":[10,10,-1,1,"031UQz#0aCz%UE|00"],"W":[13,10,-1,1,"00V)HNM=E>4&ZkI7zls>00"],"X":[10,10,-1,1,"01m;Ra0~+hU<@Mw00"],"Y":[10,10,-1,1,"01iVCXdVLqz%UK~00"],"Z":[9,10,-1,1,"03QK?fWW|DVm|-?"],"a":[8,7,-1,4,"05}XhY&-w"],"b":[8,10,-1,1,"0AL^>JSHY4JOB"],"c":[7,7,-1,4,"0C9r`2LJ#"],"d":[8,10,-1,1,"00ssIJ|<=+J^%"],"e":[7,7,-1,4,"0CBU%2LJ#"],"f":[6,10,-1,1,"0OJU7f(S4G"],"g":[8,10,-1,3,"002B}I3PSEJOB"],"h":[8,10,-1,1,"03aYBJSHY4HUI"],"i":[5,10,-1,1,"0SE#Rgm3@"],"j":[7,12,-2,1,"003YCg9Z#3Fu(u"],"k":[9,10,-1,1,"01yZS0zp9FST+Cv"],"l":[5,10,-1,1,"0|-J8gm3@"],"m":[11,7,-1,4,"00*#>5@JkkfB*"],"n":[8,7,-1,4,"06ZopCN=;"],"o":[8,7,-1,4,"05~jcEI0r"],"p":[8,9,-1,4,"0DLAUCOjZ;00"],"q":[9,10,-1,3,"000k!#$hn{3<dxI"],"r":[7,7,-1,4,"0C>TJ1^@s"],"s":[7,7,-1,4,"0C9o9j{pD"],"t":[6,8,-1,3,"0EY-5g8%"],"u":[8,7,-1,4,"0AwU2Bt8H"],"v":[8,7,-1,4,"0Aw^c7!Uv"],"w":[10,7,-1,4,"02pFW{2l~=00"],"x":[8,7,-1,4,"0CYGQIBWm"],"y":[8,9,-1,4,"0Aw^c7!VL(00"],"z":[7,7,-1,4,"0Ptah4}bs"],"0":[8,10,-1,1,"05~jcY;0^SH~;"],"1":[8,10,-1,1,"02nwJ7#J8BJOB"],"2":[8,10,-1,1,"05}W`3>Xj~d;k"],"3":[8,10,-1,1,"05}W`7z_+dcmM"],"4":[8,10,-1,1,"01O-)EKGb13;+"],"5":[8,10,-1,1,"06ZW7I1CI-H~;"],"6":[8,10,-1,1,"030M>cx+@WH~;"],"7":[8,10,-1,1,"06YW)2nY}mFaQ"],"8":[8,10,-1,1,"05~ixIBaBWH~;"],"9":[8,10,-1,1,"061)HY&;AMH~;"]," ":[2.75,0,-1,9,""],".":[5,4,-1,7,"0SEv"],",":[5,6,-1,7,"0SH6@"],";":[6,9,-1,4,"0K)(<!w3K"],":":[6,7,-1,4,"0K)(<zyJ"],"!":[6,10,-1,1,"0K*6%fDAAI"],"?":[8,10,-1,1,"05}W`7!Uvu5C8"],"\'":[5,10,-1,1,"0SG_<0000"],"-":[6,5,-1,6,"0l)wN"],"(":[6,12,-1,1,"07D2Nh6o_R00"],")":[6,12,-1,1,"0RjvVK?E>_00"],"\\"":[8,10,-1,1,"06Zil00000000"],"/":[7,10,-2,1,"01zMn0t65s00"],"&":[11,10,-1,1,"00V$n3IW)A3BedYfB*"],"%":[13,10,-1,1,"006`bAX)*S0bmw@Gzh=|00"],"$":[8,12,-1,0,"01!MdFgP3(RCo{o"],"#":[8,10,-1,1,"02Bm#C@6d=C;$"],"@":[12,12,-1,1,"004LpLk1@zmMcQEF9Qe<000"],"*":[8,10,-1,1,"01!MlJP-f?000"],"+":[8,8,-1,3,"00;;^2nYZG"],"=":[8,7,-1,4,"06qXd0000"],"<":[8,8,-1,3,"00tN!7zO|U"],">":[8,8,-1,3,"03a9!7$5)u"],"[":[6,11,-1,1,"0Ky0$f(RhM00"],"]":[6,11,-1,1,"0mBS1!wfON00"],"\\u2014":[15,5,-2,6,"004jR00000000"],"\\u2013":[9,5,-2,6,"03Uz=000"],"\\u00b7":[6,7,-1,4,"0K)(P000"],"\\u2019":[6,10,-1,1,"0K*I*00000"],"\\u2018":[6,10,-1,1,"073{b00000"],"\\u201c":[8,10,-1,1,"02C-FEC2ui000"],"\\u201d":[8,10,-1,1,"04y{l2mk;8000"],"\\u2026":[13,4,-1,7,"00EN>m;e9"],"\\u00e9":[7,10,-1,1,"05CuUjh-+#00"],"\\u00fc":[8,10,-1,1,"000;OWF#acJ^%"],"\\u00f1":[8,10,-1,1,"02C|$JSHY4HUI"]},"adv":{"A":8,"B":7,"C":8,"D":8,"E":7,"F":7,"G":9,"H":9,"I":4,"J":6,"K":9,"L":7,"M":10,"N":8,"O":9,"P":7,"Q":9,"R":8,"S":6,"T":7,"U":8,"V":8,"W":11,"X":8,"Y":8,"Z":7,"a":6,"b":6,"c":5,"d":6,"e":5,"f":4,"g":6,"h":6,"i":3,"j":4,"k":6,"l":3,"m":9,"n":6,"o":6,"p":6,"q":6,"r":5,"s":4,"t":4,"u":6,"v":6,"w":8,"x":6,"y":6,"z":5,"0":6,"1":6,"2":6,"3":6,"4":6,"5":6,"6":6,"7":6,"8":6,"9":6," ":3,".":3,",":3,";":4,":":4,"!":4,"?":6,"\'":3,"-":4,"(":4,")":4,"\\"":6,"/":3,"&":9,"%":11,"$":6,"#":6,"@":10,"*":6,"+":6,"=":6,"<":6,">":6,"[":4,"]":4,"\\u2014":11,"\\u2013":6,"\\u00b7":4,"\\u2019":4,"\\u2018":4,"\\u201c":6,"\\u201d":6,"\\u2026":11,"\\u00e9":5,"\\u00fc":6,"\\u00f1":6}}'
FONTS['SR14'] = '{"ascent":13,"height":17,"glyphs":{"A":[13,12,-1,2,"001xnfEEC-1b{{Z@DPCp3^)J)"],"B":[11,12,-1,2,"00-bk2*D6O1R#bG!Vvrb00"],"C":[11,12,-1,2,"00Hno5CQ-|2mt^fLI^$p00"],"D":[12,12,-1,2,"00Zz4!2}RN1`uHc5J3z-000"],"E":[11,12,-1,2,"00-be2mv5G1OR{#0ucTH00"],"F":[10,12,-1,2,"01v?cKoAFk06-7~1AqV"],"G":[12,12,-1,2,"008(9LI5BF03ZSkAi)d|fB*"],"H":[12,12,-1,2,"00WE=!3+?={1Cwm5Wx&MzyJ"],"I":[7,12,-1,2,"0B}Ho0t5&UAm9K"],"J":[8,12,-1,2,"02~Mi2nYxW2uN@M"],"K":[12,12,-1,2,"00WE>0U#CuU>*T55rGIe-~a"],"L":[11,12,-1,2,"00#g-2mt^f1OR{#0ucTH00"],"M":[15,12,-1,2,"003ZcV8FwG#{rfBECUz=Fa}`A-~a#"],"N":[12,12,-1,2,"00WE|K*R(<WCK7H0l*9}KmY"],"O":[12,12,-1,2,"008hX!UP~f1|VVtAVCZd000"],"P":[10,12,-1,2,"01tsML=gnR;6M-r1AqV"],"Q":[12,14,-1,2,"008hX!UP~f1|VVtAVCZdfEWPa00"],"R":[12,12,-1,2,"00Zz5ffx~i5FP<A5dj!DzyJ"],"S":[10,12,-1,2,"00)8)fG`IDa0~$m!{7h"],"T":[11,12,-1,2,"01xpH0sue=0RSKb0Dw3E00"],"U":[12,12,-1,2,"00Rs#Lj*8G1TaGc5J89!000"],"V":[12,12,-1,2,"00Rs#K?oRtfDHi91^{3J000"],"W":[16,12,-1,2,"003|dFbFY-5r`6y8qf+*3}6gk03ZMW"],"X":[12,12,-1,2,"00WE|fY1g2U<LrN34sVOzyJ"],"Y":[12,12,-1,2,"00WE=frt$N&;|ft1^{3O000"],"Z":[11,12,-1,2,"00-cV0RUha0|3Af1`z%L00"],"a":[9,9,-1,5,"03HDVgTWz?d;kC"],"b":[9,12,-1,2,"05Avy1Hll8Mj{ap000"],"c":[8,9,-1,5,"03ISBU?3nI00"],"d":[9,12,-1,2,"00RJkLE#XH#3B&~fB*"],"e":[8,9,-1,5,"030SJd>|kk00"],"f":[7,12,-1,2,"060N|h71@mV88$"],"g":[9,13,-1,4,"000MsLLm_FKt2(O$G`v"],"h":[9,12,-1,2,"01yZS1K|*eL?RIlfB*"],"i":[6,12,-1,2,"00ICo!wfLP00"],"j":[7,15,-2,2,"003YCg9Z#3Fkrz3000"],"k":[9,12,-1,2,"01yZS0wExvcr+6XzyJ"],"l":[6,12,-1,2,"0K*J0!wfLP00"],"m":[13,9,-1,5,"00I68m_$M%5fF%m%m4r"],"n":[9,9,-1,5,"03Qg1LLm@{Yybc"],"o":[9,9,-1,5,"01gO*MlleGH~;_"],"p":[9,12,-1,5,"03Ha0LLm@{cpwlA000"],"q":[9,13,-1,4,"000MsLL(4}L>>VEfWQC"],"r":[7,9,-1,5,"09e5S1PB-a"],"s":[7,9,-1,5,"0C0f=fq@(V"],"t":[6,11,-1,3,"00Imkf(Rhs00"],"u":[9,9,-1,5,"022s=LLm@{d;kC"],"v":[9,9,-1,5,"06B<;K|tUj5C8x"],"w":[13,9,-1,5,"00V;vkZgf)48UdqAOHX"],"x":[9,9,-1,5,"02u`X0D#~aOaK4"],"y":[9,12,-1,5,"02z#eK|tUz5C{Mq000"],"z":[8,9,-1,5,"06Yu`7!V?U00"],"0":[9,12,-1,2,"01gO*LL(WBL?RIf000"],"1":[9,12,-1,2,"00agB0DwRs5C{YZ000"],"2":[9,12,-1,2,"03Hc|Kp-#>5D*X#fB*"],"3":[9,12,-1,2,"03HZ{Kww}91OfpM000"],"4":[9,12,-1,2,"00RMm!C<hM41WUwfB*"],"5":[9,12,-1,2,"03Qeh0s-I%1OfpM000"],"6":[9,12,-1,2,"01pg=0s-)dMk5gi000"],"7":[9,12,-1,2,"03V2eKtLc65C{ka000"],"8":[9,12,-1,2,"01gO*LSW#CL?RIf000"],"9":[9,12,-1,2,"01gO@Mj;UR1OfvO000"]," ":[3.5,0,-1,12,""],".":[6,3,-1,11,"0Du4"],",":[6,5,-1,11,"0D}Mk"],";":[6,11,-1,5,"0KfnM01PmI00"],":":[6,9,-1,5,"0KfnM01N;"],"!":[7,12,-1,2,"03bkt0t5&E06+i"],"?":[8,12,-1,2,"06YW+1_Tfg000mG"],"\'":[5,12,-1,2,"0SG_<00000"],"-":[7,6,-1,8,"0Pp|+000"],"(":[7,15,-1,2,"01!cf1PBlyK!Je)000"],")":[7,15,-1,2,"004l2fdT{w5MY7;000"],"\\"":[8,12,-1,2,"04yXV0000000000"],"/":[6,12,-1,2,"03ZYqLI@!Q00"],"&":[13,12,-1,2,"008g=z$O8p4lvmSXd!_P2bcf="],"%":[14,12,-1,2,"007|vL>V9@0OSBJ0VD*FB0vrR00"],"$":[9,14,-1,1,"00akxLV>_=918`4hk$?p"],"#":[9,12,-1,2,"00{(wNAQ3U{v;9!000"],"@":[15,15,-1,2,"000NTAV7dY9E3>;A`(O-fJ-2o0e}I30Pp|+00"],"*":[9,12,-1,2,"00atyf}lVE00000000"],"+":[10,10,-1,4,"0000006zc#0000000"],"=":[10,9,-1,5,"01v<b06zc#00000"],"<":[10,10,-1,4,"002N>U?2tnU<3dF00"],">":[10,10,-1,4,"00;qq7y$u+fPer100"],"[":[7,14,-1,2,"0C0f<1PBlyK!F2*00"],"]":[7,14,-1,2,"0B~Tzg9Z#3Fkr)g00"],"\\u2014":[18,6,-2,8,"000mFzyJUM00000000"],"\\u2013":[11,6,-2,8,"00-~@0000000"],"\\u00b7":[7,7,-1,7,"03ZMW0000"],"\\u2019":[7,12,-1,2,"03bjB000000000"],"\\u2018":[7,12,-1,2,"03gAD000000000"],"\\u201c":[8,12,-1,2,"001N;0000000000"],"\\u201d":[8,12,-1,2,"05mip0000000000"],"\\u2026":[16,3,-1,11,"000q)000"],"\\u00e9":[8,12,-1,2,"00amC9401wARrt7"],"\\u00fc":[9,12,-1,2,"000F50$~t{L?RInfB*"],"\\u00f1":[9,12,-1,2,"01N{F1K|*eL?RIlfB*"]},"adv":{"A":10,"B":9,"C":9,"D":10,"E":9,"F":8,"G":10,"H":10,"I":5,"J":5,"K":10,"L":9,"M":12,"N":10,"O":10,"P":8,"Q":10,"R":9,"S":8,"T":9,"U":10,"V":10,"W":13,"X":10,"Y":10,"Z":9,"a":6,"b":7,"c":6,"d":7,"e":6,"f":5,"g":7,"h":7,"i":4,"j":4,"k":7,"l":4,"m":11,"n":7,"o":7,"p":7,"q":7,"r":5,"s":5,"t":4,"u":7,"v":7,"w":10,"x":7,"y":7,"z":6,"0":7,"1":7,"2":7,"3":7,"4":7,"5":7,"6":7,"7":7,"8":7,"9":7," ":4,".":4,",":4,";":4,":":4,"!":5,"?":6,"\'":3,"-":5,"(":5,")":5,"\\"":6,"/":4,"&":11,"%":12,"$":7,"#":7,"@":13,"*":7,"+":8,"=":8,"<":8,">":8,"[":5,"]":5,"\\u2014":14,"\\u2013":7,"\\u00b7":5,"\\u2019":5,"\\u2018":5,"\\u201c":6,"\\u201d":6,"\\u2026":14,"\\u00e9":6,"\\u00fc":7,"\\u00f1":7}}'
FONTS['SR11'] = '{"ascent":10,"height":13,"glyphs":{"A":[10,10,-1,1,"00RKPP!<G%;EW>x00"],"B":[9,10,-1,1,"03Qg1L*W>NMm_)l"],"C":[9,10,-1,1,"01t=+1_J<qLLUGC"],"D":[10,10,-1,1,"01tu?gdvDR5QIJe00"],"E":[9,10,-1,1,"03Qeh1Hk}*Kt2Ef"],"F":[8,10,-1,1,"06rifJRl$-FaQ"],"G":[10,10,-1,1,"00+VVfM6KH5QHB900"],"H":[10,10,-1,1,"01Uzqgg*#E5QH-T00"],"I":[6,10,-1,1,"0Ky0$f(S4G"],"J":[7,10,-1,1,"05Cv-0t5(P00"],"K":[10,10,-1,1,"01Uz)kSGlTV2CjQ00"],"L":[9,10,-1,1,"02l}a0s#PkKt2Ef"],"M":[12,10,-1,1,"00Rs#!<;F?tS-V#B)|X"],"N":[10,10,-1,1,"01QJAq%8?TFpMDp00"],"O":[10,10,-1,1,"00)8)gkhLM5QH8800"],"P":[8,10,-1,1,"06ZolCOjY@FaQ"],"Q":[10,12,-1,1,"00)8)gkhLs5QH88fDix"],"R":[10,10,-1,1,"01pBnh$asLK!`H{00"],"S":[8,10,-1,1,"06ZWdI1B^?JOB"],"T":[9,10,-1,1,"06&5O0DwRs5EuXe"],"U":[10,10,-1,1,"01QG9gdqq*5X2q;00"],"V":[10,10,-1,1,"01QJAKoSOkz%T#+00"],"W":[13,10,-1,1,"00RLCfJA|G3ZP~KFbIGE00"],"X":[10,10,-1,1,"01Uw(Fbo3$U<e}s00"],"Y":[10,10,-1,1,"01QI_NC*P}z%UE|00"],"Z":[9,10,-1,1,"03QJXfPlb2Kt2Ef"],"a":[7,7,-1,4,"0B|A1hX4Q"],"b":[8,10,-1,1,"0AL^>I3y$_H~;"],"c":[7,7,-1,4,"0C0i=2LJ#"],"d":[8,10,-1,1,"01N~KJS0S9JOB"],"e":[7,7,-1,4,"0C1zi2LJ#"],"f":[6,10,-1,1,"0AdI*f(S4G"],"g":[8,10,-1,3,"002BBI3PR(JOB"],"h":[8,10,-1,1,"0AL^>I3y$_Bme"],"i":[5,10,-1,1,"00;sQgdhL"],"j":[6,12,-2,1,"0096HK?D#(00"],"k":[8,10,-1,1,"03aYBBp^5_Bme"],"l":[5,10,-1,1,"0SH16gdhL"],"m":[11,7,-1,4,"00-cb5<*B@000"],"n":[8,7,-1,4,"05~KhBrE^"],"o":[8,7,-1,4,"05~K>Bsc&"],"p":[8,9,-1,4,"05~KhBsd^o00"],"q":[8,10,-1,3,"002BBL}WY!3;+"],"r":[6,7,-1,4,"0OANBfB*"],"s":[6,7,-1,4,"0LBam-~a"],"t":[5,9,-1,2,"00_bmh5!"],"u":[8,7,-1,4,"0Bj^ABs>5"],"v":[8,7,-1,4,"0AwUE7!Uv"],"w":[10,7,-1,4,"02pFWv=#(_00"],"x":[8,7,-1,4,"03;X?2y6f"],"y":[8,9,-1,4,"0AwUE7!VL(00"],"z":[7,7,-1,4,"0PtXf4}bs"],"0":[8,10,-1,1,"05~LML_}mHH~;"],"1":[8,10,-1,1,"01z+`5D*X$7yt"],"2":[8,10,-1,1,"05}8$2nY}$d;k"],"3":[8,10,-1,1,"05}8;7z6|aH~;"],"4":[8,10,-1,1,"00;;eC<uHA2mk"],"5":[8,10,-1,1,"06YKyI0OU)H~;"],"6":[8,10,-1,1,"030MBd}Jgf7yt"],"7":[8,10,-1,1,"06YW$2nY}mAOH"],"8":[8,10,-1,1,"05~KhI3z?QH~;"],"9":[8,10,-1,1,"061hsWHbZ>H~;"]," ":[2.75,0,-1,9,""],".":[5,3,-1,8,"0RR"],",":[5,5,-1,8,"0SEv9"],";":[5,9,-1,4,"0RR9HfB*"],":":[5,7,-1,4,"0RR9H00"],"!":[6,10,-1,1,"0D=f0f&d@@"],"?":[7,10,-1,1,"0B|5cf&c&z00"],"\'":[4,10,-1,1,"1^@s600"],"-":[6,5,-1,6,"0l)wN"],"(":[6,12,-1,1,"00Iahh6o^m00"],")":[6,12,-1,1,"00IOMK?D$h00"],"\\"":[6,10,-1,1,"0HTTj00000"],"/":[6,10,-1,1,"06_pCfDk|c"],"&":[11,10,-1,1,"00V%K8UdJE8N(PofB*"],"%":[11,10,-1,1,"00to>B?ABp0+13BfB*"],"$":[8,12,-1,0,"002B7FgP3pL^uEd"],"#":[8,10,-1,1,"02Bm#ASiq&2mk"],"@":[12,12,-1,1,"004LpLI5WskP1NXAOZjn000"],"*":[8,10,-1,1,"01z}7G!Os)000"],"+":[8,9,-1,2,"00000JOBUy00"],"=":[8,7,-1,4,"06YLZ0000"],"<":[8,8,-1,3,"000;u7ytkO"],">":[8,8,-1,3,"03Zki2p|9e"],"[":[6,11,-1,1,"0Ky0$f(RhM00"],"]":[6,11,-1,1,"0Ko(hK?D%M00"],"\\u2014":[15,5,-2,6,"004jR00000000"],"\\u2013":[9,5,-2,6,"03QGV000"],"\\u00b7":[6,6,-1,5,"0Du4h00"],"\\u2019":[6,10,-1,1,"0D%Yq00000"],"\\u2018":[6,10,-1,1,"00IaA00000"],"\\u201c":[7,10,-1,1,"06-x?0000000"],"\\u201d":[7,10,-1,1,"08pSn0000000"],"\\u2026":[13,3,-1,8,"009vI00"],"\\u00e9":[7,10,-1,1,"01!X}g&q(%00"],"\\u00fc":[8,10,-1,1,"001ZeY$PNkJOB"],"\\u00f1":[8,10,-1,1,"05AvuI3y$_EC2"]},"adv":{"A":8,"B":7,"C":7,"D":8,"E":7,"F":6,"G":8,"H":8,"I":4,"J":4,"K":8,"L":7,"M":10,"N":8,"O":8,"P":6,"Q":8,"R":7,"S":6,"T":7,"U":8,"V":8,"W":10,"X":8,"Y":8,"Z":7,"a":5,"b":6,"c":5,"d":6,"e":5,"f":4,"g":6,"h":6,"i":3,"j":3,"k":6,"l":3,"m":9,"n":6,"o":6,"p":6,"q":6,"r":4,"s":4,"t":3,"u":6,"v":6,"w":8,"x":6,"y":6,"z":5,"0":6,"1":6,"2":6,"3":6,"4":6,"5":6,"6":6,"7":6,"8":6,"9":6," ":3,".":3,",":3,";":3,":":3,"!":4,"?":5,"\'":2,"-":4,"(":4,")":4,"\\"":4,"/":3,"&":9,"%":9,"$":6,"#":6,"@":10,"*":6,"+":6,"=":6,"<":6,">":6,"[":4,"]":4,"\\u2014":11,"\\u2013":6,"\\u00b7":4,"\\u2019":4,"\\u2018":4,"\\u201c":5,"\\u201d":5,"\\u2026":11,"\\u00e9":5,"\\u00fc":6,"\\u00f1":6}}'
FONTS['SI20'] = '{"ascent":18,"height":23,"glyphs":{"A":[17,15,-3,4,"0000u02}}w01E&Nzyx3hFaj6@`~e360fB(Q!0-S7"],"B":[14,15,-1,4,"004i0!vh8k7%;%Y1Nay)VBvv=4j3{2fB*m"],"C":[16,15,-1,4,"0005}2LucR7yuXmFaR(BFaR(BFbEh392f`S000"],"D":[18,16,-2,4,"000C20AS!47zP6YfWTld7z_*p0|3ClU@$NY7!UXW00000"],"E":[15,15,-2,4,"001BO7!WWZU;w}Yhy(BpAQ%8J0AN7ChyDNn00"],"F":[16,15,-2,4,"000mC1_TBK1^@;C1`r4E3=j+e3;+xO3;;d=000"],"G":[17,15,-1,4,"0002~0l@))fq($O0KfoX05Con1`GxR0|CK+KY#!L"],"H":[19,15,-2,4,"0005;@E8~a0{~!P3=9E*fIsjI3;}_FFfaxN0KmX}d;kCd"],"I":[11,15,-2,4,"00Hm}0{~zQ0e~<L0e~<D0Kj|z00"],"J":[12,15,-1,4,"002AzfEWRQFarQE0{}1r0AOYVzyJU"],"K":[18,15,-2,4,"000Byz+k`_U<M!okN|i99{>#C0~i3q05IST7!QYl000"],"L":[14,15,-2,4,"002G!U;%&z02lyZ0e}nuFaW><1Pl=WzyJU"],"M":[21,15,-2,4,"0001Z4*|e%4hMi(I0C}J7B&E}FbI)=MwkLPz!Am(j4&PtzyJUM"],"N":[18,15,-2,4,"000BSz&Jn_5Cwz*F#t?J5wHws0vZ5=fFR%q7!L#h000"],"O":[16,15,-1,4,"0005-1{@3w7zP*yFa|INFb*&bFbo(N954sK000"],"P":[15,15,-2,4,"001B07+^49V8Fuxjsx%v02lx;0AK*X2fzRT00"],"Q":[17,18,-1,4,"0002^0fPa7fq-DZFyI(q3@`>51`GoO0|3JSJ^%v%0l)xw0000"],"R":[15,15,-2,4,"001B07+^49V8Fuxjsx%vU>LwLfMI~c2g85>00"],"S":[12,15,-1,4,"004XlVT2d~zzzU-0l*9Z#0+7B@Bjb"],"T":[15,15,-1,4,"002MmMj;G9FaTfxzyW{*00saU05AYx1MmO<00"],"U":[18,15,-1,4,"000NWz`$TI5DWwZ0RX^2U=SD#1_A+qfM8$@FahuY000"],"V":[17,15,-1,4,"0018k1_A+r0KouZfG~gzzy?4AKmp(YU;r=x5C8xG"],"W":[21,15,-1,4,"0002+2L=c*7-0az2nINSF~k9uKn$_~IN$-t01PkyVSoY%00000"],"X":[16,15,-2,4,"000l30~iAk0iXfE0l)#k0l)&l1Yitc7+^T~000"],"Y":[15,15,-1,4,"004Y=FhF4d#sJ6xpaZ}I00saU05AYx1MmO<00"],"Z":[14,15,-1,4,"002M12Lu=Zzy<&~0Kf(SFaf~^2rwc4fB*m"],"a":[12,11,-1,8,"004X#!3;3N2qA+QGlAFu00"],"b":[12,16,-1,3,"00F=Z0Du?)fE$6#7{LTE!wfKk7(M_1"],"c":[11,11,-1,8,"008h~2m=6M2mydG1Hb?P"],"d":[13,16,-1,3,"000L77y!To03aU&7!bjR3?M@T7#YBJ000"],"e":[11,11,-1,8,"008h}2*VhB2mydG1Hb?P"],"f":[10,20,-1,3,"007`fFbo0%;9wXA0RTWS3<ChbAQ%P!00"],"g":[12,15,-1,8,"004XlK@2d%3^2nOGlAFvgb+gq-~a#"],"h":[12,16,-1,3,"00F=Z0Du?)fE$6#7{LrM!w4{g7$Lv_"],"i":[8,15,-1,4,"01ONO02mk;7#I*RFgO4"],"j":[11,19,-4,4,"001xs0000606-W60ALIO0ALIOfFLXf0000"],"k":[12,16,-1,3,"00F=V0Du?)fEdA$5(8j9128iK5Fvm7"],"l":[8,16,-1,3,"02~Yq3<ww)7#J83Ffcd("],"m":[16,11,-1,8,"0029j9PAjx5QH&|F^n;cF^n+`000"],"n":[12,11,-1,8,"00X!j!Hf{Y3^0QTF@hWb00"],"o":[12,11,-1,8,"008(H!vruw1R%l;F@f*^00"],"p":[14,15,-3,8,"000|+a{-J55HP^Q0|*RYJ^+9Q02l!90000"],"q":[12,15,-1,8,"004X#K@2d%3?Rb@GlAFvfEWP)7ytk"],"r":[10,11,-1,8,"00!acU>F1g0KhN|000"],"s":[10,11,-1,8,"00+Ymz!(F7aSTHbfB*"],"t":[8,13,-1,6,"00;;^7!VLJFfcGY00"],"u":[12,11,-1,8,"00WE|!3+??3^0QjGlARy00"],"v":[11,11,-1,8,"00tPt2tk-K27qu30RR91"],"w":[16,11,-1,8,"001xy5QG_w8OR#Y8qf@23}6UA000"],"x":[12,11,-2,8,"00G7fKxhX5a0da9F@qcc00"],"y":[13,15,-3,8,"003cu3=BYK10Wgza037s0DuSpz&HQ^00"],"z":[11,11,-2,8,"00Zzw0f1l(0|3AnhwuOZ"],"0":[12,15,-1,4,"004Ll!G;)P1~6j=FvAQm!w4|}-~a#"],"1":[12,15,-1,4,"000mN0I&l9FaiJ|1^{3N0AK_I_y7O"],"2":[12,15,-1,4,"008(H!3F?e1OUJo0RUhO0RVr8_y7O"],"3":[13,15,-2,4,"002G$7!be)05Agp@BqLA02n~R3?G0100"],"4":[12,15,-1,4,"000aDz&rxLNC<(LF@hL>;5Y*SFaQ7"],"5":[12,15,-1,4,"008_S!2l2e03QGt0Kg0YzzAW7-~a#"],"6":[12,15,-1,4,"002G=V1gI}05^jSFvAQm!weCC@Bjb"],"7":[13,15,-1,4,"0094o_#l7;06+!+AOZj|0{{>KfEWM(00"],"8":[12,15,-1,4,"004XpVTKrCgc!j1FvARB#tbom@Bjb"],"9":[12,15,-1,4,"008(H!Gthl1~6fc55Non!Wbh1-~a#"]," ":[5.0,0,-1,17,""],".":[7,4,-1,15,"0ARoX"],",":[7,7,-1,15,"0AS$31ONa"],";":[9,14,-1,8,"00sj90000002mAc0s;U4"],":":[9,11,-1,8,"00sj90000002mAa00"],"!":[9,15,-1,4,"00RR7fWTlN5C{YS00Dr&00"],"?":[12,15,-1,4,"008_5V1@u-1OdQs1OPw)000aCzyJU"],"\'":[7,15,-1,4,"01#lof&c&j00000000"],"-":[9,7,-1,12,"03Q#400000"],"(":[10,20,-1,3,"001B`5DW$ZfIu(|0|3A<3<Chb5C#B100"],")":[10,20,-2,3,"00IC&2m=7XFbo3#z%U2~0f0a-7z_je00"],"\\"":[11,15,-1,4,"00FQj1i+XA00000000000000000"],"/":[11,15,-2,4,"000mK0DvF_0RUhK0{}o60sw#j00"],"&":[18,15,-1,4,"0002^0Am0czy>e@m;iY2J{TFq3_Ak{fWW{wcmwBv000"],"%":[19,15,-1,4,"0005tKxPma#se9EVjv920P=VMkpLzz2*d&yfP*kFJOBUy"],"$":[12,17,-1,3,"000mN;g%UepdJ9=2Y@^Pz)VEOSU&(j000"],"#":[13,15,-1,4,"000pIhzNj0AMhdp5D|m_1VBUrATa;{00"],"@":[20,19,-1,4,"0000F-~$1GU<?cZK!d~(%s~i*F$hBugfSR{F^DsJ0Uf{?004jh1_l5hfB*mh"],"*":[12,15,-1,4,"001xp0saSp{sRCo00000000000000"],"+":[16,14,-1,5,"000000RRC20RRC2ANT<P0RRC20RR9100000"],"=":[16,11,-1,8,"001BO00000001BO0000000000000"],"<":[16,14,-1,5,"0000002lyZ0e}Vo7yt$U0e}Et02lxO00000"],">":[16,14,-1,5,"000007yt$U0e}Et02lyZ0e}tw7ytkO00000"],"[":[11,19,-1,3,"008h10sz1m0{~zM0RUhO0e~<B0Dv$DfB*m"],"]":[11,19,-2,3,"008g?0KgCi0Kgan06+)>0ALIOfFJ}1fB*m"],"\\u2014":[21,7,-2,12,"00061|9}7h00000000000000"],"\\u2013":[14,7,-2,12,"0095M000000000000"],"\\u00b7":[7,9,-1,10,"05D(x00000"],"\\u2019":[9,15,-1,4,"00RMlKtMnM000000000000"],"\\u2018":[9,15,-1,4,"009930Ki}X000000000000"],"\\u201c":[13,15,-1,4,"000pI5D@^(24DaH00000000000000000"],"\\u201d":[13,15,-1,4,"001)qm;^vX1V8`)00000000000000000"],"\\u2026":[20,4,-1,15,"000997%*Xg000"],"\\u00e9":[12,16,-1,3,"000aDfFJ+>00)7H5rY^$0st@r5FP*k"],"\\u00fc":[12,15,-1,4,"002w`zyJUPj2OWT5W@^GgBUY`+yDR"],"\\u00f1":[12,16,-1,3,"003YMKo|f306T%q7{LrM!w4{g7$Lv_"]},"adv":{"A":12,"B":12,"C":13,"D":14,"E":12,"F":12,"G":14,"H":14,"I":7,"J":9,"K":13,"L":11,"M":17,"N":13,"O":14,"P":12,"Q":14,"R":12,"S":10,"T":11,"U":14,"V":12,"W":17,"X":12,"Y":11,"Z":11,"a":10,"b":10,"c":9,"d":10,"e":9,"f":6,"g":10,"h":10,"i":6,"j":6,"k":9,"l":6,"m":14,"n":10,"o":10,"p":10,"q":10,"r":8,"s":8,"t":6,"u":10,"v":9,"w":13,"x":9,"y":9,"z":8,"0":10,"1":10,"2":10,"3":10,"4":10,"5":10,"6":10,"7":10,"8":10,"9":10," ":5,".":5,",":5,";":7,":":7,"!":7,"?":10,"\'":4,"-":7,"(":7,")":7,"\\"":8,"/":6,"&":16,"%":17,"$":10,"#":10,"@":18,"*":10,"+":14,"=":14,"<":14,">":14,"[":8,"]":8,"\\u2014":18,"\\u2013":10,"\\u00b7":5,"\\u2019":7,"\\u2018":7,"\\u201c":11,"\\u201d":11,"\\u2026":18,"\\u00e9":9,"\\u00fc":10,"\\u00f1":10}}'
FONTS['SI13'] = '{"ascent":12,"height":15,"glyphs":{"A":[11,11,-2,2,"003YN0)P+`1K@-pgg5{I"],"B":[10,11,-1,2,"00+SsMiB?Y5XK=7fB*"],"C":[11,11,-1,2,"008)57y<x52mt^vgWv!F"],"D":[13,12,-2,2,"004Xf7!W{$1Q1|@3=qKl00000"],"E":[11,11,-2,2,"00H<R1OSj81^~bihwuOZ"],"F":[12,11,-2,2,"008_5K!6AU@E8Gr5CMPy00"],"G":[12,11,-1,2,"004X#LjWKG03pH%FoEy@00"],"H":[13,11,-2,2,"003hG7!bgO2jF1?7!bh5000"],"I":[8,11,-2,2,"01ONW2nYxm7#IK"],"J":[9,11,-1,2,"00#j8fWTlN5J)%x00"],"K":[13,11,-2,2,"003hGAQAwe2LNmXAQ6Ga000"],"L":[10,11,-2,2,"00RJkAP52hfM5_0zyJ"],"M":[15,11,-2,2,"000;;Fu-Gg#{kv@s0ok~AY{M*00"],"N":[13,11,-2,2,"003hH5EOu<0e}PoFcE-+000"],"O":[12,11,-1,2,"008h9!vr8g1R%l)F@fL!00"],"P":[11,11,-2,2,"00HnL1Yn391^~bi0{{R3"],"Q":[12,13,-1,2,"008(H!vr8g1R%l)F@f*~05|{u"],"R":[11,11,-2,2,"00HnL1YnpR2EfP>gD?O9"],"S":[9,11,-1,2,"01pg?0f1l_1VTOl00"],"T":[10,11,-1,2,"01x0uFbo3#fFKA4000"],"U":[13,11,-1,2,"006=S5Fmj72mrzc5HSGo000"],"V":[12,11,-1,2,"00RsVfe;Y^pb7xM3;=)t00"],"W":[14,11,-1,2,"006*25d_E+AVdM&24Dz)AOHXW"],"X":[12,11,-2,2,"007JcfKUbiU<LrN5d$~?00"],"Y":[11,11,-1,2,"00%Hc4FRAS0sue=0{{R3"],"Z":[10,11,-1,2,"00+V_7z6_WfIuN1zyJ"],"a":[9,8,-1,5,"01pU+#zP>`00"],"b":[9,11,-1,2,"00;yE1L2T}L?j#l00"],"c":[8,8,-1,5,"03IM9U|=`^"],"d":[9,11,-1,2,"00Dr2LE#XX$YdG-00"],"e":[8,8,-1,5,"030MZU|=`^"],"f":[8,14,-1,2,"01OZiI4~d}ARu61KmY"],"g":[9,11,-1,5,"01pU+Mq?n*2t+&p00"],"h":[9,11,-1,2,"00;yE1L2T}Oe8Y^00"],"i":[6,11,-1,2,"06+jR!U!OM00"],"j":[8,14,-3,2,"00aO43<L}a2nYxmFaQ"],"k":[8,11,-1,2,"05A|RCLlN{EMx!"],"l":[6,11,-1,2,"06_#0!U!OM00"],"m":[11,8,-1,5,"00+3)5@JY686W@"],"n":[9,8,-1,5,"03Qs5LSZ4800"],"o":[9,8,-1,5,"01gO*Mj<fp00"],"p":[10,11,-2,5,"00+U4L=gmmz<?kO000"],"q":[9,11,-1,5,"01pU+Mq@DW2m}HE00"],"r":[8,8,-1,5,"06a7xARr(B"],"s":[7,8,-1,5,"0C<6bfgS("],"t":[6,9,-1,4,"07Hl%f(!r"],"u":[9,8,-1,5,"01*g;!a*R=00"],"v":[8,8,-1,5,"03skHI2aHB"],"w":[11,8,-1,5,"00bD46GN~j1b_e"],"x":[9,8,-2,5,"01bkHfWV-b00"],"y":[10,11,-3,5,"00JO@Gz0;FKoAHF000"],"z":[8,8,-2,5,"03HMg7!W)F"],"0":[9,11,-1,2,"00#twLLm`|%p@ED00"],"1":[9,11,-1,2,"00IXA0DwRs5EvW)00"],"2":[9,11,-1,2,"01pU&Kp-F>ARs;f00"],"3":[10,11,-2,2,"00V&#1OfwqFbpCO000"],"4":[9,11,-1,2,"00RMm!9gGp`~(I700"],"5":[9,11,-1,2,"01pTR1HdpC3`9Ht00"],"6":[9,11,-1,2,"00#sF0s-KNL?#XZ00"],"7":[9,11,-1,2,"01t?OKtKQ>AP^7$00"],"8":[9,11,-1,2,"01pg?Lm=RY#AY4<00"],"9":[9,11,-1,2,"01gO*LLu-73<Mki00"]," ":[3.25,0,-1,11,""],".":[5,3,-1,10,"0RR"],",":[5,5,-1,10,"0SG_<"],";":[6,10,-1,5,"06+i$0t6rc"],":":[6,8,-1,5,"06+i$0ss"],"!":[6,11,-1,2,"0AYj>K>z@N00"],"?":[9,11,-1,2,"01p6wKwv-s000O800"],"\'":[5,11,-1,2,"0E7Sl0000"],"-":[6,6,-1,7,"0pI`t00"],"(":[7,14,-1,2,"00<z11PCx-z<~h(00"],")":[7,14,-2,2,"001B$K!FAb5I}$c00"],"\\"":[8,11,-1,2,"02CAi000000000"],"/":[8,11,-2,2,"000C42mlZOAOHX"],"&":[13,11,-1,2,"003|XKr#T}4se?Ua3O*A000"],"%":[13,11,-1,2,"0080%07(K+9dHzZBmp1}000"],"$":[9,13,-1,1,"00IYwLjb@q90DUB0ssI"],"#":[9,11,-1,2,"00aPs!9XGSKnNrN00"],"@":[14,13,-1,2,"0018Vfdm92kdi`431}z4fB^sl-~a#"],"*":[9,11,-1,2,"00a($gP=eF0000000"],"+":[11,10,-1,3,"004jx0s-&{0RR91000"],"=":[11,8,-1,5,"00ZCv00Hm-0000"],"<":[11,10,-1,3,"0000C1_1yN0DuSp000"],">":[11,10,-1,3,"0001B0{{>N0ssI2000"],"[":[8,13,-1,2,"02~ky5D*YBARr(x00"],"]":[8,13,-2,2,"01N~K1OyBS2nYxm00"],"\\u2014":[15,6,-2,7,"004jR0000000000"],"\\u2013":[10,6,-2,7,"01v<b00000"],"\\u00b7":[5,7,-1,6,"0RR9100"],"\\u2019":[6,11,-1,2,"0APdw0000000"],"\\u2018":[6,11,-1,2,"03ieb0000000"],"\\u201c":[9,11,-1,2,"00jhsKmY&$0000000"],"\\u201d":[9,11,-1,2,"01X0yKmY&$0000000"],"\\u2026":[14,3,-1,10,"004-<000"],"\\u00e9":[9,11,-1,2,"00RI30l^^Pz+fBz00"],"\\u00fc":[9,12,-1,1,"000Dl009t)Oe7Kw000"],"\\u00f1":[9,11,-1,2,"01N?u1L2T}Oe8Y^00"]},"adv":{"A":8,"B":8,"C":9,"D":9,"E":8,"F":8,"G":9,"H":9,"I":4,"J":6,"K":9,"L":7,"M":11,"N":9,"O":9,"P":8,"Q":9,"R":8,"S":6,"T":7,"U":9,"V":8,"W":11,"X":8,"Y":7,"Z":7,"a":6,"b":6,"c":6,"d":6,"e":6,"f":4,"g":6,"h":6,"i":4,"j":4,"k":6,"l":4,"m":9,"n":6,"o":6,"p":6,"q":6,"r":5,"s":5,"t":4,"u":6,"v":6,"w":9,"x":6,"y":6,"z":5,"0":6,"1":6,"2":6,"3":6,"4":6,"5":6,"6":6,"7":6,"8":6,"9":6," ":3,".":3,",":3,";":4,":":4,"!":4,"?":6,"\'":3,"-":4,"(":4,")":4,"\\"":5,"/":4,"&":10,"%":11,"$":6,"#":6,"@":12,"*":6,"+":9,"=":9,"<":9,">":9,"[":5,"]":5,"\\u2014":12,"\\u2013":6,"\\u00b7":3,"\\u2019":4,"\\u2018":4,"\\u201c":7,"\\u201d":7,"\\u2026":12,"\\u00e9":6,"\\u00fc":6,"\\u00f1":6}}'


# ---- scene helpers (all drawing is clipped to the scene box) ----
def _sky(cv, x, y, w, h, stops):
    cv.vgrad(x, y, w, h, stops)


def _stars(cv, x, y, w, h, seed, n=26):
    rnd = random.Random(seed)
    for _ in range(n):
        xx = rnd.randrange(x + 2, x + w - 2)
        yy = rnd.randrange(y + 2, y + int(h * 0.55))
        r = rnd.choice([0, 0, 1])
        cv.disc(xx, yy, r, (255, 255, 240) if rnd.random() < 0.7 else (200, 210, 255))


def _moon(cv, cx, cy, r):
    cv.glow(cx, cy, r * 3, (250, 244, 200), 90)
    cv.disc(cx, cy, r, (248, 242, 214))
    cv.disc(cx - r // 3, cy - r // 4, r // 4, (228, 220, 190))
    cv.disc(cx + r // 4, cy + r // 3, r // 5, (232, 224, 194))


def _city(cv, x, y, w, base_y, seed, lit=0.55, body=(22, 26, 44), win=(255, 196, 90)):
    """Night skyline; buildings from y to base_y, seeded windows."""
    rnd = random.Random(seed)
    bx = x
    while bx < x + w - 4:
        bw = rnd.randrange(12, 30)
        bh = rnd.randrange(int((base_y - y) * 0.35), int((base_y - y) * 0.95))
        by = base_y - bh
        cv.rect(bx, by, bw, bh, body)
        if rnd.random() < 0.35:
            cv.rect(bx + bw // 3, by - 4, 2, 4, body)
        for wy in range(by + 5, base_y - 4, 7):
            for wx in range(bx + 3, bx + bw - 3, 6):
                if rnd.random() < lit:
                    cv.rect(wx, wy, 3, 4, win if rnd.random() < 0.8 else (150, 200, 255))
        bx += bw + rnd.randrange(1, 5)


def _flames(cv, fx, fy, s, seed):
    """Flame cluster rising from base point (fx, fy); s = size."""
    rnd = random.Random(seed)
    cv.glow(fx, fy - int(s * 0.4), int(s * 1.1), (255, 140, 30), 110)
    for k in range(3):
        off = rnd.randrange(-int(s * 0.45), int(s * 0.45))
        hs = s * rnd.uniform(0.7, 1.05)
        base = fy
        tipx = fx + off + rnd.randrange(-3, 4)
        tipy = fy - hs
        cv.poly([(fx + off - hs * 0.42, base), (tipx, tipy),
                 (fx + off + hs * 0.42, base)], (232, 92, 20))
        cv.poly([(fx + off - hs * 0.26, base), (tipx, tipy + hs * 0.18),
                 (fx + off + hs * 0.26, base)], (250, 176, 40))
        cv.poly([(fx + off - hs * 0.12, base), (tipx, tipy + hs * 0.38),
                 (fx + off + hs * 0.12, base)], (255, 236, 150))


def _smoke(cv, sx, sy, seed, n=5, drift=-8, c1=(70, 66, 62), c2=(150, 146, 138)):
    rnd = random.Random(seed)
    x, y = sx, sy
    for k in range(n):
        r = 4 + k * 3 + rnd.randrange(0, 3)
        col = mix(c1, c2, k / max(1, n - 1))
        cv.disc_a(x, y, r, col, 150)
        cv.disc_a(x + r // 2, y - 1, r // 2, mix(col, WHITE, 0.25), 110)
        x += drift + rnd.randrange(-3, 4)
        y -= r + rnd.randrange(2, 6)


def _sea(cv, x, y, w, h, top, bot, seed):
    cv.vgrad(x, y, w, h, [(0, top), (1, bot)])
    rnd = random.Random(seed)
    for _ in range(int(w * h / 260)):
        wx = rnd.randrange(x + 3, x + w - 8)
        wy = rnd.randrange(y + 2, y + h - 2)
        ln = rnd.randrange(4, 12)
        cv.hline(wx, wy, ln, mix(top, WHITE, 0.45), 1)


def _ship(cv, x, y, s, hull=(26, 26, 30), deck=(200, 60, 40)):
    """Cargo ship, hull from (x,y) width ~5.4*s, height ~1.1*s."""
    w = int(5.4 * s)
    h = int(1.1 * s)
    cv.poly([(x, y), (x + w, y), (x + w - int(0.5 * s), y + h),
             (x + int(0.4 * s), y + h)], hull)
    cv.rect(x + int(0.5 * s), y - int(0.55 * s), int(1.1 * s), int(0.55 * s), (240, 240, 235))
    for k, col in enumerate([(198, 60, 40), (30, 90, 140), (200, 150, 30), (40, 120, 70)]):
        cv.rect(x + int(1.8 * s) + k * int(0.85 * s), y - int(0.5 * s),
                int(0.75 * s), int(0.5 * s), col)
    cv.rect(x + int(4.7 * s), y - int(0.8 * s), int(0.3 * s), int(0.8 * s), deck)
    # reflection
    for k in range(3):
        cv.hline(x + int(0.6 * s) + k * 8, y + h + 3 + k * 3, w - int(1.2 * s) - k * 16,
                 mix(hull, WHITE, 0.25), 1)


def _figure(cv, x, y, s, shirt, skin=(214, 178, 138)):
    """Simple standing person, height ~2.6*s, feet at (x, y)."""
    cv.disc(x, y - int(2.3 * s), max(2, int(0.32 * s)), skin)
    cv.poly([(x - int(0.55 * s), y), (x - int(0.4 * s), y - int(1.9 * s)),
             (x + int(0.4 * s), y - int(1.9 * s)), (x + int(0.55 * s), y)], shirt)
    cv.rect(x - int(0.42 * s), y - int(0.9 * s), int(0.84 * s), int(0.9 * s), (30, 30, 34))


def _flag(cv, x, y, w, h, bands, pole_h=None):
    """Horizontal-band flag on a pole; bands = list of colors top..bottom."""
    ph = pole_h if pole_h is not None else h + 14
    cv.vline(x, y, ph, (60, 55, 45), 2)
    bh = h // max(1, len(bands))
    for k, col in enumerate(bands):
        cv.rect(x + 2, y + k * bh, w, bh + (1 if k == len(bands) - 1 else 0), col)


def _globe(cv, cx, cy, r):
    cv.disc(cx, cy, r, (38, 110, 180))
    cv.glow(cx - r // 3, cy - r // 3, r, (120, 190, 240), 60)
    rnd = random.Random(7)
    for _ in range(7):
        gx = cx + rnd.randrange(-r + 4, r - 8)
        gy = cy + rnd.randrange(-r + 4, r - 8)
        if (gx - cx) ** 2 + (gy - cy) ** 2 < (r - 3) ** 2:
            cv.ellipse(gx, gy, rnd.randrange(3, 7), rnd.randrange(2, 5), (74, 150, 80))
    cv.ellipse(cx - r // 2, cy - r // 2, r // 2, r // 3, (120, 190, 235))
    # graticule cross
    cv.hline(cx - r, cy, 2 * r, mix((38, 110, 180), WHITE, 0.35), 1)
    cv.vline(cx, cy - r, 2 * r, mix((38, 110, 180), WHITE, 0.35), 1)


def _mountains(cv, x, y, w, h, seed, cols):
    rnd = random.Random(seed)
    for layer, col in enumerate(cols):
        pts = [(x, y + h)]
        px = x
        base = y + h - layer * (h // (len(cols) + 1))
        while px < x + w:
            pw = rnd.randrange(20, 46)
            ph = rnd.randrange(h // 3, h - layer * 4)
            pts.append((px + pw // 2, base - ph))
            px += pw
        pts.append((x + w, y + h))
        cv.poly(pts, col)


def _pines(cv, x, y, w, h, seed, col=(24, 60, 36)):
    rnd = random.Random(seed)
    xx = x + 4
    while xx < x + w - 6:
        s = rnd.randrange(6, 12)
        cv.poly([(xx, y + h), (xx + s // 2, y + h - s * 2), (xx + s, y + h)], col)
        cv.rect(xx + s // 2 - 1, y + h - 2, 2, 2, (70, 50, 30))
        xx += s + rnd.randrange(3, 9)


# ---- hero scenes (310 x ~150) ----
def scene_cop31(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (232, 214, 170)), (0.55, (214, 190, 148)), (1, (186, 158, 118))])
    # arched windows with sky
    for k in range(3):
        wx = x + 14 + k * (w // 3)
        ww = w // 3 - 22
        cv.poly([(wx, y + h), (wx, y + 26), (wx + ww // 2, y + 8), (wx + ww, y + 26),
                 (wx + ww, y + h)], (168, 196, 214))
        cv.poly([(wx, y + h), (wx, y + 30), (wx + ww // 2, y + 14), (wx + ww, y + 30),
                 (wx + ww, y + h)], mix((168, 196, 214), (250, 220, 140), 0.35))
        cv.rect(wx, y + 26, ww, 3, (120, 96, 66))
    # sun through middle arch
    cv.disc(x + w // 2, y + 34, 9, (250, 214, 120))
    cv.glow(x + w // 2, y + 34, 26, (250, 214, 120), 80)
    # hanging lamps
    for lx in (x + 40, x + w // 2, x + w - 40):
        cv.vline(lx, y + 2, 10, (90, 70, 44), 1)
        cv.disc(lx, y + 14, 4, (255, 220, 130))
        cv.glow(lx, y + 14, 12, (255, 220, 130), 70)
    # globe emblem on wall centre
    _globe(cv, x + w // 2, y + 62, 20)
    # long table
    ty = y + h - 30
    cv.poly([(x + 10, ty + 22), (x + 16, ty), (x + w - 16, ty), (x + w - 10, ty + 22)],
            (96, 64, 40))
    cv.rect(x + 10, ty, w - 20, 4, (126, 88, 52))
    # delegates seated behind table
    rnd = random.Random(31)
    shirts = [(176, 32, 32), (28, 76, 140), (0, 104, 68), (198, 128, 0), (92, 58, 140),
              (30, 30, 34), (120, 60, 20)]
    for k in range(7):
        fx = x + 26 + k * ((w - 52) // 6)
        cv.disc(fx, ty - 12, 7, (214, 178, 138) if k % 2 else (168, 128, 96))
        cv.ellipse(fx, ty - 2, 10, 8, shirts[k % len(shirts)])
    # flags on the table
    for k, cols in enumerate([[(200, 40, 40), WHITE, (30, 80, 160)],
                              [(0, 120, 60), WHITE, (220, 60, 40)],
                              [(30, 80, 160), WHITE, (200, 40, 40)]]):
        fx = x + w // 2 - 34 + k * 34
        _flag(cv, fx, ty - 26, 16, 12, cols, pole_h=26)
    # podium right
    cv.rect(x + w - 44, ty - 6, 34, h - ty + 6 - 22 + 22, (70, 48, 30))
    cv.rect(x + w - 44, ty - 6, 34, 4, (100, 70, 44))
    cv.unclip()


def scene_ukraine(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (8, 12, 30)), (0.6, (20, 30, 58)), (1, (52, 44, 66))])
    _stars(cv, x, y, w, h, 11, 34)
    _moon(cv, x + w - 34, y + 26, 10)
    base = y + h - 12
    _city(cv, x + 4, y + 30, w - 8, base, 22, lit=0.6)
    # fires at building bases
    rnd = random.Random(5)
    for _ in range(4):
        fx = x + rnd.randrange(20, w - 20)
        _flames(cv, fx, base, 12, rnd.randrange(1000))
    # drone streaks
    for k in range(7):
        sx = x + rnd.randrange(10, w - 60)
        sy = y + rnd.randrange(6, 50)
        cv.line(sx, sy, sx + 34, sy + 26, (255, 210, 130), 2)
        cv.disc(sx + 34, sy + 26, 3, (255, 230, 170))
        cv.glow(sx + 34, sy + 26, 10, (255, 180, 80), 120)
    _smoke(cv, x + w // 3, y + 46, 9, n=4, drift=-6)
    _smoke(cv, x + 2 * w // 3, y + 52, 4, n=4, drift=5)
    cv.rect(x, base, w, h - (base - y), (12, 12, 20))
    cv.unclip()


def scene_bahrain(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (250, 150, 60)), (0.45, (214, 84, 48)),
                           (0.75, (96, 52, 96)), (1, (40, 34, 70))])
    cv.disc(x + int(w * 0.68), y + 30, 13, (255, 226, 150))
    cv.glow(x + int(w * 0.68), y + 30, 44, (255, 190, 90), 110)
    # refinery silhouette
    base = y + int(h * 0.62)
    cv.rect(x, base, w, h - (base - y), (52, 40, 52))
    for k in range(5):
        tx = x + 12 + k * 22
        th = 26 + (k % 3) * 10
        cv.rect(tx, base - th, 10, th, (38, 30, 40))
        cv.disc(tx + 5, base - th - 2, 3, (38, 30, 40))
        for wy in range(base - th + 5, base - 4, 8):
            cv.rect(tx + 2, wy, 2, 3, (255, 190, 90))
    # flare stack with flame
    cv.rect(x + w - 52, base - 52, 8, 52, (38, 30, 40))
    _flames(cv, x + w - 48, base - 52, 16, 77)
    # storage tanks
    for k in range(3):
        tx = x + 130 + k * 34
        cv.ellipse(tx + 11, base - 8, 11, 8, (66, 52, 60))
        cv.rect(tx, base - 16, 22, 16, (66, 52, 60))
    # sea with reflections
    _sea(cv, x, base, w, h - (base - y), (120, 60, 80), (36, 30, 58), 3)
    cv.glow(x + int(w * 0.68), base + 14, 30, (255, 170, 80), 90)
    # ship
    _ship(cv, x + 14, base + 14, 9)
    _smoke(cv, x + w - 48, base - 58, 12, n=5, drift=7)
    # birds
    for bx, by in [(x + 40, y + 18), (x + 56, y + 26), (x + 30, y + 30)]:
        cv.line(bx - 5, by, bx, by - 3, (30, 24, 34), 1)
        cv.line(bx, by - 3, bx + 5, by, (30, 24, 34), 1)
    cv.unclip()


# ---- mid scenes (~190 x 110) ----
def scene_sparta(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (96, 100, 112)), (0.5, (70, 74, 90)), (1, (46, 50, 66))])
    _smoke(cv, x + w // 2, y + 30, 21, n=4, drift=6)
    base = y + int(h * 0.66)
    _sea(cv, x, base, w, h - (base - y), (52, 62, 84), (26, 30, 48), 8)
    # burning ship, listing
    cv.poly([(x + 24, base - 6), (x + w - 30, base - 14), (x + w - 40, base + 8),
             (x + 30, base + 8)], (24, 24, 28))
    cv.rect(x + 40, base - 22, 26, 16, (210, 210, 205))
    _flames(cv, x + w // 2 - 8, base - 8, 15, 41)
    _flames(cv, x + w // 2 + 22, base - 10, 11, 42)
    cv.glow(x + w // 2, base + 6, 34, (255, 150, 50), 100)
    # distant coastline + rescue boat
    cv.poly([(x, base - 4), (x + 40, base - 14), (x + 80, base - 4)], (40, 44, 56))
    cv.poly([(x + w - 52, base + 16), (x + w - 30, base + 16), (x + w - 34, base + 22),
             (x + w - 48, base + 22)], (220, 90, 30))
    cv.unclip()


def scene_kryvyi(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (214, 150, 96)), (0.55, (150, 96, 88)), (1, (70, 58, 74))])
    cv.disc(x + w - 26, y + 18, 9, (250, 214, 150))
    base = y + h - 10
    # damaged apartment blocks, broken tops
    rnd = random.Random(17)
    bx = x + 6
    while bx < x + w - 10:
        bw = rnd.randrange(20, 34)
        bh = rnd.randrange(34, 62)
        by = base - bh
        cv.rect(bx, by, bw, bh, (52, 44, 48))
        # jagged broken roof
        cv.poly([(bx, by), (bx + bw // 3, by - 7), (bx + 2 * bw // 3, by + 2),
                 (bx + bw, by - 5), (bx + bw, by), ], (52, 44, 48))
        for wy in range(by + 6, base - 5, 8):
            for wx in range(bx + 4, bx + bw - 4, 7):
                if rnd.random() < 0.5:
                    cv.rect(wx, wy, 3, 4, (255, 200, 110))
        bx += bw + 3
    _smoke(cv, x + w // 2, y + 26, 31, n=4, drift=-5)
    _flames(cv, x + 30, base, 10, 55)
    cv.rect(x, base, w, h - (base - y), (30, 26, 30))
    # searchlight beam
    cv.poly([(x + w - 20, base), (x + w - 60, y + 10), (x + w - 44, y + 10)], (255, 240, 180))
    cv.unclip()


def scene_chapo(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (250, 170, 90)), (0.5, (200, 110, 90)), (1, (110, 70, 96))])
    _mountains(cv, x, y + int(h * 0.3), w, int(h * 0.4), 61, [(120, 80, 90), (90, 60, 76)])
    base = y + int(h * 0.72)
    cv.rect(x, base, w, h - (base - y), (150, 110, 70))
    cv.hline(x, base, w, (110, 80, 52), 2)
    # road
    cv.poly([(x, y + h), (x + w, y + h), (x + w - 30, base + 6), (x + 30, base + 6)],
            (60, 56, 52))
    # police SUVs with light bars
    for k in range(2):
        sx = x + 26 + k * 74
        sy = base + 12
        cv.rect(sx, sy, 44, 12, (24, 28, 40))
        cv.poly([(sx + 8, sy), (sx + 14, sy - 8), (sx + 32, sy - 8), (sx + 38, sy)], (24, 28, 40))
        cv.disc(sx + 10, sy + 13, 4, (20, 20, 22))
        cv.disc(sx + 34, sy + 13, 4, (20, 20, 22))
        cv.glow(sx + 22, sy - 10, 12, (255, 60, 50) if k == 0 else (70, 120, 255), 150)
        cv.disc(sx + 18, sy - 10, 3, (255, 60, 50) if k == 0 else (70, 120, 255))
        cv.disc(sx + 26, sy - 10, 3, (70, 120, 255) if k == 0 else (255, 60, 50))
    # helicopter silhouette
    hx, hy = x + w - 44, y + 16
    cv.ellipse(hx, hy, 16, 5, (30, 28, 34))
    cv.rect(hx + 14, hy - 1, 16, 2, (30, 28, 34))
    cv.line(hx - 8, hy - 3, hx + 10, hy - 3, (30, 28, 34), 1)
    cv.line(hx + 4, hy + 4, hx + 4, hy + 12, (30, 28, 34), 1)
    cv.unclip()


def scene_nepal(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (150, 200, 235)), (0.6, (210, 225, 235)), (1, (240, 230, 205))])
    cv.disc(x + w - 30, y + 18, 10, (255, 226, 150))
    # India Gate style arch
    ax, ay, aw, ah = x + w // 2 - 26, y + 30, 52, 58
    cv.rect(ax, ay, aw, ah, (196, 158, 104))
    cv.poly([(ax - 6, ay + 12), (ax + aw // 2, ay - 12), (ax + aw + 6, ay + 12)], (196, 158, 104))
    cv.poly([(ax + 16, ay + ah), (ax + 16, ay + 26), (ax + aw - 16, ay + 26),
             (ax + aw - 16, ay + ah)], (120, 88, 60))
    cv.rect(ax - 6, ay + 12, aw + 12, 4, (160, 124, 78))
    # flags
    _flag(cv, x + 16, y + 44, 20, 12, [(255, 120, 40), WHITE, (0, 130, 60)], pole_h=34)
    _flag(cv, x + w - 38, y + 44, 20, 12, [(220, 40, 40), (30, 80, 160), (220, 40, 40)], pole_h=34)
    # crowd
    rnd = random.Random(71)
    base = y + h - 8
    for k in range(9):
        fx = x + 12 + k * ((w - 24) // 8)
        _figure(cv, fx, base, 5, rnd.choice([(176, 32, 32), (28, 76, 140), (0, 104, 68),
                                             (198, 128, 0), (240, 230, 210)]))
    cv.rect(x, base, w, h - (base - y), (120, 100, 70))
    cv.unclip()


def scene_eisenkot(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (140, 190, 230)), (0.6, (205, 220, 232)), (1, (238, 228, 200))])
    # stone government building with columns
    bx, by, bw, bh = x + 24, y + 34, w - 48, 52
    cv.rect(bx, by, bw, bh, (214, 196, 164))
    cv.poly([(bx - 8, by), (bx + bw // 2, by - 16), (bx + bw + 8, by)], (196, 176, 140))
    cv.rect(bx - 8, by, bw + 16, 4, (170, 150, 116))
    for k in range(5):
        cx = bx + 12 + k * ((bw - 24) // 4)
        cv.rect(cx, by + 10, 7, bh - 10, (186, 166, 130))
    cv.rect(bx + bw // 2 - 9, by + 26, 18, bh - 26, (90, 70, 50))
    # Israeli flags
    for fx in (x + 8, x + w - 26):
        _flag(cv, fx, y + 40, 18, 11, [WHITE, (30, 80, 180), WHITE], pole_h=30)
    # podium + speaker
    cv.rect(x + w // 2 - 14, y + h - 22, 28, 14, (70, 52, 36))
    _figure(cv, x + w // 2, y + h - 22, 6, (30, 36, 48))
    cv.rect(x, y + h - 8, w, 8, (140, 124, 92))
    cv.unclip()


def scene_france(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (178, 190, 205)), (0.6, (210, 205, 190)), (1, (232, 214, 180))])
    # Eiffel silhouette in haze
    ex = x + w - 42
    cv.poly([(ex - 16, y + h - 30), (ex, y + 12), (ex + 16, y + h - 30)], (120, 118, 128))
    cv.rect(ex - 22, y + h - 34, 44, 4, (120, 118, 128))
    cv.rect(ex - 12, y + h - 52, 24, 3, (120, 118, 128))
    # street + crowd with placards
    base = y + h - 12
    cv.rect(x, base, w, h - (base - y), (96, 90, 84))
    rnd = random.Random(91)
    for k in range(10):
        fx = x + 10 + k * ((w - 20) // 9)
        _figure(cv, fx, base + 2, 6, rnd.choice([(176, 32, 32), (28, 76, 140), (240, 230, 210),
                                                 (0, 104, 68), (60, 60, 66)]))
        if k % 3 == 0:
            cv.rect(fx - 9, base - 34, 18, 11, (250, 244, 228))
            cv.rect(fx - 9, base - 34, 18, 2, (176, 32, 32))
            cv.vline(fx + 8, base - 34, 14, (90, 80, 66), 1)
    _smoke(cv, x + 30, y + 30, 97, n=3, drift=4)
    cv.unclip()


def scene_norway(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (250, 170, 90)), (0.5, (220, 130, 110)), (1, (120, 90, 120))])
    cv.disc(x + 30, y + 20, 11, (255, 226, 150))
    cv.glow(x + 30, y + 20, 34, (255, 200, 110), 90)
    base = y + int(h * 0.62)
    _sea(cv, x, base, w, h - (base - y), (90, 90, 130), (40, 44, 80), 13)
    # offshore platform
    px = x + w // 2 - 34
    cv.rect(px, base - 26, 68, 10, (40, 42, 50))
    for lx in (px + 6, px + 56):
        cv.rect(lx, base - 26, 5, 26, (40, 42, 50))
    cv.rect(px + 22, base - 44, 24, 18, (52, 56, 64))
    cv.line(px + 46, base - 44, px + 66, base - 62, (40, 42, 50), 3)
    cv.line(px + 66, base - 62, px + 66, base - 30, (40, 42, 50), 2)
    for wx in range(px + 4, px + 64, 8):
        cv.rect(wx, base - 24, 3, 3, (255, 210, 110))
    # gulls
    for bx, by in [(x + w - 40, y + 14), (x + w - 26, y + 22)]:
        cv.line(bx - 4, by, bx, by - 2, (30, 26, 34), 1)
        cv.line(bx, by - 2, bx + 4, by, (30, 26, 34), 1)
    cv.unclip()


def scene_gaza(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (240, 200, 140)), (0.6, (228, 180, 120)), (1, (200, 160, 110))])
    # ruined buildings background
    cv.rect(x + 8, y + 34, 26, 34, (150, 128, 100))
    cv.poly([(x + 8, y + 34), (x + 18, y + 26), (x + 28, y + 34)], (150, 128, 100))
    cv.rect(x + w - 40, y + 40, 30, 28, (160, 138, 108))
    _smoke(cv, x + 22, y + 30, 111, n=3, drift=3)
    base = y + int(h * 0.68)
    cv.rect(x, base, w, h - (base - y), (196, 164, 110))
    cv.poly([(x, y + h), (x + w, y + h), (x + w - 24, base + 4), (x + 24, base + 4)],
            (150, 124, 88))
    # white aid truck with red cross
    tx, ty = x + w // 2 - 42, base + 8
    cv.rect(tx, ty, 84, 20, (248, 246, 240))
    cv.rect(tx + 62, ty + 4, 22, 16, (248, 246, 240))
    cv.rect(tx + 8, ty + 5, 12, 10, (200, 40, 40))
    cv.rect(tx + 11, ty + 2, 6, 16, (200, 40, 40))
    cv.rect(tx + 5, ty + 8, 18, 4, (200, 40, 40))
    cv.disc(tx + 16, ty + 22, 5, (20, 20, 22))
    cv.disc(tx + 44, ty + 22, 5, (20, 20, 22))
    cv.disc(tx + 70, ty + 22, 5, (20, 20, 22))
    # dust
    cv.disc_a(tx + 84, ty + 16, 8, (220, 200, 160), 120)
    cv.disc_a(tx + 92, ty + 12, 6, (220, 200, 160), 100)
    cv.unclip()


def scene_poland(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (120, 180, 235)), (0.6, (190, 215, 240)), (1, (240, 232, 205))])
    # jets with contrails
    for k in range(2):
        jx, jy = x + 30 + k * 60, y + 16 + k * 12
        cv.line(jx - 34, jy + 8, jx - 4, jy + 2, (255, 255, 255), 2)
        cv.poly([(jx, jy), (jx + 18, jy + 3), (jx, jy + 6)], (60, 64, 74))
        cv.line(jx + 2, jy + 2, jx + 12, jy - 4, (60, 64, 74), 2)
    # flags: Poland + NATO + EU
    _flag(cv, x + 22, y + 44, 26, 16, [WHITE, (220, 40, 60)], pole_h=44)
    _flag(cv, x + 62, y + 44, 26, 16, [(20, 50, 140), (20, 50, 140)], pole_h=44)
    cv.disc(x + 75, y + 52, 4, (255, 220, 80))
    _flag(cv, x + 102, y + 44, 26, 16, [(20, 50, 140), (255, 220, 80), (20, 50, 140)], pole_h=44)
    # soldiers silhouettes
    base = y + h - 8
    for k in range(4):
        fx = x + 30 + k * 38
        _figure(cv, fx, base, 7, (44, 52, 40))
        cv.line(fx + 6, base - 16, fx + 14, base - 24, (44, 52, 40), 2)
    cv.rect(x, base, w, h - (base - y), (110, 100, 78))
    cv.unclip()


def scene_f1(cv, x, y, w, h):
    cv.clip(x, y, w, h)
    _sky(cv, x, y, w, h, [(0, (10, 10, 30)), (0.6, (30, 20, 60)), (1, (70, 40, 90))])
    _stars(cv, x, y, w, h, 131, 20)
    # neon skyline
    base = y + int(h * 0.6)
    rnd = random.Random(141)
    bx = x + 4
    neons = [(255, 60, 120), (60, 220, 255), (255, 200, 60), (160, 90, 255)]
    while bx < x + w - 8:
        bw = rnd.randrange(14, 26)
        bh = rnd.randrange(18, 42)
        cv.rect(bx, base - bh, bw, bh, (18, 18, 34))
        col = neons[rnd.randrange(len(neons))]
        for wy in range(base - bh + 4, base - 4, 7):
            if rnd.random() < 0.6:
                cv.rect(bx + 3, wy, bw - 6, 2, col)
        bx += bw + 2
    cv.rect(x, base, w, h - (base - y), (16, 14, 26))
    # race car with motion lines
    cx, cy = x + w // 2 - 40, base + 12
    cv.hline(x + 6, cy + 2, 60, (255, 255, 255), 1)
    cv.hline(x + 10, cy + 8, 44, (200, 200, 210), 1)
    cv.poly([(cx, cy + 14), (cx + 12, cy + 2), (cx + 62, cy + 2), (cx + 80, cy + 14)],
            (200, 30, 30))
    cv.poly([(cx + 18, cy + 2), (cx + 26, cy - 6), (cx + 44, cy - 6), (cx + 50, cy + 2)],
            (40, 40, 52))
    cv.disc(cx + 18, cy + 14, 6, (12, 12, 14))
    cv.disc(cx + 62, cy + 14, 6, (12, 12, 14))
    cv.disc(cx + 18, cy + 14, 3, (200, 200, 210))
    cv.disc(cx + 62, cy + 14, 3, (200, 200, 210))
    # checkered flag
    fx = x + w - 30
    for r in range(4):
        for c in range(4):
            cv.rect(fx + c * 5, y + 8 + r * 5, 5, 5,
                    WHITE if (r + c) % 2 == 0 else BLACK)
    cv.vline(fx - 1, y + 8, 26, (60, 55, 45), 2)
    cv.unclip()


# ---- layout + stories ----
MAP_GRID = [
    "............................................",
    "............................................",
    "..########...###......#####...##########......",
    "..#########..........######..###########.....",
    "...########...........#####...##########......",
    "....######.............####....########.......",
    ".....####...............###.....######........",
    "......###...............##.......####.........",
    ".......##...............##........##.........",
    "........##..............###...................",
    ".........###.............##...................",
    "..........##............##....................",
    "..........##.............#.........####........",
    "...........#......................######......",
    "..................................####........",
    "............................................",
]

PIN_POS = {1: (24, 5), 2: (23, 3), 3: (27, 6), 4: (23, 2), 5: (24, 4),
           6: (5, 7), 7: (29, 6), 8: (25, 6), 9: (20, 4), 10: (21, 2),
           11: (25, 7), 12: (22, 3), 13: (3, 6)}

HEROES = [
    dict(num=1, region="EUROPE", place="ANTALYA, TURKEY · CLIMATE",
         kicker="COP31: DEAL CLOSE",
         headline="COP31 climate talks close in on a final deal",
         body="A new package lands after talks run past Friday's deadline; "
              "objections due 03:00 GMT.",
         src="Reuters, BBC", scene="cop31"),
    dict(num=2, region="EUROPE", place="KYIV, UKRAINE · WAR",
         kicker="UKRAINE: BARRAGE",
         headline="Russia fires 400 drones and 110 missiles",
         body="One of the war's largest overnight attacks; at least seven "
              "people are killed in Kyiv.",
         src="Al Jazeera", scene="ukraine"),
    dict(num=3, region="MIDDLE EAST", place="MANAMA, BAHRAIN · IRAN WAR",
         kicker="BAHRAIN: STRUCK",
         headline="Iran strikes US bases in Bahrain",
         body="An industrial site burns, no injuries; tankers are hit in Hormuz.",
         src="Al Jazeera, CNA", scene="bahrain"),
]

MIDS = [
    dict(num=4, region="EUROPE", place="GULF OF FINLAND",
         kicker="SHIP ABLAZE",
         headline="Cargo ship burns after drone strike",
         body="Finland blames Ukraine. (BBC)", scene="sparta"),
    dict(num=5, region="EUROPE", place="KRYVYI RIH",
         kicker="2 DEAD, 60 HURT",
         headline="Strike hits Zelenskyy's home city",
         body="Two killed, 60 hurt. (Al Jazeera)",
         scene="kryvyi"),
    dict(num=6, region="AMERICAS", place="SINALOA, MEXICO",
         kicker="11 DEAD",
         headline="‘El Chapo Isidro’ caught in Sinaloa",
         body="Fugitive held after shoot-out. (BBC)", scene="chapo"),
    dict(num=7, region="ASIA-PACIFIC", place="NEW DELHI",
         kicker="2-DAY VISIT",
         headline="Nepal PM lands in Delhi",
         body="Nepal PM begins two-day visit. (PTI)", scene="nepal"),
    dict(num=8, region="MIDDLE EAST", place="JERUSALEM",
         kicker="COALITION TALKS",
         headline="Eisenkot invites Likud to talks",
         body="Seeks broadest coalition. (ST)",
         scene="eisenkot"),
    dict(num=9, region="EUROPE", place="PARIS",
         kicker="4TH WEEKEND",
         headline="Fourth weekend of France protests",
         body="Fourth weekend of marches. (Reuters)", scene="france"),
    dict(num=10, region="EUROPE", place="OSLO",
         kicker="LICENCES VOID",
         headline="Norway court voids oil licences",
         body="Permits for new fields void. (Reuters)", scene="norway"),
    dict(num=11, region="MIDDLE EAST", place="GAZA",
         kicker="3 KILLED",
         headline="Strike hits Gaza food-aid vehicle",
         body="Three killed in air attack. (Al Jazeera)",
         scene="gaza"),
    dict(num=12, region="EUROPE", place="WARSAW",
         kicker="NATO PLEDGE",
         headline="Rutte: all of NATO stands with Poland",
         body="Pledge follows incursion. (AFP)",
         scene="poland"),
    dict(num=13, region="AMERICAS", place="LAS VEGAS",
         kicker="POLE",
         headline="Verstappen on pole under the lights",
         body="Antonelli drops five places. (F1)", scene="f1"),
]

BRIEFS = [
    (14, "FBI probes apparent hack of crime database (BBC)"),
    (15, "Teen gamer helps FBI rescue a girl (BBC)"),
    (16, "Midterm loss corners Vance as 2028 field widens (ST)"),
    (17, "Saudi air defences down a missile (Investing.com)"),
    (18, "Lebanon: Aoun demands Israeli pullout (Al Jazeera)"),
    (19, "Iran warns of a ‘silent economic war’ (Al Jazeera)"),
    (20, "Hormuz: Pugh swims strait as tanker is struck (BBC)"),
    (21, "Moldova: Russian airspace breach reported (Kyiv Ind.)"),
    (22, "Belgium: air traffic halts in 23 Nov strike (ST)"),
    (23, "Germany: IG Metall widens strikes (Reuters)"),
    (24, "Portugal: Lisbon march on living costs (Reuters)"),
    (25, "Denmark expels Russian attaché (Guardian)"),
    (26, "Bangladesh: 30 Awami League homes torched (TOI)"),
    (27, "Australia: Fred Nile, ex-NSW MP, dies aged 92 (ABC)"),
    (28, "Bystanders pull driver from burning car (ABC)"),
    (29, "Melbourne: 70 years since 1956 Olympics (ABC)"),
    (30, "EU–Indonesia sign deal after 10 years (DW)"),
    (31, "Rugby: England beat New Zealand (Reuters)"),
    (32, "Rugby: France beat Argentina into final (Reuters)"),
    (33, "Tennis: Zverev v Alcaraz in ATP Finals final (TOI)"),
    (34, "Football: Liverpool host Man Utd today (Al Jazeera)"),
    (35, "Hong Kong votes for 723 seats (AP)"),
]

STATS = [
    ("~200", "nations at the COP31 talks"),
    ("400+", "drones fired at Ukraine"),
    ("110", "missiles in the same night"),
    ("16", "crew rescued from Sparta II"),
    ("2", "US bases hit in Bahrain"),
    ("60", "hurt in Kryvyi Rih"),
]

REGIONS = [("EUROPE", 12, REG_EU), ("MIDDLE EAST", 7, REG_ME),
           ("AMERICAS", 5, REG_AM), ("ASIA-PACIFIC", 5, REG_AP),
           ("WORLD", 6, REG_WO)]

SCENES = {
    "cop31": scene_cop31, "ukraine": scene_ukraine, "bahrain": scene_bahrain,
    "sparta": scene_sparta, "kryvyi": scene_kryvyi, "chapo": scene_chapo,
    "nepal": scene_nepal, "eisenkot": scene_eisenkot, "france": scene_france,
    "norway": scene_norway, "gaza": scene_gaza, "poland": scene_poland,
    "f1": scene_f1,
}


def draw_map(cv, x, y):
    draw_text(cv, x, y, "WHERE IT HAPPENED", "SB13", RED)
    draw_text(cv, x + 152, y + 1, "pins match story numbers", "SR11", GREY)
    my = y + 18
    cell = 7
    for r, row in enumerate(MAP_GRID):
        row = row.ljust(44, ".")[:44]
        for c, ch in enumerate(row):
            if ch == "#":
                cv.rect(x + c * cell, my + r * cell, 3, 3, (150, 138, 108))
    for num, (c, r) in PIN_POS.items():
        px = x + c * cell + 1
        py = my + r * cell + 1
        cv.disc(px, py, 6, RED)
        draw_text(cv, px, py - 5, str(num), "SB11", WHITE, align="c")


def chip(cv, x, y, text, fg=WHITE, bg=RED, font="SB11"):
    w = text_w(text, font) + 12
    cv.rect(x, y, w, 16, bg)
    draw_text(cv, x + 6, y + 2, text, font, fg)
    return w


def main():
    import os
    cv = Canvas(W, H, PAPER)
    cv.grain(0, 0, W, H, 20261122, 2600)
    MX = 14
    CW = W - 2 * MX  # 996

    # kicker
    draw_text(cv, MX, 8, "THE WORLD IN ONE DAY", "SB13", RED)
    draw_text(cv, W - MX, 8,
              "35 STORIES · 6 REGIONS · EVERY ONE DATED SUNDAY 22 NOVEMBER 2026",
              "SB11", INK, align="r")
    cv.hline(MX, 24, CW, INK, 2)

    # masthead
    draw_text(cv, W // 2, 30, "Sunday 22 November 2026", "SB64", INK, align="c")
    draw_text(cv, W // 2, 100,
              "Climate deal in sight at COP31 · Russia's 400-drone barrage on "
              "Ukraine · Iran hits US bases in Bahrain",
              "SI20", INK, align="c")
    cv.hline(MX, 122, CW, INK, 1)
    cv.hline(MX, 125, CW, INK, 2)

    # stat strip
    sy = 130
    colw = CW // 6
    for k, (num, lab) in enumerate(STATS):
        cx = MX + k * colw + colw // 2
        draw_text(cv, cx, sy, num, "SB28", RED, align="c")
        draw_text(cv, cx, sy + 28, lab, "SR11", INK, align="c")
        if k:
            cv.vline(MX + k * colw, sy + 2, 40, (200, 190, 168), 1)
    cv.hline(MX, sy + 46, CW, INK, 1)

    # region bar
    ry = sy + 52
    total = sum(n for _, n, _ in REGIONS)
    rx = MX
    for name, n, col in REGIONS:
        rw = round(CW * n / total)
        cv.rect(rx, ry, rw, 18, col)
        draw_text(cv, rx + rw // 2, ry + 3, "%s %d" % (name, n), "SB11", WHITE, align="c")
        rx += rw

    # heroes
    hy = ry + 26
    hw = 326
    gap = 9
    scene_h = 124
    hero_bottom = hy
    for k, st in enumerate(HEROES):
        hx = MX + k * (hw + gap)
        cv.rect(hx - 1, hy - 1, hw + 2, scene_h + 2, INK)
        SCENES[st["scene"]](cv, hx, hy, hw, scene_h)
        chip(cv, hx, hy, st["kicker"])
        ty = hy + scene_h + 8
        draw_text(cv, hx, ty, "%d %s" % (st["num"], st["place"]), "SB11", RED)
        draw_text(cv, hx + hw, ty, st["src"], "SR11", GREY, align="r")
        ty += 16
        ty = draw_para(cv, hx, ty, st["headline"], "SB28", INK, hw, 28)
        ty = draw_para(cv, hx, ty + 2, st["body"], "SR14", INK, hw, 17)
        hero_bottom = max(hero_bottom, ty)

    # mid grid 5 x 2
    my = hero_bottom + 10
    mw = 192
    mgap = 9
    mscene = 78
    row_h = 164
    for idx, st in enumerate(MIDS):
        row, col = divmod(idx, 5)
        mx = MX + col * (mw + mgap)
        yy = my + row * row_h
        cv.rect(mx - 1, yy - 1, mw + 2, mscene + 2, INK)
        SCENES[st["scene"]](cv, mx, yy, mw, mscene)
        chip(cv, mx, yy, st["kicker"])
        # number disc top-right of scene
        cv.disc(mx + mw - 9, yy + 9, 8, WHITE)
        draw_text(cv, mx + mw - 9, yy + 4, str(st["num"]), "SB11", RED, align="c")
        ty = yy + mscene + 6
        draw_text(cv, mx, ty, st["place"], "SB11", RED)
        ty += 15
        ty = draw_para(cv, mx, ty, st["headline"], "SB19", INK, mw, 19)
        draw_para(cv, mx, ty + 2, st["body"], "SR11", GREY, mw, 13)
    mid_bottom = my + 2 * row_h - 12

    # divider
    cv.hline(MX, mid_bottom + 4, CW, INK, 1)

    # bottom: map left, briefs right
    by = mid_bottom + 12
    draw_map(cv, MX, by)
    bx = MX + 348
    draw_text(cv, bx, by, "ALSO ON SUNDAY 22 NOVEMBER — 22 MORE STORIES", "SB13", INK)
    cv.hline(bx, by + 16, W - MX - bx, INK, 1)
    bw = (W - MX - bx - 14) // 2
    for i, (num, txt) in enumerate(BRIEFS):
        col = i // 11
        row = i % 11
        tx = bx + col * (bw + 14)
        ty = by + 22 + row * 12
        draw_text(cv, tx, ty, "%d" % num, "SB11", RED)
        draw_text(cv, tx + 20, ty, txt, "SR11", INK)

    # date check
    dy = by + 168
    cv.rect(MX, dy, CW, 26, PAPER2)
    cv.hline(MX, dy, CW, RED, 1)
    cv.hline(MX, dy + 25, CW, RED, 1)
    cv.vline(MX, dy, 26, RED, 1)
    cv.vline(MX + CW - 1, dy, 26, RED, 1)
    draw_text(cv, MX + 8, dy + 7, "DATE CHECK", "SB11", RED)
    draw_text(cv, MX + 94, dy + 7,
              "Left out as other days' news: the Peru earthquake (Fri 20 Nov local) · "
              "Russian missiles landing in Poland (19 Nov) · the Kerch Bridge strikes "
              "(earlier this week) · the Shenzhen summit (19 Nov).",
              "SR11", INK)

    # footer
    fy = dy + 32
    draw_text(cv, MX, fy,
              "Sources: Reuters, AP, AFP, BBC, Al Jazeera, DW, The Straits Times, Sky News, "
              "CNA, ABC Australia, Times of India, The Guardian, Kyiv Independent.",
              "SR11", GREY)
    draw_text(cv, MX, fy + 11,
              "Every story names its outlet. Pictures and map: original, drawn in code.",
              "SR11", GREY)
    draw_text(cv, W - MX, fy + 11, "SUNDAY 22 NOVEMBER 2026 · ONE PAGE", "SB11", INK,
              align="r")

    out = os.environ.get("MAKEFUN_OUTPUT_DIR")
    paths = ["entry.png"]
    if out:
        os.makedirs(out, exist_ok=True)
        paths.append(os.path.join(out, "entry.png"))
    for p in paths:
        write_png(p, cv)
    print("wrote", paths)


if __name__ == "__main__":
    main()
