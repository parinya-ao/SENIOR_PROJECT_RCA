#!/usr/bin/env bash
# Installs and verifies C++ quality tools without changing firmware settings.
set -Eeuo pipefail

if [[ ! -r /etc/os-release ]]; then
  echo 'ERROR: cannot identify the operating system.' >&2
  exit 2
fi
# shellcheck disable=SC1091
. /etc/os-release

user_name="${SUDO_USER:-$(id -un)}"
user_home="$HOME"
if command -v getent >/dev/null 2>&1; then
  IFS=: read -r _ _ _ _ _ detected_home _ < <(getent passwd "$user_name")
  if [[ -d "${detected_home:-}" ]]; then
    user_home="$detected_home"
  fi
fi
user_data="${XDG_DATA_HOME:-$user_home/.local/share}"
tool_root="${CPP_QUALITY_TOOL_ROOT:-$user_data/senior-project-rca/cpp-quality}"
export PATH="$user_home/.local/bin:$user_home/.local/share/mise/shims:$user_home/.bun/bin:$PATH"
if [[ ${EUID:-$(id -u)} -eq 0 && -n ${SUDO_USER:-} ]]; then
  exec sudo -u "$user_name" env HOME="$user_home" \
    CPP_QUALITY_TOOL_ROOT="$tool_root" PATH="$PATH" bash "$0"
fi

case "${ID:-}" in
  fedora)
    export PATH="$tool_root/root/usr/bin:$HOME/.local/bin:$PATH"
    missing=0
    for tool in clang++ clang-tidy include-what-you-use clang-doc; do
      if ! command -v "$tool" >/dev/null 2>&1; then
        missing=1
      fi
    done
    if (( missing )); then
      for tool in dnf rpm2cpio cpio; do
        if ! command -v "$tool" >/dev/null 2>&1; then
          printf 'ERROR: Fedora installation requires %s.\n' "$tool" >&2
          exit 2
        fi
      done
      mkdir -p "$tool_root/rpms" "$tool_root/root"
      dnf download --resolve --destdir="$tool_root/rpms" \
        --arch=x86_64,noarch clang clang-tools-extra iwyu
      for package in "$tool_root"/rpms/*.rpm; do
        [[ -f "$package" ]] || continue
        (cd "$tool_root/root" && rpm2cpio "$package" | cpio -idu --quiet)
      done
    fi
    export PATH="$tool_root/root/usr/bin:$PATH"
    for tool_bin in "$tool_root/root"/usr/lib64/llvm*/bin \
        "$tool_root/root"/usr/lib/llvm*/bin; do
      if [[ -d "$tool_bin" ]]; then
        export PATH="$tool_bin:$PATH"
      fi
    done
    for library_dir in "$tool_root/root"/usr/lib64 \
        "$tool_root/root"/usr/lib \
        "$tool_root/root"/usr/lib64/llvm*/lib \
        "$tool_root/root"/usr/lib/llvm*/lib; do
      if [[ -d "$library_dir" ]]; then
        export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}$library_dir"
      fi
    done
    ;;
  debian|ubuntu)
    if ! command -v apt-get >/dev/null 2>&1; then
      echo 'ERROR: apt-get is unavailable on this Debian-family system.' >&2
      exit 2
    fi
    packages=(clang clang-tools clang-tidy clang-format llvm doxygen iwyu)
    missing_packages=()
    for package in "${packages[@]}"; do
      if status=$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null); then
        [[ "$status" == installed ]] || missing_packages+=("$package")
      else
        missing_packages+=("$package")
      fi
    done
    if (( ${#missing_packages[@]} )); then
      if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
        apt-get update
        apt-get install -y "${missing_packages[@]}"
      elif command -v sudo >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y "${missing_packages[@]}"
      else
        echo 'ERROR: installing missing Debian packages requires root access.' >&2
        exit 2
      fi
    fi
    ;;
  *)
    printf 'ERROR: unsupported OS ID: %s\n' "${ID:-unknown}" >&2
    exit 2
    ;;
esac

export PATH="$user_home/.local/bin:$PATH"
if ! doxygen --version >/dev/null 2>&1 && command -v mise >/dev/null 2>&1; then
  doxygen_path=$(mise exec github:doxygen/doxygen@Release_1_18_0 -- \
    sh -c 'command -v doxygen')
  export PATH="${doxygen_path%/*}:$PATH"
fi
for tool in lizard jscpd; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    if command -v pipx >/dev/null 2>&1; then
      pipx install "$tool"
    elif command -v uv >/dev/null 2>&1; then
      uv tool install "$tool"
    else
      printf 'ERROR: install %s using pipx or uv; neither is available.\n' \
        "$tool" >&2
      exit 2
    fi
  fi
done

find_tool() {
  local base="$1" candidate
  if command -v "$base" >/dev/null 2>&1; then
    command -v "$base"
    return 0
  fi
  for candidate in /usr/bin/"${base}"-[0-9]* \
      /usr/lib/llvm-*/bin/"${base}" \
      /usr/lib64/llvm*/bin/"${base}"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

tools=(clang clang++ clang-format clang-tidy doxygen lizard jscpd \
  include-what-you-use clang-doc)
errors=0
printf '\n=== TOOL VERIFICATION ===\n'
for name in "${tools[@]}"; do
  if path=$(find_tool "$name"); then
    if version_output=$("$path" --version 2>&1); then
      status=0
    elif version_output=$("$path" --help 2>&1); then
      status=0
    else
      status=1
    fi
    if (( status == 0 )); then
      printf 'OK   %-24s %s\n' "$name" "$path"
      printf '%s\n' "${version_output%%$'\n'*}"
    else
      printf 'FAIL %-24s %s\n' "$name" "$path" >&2
      errors=$((errors + 1))
    fi
  else
    printf 'MISS %-24s\n' "$name" >&2
    errors=$((errors + 1))
  fi
done

if (( errors > 0 )); then
  printf 'ERROR: %d requested tool(s) are unavailable or failed to run.\n' \
    "$errors" >&2
  exit 1
fi
printf '\nAll requested C++ quality tools are available.\n'
