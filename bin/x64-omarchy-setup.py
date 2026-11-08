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
UPSTREAM_PKGS_REPO = "https://pkgs.omarchy.org/$arch/"

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
    'yaru-icon-theme'
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
    log("Configurando repositorio oficial Basecamp [omarchy] en pacman.conf...")
    conf_path = "/etc/pacman.conf"
    if not os.path.exists(conf_path):
        return
    
    with open(conf_path, "r", encoding="utf-8") as f:
        conf = f.read()

    # Reparar URLs mal formadas
    if "https://pkgs.omarchy.org//" in conf:
        conf = conf.replace("https://pkgs.omarchy.org//", "https://pkgs.omarchy.org/$arch/")

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

    # Inyectar repositorio [omarchy] antes de repositorios secundarios
    if "[omarchy]" not in conf:
        match = re.search(r'^\[(?!options\]).*?\]', conf, re.MULTILINE)
        if match:
            idx = match.start()
            repo_block = f"[omarchy]\nSigLevel = Optional TrustAll\nServer = {UPSTREAM_PKGS_REPO}\n\n"
            conf = conf[:idx] + repo_block + conf[idx:]
        else:
            conf += f"\n[omarchy]\nSigLevel = Optional TrustAll\nServer = {UPSTREAM_PKGS_REPO}\n"

    with open(conf_path, "w", encoding="utf-8") as f:
        f.write(conf)

    log("Sincronizando bases de datos de Pacman...")
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
            log("Advertencia: Pacman reportó un código de salida no cero, reintentando paquetes críticos...", "33")
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

    # Servicios systemd de usuario
    srv_dir = os.path.join(OMARCHY_DIR, "default/systemd/user")
    if os.path.isdir(srv_dir):
        dest_srv = "/usr/lib/systemd/user"
        os.makedirs(dest_srv, exist_ok=True)
        for s in os.listdir(srv_dir):
            if s.endswith(".service"):
                shutil.copy2(os.path.join(srv_dir, s), os.path.join(dest_srv, s))

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

def setup_user_configs(users, default_theme="Tokyo Night"):
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
    parser.add_argument("--theme", default="Tokyo Night", help="Tema predeterminado")
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
