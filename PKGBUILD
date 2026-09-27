# Maintainer: Clove Twilight <clove@doughmination.gay>
#
# MorvaneOS installer: archinstall ported to Artix/runit.
# Built from the `morvane` branch of github.com/MorvaneOS/Installer. To release, set
# `version` in pyproject.toml and pkgver here to the same new number and push.
# Based on archinstall's own PKGBUILD (David Runge, Giancarlo Razzolini, Anton Hvornum).

pkgname=morvane-installer
pkgver=4.5.0
pkgrel=1
pkgdesc="MorvaneOS installer (archinstall ported to Artix and runit)"
arch=(any)
url="https://github.com/MorvaneOS/Installer"
license=(GPL-3.0-only)
depends=(
  'artools-base'  # basestrap, artix-chroot
  'btrfs-progs'
  'coreutils'
  'cryptsetup'
  'dosfstools'
  'e2fsprogs'
  'glibc'
  'kbd'
  'libcrypt.so'
  'libxcrypt'
  'pciutils'
  'procps-ng'
  'python'
  'python-cryptography'
  'python-pydantic'
  'python-pyparted'  # from [morvane]
  'python-textual'
  'python-markdown-it-py'
  'python-linkify-it-py'
  'util-linux'
  'xfsprogs'
  'lvm2'
  'f2fs-tools'
  'libfido2'
)
makedepends=(
  'git'
  'python-build'
  'python-installer'
  'python-setuptools'
  'python-wheel'
)

conflicts=(archinstall)
source=("$pkgname::git+$url.git#branch=morvane")
sha256sums=('SKIP')

prepare() {
  cd "$pkgname"
  # The branch has to be the release pyproject.toml says it is, so a forgotten bump
  # stops the build instead of packaging new code under an old version
  local version
  version=$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml)
  if [[ $version != "$pkgver" ]]; then
    error "pyproject.toml says $version, but pkgver is $pkgver"
    return 1
  fi
}

build() {
  cd "$pkgname"
  python -m build --wheel --no-isolation
}

package() {
  cd "$pkgname"
  python -m installer --destdir="$pkgdir" dist/*.whl
}
