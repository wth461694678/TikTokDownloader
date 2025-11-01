# GitHub Actions 参数转换示例

## 原始命令行参数
```bash
--urls "https://www.douyin.com/user/self?from_tab_name=main&modal_id=7253355171290352955&showTab=favorite_collection" --storage-format csv --max-pages 3
```

## 转换为 GitHub Actions 参数

### 方式一：用于 comment 操作（采集评论）
```json
{
  "cookie": "your_cookie_here",
  "action": "comment", 
  "kwargs": "{\"urls\": \"https://www.douyin.com/user/self?from_tab_name=main&modal_id=7253355171290352955&showTab=favorite_collection\", \"storage_format\": \"csv\", \"max_pages\": 3}"
}
```

### 方式二：用于 detail 操作（获取作品详情）
```json
{
  "cookie": "your_cookie_here",
  "action": "detail",
  "kwargs": "{\"urls\": \"https://www.douyin.com/user/self?from_tab_name=main&modal_id=7253355171290352955&showTab=favorite_collection\", \"storage_format\": \"csv\", \"max_pages\": 3}"
}
```

### 方式三：用于 account 操作（获取账号作品）
```json
{
  "cookie": "your_cookie_here", 
  "action": "account",
  "kwargs": "{\"urls\": \"https://www.douyin.com/user/self?from_tab_name=main&modal_id=7253355171290352955&showTab=favorite_collection\", \"storage_format\": \"csv\", \"max_pages\": 3, \"account_tab\": \"favorite\"}"
}
```

## 推荐的 kwargs 参数（单独的JSON字符串）

根据URL中的 `showTab=favorite_collection`，推荐使用 account 操作：

```json
{"urls": "https://www.douyin.com/user/self?from_tab_name=main&modal_id=7253355171290352955&showTab=favorite_collection", "storage_format": "csv", "max_pages": 3, "account_tab": "favorite"}
```

## 完整的 GitHub Actions 调用参数

**cookie**: `your_actual_cookie_string`

**action**: `account`

**kwargs**: `{"urls": "https://www.douyin.com/user/self?from_tab_name=main&modal_id=7253355171290352955&showTab=favorite_collection", "storage_format": "csv", "max_pages": 3, "account_tab": "favorite"}`

## 注意事项

1. **Cookie 替换**: 将 `your_actual_cookie_string` 替换为实际的 Cookie 值
2. **URL 分析**: 该 URL 包含 `showTab=favorite_collection`，表示用户的收藏合集页面
3. **操作选择**: 建议使用 `account` 操作来获取账号的收藏内容
4. **JSON 转义**: 在 kwargs 中，双引号需要用反斜杠转义
5. **参数完整性**: 所有参数都已包含在 kwargs 中，便于 Python 脚本解析