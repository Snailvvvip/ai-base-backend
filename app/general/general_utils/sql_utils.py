import json
import re


# 将json字符串中的 \u00A0 全部去掉，\u00A0 表示 &nbsp，当这个字符存在的时候会导致无法将json字符串合法地解析为对象/字典
def format_json_string(json_str):
  json_str = re.sub(r'\u00A0', '', json_str)
  return json_str


# 将值转化为json字符串
def array_json_encoder(val):
  return json.dumps(val, ensure_ascii=False)


# 将json字符串转为数组
def array_json_decoder(val):
  try:
    return json.loads(val)
  except json.JSONDecodeError:
    return ""


# 将数组转为逗号连接的字符串
def array_string_encoder(val):
  return ",".join(val) if isinstance(val, list) else val


# 将逗号连接的字符串转换为数组
def array_string_decoder(val):
  return val.split(",") if isinstance(val, str) else val


# 值格式化类型arrayjson
MODULE_CONVERT_TYPE_ARRAY_JSON = 'arrayjson'
# 值格式化类型arraystring
MODULE_CONVERT_TYPE_ARRAY_STRING = 'arraystring'

# 转化工具
ConvertTypes = {
  "arrayjson": {
    "encode": array_json_encoder,
    "decode": array_json_decoder,
  },
  "arraystring": {
    "encode": array_string_encoder,
    "decode": array_string_decoder,
  }
}


# 根据module_config创建一个转化器
def create_convertor(config):
  convert_columns = [(col_name, col_config) for col_name, col_config in config["columns"].items() if col_config.get("convert")]

  # print('convert_columns ==>>', convert_columns)

  # 将值转化为字符串
  def encode_list(list_):
    if not len(convert_columns):
      return
    for item in list_:
      for col_name, col_config in convert_columns:
        if get_value(item, col_name, None) is not None:
          if not isinstance(item[col_name], str):
            item[col_name] = ConvertTypes[col_config["convert"]]["encode"](item[col_name])

  # 将字符串转化为值
  def decode_list(list_):
    if not len(convert_columns):
      return
    for item in list_:
      for col_name, col_config in convert_columns:
        if get_value(item, col_name, None) is not None:
          if isinstance(item[col_name], str):
            item[col_name] = ConvertTypes[col_config["convert"]]["decode"](item[col_name])

  return {
    "encode_list": encode_list,
    "decode_list": decode_list
  }


# 将驼峰命名转换为下划线命名
def to_line(hump_name: str) -> str:
  return re.sub(r'([A-Z])', r'_\1', hump_name).lower()


# 格式化字段信息
def format_columns(columns):
  # 通过驼峰命名找到字段信息
  hump_to_columns = {}
  # 通过下划线命名找到字段信息
  line_to_columns = {}

  for hump_name, col_config in columns.items():
    line_name = to_line(hump_name)
    query = get_value(col_config, "query", None) or f"t1.{line_name}"
    info = {
      **col_config,
      "hump_name": hump_name,
      "line_name": line_name,
      "query": query,
      "col_name": query.split('.')[1]
    }
    hump_to_columns[hump_name] = info
    line_to_columns[line_name] = info
  return {
    # 通过下划线命令查找列信息
    "hump_to_columns": hump_to_columns,
    # 通过驼峰命名查找列信息
    "line_to_columns": line_to_columns,
  }


# 通用的获取属性值的方法
def get_value(obj, attr_name, default=None):
  if isinstance(obj, dict):
    return obj.get(attr_name, default)
  else:
    return getattr(obj, attr_name, default)


# 获取值的sql查询语句
def get_value_sql(value, value_type, sql_values):
  if value_type == 'string' or value_type == 'number':
    sql_values.append(value)
    return '?'
  elif value_type == 'date':
    sql_values.append(value)
    return "str_to_date(?, '%%Y-%%m-%%d')"
  elif value_type == 'datetime':
    sql_values.append(value)
    return "str_to_date(?, '%%Y-%%m-%%d %%H:%%i:%%s')"
  elif value_type == 'time':
    sql_values.append(value)
    return "str_to_date(?, '%%H:%%i:%%s')";


def parse_env_content(env_content):
  """
  将.env文件内容解析为字典格式

  Args:
      env_content (str): .env文件的内容字符串

  Returns:
      dict: 包含所有环境变量的字典
  """
  config_dict = {}

  # 按行分割内容
  lines = env_content.strip().split('\n')

  # 定义注释和值的正则表达式
  pattern = r'^([^=#]+)=([^#]*)(?:#.*)?$'

  for line in lines:
    line = line.strip()
    if line and not line.startswith('#'):  # 忽略空行和纯注释行
      match = re.match(pattern, line)
      if match:
        key = match.group(1).strip()
        value = match.group(2).strip()
        # 移除可能存在的引号
        if value.startswith('"') and value.endswith('"'):
          value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
          value = value[1:-1]
        config_dict[key] = value

  return config_dict


show_sql = True


# 一个用于打印sql的工具函数
def log_sql(sql, values):
  if show_sql:
    print("\n/*---------------------------------------log sql-------------------------------------------*/\n")
    print("\nsource sql-->>\n")
    print(sql)
    print("\nsql params-->>\n")
    print(values)
    count = 0

    def replace_callback(match):
      nonlocal count
      val = values[count]
      count = count + 1
      if isinstance(val, str):
        return val
      if isinstance(val, list):
        return ', '.join(map(str, val))
      # formatDebugData 要加上''，不然有些关键词没有''当做字符串的话会报错
      return f"'{str(val)}'"

    import re
    target_sql = re.sub(r'\?+', replace_callback, sql)
    print("\ntarget sql-->>\n")
    print(target_sql)
    print("\n")
