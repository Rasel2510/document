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

def generate_api_file(method, feature_snake, class_prefix, endpoint_method, params, is_multipart):
    param_declarations = '\n'.join([f"    required dynamic {p}," for p in params])
    
    if is_multipart:
        body_fields = '\n'.join([
            f'        if ({p} != null)\n          "{p}": await MultipartFile.fromFile({p}, filename: {p}.split(\'/\').last),'
            if p == 'image' else f'        if ({p} != null) "{p}": {p},'
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

    param_signature = f"{{\n{param_declarations}\n  }}" if params else "()"
    param_call = "" if not params else f"{{\n{param_declarations}\n  }}"

    return f"""import 'package:{APP_PACKAGE}/constants/common_imports.dart';

final class {class_prefix}Api {{
  static final {class_prefix}Api _singleton = {class_prefix}Api._internal();
  {class_prefix}Api._internal();
  static {class_prefix}Api get instance => _singleton;

  Future<Map<String, dynamic>> {to_camel_case(feature_snake)}Api({param_signature if params else ''}) async {{
    try {{
{data_block}
      if ({status_check}) {{
        final result = response.data as Map<String, dynamic>;
        ToastUtil.showShortToast("Success");
        return result;
      }} else {{
        throw DataSource.DEFAULT.getFailure();
      }}
    }} catch (error) {{
      debugPrint("{class_prefix} error: $error");
      rethrow;
    }}
  }}
}}
"""

def generate_rx_file(feature_snake, class_prefix, feature_folder, params):
    param_declarations = '\n'.join([f"    required dynamic {p}," for p in params])
    param_pass = '\n'.join([f"        {p}: {p}," for p in params])

    param_signature = f"{{\n{param_declarations}\n  }}" if params else "()"
    param_call = f"(\n{param_pass}\n      )" if params else "()"

    return f"""import 'dart:developer';

import 'package:{APP_PACKAGE}/constants/common_imports.dart';
import 'package:{APP_PACKAGE}/feature/{feature_folder}/data/{feature_snake}/{feature_snake}_api.dart';

final class {class_prefix}Rx extends RxResponseInt<Map<String, dynamic>> {{
  final api = {class_prefix}Api.instance;

  {class_prefix}Rx({{required super.empty, required super.dataFetcher}});
  ValueStream get getFileData => dataFetcher.stream;

  Future<bool> {to_camel_case(feature_snake)}Rx({param_signature if params else ''}) async {{
    try {{
      final data = await api.{to_camel_case(feature_snake)}Api{param_call};

      await handleSuccessWithReturn(data);
      return true;
    }} catch (error) {{
      return await handleErrorWithReturn(error);
    }}
  }}

  @override
  handleSuccessWithReturn(Map<String, dynamic> data) {{
    dataFetcher.sink.add(data);
    return super.handleSuccessWithReturn(data);
  }}

  @override
  handleErrorWithReturn(dynamic error) {{
    if (error is DioException) {{
      if (error.response!.statusCode == 400) {{
        ToastUtil.showShortToast(error.response!.data["error"]);
      }} else {{
        ToastUtil.showShortToast(error.response!.data["message"]);
      }}
    }}
    log(error.toString());
    dataFetcher.sink.addError(error);
    return super.handleErrorWithReturn(error);
  }}
}}
"""

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    print("=" * 50)
    print("   Flutter API Boilerplate Generator")
    print("=" * 50)

    print("\n📁 Feature folder (e.g. profile, auth_screen): ", end="")
    feature_folder = to_snake_case(input().strip())

    print("📄 API name in snake_case (e.g. update_profile, post_login): ", end="")
    feature_snake = to_snake_case(input().strip())

    print("🔤 Class prefix in PascalCase (e.g. UpdateProfile, PostLogin): ", end="")
    class_prefix = input().strip() or to_pascal_case(feature_snake)

    print("🌐 HTTP method (get / post / patch / put / delete): ", end="")
    method = input().strip().lower()

    print("📦 Parameters (comma separated, leave blank if none): ", end="")
    raw_params = input().strip()
    params = [p.strip() for p in raw_params.split(',')] if raw_params else []

    is_multipart = False
    if 'image' in params:
        print("📸 Image param detected — use multipart/form-data? (y/n): ", end="")
        is_multipart = input().strip().lower() == 'y'

    print("\n📂 Output folder path (leave blank for current directory): ", end="")
    output_root = input().strip() or "."

    # Create folder
    output_dir = os.path.join(output_root, feature_snake)
    os.makedirs(output_dir, exist_ok=True)

    # Generate files
    api_content = generate_api_file(method, feature_snake, class_prefix, method, params, is_multipart)
    rx_content = generate_rx_file(feature_snake, class_prefix, feature_folder, params)

    api_path = os.path.join(output_dir, f"{feature_snake}_api.dart")
    rx_path = os.path.join(output_dir, f"{feature_snake}_rx.dart")

    with open(api_path, 'w') as f:
        f.write(api_content)

    with open(rx_path, 'w') as f:
        f.write(rx_content)

    print("\n✅ Files generated:")
    print(f"   📄 {api_path}")
    print(f"   📄 {rx_path}")
    print(f"\n💡 Don't forget to add endpoint in Endpoints.{to_camel_case(feature_snake)}()")
    print("=" * 50)

if __name__ == "__main__":
    main()
