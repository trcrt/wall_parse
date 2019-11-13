# wall_parse
Allows to search posts and likes made by specified user in VK group. Supports multi-account parsing.

Requires config file with following format:
```json
{
	"access_tokens": ["vk_access_token"],
	"accounts": [["login", "password"]],
	"group_name": "vk_group_screen_name",
	"user_name": "screen_name_of_user_to_search_for",
	"need_parse_likes": false
}
```
