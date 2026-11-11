-- X64 LIOS + Omarchy monitor defaults: preferred mode, auto placement, 1.0 native scale.
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

-- GDK_SCALE default to 1 for standard Full HD (1080p) laptops and monitors.
hl.env("GDK_SCALE", "1")
