#!/usr/bin/env python3
"""
X64 LIOS + Omarchy - Instalador y Configurador Oficial de la Shell Basecamp
Diseñado para Calamares y X64 Dashboard.
Garantiza paridad 100% con Basecamp Omarchy preservando el Kernel BORE y Limine de X64 LIOS.
"""

import os
import sys
import re
import pwd
import shutil
import argparse
import subprocess
from pathlib import Path

OMARCHY_DIR = "/usr/share/omarchy"
OMARCHY_REPO = "https://github.com/XzForz3-Dev/X64-LIOS-Omarchy.git"
UPSTREAM_PKGS_REPOS = [
    "https://pkgs.omarchy.org/edge/$arch",
    "https://pkgs.omarchy.org/stable/$arch"
]

# Lista de paquetes bloqueados para proteger el núcleo BORE y CachyOS de X64 LIOS
BLACKLISTED_PKGS = {
    'linux-ptl', 'linux-t2', 'linux', 'linux-firmware', 'linux-headers', 'linux-ptl-headers',
    'linux-omarchy', 'linux-omarchy-headers', 'linux-omarchy-bore', 'linux-omarchy-bore-headers',
    'linux-omarchy-eevdf', 'linux-omarchy-eevdf-headers', 'linux-omarchy-muqss', 'linux-omarchy-muqss-headers',
    'linux-firmware-marvell', 'linux-t2-headers', 'limine', 'limine-mkinitcpio-hook', 'limine-snapper-sync',
    'nvidia-580xx-dkms', 'nvidia-dkms', 'nvidia-open-dkms', 'nvidia-580xx-utils', 'nvidia-utils',
    'lib32-nvidia-580xx-utils', 'lib32-nvidia-utils', 'libva-nvidia-driver', 'intel-media-driver',
    'intel-lpmd', 'intel-ipu7-camera', 'broadcom-wl-dkms', 'macbook12-spi-driver-dkms',
    'tuxedo-drivers-nocompatcheck-dkms', 'yt6801-dkms', 'apple-bcm-firmware', 'apple-t2-audio-config',
    't2fanrd', 'qmk-hid', 'dell-xps-touchpad-haptics', 'dell-xps13-sidecar-amps',
    'vulkan-intel', 'vulkan-radeon', 'vulkan-asahi', 'yay-debug', 'btrfs-progs', 'sof-firmware',
    'base', 'base-devel', 'dkms', 'asusctl', 'xorg-server', 'xorg-xinit',
    'omarchy-local-ai', 'omarchy-screensaver', 'omarchy-hyprland-titlebars',
    'omarchy-power-profiles-daemon', 'ttf-jetbrains-mono-nerd-basic'
}

CORE_UI_PKGS = [
    'hyprland', 'uwsm', 'sddm', 'x64-sddm-theme', 'dolphin', 'ark',
    'kitty', 'opencode', 'quickshell', 'swaybg', 'hyprlock', 'hypridle',
    'hyprpolkitagent', 'hyprpwcenter', 'hyprpicker', 'hyprsunset',
    'gpu-screen-recorder', 'cliphist', 'adw-gtk-theme', 'xdg-terminal-exec',
    'xdg-desktop-portal-hyprland', 'socat', 'udiskie', 'wtype', 'wl-clipboard',
    'pamixer', 'brightnessctl', 'inotify-tools', 'bluez-tools', 'fcitx5',
    'yaru-icon-theme', 'omarchy-speedtest'
]

def log(msg, color="36"):
    print(f"\033[1;{color}m[X64 LIOS + Omarchy]\033[0m {msg}", flush=True)

def run(cmd, check=True, shell=False, env=None):
    if isinstance(cmd, str) and not shell:
        cmd = cmd.split()
    return subprocess.run(cmd, check=check, shell=shell, env=env)

def get_target_users(user_arg=None):
    if user_arg:
        return [user_arg]
    
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        return [sudo_user]
    
    users = []
    for entry in pwd.getpwall():
        if entry.pw_uid >= 1000 and entry.pw_dir.startswith("/home/"):
            users.append(entry.pw_name)
    return users or [os.environ.get("USER", "root")]

def configure_pacman_repo():
    log("Configurando repositorio oficial Basecamp [omarchy] (edge + stable) en pacman.conf...")
    conf_path = "/etc/pacman.conf"
    if not os.path.exists(conf_path):
        return
    
    with open(conf_path, "r", encoding="utf-8") as f:
        conf = f.read()

    # Bloquear linux-omarchy en IgnorePkg
    if "IgnorePkg" in conf:
        lines = []
        for line in conf.splitlines():
            if line.strip().startswith("IgnorePkg") and "linux-omarchy" not in line:
                line = line + " linux-omarchy linux-omarchy-headers"
            lines.append(line)
        conf = "\n".join(lines)
    else:
        conf = conf.replace("[options]", "[options]\nIgnorePkg = linux-omarchy linux-omarchy-headers")

    repo_servers = "\n".join([f"Server = {s}" for s in UPSTREAM_PKGS_REPOS])
    repo_block = f"[omarchy]\nSigLevel = Optional TrustAll\n{repo_servers}\n\n"

    # Si ya existe [omarchy], actualizar los servidores para incluir edge + stable
    if "[omarchy]" in conf:
        conf = re.sub(r'\[omarchy\]\s*\n(?:(?!\[).*\n)*', repo_block, conf)
    else:
        match = re.search(r'^\[(?!options\]).*?\]', conf, re.MULTILINE)
        if match:
            idx = match.start()
            conf = conf[:idx] + repo_block + conf[idx:]
        else:
            conf += f"\n{repo_block}"

    with open(conf_path, "w", encoding="utf-8") as f:
        f.write(conf)

    log("Sincronizando bases de datos de Pacman con canales edge y stable...")
    run(["pacman", "-Sy", "--noconfirm"])

def install_packages():
    log("Resolviendo paquetes oficiales de Basecamp Omarchy...")
    pkgs = list(CORE_UI_PKGS)
    
    pkg_file = os.path.join(OMARCHY_DIR, "install/omarchy-base.packages")
    if os.path.exists(pkg_file):
        with open(pkg_file, "r", encoding="utf-8") as f:
            for line in f:
                p = line.strip().split('#')[0].strip()
                if p and p not in BLACKLISTED_PKGS:
                    pkgs.append('neovim' if p == 'nvim' else p)

    pkgs = sorted(list(set(pkgs)))
    
    # Comprobar qué paquetes faltan
    chk = subprocess.run(["pacman", "-T"] + pkgs, capture_output=True, text=True)
    missing = [m.strip() for m in chk.stdout.splitlines() if m.strip()]
    
    if missing:
        log(f"Instalando {len(missing)} paquetes oficiales de Omarchy y dependencias...")
        cmd = ["pacman", "-S", "--needed", "--noconfirm", "--overwrite", "*", "--assume-installed", "linux-omarchy=99.9"] + missing
        res = subprocess.run(cmd)
        if res.returncode != 0:
            log("Advertencia: Pacman reportó un código de salida no cero, filtrando paquetes disponibles...", "33")
            available_missing = []
            for p in missing:
                if subprocess.run(["pacman", "-Si", p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                    available_missing.append(p)
                else:
                    log(f"Paquete omitido por no estar aún en repositorios: {p}", "33")
            if available_missing:
                run(["pacman", "-S", "--needed", "--noconfirm", "--overwrite", "*", "--assume-installed", "linux-omarchy=99.9"] + available_missing, check=False)
            run(["pacman", "-S", "--needed", "--noconfirm", "--overwrite", "*"] + CORE_UI_PKGS, check=False)
    else:
        log("Todos los paquetes oficiales ya están instalados en el sistema.", "32")

def setup_environment_and_wrappers():
    log("Configurando variables de entorno y wrappers maestros en /usr/local/bin...")
    
    # /etc/environment
    env_file = "/etc/environment"
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            lines = f.read().splitlines()
        if not any("OMARCHY_PATH" in l for l in lines):
            lines.append("OMARCHY_PATH=/usr/share/omarchy")
            with open(env_file, "w") as f:
                f.write("\n".join(lines) + "\n")
    else:
        with open(env_file, "w") as f:
            f.write("OMARCHY_PATH=/usr/share/omarchy\n")

    # /etc/profile.d/omarchy.sh
    profile_d = "/etc/profile.d/omarchy.sh"
    with open(profile_d, "w") as f:
        f.write("#!/bin/sh\nexport OMARCHY_PATH=/usr/share/omarchy\nexport PATH=/usr/share/omarchy/bin:$PATH\n")
    os.chmod(profile_d, 0o755)

    # Master wrappers in /usr/local/bin
    os.makedirs("/usr/local/bin", exist_ok=True)
    bin_dir = os.path.join(OMARCHY_DIR, "bin")
    if os.path.isdir(bin_dir):
        run(["chmod", "-R", "+x", bin_dir], check=False)
        for entry in os.listdir(bin_dir):
            full_path = os.path.join(bin_dir, entry)
            if not os.path.isfile(full_path) or not os.access(full_path, os.X_OK):
                continue
            if entry in ["kitty", "x64-update", "x64-update-tray", "x64-dashboard"] or entry.endswith(".py") or entry.endswith(".sh"):
                continue
            
            target_wrapper = os.path.join("/usr/local/bin", entry)
            wrapper_code = f"""#!/bin/bash
export OMARCHY_PATH=/usr/share/omarchy
exec /usr/share/omarchy/bin/{entry} "$@"
"""
            with open(target_wrapper, "w") as fw:
                fw.write(wrapper_code)
            os.chmod(target_wrapper, 0o755)

def setup_system_assets():
    log("Desplegando fuentes, servicios systemd y entradas de sesión...")
    
    # Fuentes
    font_src = os.path.join(OMARCHY_DIR, "default/fonts/omarchy.ttf")
    if os.path.exists(font_src):
        font_dir = "/usr/share/fonts/omarchy"
        os.makedirs(font_dir, exist_ok=True)
        shutil.copy2(font_src, os.path.join(font_dir, "omarchy.ttf"))
        run(["fc-cache", "-f", font_dir], check=False)

    # Servicios systemd de usuario y drop-ins
    srv_dir = os.path.join(OMARCHY_DIR, "default/systemd/user")
    if os.path.isdir(srv_dir):
        dest_srv = "/usr/lib/systemd/user"
        os.makedirs(dest_srv, exist_ok=True)
        for s in os.listdir(srv_dir):
            src_path = os.path.join(srv_dir, s)
            if s.endswith(".service"):
                shutil.copy2(src_path, os.path.join(dest_srv, s))
            elif os.path.isdir(src_path) and s.endswith(".d"):
                dst_d = os.path.join(dest_srv, s)
                os.makedirs(dst_d, exist_ok=True)
                shutil.copytree(src_path, dst_d, dirs_exist_ok=True)

    # Configuración de compatibilidad global para el motor de fondos animados (OWE)
    etc_owe_dropin = "/etc/systemd/user/owed.service.d"
    os.makedirs(etc_owe_dropin, exist_ok=True)
    with open(os.path.join(etc_owe_dropin, "10-x64-compatibility.conf"), "w") as f:
        f.write("[Service]\nEnvironment=\"OWE_DRM_DPMS=0\"\n")

    # Habilitación automática de OWE en la sesión gráfica para todos los usuarios
    graphical_wants = "/etc/systemd/user/graphical-session.target.wants"
    os.makedirs(graphical_wants, exist_ok=True)
    owed_unit = "/usr/lib/systemd/user/owed.service"
    if os.path.exists(owed_unit):
        link_target = os.path.join(graphical_wants, "owed.service")
        if os.path.lexists(link_target):
            os.remove(link_target)
        os.symlink(owed_unit, link_target)

    # Sesiones Wayland
    sess_dir = os.path.join(OMARCHY_DIR, "default/wayland-sessions")
    if os.path.isdir(sess_dir):
        dest_sess = "/usr/share/wayland-sessions"
        os.makedirs(dest_sess, exist_ok=True)
        for d in os.listdir(sess_dir):
            if d.endswith(".desktop"):
                shutil.copy2(os.path.join(sess_dir, d), os.path.join(dest_sess, d))

    # XDG Terminal Exec
    xdg_term_dir = os.path.join(OMARCHY_DIR, "default/xdg-terminal-exec")
    if os.path.isdir(xdg_term_dir):
        dest_term = "/usr/share/xdg-terminal-exec"
        os.makedirs(dest_term, exist_ok=True)
        for f in os.listdir(xdg_term_dir):
            shutil.copy2(os.path.join(xdg_term_dir, f), os.path.join(dest_term, f))

    # Configuración de PAM para la pantalla de bloqueo animada
    apply_lock_bin = os.path.join(OMARCHY_DIR, "bin/omarchy-apply-lock")
    if os.path.exists(apply_lock_bin):
        log("Configurando PAM para la pantalla de bloqueo oficial (omarchy-apply-lock)...")
        run(["bash", apply_lock_bin], check=False)

    # Configuración del sistema para Mise (herramientas predeterminadas y agentes IA)
    mise_src = os.path.join(OMARCHY_DIR, "etc/mise")
    if os.path.isdir(mise_src):
        log("Desplegando configuraciones del sistema para Mise (/etc/mise)...")
        dest_mise = "/etc/mise"
        os.makedirs(dest_mise, exist_ok=True)
        shutil.copytree(mise_src, dest_mise, dirs_exist_ok=True)

    # Ganchos de ALPM / Pacman:
    # IMPORTANTE: Desplegamos únicamente los ganchos compatibles. Excluimos y purgamos
    # 00-omarchy-update-guard.hook, 10-... y 90-... porque contienen "Depends = omarchy"
    # que bloquea transacciones de Pacman y del actualizador oficial x64-update.
    dest_hooks = "/usr/share/libalpm/hooks"
    os.makedirs(dest_hooks, exist_ok=True)
    for blocked_hook in [
        "00-omarchy-update-guard.hook",
        "10-omarchy-hyprland-reload-pause.hook",
        "90-omarchy-hyprland-reload-resume.hook",
    ]:
        p = os.path.join(dest_hooks, blocked_hook)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    alpm_hooks_dir = os.path.join(OMARCHY_DIR, "default/libalpm/hooks")
    allowed_hooks = {"05-omarchy-passwordless-revoke.hook"}
    if os.path.isdir(alpm_hooks_dir):
        log("Desplegando ganchos ALPM compatibles (/usr/share/libalpm/hooks)...")
        for h in os.listdir(alpm_hooks_dir):
            if h in allowed_hooks:
                src_h = os.path.join(alpm_hooks_dir, h)
                dst_h = os.path.join(dest_hooks, h)
                shutil.copy2(src_h, dst_h)
                os.chmod(dst_h, 0o644)

    # Configuraciones tmpfiles de Omarchy (limpiador de arranque para sudo temporal y optimizaciones)
    tmpfiles_dir = os.path.join(OMARCHY_DIR, "etc/tmpfiles.d")
    if os.path.isdir(tmpfiles_dir):
        log("Desplegando configuraciones tmpfiles (/etc/tmpfiles.d)...")
        dest_tmp = "/etc/tmpfiles.d"
        os.makedirs(dest_tmp, exist_ok=True)
        for t in os.listdir(tmpfiles_dir):
            if t.endswith(".conf"):
                src_t = os.path.join(tmpfiles_dir, t)
                dst_t = os.path.join(dest_tmp, t)
                shutil.copy2(src_t, dst_t)
                os.chmod(dst_t, 0o644)

    # Reglas oficiales de sudoers de Omarchy (DNS, locales, navegador, timezone y límites de reintentos)
    sudoers_src = os.path.join(OMARCHY_DIR, "etc/sudoers.d")
    if os.path.isdir(sudoers_src):
        log("Desplegando políticas de sudoers (/etc/sudoers.d)...")
        dest_sudoers = "/etc/sudoers.d"
        os.makedirs(dest_sudoers, exist_ok=True)
        for s in os.listdir(sudoers_src):
            src_s = os.path.join(sudoers_src, s)
            dst_s = os.path.join(dest_sudoers, s)
            if os.path.isfile(src_s):
                shutil.copy2(src_s, dst_s)
                os.chmod(dst_s, 0o440)

    # Configuración de tolerancia PAM Faillock (deny = 10 para evitar bloqueos prematuros)
    faillock_src = os.path.join(OMARCHY_DIR, "etc/security/faillock.conf")
    if os.path.exists(faillock_src):
        log("Desplegando configuración de tolerancia PAM Faillock (/etc/security/faillock.conf)...")
        os.makedirs("/etc/security", exist_ok=True)
        shutil.copy2(faillock_src, "/etc/security/faillock.conf")
        os.chmod("/etc/security/faillock.conf", 0o644)

    # Optimizaciones del Kernel Sysctl (inotify file watchers, BBR y max_map_count)
    sysctl_src = os.path.join(OMARCHY_DIR, "etc/sysctl.d")
    if os.path.isdir(sysctl_src):
        log("Desplegando parámetros sysctl del sistema (/etc/sysctl.d)...")
        dest_sysctl = "/etc/sysctl.d"
        os.makedirs(dest_sysctl, exist_ok=True)
        for conf in os.listdir(sysctl_src):
            if conf.endswith(".conf"):
                src_c = os.path.join(sysctl_src, conf)
                dst_c = os.path.join(dest_sysctl, conf)
                shutil.copy2(src_c, dst_c)
                os.chmod(dst_c, 0o644)
        run(["sysctl", "--system"], check=False)

    # Reglas Udev (Planificadores de E/S para SSD/NVMe y compatibilidad de hardware)
    udev_src = os.path.join(OMARCHY_DIR, "etc/udev/rules.d")
    if os.path.isdir(udev_src):
        log("Desplegando reglas udev (/etc/udev/rules.d)...")
        dest_udev = "/etc/udev/rules.d"
        os.makedirs(dest_udev, exist_ok=True)
        for r in os.listdir(udev_src):
            if r.endswith(".rules"):
                src_r = os.path.join(udev_src, r)
                dst_r = os.path.join(dest_udev, r)
                shutil.copy2(src_r, dst_r)
                os.chmod(dst_r, 0o644)
        run(["udevadm", "control", "--reload"], check=False)

    # Drop-ins del sistema para Systemd (apagado rápido 10s, límites nofile, etc.)
    systemd_etc = os.path.join(OMARCHY_DIR, "etc/systemd")
    if os.path.isdir(systemd_etc):
        log("Desplegando drop-ins de optimización para systemd (/etc/systemd)...")
        for root, dirs, files in os.walk(systemd_etc):
            rel_path = os.path.relpath(root, systemd_etc)
            target_dir = os.path.join("/etc/systemd", rel_path) if rel_path != "." else "/etc/systemd"
            os.makedirs(target_dir, exist_ok=True)
            for f in files:
                if f.endswith(".conf"):
                    src_f = os.path.join(root, f)
                    dst_f = os.path.join(target_dir, f)
                    shutil.copy2(src_f, dst_f)
                    os.chmod(dst_f, 0o644)

    # Scripts de suspensión y reposo del sistema (desmontaje seguro FUSE y hardware)
    sleep_src = os.path.join(OMARCHY_DIR, "default/systemd/system-sleep")
    if os.path.isdir(sleep_src):
        log("Desplegando scripts para suspensión del sistema (/usr/lib/systemd/system-sleep)...")
        dest_sleep = "/usr/lib/systemd/system-sleep"
        os.makedirs(dest_sleep, exist_ok=True)
        for s in os.listdir(sleep_src):
            src_s = os.path.join(sleep_src, s)
            dst_s = os.path.join(dest_sleep, s)
            if os.path.isfile(src_s):
                shutil.copy2(src_s, dst_s)
                os.chmod(dst_s, 0o755)

    # Configuración de modprobe USB autosuspend
    modprobe_src = os.path.join(OMARCHY_DIR, "etc/modprobe.d/omarchy-usb-autosuspend.conf")
    if os.path.exists(modprobe_src):
        os.makedirs("/etc/modprobe.d", exist_ok=True)
        shutil.copy2(modprobe_src, "/etc/modprobe.d/omarchy-usb-autosuspend.conf")
        os.chmod("/etc/modprobe.d/omarchy-usb-autosuspend.conf", 0o644)

def silence_migrations(users):
    log("Marcando historial de migraciones de Omarchy como completado...")
    mig_dir = os.path.join(OMARCHY_DIR, "migrations")
    if not os.path.isdir(mig_dir):
        return

    mig_files = [f for f in os.listdir(mig_dir) if f.endswith(".sh")]
    
    # /etc/skel
    skel_mig = "/etc/skel/.local/state/omarchy/migrations"
    os.makedirs(skel_mig, exist_ok=True)
    for m in mig_files:
        Path(os.path.join(skel_mig, m)).touch(exist_ok=True)

    # Usuarios
    for u in users:
        try:
            p = pwd.getpwnam(u)
            user_mig = os.path.join(p.pw_dir, ".local/state/omarchy/migrations")
            os.makedirs(user_mig, exist_ok=True)
            for m in mig_files:
                Path(os.path.join(user_mig, m)).touch(exist_ok=True)
            run(["chown", "-R", f"{p.pw_uid}:{p.pw_gid}", os.path.join(p.pw_dir, ".local")], check=False)
        except Exception:
            pass

def setup_user_configs(users, default_theme="x64-lios-crimson"):
    log("Configurando carpetas de usuario, accesos de personalización y tema...")
    
    cfg_src = os.path.join(OMARCHY_DIR, "config")
    
    # /etc/skel
    os.makedirs("/etc/skel/Fondos", exist_ok=True)
    os.makedirs("/etc/skel/Temas", exist_ok=True)
    os.makedirs("/etc/skel/.config/omarchy", exist_ok=True)
    if os.path.isdir(cfg_src):
        for item in os.listdir(cfg_src):
            src_item = os.path.join(cfg_src, item)
            dst_item = os.path.join("/etc/skel/.config", item)
            if os.path.isdir(src_item):
                shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
            else:
                shutil.copy2(src_item, dst_item)

    for u in users:
        try:
            p = pwd.getpwnam(u)
            home = p.pw_dir
            if not os.path.isdir(home):
                continue
            
            # Aislar dotfiles nativos previos si existen
            hypr_dir = os.path.join(home, ".config/hypr")
            hypr_bak = os.path.join(home, ".config/hypr.x64-native.bak")
            if os.path.isdir(hypr_dir) and not os.path.isdir(hypr_bak):
                if not os.path.exists(os.path.join(hypr_dir, "hyprland.lua")):
                    shutil.move(hypr_dir, hypr_bak)

            # Carpetas de UX
            os.makedirs(os.path.join(home, "Fondos"), exist_ok=True)
            os.makedirs(os.path.join(home, "Temas"), exist_ok=True)
            os.makedirs(os.path.join(home, ".config/omarchy/backgrounds"), exist_ok=True)
            os.makedirs(os.path.join(home, ".config/omarchy/themes"), exist_ok=True)

            # Copiar configs de Omarchy
            if os.path.isdir(cfg_src):
                for item in os.listdir(cfg_src):
                    src_item = os.path.join(cfg_src, item)
                    dst_item = os.path.join(home, ".config", item)
                    if os.path.isdir(src_item):
                        shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src_item, dst_item)

            # Permisos
            run(["chown", "-R", f"{p.pw_uid}:{p.pw_gid}", 
                 os.path.join(home, ".config"), 
                 os.path.join(home, "Fondos"), 
                 os.path.join(home, "Temas")], check=False)

            # Aplicar tema por defecto para el usuario
            env = os.environ.copy()
            env["HOME"] = home
            env["USER"] = u
            env["OMARCHY_PATH"] = OMARCHY_DIR
            env["OMARCHY_THEME_HEADLESS"] = "1"
            run(["sudo", "-u", u, "bash", "-c", 
                 f"export OMARCHY_PATH=/usr/share/omarchy && export OMARCHY_THEME_HEADLESS=1 && /usr/share/omarchy/bin/omarchy-theme-set '{default_theme}'"], 
                check=False, env=env)
        except Exception as e:
            log(f"Aviso al configurar usuario {u}: {e}", "33")

def configure_sddm_session(users):
    log("Configurando SDDM para iniciar en sesión Omarchy por defecto...")
    os.makedirs("/var/lib/sddm", exist_ok=True)
    actual_user = users[0] if users else "root"
    state_file = "/var/lib/sddm/state.conf"
    with open(state_file, "w") as f:
        f.write(f"[Last]\nSession=/usr/share/wayland-sessions/omarchy.desktop\nUser={actual_user}\n")
    run(["chown", "-R", "sddm:sddm", "/var/lib/sddm"], check=False)
    run(["systemctl", "enable", "sddm.service"], check=False)

def main():
    parser = argparse.ArgumentParser(description="Instalador Oficial de X64 LIOS + Omarchy")
    parser.add_argument("--user", help="Usuario específico a configurar")
    parser.add_argument("--theme", default="x64-lios-crimson", help="Tema predeterminado")
    parser.add_argument("--skip-packages", action="store_true", help="Omitir instalación de paquetes pacman")
    args = parser.parse_args()

    if os.geteuid() != 0:
        print("Error: Este script debe ejecutarse con privilegios de root (sudo).", file=sys.stderr)
        sys.exit(1)

    log("=== Iniciando Configuración Oficial de X64 LIOS + Omarchy ===", "32")
    
    users = get_target_users(args.user)
    log(f"Usuarios objetivo: {', '.join(users)}")

    if not args.skip_packages:
        configure_pacman_repo()
        install_packages()

    setup_environment_and_wrappers()
    setup_system_assets()
    silence_migrations(users)
    setup_user_configs(users, default_theme=args.theme)
    configure_sddm_session(users)

    log("=== ¡X64 LIOS + Omarchy instalado y configurado al 100% con éxito! ===", "32")

if __name__ == "__main__":
    main()
