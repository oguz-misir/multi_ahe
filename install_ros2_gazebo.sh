#!/usr/bin/env bash
# =============================================================================
# AHE-MRTA — ROS 2 Jazzy + Gazebo Harmonic + TurtleBot3 Kurulum Scripti
#
# Platform: Ubuntu 24.04 LTS (Noble)
# ROS 2:    Jazzy Jalisco
# Gazebo:   Harmonic (gz-sim 8.x)
# Robot:    TurtleBot3 Waffle Pi
#
# Kullanım: sudo bash install_ros2_gazebo.sh
# =============================================================================

set -euo pipefail

# Renk kodları
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${GREEN}════════════════════════════════════════${NC}"; echo -e "${GREEN}▶ $1${NC}"; }

# Root kontrolü
if [ "$EUID" -ne 0 ]; then
    err "Bu script root yetkisi gerektirir: sudo bash $0"
fi

UBUNTU_CODENAME=$(lsb_release -sc)
UBUNTU_VERSION=$(lsb_release -sr)

if [ "$UBUNTU_CODENAME" != "noble" ]; then
    warn "Bu script Ubuntu 24.04 (noble) için tasarlanmıştır. Mevcut: $UBUNTU_CODENAME"
    warn "Devam etmek istiyor musunuz? [y/N]"
    read -r ans
    [ "$ans" != "y" ] && exit 0
fi

# ── Adım 1: Sistem güncellemesi ─────────────────────────────────────────────
step "Adım 1: Sistem paketleri güncelleniyor"
apt-get update -q
apt-get install -y -q \
    software-properties-common \
    curl \
    gnupg \
    lsb-release \
    locales \
    ca-certificates \
    git
log "Temel paketler kuruldu"

# ── Adım 2: Locale ──────────────────────────────────────────────────────────
step "Adım 2: Locale ayarlanıyor (UTF-8)"
locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8
log "Locale: en_US.UTF-8"

# ── Adım 3: ROS 2 Jazzy deposu ──────────────────────────────────────────────
step "Adım 3: ROS 2 Jazzy apt deposu ekleniyor"
mkdir -p /etc/apt/keyrings
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /etc/apt/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/ros2.list

apt-get update -q
log "ROS 2 Jazzy deposu eklendi"

# ── Adım 4: ROS 2 Jazzy kurulumu ────────────────────────────────────────────
step "Adım 4: ROS 2 Jazzy Desktop + Dev Tools kuruluyor (~2GB)"
apt-get install -y -q \
    ros-jazzy-desktop \
    ros-dev-tools \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    python3-argcomplete
log "ROS 2 Jazzy Desktop kuruldu"

# ── Adım 5: Gazebo Harmonic deposu ──────────────────────────────────────────
step "Adım 5: Gazebo Harmonic (gz-sim 8) deposu ekleniyor"
curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
    -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
    http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/gazebo-stable.list

apt-get update -q
log "Gazebo Harmonic deposu eklendi"

# ── Adım 6: Gazebo + ros_gz entegrasyon paketleri ───────────────────────────
step "Adım 6: Gazebo Harmonic + ros_gz paketleri kuruluyor (~1GB)"
apt-get install -y -q \
    gz-harmonic \
    ros-jazzy-ros-gz \
    ros-jazzy-ros-gz-sim \
    ros-jazzy-ros-gz-bridge \
    ros-jazzy-ros-gz-image \
    ros-jazzy-ros-gz-interfaces
log "Gazebo Harmonic + ros_gz kuruldu"

# ── Adım 7: Nav2 ────────────────────────────────────────────────────────────
step "Adım 7: Nav2 (Navigation2) kuruluyor"
apt-get install -y -q \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-nav2-minimal-tb3-sim
log "Nav2 kuruldu"

# ── Adım 8: TurtleBot3 ──────────────────────────────────────────────────────
step "Adım 8: TurtleBot3 (ROBOTIS) paketleri kuruluyor"
apt-get install -y -q \
    ros-jazzy-turtlebot3 \
    ros-jazzy-turtlebot3-gazebo \
    ros-jazzy-turtlebot3-description \
    ros-jazzy-turtlebot3-simulations
log "TurtleBot3 kuruldu"

# ── Adım 9: rosdep başlatma ─────────────────────────────────────────────────
step "Adım 9: rosdep başlatılıyor"
rosdep init 2>/dev/null || warn "rosdep zaten başlatılmış"
su -c "rosdep update" "$SUDO_USER" 2>/dev/null || warn "rosdep update başarısız — elle çalıştırın"
log "rosdep hazır"

# ── Adım 10: Ekstra Python paketleri ────────────────────────────────────────
step "Adım 10: Python analiz kütüphaneleri"
python3 -m pip install --break-system-packages \
    pandas matplotlib numpy scipy Pillow pyyaml 2>&1 | tail -3
log "Python kütüphaneleri kuruldu"

# ── Adım 10b: Video kayıt bağımlılıkları (Xvfb + ffmpeg) ────────────────────
step "Adım 10b: Video kayıt bağımlılıkları (Xvfb + ffmpeg)"
apt-get install -y -q xvfb ffmpeg
log "Xvfb + ffmpeg kuruldu (--record-video bayrağı için gerekli)"

# ── Adım 11: Bash profile ───────────────────────────────────────────────────
step "Adım 11: ~/.bashrc otomatik source ekleniyor"
BASHRC="/home/$SUDO_USER/.bashrc"
ROS_SOURCE="source /opt/ros/jazzy/setup.bash"
TBOT3_ENV="export TURTLEBOT3_MODEL=waffle_pi"
GZ_RESOURCE="export GZ_SIM_RESOURCE_PATH=/opt/ros/jazzy/share/turtlebot3_gazebo/models"

if ! grep -q "ros/jazzy/setup.bash" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# ROS 2 Jazzy" >> "$BASHRC"
    echo "$ROS_SOURCE" >> "$BASHRC"
    echo "$TBOT3_ENV" >> "$BASHRC"
    echo "$GZ_RESOURCE" >> "$BASHRC"
    log "~/.bashrc güncellendi (ROS 2 Jazzy + TURTLEBOT3_MODEL + GZ_SIM_RESOURCE_PATH)"
else
    warn "ROS 2 source zaten ~/.bashrc içinde — güncelleme atlandı"
fi

# ── Özet ────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║             KURULUM TAMAMLANDI                               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  ROS 2 Jazzy    : /opt/ros/jazzy/"
echo "  Gazebo Harmonic: gz sim"
echo "  TurtleBot3     : ros-jazzy-turtlebot3-*"
echo ""
echo "  Yeni terminal açın veya şunu çalıştırın:"
echo "    source /opt/ros/jazzy/setup.bash"
echo ""
echo "  Workspace build (multi_ahe):"
echo "    cd ~/multi_ahe"
echo "    colcon build --symlink-install"
echo "    source install/setup.bash"
echo ""
echo "  Demo:"
echo "    export TURTLEBOT3_MODEL=waffle_pi"
echo "    ros2 launch m_ahe_mrta_bringup phase9_demo.launch.py strategy:=full_ahe_mrta scenario:=robot_failure seed:=1"
echo ""

# Versiyon doğrulama
echo "  ── Yüklü versiyonlar ───"
ros2_ver=$(dpkg -l ros-jazzy-ros-base 2>/dev/null | grep "^ii" | awk '{print $3}' || echo "?")
gz_ver=$(gz --version 2>/dev/null | head -1 || echo "?")
echo "  ROS 2 Jazzy : $ros2_ver"
echo "  Gazebo      : $gz_ver"
echo ""
