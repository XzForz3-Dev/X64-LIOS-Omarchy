-- X64 LIOS: Spanish / ISO keyboard Quake console bindings (key code 49 = º / ª)
o.bind("SUPER + code:49", "Toggle Quake console", hl.dsp.workspace.toggle_special("qconsole"))
o.bind("SUPER + SHIFT + code:49", "Move window to Quake console", hl.dsp.window.move({ workspace = "special:qconsole", follow = false }))
