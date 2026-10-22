import io
import re
import zipfile
import requests

SUPPORTED_EXTENSIONS = {
    'py': 'Python',
    'js': 'JavaScript',
    'ts': 'TypeScript',
    'java': 'Java',
    'c': 'C',
    'cpp': 'C++',
    'h': 'C/C++ Header',
    'cs': 'C#',
    'go': 'Go',
    'rs': 'Rust',
    'rb': 'Ruby',
    'php': 'PHP',
    'html': 'HTML',
    'css': 'CSS',
    'sql': 'SQL',
    'md': 'Markdown',
    'txt': 'Text',
    'json': 'JSON',
    'yaml': 'YAML',
    'toml': 'TOML',
}

SKIPPED_DIR_PATTERNS = [
    r'(^|/)\.git($|/)',
    r'(^|/)node_modules($|/)',
    r'(^|/)__pycache__($|/)',
    r'(^|/)build($|/)',
    r'(^|/)dist($|/)',
    r'(^|/)\.venv($|/)',
    r'(^|/)venv($|/)',
    r'(^|/)\.idea($|/)',
    r'(^|/)\.vscode($|/)',
]

def parse_github_url(url):
    """
    Validates and extracts (owner, repo) from https://github.com/{owner}/{repo}
    """
    match = re.match(r'^https://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$', url.strip())
    if not match:
        return None, None
    return match.group(1), match.group(2)

def download_github_zip(owner, repo):
    """
    Downloads repo zipball from api.github.com in memory.
    Enforces maximum 10 MB download size.
    Returns bytes.
    Raises ValueError with user-friendly error message on failures.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
    headers = {
        "User-Agent": "SyntaxSense-Assistant/1.0",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        response = requests.get(api_url, headers=headers, stream=True, timeout=30)
    except requests.RequestException:
        raise ValueError("Failed to connect to GitHub. Please check your internet connection and try again.")

    if response.status_code == 404:
        raise ValueError("Repository not found or not public")
    elif response.status_code != 200:
        raise ValueError(f"GitHub returned HTTP {response.status_code}")

    # Read stream with 10 MB limit
    max_zip_bytes = 10 * 1024 * 1024  # 10 MB
    content = bytearray()
    for chunk in response.iter_content(chunk_size=65536):
        content.extend(chunk)
        if len(content) > max_zip_bytes:
            raise ValueError("Repository ZIP archive exceeds 10 MB limit")

    return bytes(content)

def inspect_github_zip(zip_bytes):
    """
    Unpacks zip in memory, categorizes files into supported and skipped.
    Limits:
      - up to 100 supported files
      - each file up to 100 KB
    Returns:
      supported_files: list of dicts:
        {'path': str, 'language': str, 'size': int, 'content': str}
      skipped_files: list of dicts:
        {'path': str, 'size': int, 'reason': str}
      folder_tree: nested dict representing the directory structure
    """
    supported_files = []
    skipped_files = []
    folder_tree = {}

    max_supported_files = 100
    max_single_file_size = 100 * 1024  # 100 KB

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        infolist = zf.infolist()
        if not infolist:
            raise ValueError("Repository archive is empty")

        # The root folder in zipball is typically '{owner}-{repo}-{hash}/'
        root_prefix = infolist[0].filename.split('/')[0] + '/'

        for info in infolist:
            if info.is_dir():
                continue

            # Strip root prefix to get relative repo path
            rel_path = info.filename
            if rel_path.startswith(root_prefix):
                rel_path = rel_path[len(root_prefix):]

            # Security: Prevent path traversal
            if ".." in rel_path or rel_path.startswith('/'):
                continue

            # Check for skipped directory patterns
            is_ignored_dir = any(re.search(pat, rel_path, re.IGNORECASE) for pat in SKIPPED_DIR_PATTERNS)
            if is_ignored_dir:
                skipped_files.append({
                    'path': rel_path,
                    'size': info.file_size,
                    'reason': 'Excluded directory (.git, build, node_modules, etc.)',
                })
                continue

            # Determine extension
            ext = rel_path.rsplit('.', 1)[-1].lower() if '.' in rel_path else ''

            if ext not in SUPPORTED_EXTENSIONS:
                skipped_files.append({
                    'path': rel_path,
                    'size': info.file_size,
                    'reason': f"Unsupported file type (.{ext})" if ext else "No file extension",
                })
                continue

            if info.file_size > max_single_file_size:
                skipped_files.append({
                    'path': rel_path,
                    'size': info.file_size,
                    'reason': f"File size ({info.file_size} bytes) exceeds 100 KB limit",
                })
                continue

            if len(supported_files) >= max_supported_files:
                skipped_files.append({
                    'path': rel_path,
                    'size': info.file_size,
                    'reason': "Exceeded 100 supported files repository limit",
                })
                continue

            # Read text in memory
            raw_bytes = zf.read(info)
            try:
                content_str = raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                content_str = raw_bytes.decode('utf-8', errors='replace')

            supported_files.append({
                'path': rel_path,
                'language': SUPPORTED_EXTENSIONS[ext],
                'size': info.file_size,
                'content': content_str,
            })

    # Build folder tree from all files
    for item in supported_files:
        _add_to_tree(folder_tree, item['path'], is_supported=True)
    for item in skipped_files:
        _add_to_tree(folder_tree, item['path'], is_supported=False, reason=item['reason'])

    return supported_files, skipped_files, folder_tree

def _add_to_tree(tree, path, is_supported=True, reason=None):
    parts = path.split('/')
    curr = tree
    for part in parts[:-1]:
        if part not in curr:
            curr[part] = {'__type__': 'dir', '__children__': {}}
        curr = curr[part]['__children__']
    file_name = parts[-1]
    curr[file_name] = {
        '__type__': 'file',
        '__supported__': is_supported,
        '__reason__': reason,
    }
