import os

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
APP_PACKAGE = "thedoctor0101"
# ──────────────────────────────────────────────

def to_pascal(name):
    return ''.join(w.capitalize() for w in name.replace('-', '_').split('_'))

def to_camel(name):
    parts = name.replace('-', '_').split('_')
    return parts[0] + ''.join(w.capitalize() for w in parts[1:])

def to_snake(name):
    return name.lower().replace(' ', '_').replace('-', '_')


# ──────────────────────────────────────────────
# TEMPLATES
# ──────────────────────────────────────────────

def gen_api(method, feature_snake, class_prefix, params, is_multipart):
    param_declarations = '\n'.join([f"    required dynamic {p}," for p in params])
    param_signature    = f"{{\n{param_declarations}\n  }}" if params else ""

    if is_multipart:
        form_fields = '\n'.join([
            f"        if ({p} != null)\n"
            f"          '{p}': await MultipartFile.fromFile({p}, filename: {p}.split('/').last),"
            if p == 'image' else
            f"        if ({p} != null) '{p}': {p},"
            for p in params
        ])
        request_block = (
            f"request: () => {method}Http(\n"
            f"          Endpoints.{to_camel(feature_snake)}(),\n"
            f"          FormData.fromMap({{\n"
            f"{form_fields}\n"
            f"          }}),\n"
            f"        ),"
        )
    elif method in ('get', 'delete') and not params:
        request_block = f"request: () => {method}Http(Endpoints.{to_camel(feature_snake)}()),"
    elif method == 'get' and params:
        query = '{' + ', '.join([f"'{p}': {p}" for p in params]) + '}'
        request_block = f"request: () => {method}Http(Endpoints.{to_camel(feature_snake)}(), queryParams: {query}),"
    else:
        body = '{' + ', '.join([f"'{p}': {p}" for p in params]) + '}'
        request_block = f"request: () => {method}Http(Endpoints.{to_camel(feature_snake)}(), {body}),"

    multipart_import = "import 'package:dio/dio.dart';\n" if is_multipart else ""

    return f"""import 'package:flutter_riverpod/flutter_riverpod.dart';
{multipart_import}import 'package:{APP_PACKAGE}/networks/base/base_api.dart';
import 'package:{APP_PACKAGE}/networks/dio/dio_singleton.dart';
import 'package:{APP_PACKAGE}/networks/endpoints.dart';
import '../model/{feature_snake}_model.dart';

final {to_camel(feature_snake)}ApiProvider =
    Provider<{class_prefix}Api>((ref) => {class_prefix}Api());

class {class_prefix}Api extends BaseApi {{
  Future<{class_prefix}Model> {to_camel(feature_snake)}({param_signature}) =>
      call(
        {request_block}
        fromJson: (json) => {class_prefix}Model.fromJson(json),
      );
}}
"""


def gen_notifier_get(feature_snake, class_prefix):
    return f"""import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:{APP_PACKAGE}/networks/base/base_async_notifier.dart';
import '../data/{feature_snake}_api.dart';
import '../model/{feature_snake}_model.dart';

final {to_camel(feature_snake)}Provider =
    AsyncNotifierProvider<{class_prefix}Notifier, {class_prefix}Model>(
  {class_prefix}Notifier.new,
);

class {class_prefix}Notifier extends BaseAsyncNotifier<{class_prefix}Model> {{
  {class_prefix}Api get _api => ref.read({to_camel(feature_snake)}ApiProvider);

  @override
  Future<{class_prefix}Model> build() =>
      fetch(() => _api.{to_camel(feature_snake)}());

  Future<void> refresh() =>
      super.refresh(() => _api.{to_camel(feature_snake)}());
}}
"""


def gen_notifier_post(feature_snake, class_prefix, params):
    param_declarations = '\n'.join([f"    required dynamic {p}," for p in params])
    param_pass         = '\n'.join([f"          {p}: {p}," for p in params])
    param_signature    = f"{{\n{param_declarations}\n  }}" if params else ""
    param_call         = f"(\n{param_pass}\n        )" if params else "()"

    return f"""import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:{APP_PACKAGE}/networks/base/base_async_notifier.dart';
import '../data/{feature_snake}_api.dart';

final {to_camel(feature_snake)}Provider =
    AsyncNotifierProvider<{class_prefix}Notifier, void>(
  {class_prefix}Notifier.new,
);

class {class_prefix}Notifier extends BaseAsyncNotifier<void> {{
  @override
  Future<void> build() async {{}}

  Future<void> {to_camel(feature_snake)}({param_signature}) =>
      run(() async {{
        await ref.read({to_camel(feature_snake)}ApiProvider).{to_camel(feature_snake)}{param_call};
      }});
}}
"""


# ──────────────────────────────────────────────
# FILE SCANNER
# ──────────────────────────────────────────────

SKIP = {'.git', '.dart_tool', '.idea', 'build', '.gradle', '__pycache__',
        'node_modules', '.flutter-plugins', '.flutter-plugins-dependencies',
        'ios', 'android', 'windows', 'macos', 'linux', 'web', 'test'}


def scan_file(filename, scan_root="."):
    matches = []
    for root, dirs, files in os.walk(scan_root):
        dirs[:] = [d for d in sorted(dirs) if d not in SKIP and not d.startswith('.')]
        if filename in files:
            matches.append(os.path.normpath(os.path.join(root, filename)))
    return matches


def pick_file(matches, label):
    if not matches:
        print(f"  {label} not found. Enter path manually (or blank to skip): ", end="")
        return input().strip() or None
    if len(matches) == 1:
        print(f"  Found: {matches[0]}")
        print(f"  Use this? (y/n): ", end="")
        return matches[0] if input().strip().lower() != 'n' else None
    print(f"\n  Multiple {label} found:")
    for i, path in enumerate(matches, 1):
        print(f"  {i}. {path}")
    print(f"  Enter number: ", end="")
    choice = input().strip()
    if choice.isdigit():
        idx = int(choice) - 1
        return matches[idx] if 0 <= idx < len(matches) else None
    return None


# ──────────────────────────────────────────────
# AUTO-REGISTER
# ──────────────────────────────────────────────

def register_endpoint(endpoints_path, feature_snake, endpoint_str):
    with open(endpoints_path, 'r', encoding='utf-8') as f:
        content = f.read()

    method_name = to_camel(feature_snake)
    new_line = f"  static String {method_name}() => \"{endpoint_str}\";"

    if f"{method_name}()" in content:
        print(f"  {method_name}() already exists — skipping.")
        return

    insert_pos = content.rfind('}')
    updated = content[:insert_pos] + f"  {new_line}\n" + content[insert_pos:]
    with open(endpoints_path, 'w', encoding='utf-8') as f:
        f.write(updated)
    print(f"  Added: {new_line.strip()}")


def register_api_access(api_access_path, feature_snake, feature_folder):
    with open(api_access_path, 'r', encoding='utf-8') as f:
        content = f.read()

    export_line = (
        f"export 'package:{APP_PACKAGE}/features/"
        f"{feature_folder}/{feature_snake}/data/{feature_snake}_api.dart';"
    )

    if export_line in content:
        print(f"  Export already exists — skipping.")
        return

    if '// Add more' in content:
        insert_pos = content.index('// Add more')
        updated = content[:insert_pos] + export_line + '\n' + content[insert_pos:]
    else:
        updated = content.rstrip() + f"\n{export_line}\n"

    with open(api_access_path, 'w', encoding='utf-8') as f:
        f.write(updated)
    print(f"  Added: {export_line}")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    print("=" * 55)
    print("   Flutter Riverpod Boilerplate Generator")
    print("=" * 55)

    print("\nFeature folder under features/ (e.g. auth, tour, profile): ", end="")
    feature_folder = to_snake(input().strip())

    print("Feature name in snake_case (e.g. sign_in, get_tours): ", end="")
    feature_snake = to_snake(input().strip())

    print(f"Class prefix PascalCase (blank = {to_pascal(feature_snake)}): ", end="")
    raw = input().strip()
    class_prefix = raw if raw else to_pascal(feature_snake)

    print("HTTP method (get / post / patch / put / delete): ", end="")
    method = input().strip().lower()

    print("Request params, comma separated (blank if none): ", end="")
    raw_params = input().strip()
    params = [p.strip() for p in raw_params.split(',')] if raw_params else []

    is_multipart = False
    if 'image' in params:
        print("Image param detected — use multipart/form-data? (y/n): ", end="")
        is_multipart = input().strip().lower() == 'y'

    # ── Output path ───────────────────────────────────────────────────────────
    pubspec_hits = [f for f in scan_file('pubspec.yaml') if os.path.isfile(f)]
    lib_root = os.path.join(os.path.dirname(pubspec_hits[0]), 'lib') if pubspec_hits else os.path.join('.', 'lib')
    output_root = os.path.join(lib_root, 'features', feature_folder, feature_snake)

    data_dir     = os.path.join(output_root, 'data')
    notifier_dir = os.path.join(output_root, 'notifier')
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(notifier_dir, exist_ok=True)

    # ── Generate 2 files ─────────────────────────────────────────────────────
    is_get = method == 'get'

    files = {
        os.path.join(data_dir,     f"{feature_snake}_api.dart"):      gen_api(method, feature_snake, class_prefix, params, is_multipart),
        os.path.join(notifier_dir, f"{feature_snake}_notifier.dart"): gen_notifier_get(feature_snake, class_prefix) if is_get else gen_notifier_post(feature_snake, class_prefix, params),
    }

    print(f"\nGenerating files in: {output_root}")
    for path, content in files.items():
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  v {os.path.relpath(path)}")

    # ── Auto-register endpoints.dart ──────────────────────────────────────────
    print("\n" + "-" * 55)
    print("Looking for endpoints.dart...")
    endpoints_path = pick_file(scan_file("endpoints.dart"), "endpoints.dart")
    if endpoints_path:
        print(f"Endpoint string (e.g. tours, auth/login): ", end="")
        endpoint_str = input().strip()
        if endpoint_str:
            register_endpoint(endpoints_path, feature_snake, endpoint_str)
    else:
        print("  Skipping endpoints.dart.")

    # ── Auto-register api_access.dart ─────────────────────────────────────────
    print("\n" + "-" * 55)
    print("Looking for api_access.dart...")
    api_access_path = pick_file(scan_file("api_access.dart"), "api_access.dart")
    if api_access_path:
        register_api_access(api_access_path, feature_snake, feature_folder)
    else:
        print("  Skipping api_access.dart.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("Done! Files created:")
    for path in files:
        print(f"  {os.path.relpath(path)}")
    print(f"\nEndpoints.{to_camel(feature_snake)}()  ->  endpoints.dart")
    print(f"Export added                        ->  api_access.dart")
    print("=" * 55)


if __name__ == "__main__":
    main()
