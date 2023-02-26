#!/bin/sh

[ $# -eq 1 ] || exit 2

VER="$1"
echo "Creating version $VER"

if [ -n "$(git diff --name-only --cached)" ]; then
    echo "Stash or commit staged changes first"
    exit 2
fi

sed -i "s/^\\(\\s*version\\s*=\\s*['\"]\\)[^'\"]*\\(['\"]\\s*\\)$/\\1"$VER"\\2/" pyproject.toml
git add pyproject.toml
git commit -m "Version $VER" --no-edit
git -c user.signingkey=E36F75307F0A0EC2D145FF5CED7A208EEEC76F2D -c user.email=python-mpv@jaseg.de tag -s "v$VER" -m "Version $VER"
git push --tags origin
