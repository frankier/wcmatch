"""
Wild Card Match.

A module for performing wild card matches.

Licensed under MIT
Copyright (c) 2018 Isaac Muse <isaacmuse@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions
of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.
"""
import os
import re
from . import file_attrs
from . import _wcparse
from . import util

__all__ = (
    "FORCECASE", "IGNORECASE", "RAWCHARS", "FILEPATHNAME", "DIRPATHNAME",
    "EXTMATCH", "GLOBSTAR", "BRACE", "MINUSNEGATE", "SYMLINKS", "HIDDEN", "RECURSIVE"
    "F", "I", "R", "P", "E", "G", "M", "DP", "FP", "SL", "HD", "RV",
    "WcMatch"
)

F = FORCECASE = _wcparse.FORCECASE
I = IGNORECASE = _wcparse.IGNORECASE
R = RAWCHARS = _wcparse.RAWCHARS
E = EXTMATCH = _wcparse.EXTMATCH
G = GLOBSTAR = _wcparse.GLOBSTAR
B = BRACE = _wcparse.BRACE
M = MINUSNEGATE = _wcparse.MINUSNEGATE

# Control `PATHNAME` individually for folder exclude and files
DP = DIRPATHNAME = 0x10000
FP = FILEPATHNAME = 0x20000
SL = SYMLINKS = 0x40000
HD = HIDDEN = 0x80000
RV = RECURSIVE = 0x100000

# Control `PATHNAME` for file and folder
P = PATHNAME = DIRPATHNAME | FILEPATHNAME

FLAG_MASK = (
    FORCECASE |
    IGNORECASE |
    RAWCHARS |
    EXTMATCH |
    GLOBSTAR |
    BRACE |
    MINUSNEGATE |
    DIRPATHNAME |
    FILEPATHNAME |
    SYMLINKS |
    HIDDEN |
    RECURSIVE
)


class WcMatch(object):
    """Finds files by wildcard."""

    def __init__(self, *args, **kwargs):
        """Initialize the directory walker object."""

        args = list(args)
        self._skipped = 0
        self._abort = False
        self._directory = util.norm_slash(args.pop(0))
        self.is_bytes = isinstance(self._directory, bytes)
        if not self._directory:
            if self.is_bytes:
                curdir = bytes(os.curdir, 'ASCII')
            else:
                curdir = os.curdir
        else:
            curdir = self._directory
        self.sep = os.fsencode(os.sep) if self.is_bytes else os.sep
        self.base = curdir if curdir.endswith(self.sep) else curdir + self.sep
        self.file_pattern = args.pop(0) if args else kwargs.pop('file_pattern', b'' if self.is_bytes else '')
        if not self.file_pattern:
            self.file_pattern = _wcparse.WcRegexp(
                (re.compile(br'^.*$', re.DOTALL),) if self.is_bytes else (re.compile(r'^.*$', re.DOTALL),)
            )
        self.exclude_pattern = args.pop(0) if args else kwargs.pop('exclude_pattern', b'' if self.is_bytes else '')
        self.flags = (args.pop(0) if args else kwargs.pop('flags', 0)) & FLAG_MASK
        self.flags |= _wcparse.NEGATE | _wcparse.DOTMATCH
        self.follow_links = bool(self.flags & SYMLINKS)
        self.show_hidden = bool(self.flags & HIDDEN)
        self.recursive = bool(self.flags & RECURSIVE)
        self.dir_pathname = bool(self.flags & DIRPATHNAME)
        self.file_pathname = bool(self.flags & FILEPATHNAME)
        if util.platform() == "windows":
            self.flags |= _wcparse._FORCEWIN
        self.flags = self.flags & (_wcparse.FLAG_MASK ^ (SYMLINKS | DIRPATHNAME | FILEPATHNAME | HIDDEN))

        self.on_init(*args, **kwargs)
        self.file_check, self.folder_exclude_check = self._compile(self.file_pattern, self.exclude_pattern)

    def _compile_wildcard(self, pattern, pathname=False):
        """Compile or format the wildcard inclusion/exclusion pattern."""

        patterns = None
        flags = self.flags
        if pathname:
            flags |= _wcparse.PATHNAME
        if pattern:
            patterns = _wcparse.WcSplit(pattern, flags=flags).split()

        return _wcparse.compile(patterns, flags) if patterns else patterns

    def _compile(self, file_pattern, folder_exclude_pattern):
        """Compile patterns."""

        if not isinstance(file_pattern, _wcparse.WcRegexp):
            file_pattern = self._compile_wildcard(file_pattern, self.file_pathname)

        if not isinstance(folder_exclude_pattern, _wcparse.WcRegexp):

            folder_exclude_pattern = self._compile_wildcard(folder_exclude_pattern, self.dir_pathname)

        return file_pattern, folder_exclude_pattern

    def _has_attributes(self, path, hidden=False, symlinks=False):
        """Check if file is hidden."""

        if self.is_bytes:
            return file_attrs.has_file_attributes_bytes(path, hidden, symlinks)
        else:
            return file_attrs.has_file_attributes(path, hidden, symlinks)

    def _valid_file(self, base, name):
        """Return whether a file can be searched."""

        valid = False
        fullpath = os.path.join(base, name)
        if self.file_check is not None and not self._has_attributes(fullpath, hidden=not self.show_hidden):
            valid = self.compare_file(fullpath[self._base_len:] if self.file_pathname else name)
        return self.on_validate_file(base, name) if valid else valid

    def compare_file(self, filename):
        """Compare filename."""

        return self.file_check.match(filename)

    def on_validate_file(self, base, name):
        """Validate file override."""

        return True

    def _valid_folder(self, base, name):
        """Return whether a folder can be searched."""

        valid = True
        fullpath = os.path.join(base, name)
        if not self.recursive or self._has_attributes(fullpath, not self.show_hidden, not self.follow_links):
            valid = False
        elif self.folder_exclude_check is not None:
            valid = self.compare_directory(fullpath[self._base_len:] if self.dir_pathname else name)
        return self.on_validate_directory(base, name) if valid else valid

    def compare_directory(self, directory):
        """Compare folder."""

        return not self.folder_exclude_check.match(directory + self.sep if self.dir_pathname else directory)

    def on_init(self, *args, **kwargs):
        """Handle custom initialization."""

    def on_validate_directory(self, base, name):
        """Validate folder override."""

        return True

    def on_skip(self, base, name):
        """On skip."""

        return None

    def on_error(self, base, name):
        """On error."""

        return None

    def on_match(self, base, name):
        """On match."""

        return os.path.join(base, name)

    def get_skipped(self):
        """Get number of skipped files."""

        return self._skipped

    def kill(self):
        """Abort process."""

        self._abort = True

    def reset(self):
        """Revive class from a killed state."""

        self._abort = False

    def _walk(self):
        """Start search for valid files."""

        self._base_len = len(self.base)

        for base, dirs, files in os.walk(self.base, followlinks=self.follow_links):
            # Remove child folders based on exclude rules
            for name in dirs[:]:
                try:
                    if not self._valid_folder(base, name):
                        dirs.remove(name)
                except Exception:
                    dirs.remove(name)
                    value = self.on_error(base, name)
                    if value is not None:  # pragma: no cover
                        yield value

                if self._abort:
                    break

            # Search files if they were found
            if len(files):
                # Only search files that are in the include rules
                for name in files:
                    try:
                        valid = self._valid_file(base, name)
                    except Exception:
                        valid = False
                        value = self.on_error(base, name)
                        if value is not None:
                            yield value

                    if valid:
                        yield self.on_match(base, name)
                    else:
                        self._skipped += 1
                        value = self.on_skip(base, name)
                        if value is not None:
                            yield value

                    if self._abort:
                        break

            if self._abort:
                break

    def match(self):
        """Run the directory walker."""

        return list(self.imatch())

    def imatch(self):
        """Run the directory walker as iterator."""

        self._skipped = 0
        for f in self._walk():
            yield f
