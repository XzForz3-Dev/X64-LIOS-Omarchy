-- X64 LIOS System Utilities (x64-hello & x64-update)
o.window("(x64-hello|x64-update)", { float = true })
o.window("(x64-hello|x64-update)", { center = true })
o.window("x64-update", { size = { 1020, 680 } })

-- X64 LIOS: load Spanish / ISO keyboard Quake console bindings (omarchy.lua lists bindings explicitly)
if _G.omarchy_default_bindings ~= false then
  require("default.hypr.bindings.x64")
end
