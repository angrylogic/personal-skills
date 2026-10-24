#!/usr/bin/env python3
"""Import, diff, and merge vendored skills using provenance in SKILL.md."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('upstream_repository', 'upstream_revision', 'upstream_path')


def git(*args, cwd=None, check=True):
    return subprocess.run(['git', *map(str, args)], cwd=cwd, check=check,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def frontmatter(data, provenance=None):
    text = data.decode('utf-8')
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not match:
        raise ValueError('SKILL.md must start with YAML frontmatter')
    # Edit only our reserved scalar keys; preserve the rest of the YAML verbatim.
    header = match[1]
    lines = header.splitlines(keepends=True)
    if not any(re.match(r'^name:\s*\S', line) for line in lines) or not any(re.match(r'^description:\s*\S', line) for line in lines):
        raise ValueError('SKILL.md needs name and description')
    starts = [i for i, line in enumerate(lines) if re.match(r'^metadata:', line)]
    if len(starts) > 1:
        raise ValueError('duplicate metadata mapping')
    previous = dict.fromkeys(FIELDS)
    if starts:
        start = starts[0]
        if not re.fullmatch(r'metadata:\s*(?:#.*)?\n?', lines[start]):
            raise ValueError('metadata must use a block mapping, not inline YAML')
        end = next((i for i in range(start + 1, len(lines)) if re.match(r'^[^\s#]', lines[i])), len(lines))
        block = lines[start + 1:end]
        kept = []
        for line in block:
            found = re.match(r'^  (' + '|'.join(FIELDS) + r'):\s*(.*?)\s*$', line)
            if found:
                key, value = found.groups()
                if previous[key] is not None:
                    raise ValueError('duplicate provenance key: ' + key)
                try:
                    previous[key] = json.loads(value)
                except ValueError:
                    raise ValueError('upstream fields must be JSON-quoted YAML strings')
            else:
                kept.append(line)
        if provenance:
            if kept and not kept[-1].endswith('\n'):
                kept[-1] += '\n'
            kept += [f'  {key}: {json.dumps(provenance[key])}\n' for key in FIELDS]
        lines[start:end] = [lines[start].rstrip('\n') + '\n', *kept] if kept else []
    elif provenance:
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        lines += ['metadata:\n', *[f'  {key}: {json.dumps(provenance[key])}\n' for key in FIELDS]]
    header = ''.join(lines).rstrip('\n')
    return ('---\n' + header + '\n---\n' + text[match.end():]).encode(), previous



def checkout(repository, revision, source, destination):
    path = PurePosixPath(source)
    if path.is_absolute() or '..' in path.parts or '\\' in source:
        raise ValueError('upstream path must be relative and contained in the repository')
    source = path.as_posix()
    with tempfile.TemporaryDirectory(prefix='skill-source-') as tmp:
        repo = Path(tmp)
        git('init', '-q', repo)
        git('fetch', '--quiet', '--depth=1', '--', repository, revision, cwd=repo)
        sha = git('rev-parse', 'FETCH_HEAD^{commit}', cwd=repo).stdout.decode().strip()
        tree = sha if source == '.' else f'{sha}:{source}'
        entries = git('ls-tree', '-rz', tree, cwd=repo).stdout.split(b'\0')
        destination.mkdir(parents=True)
        for entry in filter(None, entries):
            header, filename = entry.split(b'\t', 1)
            mode, kind, oid = header.split()
            if kind != b'blob' or mode not in (b'100644', b'100755'):
                raise ValueError('symlinks and submodules are unsupported in imported skills')
            relative = os.fsdecode(filename)
            if any(part in ('.git', '..') for part in PurePosixPath(relative).parts):
                raise ValueError('unsafe upstream filename')
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git('cat-file', 'blob', oid.decode(), cwd=repo).stdout)
            target.chmod(0o755 if mode == b'100755' else 0o644)
        skill = destination / 'SKILL.md'
        skill.write_bytes(frontmatter(skill.read_bytes())[0])
        return sha


def local_tree(source, destination):
    if source.is_symlink():
        raise ValueError('local skill cannot be a symlink')
    for item in source.rglob('*'):
        if item.is_symlink():
            raise ValueError(f'local symlink is unsupported: {item}')
    shutil.copytree(source, destination)
    skill = destination / 'SKILL.md'
    skill.write_bytes(frontmatter(skill.read_bytes())[0])


def files(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), bool(p.stat().st_mode & 0o111))
            for p in root.rglob('*') if p.is_file()}


def merge(base, local, upstream, result):
    trees = [files(p) for p in (base, local, upstream)]
    conflicts = []
    result.mkdir()
    for name in sorted(set().union(*trees)):
        b, l, u = (tree.get(name) for tree in trees)
        if l == b:
            value = u
        elif u == b or l == u:
            value = l
        elif all(v is not None for v in (b, l, u)):
            # Merge content and executable mode independently.
            modes = [v[1] for v in (b, l, u)]
            mode = modes[2] if modes[1] == modes[0] else modes[1]
            with tempfile.TemporaryDirectory() as tmp:
                paths = [Path(tmp) / str(i) for i in range(3)]
                for p, v in zip(paths, (l, b, u)):
                    p.write_bytes(v[0])
                merged = git('merge-file', '-p', '-L', 'local', '-L', 'baseline', '-L', 'upstream', *paths, check=False)
            if merged.returncode:
                conflicts.append(name)
            value = (merged.stdout if 0 <= merged.returncode < 128 else l[0], mode)
        else:
            conflicts.append(name)
            value = l if l is not None else u
        if value is not None:
            target = result / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(value[0])
            target.chmod(0o755 if value[1] else 0o644)
    return conflicts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='skills repository root')
    commands = parser.add_subparsers(dest='command', required=True)
    imp = commands.add_parser('import', help='copy an upstream skill and record its exact revision')
    imp.add_argument('name')
    imp.add_argument('repository')
    imp.add_argument('path', help='skill directory within upstream repository')
    imp.add_argument('--ref', default='HEAD')
    for command in ('diff', 'update'):
        sub = commands.add_parser(command)
        sub.add_argument('name')
        if command == 'diff':
            sub.add_argument('--ref', help='compare local skill against this upstream ref instead of baseline')
        else:
            sub.add_argument('--ref', required=True, help='new upstream branch, tag, or commit')
            sub.add_argument('--output', type=Path, help='write a review tree instead of applying; required on conflicts')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', args.name):
        raise ValueError('name must use lowercase letters, digits, and hyphens')
    target = args.root.resolve() / 'skills' / args.name
    if target.parent.is_symlink() or target.is_symlink():
        raise ValueError('skill destination must not be a symlink')
    if getattr(args, 'output', None):
        output = args.output.resolve()
        if output == target or target in output.parents:
            raise ValueError('review output must be outside the working skill')
        if output.exists():
            raise ValueError('review output must not already exist')
    with tempfile.TemporaryDirectory(prefix='skill-work-') as tmp:
        work = Path(tmp)
        if args.command == 'import':
            if target.exists():
                raise ValueError(f'destination already exists: {target}')
            sha = checkout(args.repository, args.ref, args.path, work / 'import')
            provenance = dict(zip(FIELDS, (args.repository, sha, args.path)))
            skill = work / 'import' / 'SKILL.md'
            skill.write_bytes(frontmatter(skill.read_bytes(), provenance)[0])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(work / 'import', target)
            print(f'Imported {args.name} at {sha}')
            return 0
        _, provenance = frontmatter((target / 'SKILL.md').read_bytes())
        if not all(isinstance(v, str) and v for v in provenance.values()):
            raise ValueError('skill lacks complete upstream metadata')
        repository, revision, source = (provenance[key] for key in FIELDS)
        if not re.fullmatch(r'[0-9a-f]{40,64}', revision):
            raise ValueError('upstream_revision must be a full commit SHA')
        local_tree(target, work / 'local')
        checkout(repository, args.ref if args.command == 'diff' and args.ref else revision, source, work / 'base')
        if args.command == 'diff':
            result = git('diff', '--no-index', '--no-ext-diff', '--binary', '--', 'base', 'local', cwd=work, check=False)
            if result.returncode not in (0, 1):
                raise ValueError(result.stderr.decode())
            sys.stdout.buffer.write(result.stdout)
            return result.returncode
        sha = checkout(repository, args.ref, source, work / 'upstream')
        conflicts = merge(work / 'base', work / 'local', work / 'upstream', work / 'merged')
        skill = work / 'merged' / 'SKILL.md'
        if conflicts:
            if args.output:
                shutil.copytree(work / 'merged', args.output)
            print(f'Upstream target: {sha}', file=sys.stderr)
            print('Conflicts: ' + ', '.join(conflicts), file=sys.stderr)
            print('Skill and provenance unchanged. ' + ('Review tree: ' + str(args.output) if args.output else 'Rerun with --output <new-directory> to inspect the merge.'), file=sys.stderr)
            return 2
        provenance['upstream_revision'] = sha
        skill.write_bytes(frontmatter(skill.read_bytes(), provenance)[0])
        if args.output:
            shutil.copytree(work / 'merged', args.output)
            print(f'Review tree written to {args.output}; working skill unchanged')
        else:
            # Stage beside destination, then swap; restore original if replacement fails.
            with tempfile.TemporaryDirectory(prefix='.skill-update-', dir=target.parent) as staging:
                staged, backup = Path(staging) / 'new', Path(staging) / 'old'
                shutil.copytree(work / 'merged', staged)
                target.rename(backup)
                try:
                    staged.rename(target)
                except BaseException:
                    backup.rename(target)
                    raise
            print(f'Updated {args.name} to {sha}')
        return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        detail = error.stderr.decode(errors='replace') if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(f'Error: {detail}', file=sys.stderr)
        sys.exit(2)
