import os

APP_PACKAGE = "thedoctor0101"

def to_pascal_case(name):
    return ''.join(word.capitalize() for word in name.replace('-', '_').split('_'))

def to_camel_case(name):
    parts = name.replace('-', '_').split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])

def to_snake_case(name):
    return name.lower().replace(' ', '_').replace('-', '_')

# ──────────────────────────────────────────────
# TEMPLATES
# ──────────────────────────────────────────────

def generate_api_file(method, feature_snake, class_prefix, params, is_multipart, use_model=False, model_name='', model_import=''):
    param_declarations = '\n'.join([f"    required dynamic {p}," for p in params])

    if is_multipart:
        body_fields = '\n'.join([
            f'        if ({p} != null)\n          "{p}": await MultipartFile.fromFile({p}, filename: {p}.split(\'/\').last),'
            if p == 'image' else f'        if ({p} != None) "{p}": {p},'
            for p in params
        ])
        data_block = f"""      FormData formData = FormData.fromMap({{
{body_fields}
      }});

      Response response = await {method}Http(Endpoints.{to_camel_case(feature_snake)}(), formData);"""
    elif method == 'get' or method == 'delete':
        data_block = f"      Response response = await {method}Http(Endpoints.{to_camel_case(feature_snake)}());"
    else:
        body_fields = '\n'.join([f'        "{p}": {p},' for p in params])
        data_block = f"""      Map<String, dynamic> data = {{
{body_fields}
      }};

      Response response = await {method}Http(Endpoints.{to_camel_case(feature_snake)}(), data);"""

    status_check = "response.statusCode == 200 || response.statusCode == 201" if method == 'post' else "response.statusCode == 200"
    param_signature = f"{{\n{param_declarations}\n  }}" if params else ""

    if use_model:
        return_type = model_name
        success_block = f"        return {model_name}.fromJson(response.data);"
        model_import_line = f"import 'package:{APP_PACKAGE}/{model_import}';\n"
    else:
        return_type = "Map<String, dynamic>"
        success_block = f"""        final result = response.data as Map<String, dynamic>;
        ToastUtil.showShortToast("Success");
        return result;"""
        model_import_line = ""

    return f"""import 'package:{APP_PACKAGE}/constants/common_imports.dart';
import 'package:dio_ansi_logger/dio_ansi_logger.dart';
{model_import_line}
final class {class_prefix}Api {{
  static final {class_prefix}Api _singleton = {class_prefix}Api._internal();
  {class_prefix}Api._internal();
  static {class_prefix}Api get instance => _singleton;

  Future<{return_type}> {to_camel_case(feature_snake)}Api({param_signature}) async {{
    try {{
{data_block}
      if ({status_check}) {{
{success_block}
      }} else {{
        throw DataSource.DEFAULT.getFailure();
      }}
    }} catch (error) {{
      AnsiLog.error('{class_prefix} failed', error: error, tag: '{class_prefix}Api');
      rethrow;
    }}
  }}
}}
"""

def generate_rx_file(feature_snake, class_prefix, feature_folder, params, use_model=False, model_name='', model_import=''):
    param_declarations = '\n'.join([f"    required dynamic {p}," for p in params])
    param_pass = '\n'.join([f"        {p}: {p}," for p in params])

    param_signature = f"{{\n{param_declarations}\n  }}" if params else ""
    param_call = f"(\n{param_pass}\n      )" if params else "()"

    response_type = model_name if use_model else "Map<String, dynamic>"
    model_import_line = f"import 'package:{APP_PACKAGE}/{model_import}';\n" if use_model else ""

    return f"""import 'package:{APP_PACKAGE}/constants/common_imports.dart';
import 'package:{APP_PACKAGE}/feature/{feature_folder}/data/{feature_snake}/{feature_snake}_api.dart';
import 'package:dio_ansi_logger/dio_ansi_logger.dart';
{model_import_line}
final class {class_prefix}Rx extends RxResponseInt<{response_type}> {{
  final api = {class_prefix}Api.instance;

  {class_prefix}Rx({{required super.empty, required super.dataFetcher}});
  ValueStream get getFileData => dataFetcher.stream;

  Future<bool> {to_camel_case(feature_snake)}Rx({param_signature}) async {{
    try {{
      final data = await api.{to_camel_case(feature_snake)}Api{param_call};
      await handleSuccessWithReturn(data);
      return true;
    }} catch (error) {{
      return await handleErrorWithReturn(error);
    }}
  }}

  @override
  handleSuccessWithReturn({response_type} data) {{
    AnsiLog.success('{class_prefix} loaded successfully', tag: '{class_prefix}Rx');
    dataFetcher.sink.add(data);
    return super.handleSuccessWithReturn(data);
  }}

  @override
  handleErrorWithReturn(dynamic error) {{
    if (error is DioException) {{
      if (error.response?.statusCode == 400) {{
        AnsiLog.warning(error.response!.data["error"].toString(), tag: '{class_prefix}Rx');
        ToastUtil.showShortToast(error.response!.data["error"]);
      }} else {{
        AnsiLog.error(error.response!.data["message"].toString(), error: error, tag: '{class_prefix}Rx');
        ToastUtil.showShortToast(error.response!.data["message"]);
      }}
    }} else {{
      AnsiLog.error('Unexpected error', error: error, tag: '{class_prefix}Rx');
    }}
    dataFetcher.sink.addError(error);
    return super.handleErrorWithReturn(error);
  }}
}}
"""

# ──────────────────────────────────────────────
# FILE SCANNER
# ──────────────────────────────────────────────

SKIP = {'.git', '.dart_tool', '.idea', 'build', '.gradle', '__pycache__',
        'node_modules', '.flutter-plugins', '.flutter-plugins-dependencies'}

def scan_folders(scan_root="."):
    all_folders = []
    for root, dirs, _ in os.walk(scan_root):
        dirs[:] = [d for d in sorted(dirs) if d not in SKIP and not d.startswith('.')]
        for d in dirs:
            full = os.path.normpath(os.path.join(root, d))
            all_folders.append(full)
    return all_folders

def scan_file(filename, scan_root="."):
    matches = []
    for root, dirs, files in os.walk(scan_root):
        dirs[:] = [d for d in sorted(dirs) if d not in SKIP and not d.startswith('.')]
        if filename in files:
            matches.append(os.path.normpath(os.path.join(root, filename)))
    return matches

def pick_folder(all_folders):
    if not all_folders:
        print("No folders found. Using current directory.")
        return "."
    print(f"\n{'#':<5} {'Folder'}")
    print("-" * 60)
    for i, folder in enumerate(all_folders, 1):
        print(f"{i:<5} {folder}")
    print("\nEnter folder number (or type a custom path): ", end="")
    choice = input().strip()
    if choice.isdigit():
        idx = int(choice) - 1
        return all_folders[idx] if 0 <= idx < len(all_folders) else "."
    return choice or "."

def pick_file(matches, label):
    if not matches:
        print(f"  {label} not found automatically.")
        print(f"  Enter path manually (or blank to skip): ", end="")
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

    method_name = to_camel_case(feature_snake)
    new_line = f"  static String {method_name}() => \"{endpoint_str}\";"

    if f"{method_name}()" in content:
        print(f"  Endpoint {method_name}() already exists — skipping.")
        return

    insert_pos = content.rfind('}')
    if insert_pos == -1:
        print("  Could not find closing brace in endpoints.dart — skipping.")
        return

    updated = content[:insert_pos] + f"{new_line}\n" + content[insert_pos:]
    with open(endpoints_path, 'w', encoding='utf-8') as f:
        f.write(updated)
    print(f"  Added: {new_line.strip()}")


def register_api_access(api_access_path, class_prefix, feature_snake,
                         use_model, model_name, model_import):
    with open(api_access_path, 'r', encoding='utf-8') as f:
        content = f.read()

    rx_class = f"{class_prefix}Rx"
    var_name  = f"{to_camel_case(feature_snake)}Rx"

    if var_name in content:
        print(f"  {var_name} already exists — skipping.")
        return

    # Add model import if needed
    if use_model and model_import:
        model_import_line = f"import 'package:{APP_PACKAGE}/{model_import}';"
        if model_import_line not in content:
            last_semi = content.rfind(';', 0, content.find('\n\n'))
            if last_semi == -1:
                last_import_idx = content.rfind("import '")
                last_semi = content.index(';', last_import_idx)
            content = content[:last_semi + 1] + f"\n{model_import_line}" + content[last_semi + 1:]

    # Build registration block matching your style
    if use_model:
        subject_type = model_name
        empty_val    = f"{model_name}()"
    else:
        subject_type = "Map<String, dynamic>"
        empty_val    = "<String, dynamic>{}"

    rx_block = (
        f"\n{rx_class} {var_name} = {rx_class}(\n"
        f"  empty: {empty_val},\n"
        f"  dataFetcher: BehaviorSubject<{subject_type}>(),\n"
        f");\n"
    )

    content = content.rstrip() + "\n" + rx_block
    with open(api_access_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Added: {rx_class} {var_name} = ...")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    print("=" * 50)
    print("   Flutter API Boilerplate Generator")
    print("=" * 50)

    print("\nFeature folder (e.g. profile, explore_tour): ", end="")
    feature_folder = to_snake_case(input().strip())

    print("API name in snake_case (e.g. get_tour, post_login): ", end="")
    feature_snake = to_snake_case(input().strip())

    print("Class prefix in PascalCase (blank = auto): ", end="")
    class_prefix = input().strip() or to_pascal_case(feature_snake)

    print("HTTP method (get / post / patch / put / delete): ", end="")
    method = input().strip().lower()

    print("Parameters (comma separated, blank if none): ", end="")
    raw_params = input().strip()
    params = [p.strip() for p in raw_params.split(',')] if raw_params else []

    is_multipart = False
    if 'image' in params:
        print("Image param detected — multipart/form-data? (y/n): ", end="")
        is_multipart = input().strip().lower() == 'y'

    print("Response type (model / map): ", end="")
    use_model = input().strip().lower() == 'model'

    model_name   = ''
    model_import = ''
    if use_model:
        print("Model class name (e.g. ToursResponse): ", end="")
        model_name = input().strip()
        print("Model import path (e.g. feature/explore_tour/model/tours_response.dart): ", end="")
        model_import = input().strip()

    # ── Pick output folder ────────────────────────────────────────────────────
    print("\nScanning folders...")
    all_folders = scan_folders()
    print("\nWhere should the files be generated?")
    output_root = pick_folder(all_folders)
    print(f"Output: {output_root}\n")

    # ── Generate files ────────────────────────────────────────────────────────
    output_dir = os.path.join(output_root, feature_snake)
    os.makedirs(output_dir, exist_ok=True)

    api_content = generate_api_file(method, feature_snake, class_prefix, params, is_multipart, use_model, model_name, model_import)
    rx_content  = generate_rx_file(feature_snake, class_prefix, feature_folder, params, use_model, model_name, model_import)

    api_path = os.path.join(output_dir, f"{feature_snake}_api.dart")
    rx_path  = os.path.join(output_dir, f"{feature_snake}_rx.dart")

    with open(api_path, 'w', encoding='utf-8') as f:
        f.write(api_content)
    with open(rx_path, 'w', encoding='utf-8') as f:
        f.write(rx_content)

    print(f"Generated:")
    print(f"  {api_path}")
    print(f"  {rx_path}")

    # ── Auto-register endpoints.dart ──────────────────────────────────────────
    print("\n" + "-" * 50)
    print("Looking for endpoints.dart...")
    endpoints_path = pick_file(scan_file("endpoints.dart"), "endpoints.dart")
    if endpoints_path:
        print(f"Endpoint string (e.g. tours, profile/update): ", end="")
        endpoint_str = input().strip()
        if endpoint_str:
            register_endpoint(endpoints_path, feature_snake, endpoint_str)
        else:
            print("  Skipped.")
    else:
        print("  Skipping endpoints.dart.")

    # ── Auto-register api_access.dart ─────────────────────────────────────────
    print("\n" + "-" * 50)
    print("Looking for api_access.dart...")
    api_access_path = pick_file(scan_file("api_access.dart"), "api_access.dart")
    if api_access_path:
        register_api_access(
            api_access_path, class_prefix, feature_snake,
            use_model, model_name, model_import
        )
    else:
        print("  Skipping api_access.dart.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("Done!")
    print(f"  {api_path}")
    print(f"  {rx_path}")
    print(f"  Endpoints.{to_camel_case(feature_snake)}()  added to endpoints.dart")
    print(f"  {to_camel_case(feature_snake)}Rx  added to api_access.dart")
    print("=" * 50)


if __name__ == "__main__":
    main()
