#!/usr/bin/env bash
# Installs and verifies C++ code quality tools on Ubuntu/Debian developer machines.
# Does not install firmware, flash boards, alter PlatformIO config or transmit RF.
set -Eeuo pipefail

if ! command -v apt-get >/dev/null 2>&1; then
  echo 'ERROR: this script targets Ubuntu/Debian (apt-get). Adapt to your OS.' >&2
  exit 2
fi

if command -v sudo >/dev/null 2>&1 && [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  SUDO=(sudo)
else
  SUDO=()
fi

# Readable audit steps; all packages are installable from official distro repos.
"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y \
  clang clang-tools clang-tidy clang-format llvm \
  doxygen graphviz iwyu pipx \
  cmake ninja-build g++

# pipx isolates Python CLI applications; jscpd v5 requires no Node.js runtime.
export PATH="$HOME/.local/bin:$PATH"
pipx ensurepath >/dev/null || true
if ! command -v lizard >/dev/null 2>&1; then
  pipx install lizard
fi
if ! command -v jscpd >/dev/null 2>&1; then
  pipx install jscpd
fi

# Distros may expose LLVM binaries with versioned suffixes.
find_tool() {
  local base="$1" candidate
  if command -v "$base" >/dev/null 2>&1; then
    command -v "$base"
    return 0
  fi
  for candidate in /usr/bin/"${base}"-[0-9]* /usr/lib/llvm-*/bin/"${base}"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

# clang itself supplies `clang --analyze`; scan-build is a convenient wrapper.
tools=(clang-tidy clang-format clang scan-build doxygen lizard jscpd include-what-you-use clang-doc)
errors=0
printf '\n=== TOOL VERIFICATION ===\n'
for name in "${tools[@]}"; do
  if path=$(find_tool "$name"); then
    printf 'OK   %-24s %s\n' "$name" "$path"
    ("$path" --version 2>&1 || "$path" --help 2>&1 || true) | head -n 2 || true
  else
    printf 'MISS %-24s\n' "$name" >&2
    errors=$((errors + 1))
  fi
done

if (( errors > 0 )); then
  echo "ERROR: $errors requested tool(s) unavailable. Find matching LLVM package versions, then rerun verification." >&2
  exit 1
fi
printf '\nAll requested C++ quality tools found. Next: run on the actual repository and record analysis coverage.\n'
